import datetime as dt

import pytest

from pipeline import consultas
from pipeline.carga import inserir_vendas
from pipeline.limpeza import limpar

TODAS = ["Norte", "Sul"]
INICIO, FIM = dt.date(2026, 1, 1), dt.date(2026, 12, 31)


@pytest.fixture
def banco(conn, fazer_df, linha_ok):
    """5 vendas com conta feita à mão.

    jan  Sul   Ana    Caneta  2 x 10,00           = 20,00
    jan  Sul   Bruno  Caderno 1 x 50,00 (-10%)    = 45,00
    jan  Norte Carla  Caneta  3 x  5,50           = 16,50
    fev  Sul   Ana    Mochila 1 x 100,00          = 100,00
    fev  Norte Carla  Caneta  1 x  4,00           =  4,00
    total = 185,50 | jan = 81,50 | fev = 104,00
    """
    def v(**kw):
        return dict(linha_ok, **kw)
    linhas = [
        v(data="05/01/2026", produto="Caneta", regiao="Sul", vendedor="Ana", quantidade="2", preco_unitario="10,00", desconto="0"),
        v(data="20/01/2026", produto="Caderno", regiao="Sul", vendedor="Bruno", quantidade="1", preco_unitario="50,00", desconto="10"),
        v(data="25/01/2026", produto="Caneta", regiao="Norte", vendedor="Carla", quantidade="3", preco_unitario="5,50", desconto="0"),
        v(data="02/02/2026", produto="Mochila", regiao="Sul", vendedor="Ana", quantidade="1", preco_unitario="100,00", desconto="0"),
        v(data="10/02/2026", produto="Caneta", regiao="Norte", vendedor="Carla", quantidade="1", preco_unitario="4,00", desconto="0"),
    ]
    limpo, _ = limpar(fazer_df(linhas))
    inserir_vendas(conn, limpo, "teste")
    conn.commit()
    return conn


def test_kpis_batem_com_a_conta_manual(banco):
    k = consultas.kpis(banco, INICIO, FIM, TODAS)
    assert k["receita_total"] == pytest.approx(185.50)
    assert k["vendas"] == 5
    assert k["itens"] == 8
    assert k["ticket_medio"] == pytest.approx(185.50 / 5)


def test_filtro_de_regiao_e_periodo(banco):
    assert consultas.kpis(banco, INICIO, FIM, ["Norte"])["receita_total"] == pytest.approx(20.50)
    so_jan = consultas.kpis(banco, INICIO, dt.date(2026, 1, 31), TODAS)
    assert so_jan["receita_total"] == pytest.approx(81.50)


def test_sem_vendas_no_filtro_devolve_zero(banco):
    k = consultas.kpis(banco, INICIO, FIM, ["Leste"])
    assert k["vendas"] == 0 and k["receita_total"] == 0


def test_receita_por_mes_com_variacao_e_acumulado(banco):
    df = consultas.receita_por_mes(banco, INICIO, FIM, TODAS)
    assert list(df["mes"]) == ["2026-01", "2026-02"]
    assert list(df["receita"]) == pytest.approx([81.50, 104.00])
    assert df["variacao"].iloc[1] == pytest.approx(22.50)          # LAG
    assert list(df["acumulado"]) == pytest.approx([81.50, 185.50])  # soma acumulada


def test_top_produtos_usa_join_com_categoria(banco):
    df = consultas.top_produtos(banco, INICIO, FIM, TODAS)
    assert list(df["produto"]) == ["Mochila", "Caderno", "Caneta"]
    assert df.set_index("produto").loc["Caneta", "receita"] == pytest.approx(40.50)
    assert df.set_index("produto").loc["Mochila", "categoria"] == "Acessórios"


def test_receita_por_categoria(banco):
    df = consultas.receita_por_categoria(banco, INICIO, FIM, TODAS).set_index("categoria")
    assert df.loc["Papelaria", "receita"] == pytest.approx(85.50)   # caneta + caderno
    assert df.loc["Acessórios", "receita"] == pytest.approx(100.00)


def test_ranking_de_vendedores_por_regiao(banco):
    df = consultas.ranking_vendedores(banco, INICIO, FIM, TODAS)
    sul = df[df["regiao"] == "Sul"].set_index("vendedor")
    assert sul.loc["Ana", "posicao"] == 1 and sul.loc["Ana", "receita"] == pytest.approx(120.00)
    assert sul.loc["Bruno", "posicao"] == 2
    norte = df[df["regiao"] == "Norte"]
    assert list(norte["vendedor"]) == ["Carla"] and int(norte["posicao"].iloc[0]) == 1


def test_a_soma_das_partes_e_igual_ao_total(banco):
    total = consultas.kpis(banco, INICIO, FIM, TODAS)["receita_total"]
    for df in (consultas.receita_por_mes(banco, INICIO, FIM, TODAS),
               consultas.receita_por_categoria(banco, INICIO, FIM, TODAS),
               consultas.ranking_vendedores(banco, INICIO, FIM, TODAS)):
        assert df["receita"].sum() == pytest.approx(total)

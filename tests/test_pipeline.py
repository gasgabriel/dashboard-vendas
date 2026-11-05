import pytest

from pipeline.executar import executar
from pipeline.extracao import ErroDeExtracao


def contar(conn, tabela):
    return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def test_fluxo_completo_e_registro_da_execucao(conn, tmp_path, escrever_csv, linha_ok):
    escrever_csv([linha_ok, dict(linha_ok, produto="Caderno", quantidade="1")], pasta=tmp_path / "d")
    resultado = executar(tmp_path / "d", "", conn=conn)

    assert contar(conn, "vendas") == 2
    status = conn.execute("SELECT status FROM execucoes").fetchone()[0]
    assert status == "ok"
    carga = resultado["cargas"][0]
    assert (carga["lidas"], carga["usadas"], carga["inseridas"]) == (2, 2, 2)


def test_rodar_duas_vezes_nao_duplica(conn, tmp_path, escrever_csv, linha_ok):
    escrever_csv([linha_ok], pasta=tmp_path / "d")
    executar(tmp_path / "d", "", conn=conn)
    segunda = executar(tmp_path / "d", "", conn=conn)
    assert contar(conn, "vendas") == 1
    assert segunda["cargas"][0]["inseridas"] == 0
    assert contar(conn, "execucoes") == 2


def test_a_mesma_venda_em_duas_fontes_conta_uma_vez(conn, tmp_path, escrever_csv, linha_ok,
                                                      servidor_http):
    web, base = servidor_http
    (web / "p.csv").write_text(
        'Data,Produto,Região,Vendedor,Qtd,Preço,Desconto (%)\n'
        '15/03/2026, caneta ,Sul,Ana,2,"3,5",10\n', encoding="utf-8")   # mesma venda, texto sujo
    escrever_csv([linha_ok], pasta=tmp_path / "d")
    executar(tmp_path / "d", f"{base}/p.csv", conn=conn)
    assert contar(conn, "vendas") == 1


def test_falha_na_planilha_desfaz_tudo_e_registra_o_erro(conn, tmp_path, escrever_csv, linha_ok,
                                                          servidor_http):
    _, base = servidor_http
    escrever_csv([linha_ok], pasta=tmp_path / "d")
    with pytest.raises(ErroDeExtracao):
        executar(tmp_path / "d", f"{base}/nao_existe.csv", conn=conn, tentativas=1, espera=0)

    assert contar(conn, "vendas") == 0                  # nada ficou pela metade
    status, mensagem = conn.execute("SELECT status, mensagem FROM execucoes").fetchone()
    assert status == "erro" and "baixar" in mensagem    # mas o erro ficou registrado


def test_pasta_sem_fontes_registra_erro(conn, tmp_path):
    with pytest.raises(ErroDeExtracao):
        executar(tmp_path / "vazia", "", conn=conn)
    assert conn.execute("SELECT status FROM execucoes").fetchone()[0] == "erro"
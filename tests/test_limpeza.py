import pytest

from pipeline.limpeza import limpar


def test_calcula_receita_com_desconto(fazer_df, linha_ok):
    df, _ = limpar(fazer_df([linha_ok]))
    # 2 x 3,50 com 10% de desconto = 6,30
    assert df["receita"].iloc[0] == pytest.approx(6.30)


def test_remove_linhas_repetidas(fazer_df, linha_ok):
    df, resumo = limpar(fazer_df([linha_ok, dict(linha_ok)]))
    assert len(df) == 1
    assert resumo.duplicadas == 1


def test_repetida_so_na_caixa_ou_nos_espacos_tambem_conta(fazer_df, linha_ok):
    outra = dict(linha_ok, produto="  caneta ")
    df, resumo = limpar(fazer_df([linha_ok, outra]))
    assert len(df) == 1
    assert resumo.duplicadas == 1


@pytest.mark.parametrize("texto", ["15/03/2026", "2026-03-15", " 15/03/2026 "])
def test_aceita_os_dois_formatos_de_data(fazer_df, linha_ok, texto):
    df, _ = limpar(fazer_df([dict(linha_ok, data=texto)]))
    assert df["data"].iloc[0].strftime("%Y-%m-%d") == "2026-03-15"


@pytest.mark.parametrize("campo, valor, contador", [
    ("data", "31/02/2026", "data_invalida"),
    ("data", "", "data_invalida"),
    ("quantidade", "", "quantidade_invalida"),
    ("quantidade", "0", "quantidade_invalida"),
    ("quantidade", "-3", "quantidade_invalida"),
    ("quantidade", "dois", "quantidade_invalida"),
    ("quantidade", "1,5", "quantidade_invalida"),
    ("preco_unitario", "abc", "preco_invalido"),
    ("preco_unitario", "-1", "preco_invalido"),
    ("desconto", "150", "desconto_invalido"),
    ("desconto", "-5", "desconto_invalido"),
    ("desconto", "muito", "desconto_invalido"),
])
def test_descarta_linha_invalida_e_conta_o_motivo(fazer_df, linha_ok, campo, valor, contador):
    df, resumo = limpar(fazer_df([linha_ok, dict(linha_ok, vendedor="Bia", **{campo: valor})]))
    assert len(df) == 1
    assert getattr(resumo, contador) == 1
    assert resumo.descartadas == 1


def test_desconto_vazio_vale_zero(fazer_df, linha_ok):
    df, resumo = limpar(fazer_df([dict(linha_ok, desconto="")]))
    assert len(df) == 1
    assert df["desconto"].iloc[0] == 0
    assert resumo.desconto_invalido == 0


def test_padroniza_texto(fazer_df, linha_ok):
    df, _ = limpar(fazer_df([dict(linha_ok, produto="  caneta ", regiao="SUL")]))
    assert df["produto"].iloc[0] == "Caneta"
    assert df["regiao"].iloc[0] == "Sul"


def test_vendedor_vazio_vira_nao_informado(fazer_df, linha_ok):
    df, _ = limpar(fazer_df([dict(linha_ok, vendedor="")]))
    assert df["vendedor"].iloc[0] == "Não informado"


def test_nao_altera_o_dataframe_original(fazer_df, linha_ok):
    bruto = fazer_df([linha_ok])
    copia = bruto.copy()
    limpar(bruto)
    assert bruto.equals(copia)
import pytest

from pipeline.extracao import (COLUNAS, ErroDeExtracao, extrair, ler_arquivo_csv,
                               ler_planilha_url, padronizar_colunas)


def test_padroniza_nomes_de_colunas_de_planilha(fazer_df):
    import pandas as pd
    df = pd.DataFrame([["15/03/2026", "Caneta", "Sul", "Ana", "2", "3,5", "10"]],
                      columns=["Data", "Produto", "Região", "Vendedor", "Qtd", "Preço", "Desconto (%)"])
    assert list(padronizar_colunas(df, "x").columns) == COLUNAS


def test_coluna_faltando_diz_qual(fazer_df):
    df = fazer_df([]).drop(columns=["preco_unitario"])
    with pytest.raises(ErroDeExtracao, match="preco_unitario"):
        padronizar_colunas(df, "arquivo.csv")


def test_le_csv_local(escrever_csv, linha_ok):
    df = ler_arquivo_csv(escrever_csv([linha_ok]))
    assert len(df) == 1 and df["preco_unitario"].iloc[0] == "3,5"


def test_csv_vazio(tmp_path):
    vazio = tmp_path / "vazio.csv"
    vazio.write_text("", encoding="utf-8")
    with pytest.raises(ErroDeExtracao, match="vazio"):
        ler_arquivo_csv(vazio)


def test_le_planilha_por_http(servidor_http):
    pasta, base = servidor_http
    (pasta / "planilha.csv").write_text(
        'Data,Produto,Região,Vendedor,Qtd,Preço,Desconto (%)\n'
        '15/03/2026,Caneta,Sul,Ana,2,"3,5",10\n', encoding="utf-8")
    df = ler_planilha_url(f"{base}/planilha.csv")
    assert list(df.columns) == COLUNAS
    assert df["preco_unitario"].iloc[0] == "3,5"      # a vírgula do preço sobrevive


def test_planilha_inexistente_tenta_de_novo_e_desiste(servidor_http):
    _, base = servidor_http
    with pytest.raises(ErroDeExtracao, match="baixar"):
        ler_planilha_url(f"{base}/nao_existe.csv", tentativas=2, espera=0)


def test_extrair_junta_todas_as_fontes(tmp_path, escrever_csv, linha_ok, servidor_http):
    pasta, base = servidor_http
    (pasta / "p.csv").write_text(
        'Data,Produto,Região,Vendedor,Qtd,Preço,Desconto (%)\n'
        '16/03/2026,Caderno,Norte,Bia,1,"18,9",0\n', encoding="utf-8")
    dados = tmp_path / "dados"
    escrever_csv([linha_ok], "a.csv", pasta=dados)
    fontes = extrair(dados, f"{base}/p.csv")
    assert [origem for origem, _ in fontes] == ["a.csv", "planilha"]


def test_sem_nenhuma_fonte(tmp_path):
    with pytest.raises(ErroDeExtracao, match="Nenhuma fonte"):
        extrair(tmp_path / "vazia", "")
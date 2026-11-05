from decimal import Decimal

import psycopg
import pytest

from pipeline.carga import garantir_produtos, gerar_chave, inserir_vendas
from pipeline.limpeza import limpar


def test_chave_e_estavel_e_muda_com_os_dados():
    from datetime import date
    a = gerar_chave(date(2026, 3, 15), "Caneta", "Sul", "Ana", 2, 3.5, 10)
    assert a == gerar_chave(date(2026, 3, 15), "Caneta", "Sul", "Ana", 2, 3.5, 10)
    assert a != gerar_chave(date(2026, 3, 15), "Caneta", "Sul", "Ana", 3, 3.5, 10)


def test_insere_e_o_banco_calcula_a_receita(conn, fazer_df, linha_ok):
    limpo, _ = limpar(fazer_df([linha_ok]))
    assert inserir_vendas(conn, limpo, "teste.csv") == 1
    receita = conn.execute("SELECT receita FROM vendas").fetchone()[0]
    assert receita == Decimal("6.30")          # 2 x 3,50 com 10% de desconto


def test_inserir_de_novo_nao_duplica(conn, fazer_df, linha_ok):
    limpo, _ = limpar(fazer_df([linha_ok]))
    assert inserir_vendas(conn, limpo, "a.csv") == 1
    assert inserir_vendas(conn, limpo, "a.csv") == 0
    assert inserir_vendas(conn, limpo, "outra_fonte") == 0   # mesma venda, outra fonte
    assert conn.execute("SELECT COUNT(*) FROM vendas").fetchone()[0] == 1


def test_produto_novo_vira_categoria_outros(conn, fazer_df, linha_ok):
    limpo, _ = limpar(fazer_df([dict(linha_ok, produto="Lupa")]))
    inserir_vendas(conn, limpo, "a.csv")
    cat = conn.execute("SELECT categoria FROM produtos WHERE nome = 'Lupa'").fetchone()[0]
    assert cat == "Outros"


def test_produtos_conhecidos_recebem_a_categoria(conn):
    garantir_produtos(conn, ["Caneta", "Mochila"])
    cats = dict(conn.execute("SELECT nome, categoria FROM produtos").fetchall())
    assert cats == {"Caneta": "Papelaria", "Mochila": "Acessórios"}


@pytest.mark.parametrize("campo, valor", [
    ("quantidade", 0), ("quantidade", -1), ("preco_unitario", 0), ("desconto", 101),
])
def test_o_banco_rejeita_dados_impossiveis(conn, campo, valor):
    garantir_produtos(conn, ["Caneta"])
    dados = {"quantidade": 1, "preco_unitario": 3.5, "desconto": 0}
    dados[campo] = valor
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO vendas (chave, data, produto, regiao, vendedor, quantidade, "
            "preco_unitario, desconto, origem) VALUES ('k', '2026-01-01', 'Caneta', 'Sul', "
            "'Ana', %(quantidade)s, %(preco_unitario)s, %(desconto)s, 'x')", dados)


def test_o_banco_rejeita_produto_inexistente(conn):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO vendas (chave, data, produto, regiao, vendedor, quantidade, "
            "preco_unitario, origem) VALUES ('k', '2026-01-01', 'Fantasma', 'Sul', 'Ana', 1, 1, 'x')")
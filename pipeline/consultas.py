"""Consultas SQL que alimentam o painel. Todas respeitam o mesmo filtro."""
from decimal import Decimal

import pandas as pd

# período e regiões escolhidos no painel
FILTRO = "v.data BETWEEN %(inicio)s AND %(fim)s AND v.regiao = ANY(%(regioes)s)"

SQL_KPIS = f"""
SELECT COALESCE(SUM(v.receita), 0)    AS receita_total,
       COUNT(*)                       AS vendas,
       COALESCE(SUM(v.quantidade), 0) AS itens,
       COALESCE(AVG(v.receita), 0)    AS ticket_medio
FROM vendas v
WHERE {FILTRO}
"""

SQL_POR_MES = f"""
SELECT to_char(date_trunc('month', v.data), 'YYYY-MM') AS mes,
       SUM(v.receita) AS receita,
       SUM(v.receita) - LAG(SUM(v.receita)) OVER (ORDER BY date_trunc('month', v.data))
           AS variacao,
       SUM(SUM(v.receita)) OVER (ORDER BY date_trunc('month', v.data)) AS acumulado
FROM vendas v
WHERE {FILTRO}
GROUP BY date_trunc('month', v.data)
ORDER BY date_trunc('month', v.data)
"""

SQL_TOP_PRODUTOS = f"""
SELECT v.produto, p.categoria, SUM(v.receita) AS receita, SUM(v.quantidade) AS itens
FROM vendas v
JOIN produtos p ON p.nome = v.produto
WHERE {FILTRO}
GROUP BY v.produto, p.categoria
ORDER BY receita DESC
LIMIT 5
"""

SQL_POR_CATEGORIA = f"""
SELECT p.categoria, SUM(v.receita) AS receita
FROM vendas v
JOIN produtos p ON p.nome = v.produto
WHERE {FILTRO}
GROUP BY p.categoria
ORDER BY receita DESC
"""

SQL_RANKING_VENDEDORES = f"""
SELECT v.regiao, v.vendedor, SUM(v.receita) AS receita,
       RANK() OVER (PARTITION BY v.regiao ORDER BY SUM(v.receita) DESC) AS posicao
FROM vendas v
WHERE {FILTRO}
GROUP BY v.regiao, v.vendedor
ORDER BY v.regiao, posicao
"""

SQL_PERIODO = "SELECT MIN(data), MAX(data) FROM vendas"
SQL_REGIOES = "SELECT DISTINCT regiao FROM vendas ORDER BY regiao"
SQL_ULTIMA_EXECUCAO = "SELECT id, inicio, fim, status, mensagem FROM execucoes ORDER BY id DESC LIMIT 1"
SQL_CARGAS = ("SELECT origem, linhas_lidas, descartadas, usadas, inseridas "
              "FROM cargas WHERE execucao_id = %(id)s ORDER BY origem")


def _tabela(conn, sql: str, params=None) -> pd.DataFrame:
    """Executa o SQL e devolve um DataFrame (números do banco viram float)."""
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        colunas = [c.name for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=colunas)
    for coluna in df.columns:
        if len(df) and isinstance(df[coluna].iloc[0], Decimal):
            df[coluna] = df[coluna].astype(float)
    return df


def kpis(conn, inicio, fim, regioes) -> dict:
    df = _tabela(conn, SQL_KPIS, {"inicio": inicio, "fim": fim, "regioes": list(regioes)})
    return {k: float(v) for k, v in df.iloc[0].items()}


def receita_por_mes(conn, inicio, fim, regioes) -> pd.DataFrame:
    return _tabela(conn, SQL_POR_MES, {"inicio": inicio, "fim": fim, "regioes": list(regioes)})


def top_produtos(conn, inicio, fim, regioes) -> pd.DataFrame:
    return _tabela(conn, SQL_TOP_PRODUTOS, {"inicio": inicio, "fim": fim, "regioes": list(regioes)})


def receita_por_categoria(conn, inicio, fim, regioes) -> pd.DataFrame:
    return _tabela(conn, SQL_POR_CATEGORIA, {"inicio": inicio, "fim": fim, "regioes": list(regioes)})


def ranking_vendedores(conn, inicio, fim, regioes) -> pd.DataFrame:
    return _tabela(conn, SQL_RANKING_VENDEDORES, {"inicio": inicio, "fim": fim, "regioes": list(regioes)})


def periodo_disponivel(conn):
    with conn.cursor() as cur:
        cur.execute(SQL_PERIODO)
        return cur.fetchone()


def regioes_disponiveis(conn) -> list:
    return list(_tabela(conn, SQL_REGIOES)["regiao"])


def ultima_execucao(conn):
    df = _tabela(conn, SQL_ULTIMA_EXECUCAO)
    return None if df.empty else df.iloc[0].to_dict()


def cargas_da_execucao(conn, exec_id: int) -> pd.DataFrame:
    return _tabela(conn, SQL_CARGAS, {"id": exec_id})
"""Carga: grava as vendas limpas no PostgreSQL, sem nunca duplicar."""
import hashlib
import logging
import time
from decimal import Decimal
from pathlib import Path

import pandas as pd
import psycopg

from . import config

log = logging.getLogger(__name__)

SCHEMA = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

SQL_INSERIR_VENDA = """
INSERT INTO vendas (chave, data, produto, regiao, vendedor,
                    quantidade, preco_unitario, desconto, origem)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (chave) DO NOTHING
"""


def conectar(url=None, tentativas: int = 15, espera: float = 2.0):
    """Conecta ao banco, tentando de novo enquanto ele ainda está subindo."""
    url = url or config.database_url()
    for n in range(1, tentativas + 1):
        try:
            return psycopg.connect(url)
        except psycopg.OperationalError:
            if n == tentativas:
                raise
            log.info("Banco ainda não respondeu (%s de %s). Aguardando...", n, tentativas)
            time.sleep(espera)


def criar_tabelas(conn) -> None:
    conn.execute(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()


def gerar_chave(data, produto, regiao, vendedor, quantidade, preco, desconto) -> str:
    """Identificador estável da venda: os mesmos dados dão sempre a mesma chave."""
    texto = "|".join([
        data.strftime("%Y-%m-%d"), produto, regiao, vendedor,
        str(int(quantidade)), f"{preco:.2f}", f"{desconto:.2f}",
    ])
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()


def garantir_produtos(conn, nomes) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO produtos (nome, categoria) VALUES (%s, %s) "
            "ON CONFLICT (nome) DO NOTHING",
            [(n, config.CATEGORIAS.get(n, "Outros")) for n in sorted(set(nomes))],
        )


def _dinheiro(valor: float) -> Decimal:
    return Decimal(str(round(float(valor), 2)))


def inserir_vendas(conn, df: pd.DataFrame, origem: str) -> int:
    """Insere as vendas que ainda não existem. Devolve quantas foram inseridas."""
    if df.empty:
        return 0
    garantir_produtos(conn, df["produto"])
    registros = [
        (gerar_chave(l.data, l.produto, l.regiao, l.vendedor,
                     l.quantidade, l.preco_unitario, l.desconto),
         l.data.date(), l.produto, l.regiao, l.vendedor, int(l.quantidade),
         _dinheiro(l.preco_unitario), _dinheiro(l.desconto), origem)
        for l in df.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        antes = _contar(cur)
        cur.executemany(SQL_INSERIR_VENDA, registros)
        return _contar(cur) - antes


def _contar(cur) -> int:
    cur.execute("SELECT COUNT(*) FROM vendas")
    return cur.fetchone()[0]
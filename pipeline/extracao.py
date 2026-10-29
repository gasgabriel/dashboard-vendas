"""Extração: lê os CSVs de uma pasta e a planilha do Google (exportada como CSV)."""
import io
import logging
import time
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

COLUNAS = ["data", "produto", "regiao", "vendedor",
           "quantidade", "preco_unitario", "desconto"]

# como as colunas aparecem em planilhas reais -> nome padrão
SINONIMOS = {
    "data": "data",
    "produto": "produto",
    "regiao": "regiao", "região": "regiao",
    "vendedor": "vendedor", "vendedora": "vendedor",
    "quantidade": "quantidade", "qtd": "quantidade", "qtde": "quantidade",
    "preco_unitario": "preco_unitario", "preço": "preco_unitario",
    "preco": "preco_unitario", "preço unitário": "preco_unitario",
    "desconto": "desconto", "desconto (%)": "desconto",
}


class ErroDeExtracao(Exception):
    """Falha ao buscar ou entender uma fonte de dados."""


def padronizar_colunas(df: pd.DataFrame, origem: str) -> pd.DataFrame:
    """Renomeia as colunas para o nome padrão e confere se nenhuma falta."""
    novos = {c: SINONIMOS.get(str(c).strip().lower()) for c in df.columns}
    df = df.rename(columns={c: n for c, n in novos.items() if n})
    faltando = [c for c in COLUNAS if c not in df.columns]
    if faltando:
        raise ErroDeExtracao(f"{origem}: faltam colunas: {', '.join(faltando)}")
    return df[COLUNAS]


def ler_arquivo_csv(caminho: Path) -> pd.DataFrame:
    """CSV local: separador ';', UTF-8, tudo como texto."""
    try:
        df = pd.read_csv(caminho, sep=";", dtype=str, encoding="utf-8")
    except pd.errors.EmptyDataError:
        raise ErroDeExtracao(f"{caminho.name}: o arquivo está vazio") from None
    except UnicodeDecodeError:
        raise ErroDeExtracao(f"{caminho.name}: salve o arquivo como UTF-8") from None
    return padronizar_colunas(df, caminho.name)


def ler_planilha_url(url: str, tentativas: int = 3, espera: float = 1.0,
                     timeout: float = 15) -> pd.DataFrame:
    """Baixa o CSV da planilha (separador ',') com timeout e novas tentativas."""
    for n in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, timeout=timeout)
            resposta.raise_for_status()
            break
        except requests.RequestException as erro:
            log.warning("Planilha: tentativa %s de %s falhou (%s)", n, tentativas, erro)
            if n == tentativas:
                raise ErroDeExtracao(f"Não consegui baixar a planilha: {erro}") from erro
            time.sleep(espera * n)
    resposta.encoding = "utf-8"
    try:
        df = pd.read_csv(io.StringIO(resposta.text), sep=",", dtype=str)
    except pd.errors.EmptyDataError:
        raise ErroDeExtracao("planilha: o conteúdo está vazio") from None
    return padronizar_colunas(df, "planilha")


def extrair(pasta: Path, url: str = "", **opcoes_http):
    """Devolve uma lista de (origem, DataFrame) com todas as fontes."""
    fontes = []
    for caminho in sorted(Path(pasta).glob("*.csv")):
        fontes.append((caminho.name, ler_arquivo_csv(caminho)))
    if url:
        fontes.append(("planilha", ler_planilha_url(url, **opcoes_http)))
    if not fontes:
        raise ErroDeExtracao(f"Nenhuma fonte encontrada em {pasta} e nenhuma URL configurada")
    return fontes
"""Limpeza dos dados."""
from dataclasses import dataclass

import pandas as pd

NAO_INFORMADO = "Não informado"


@dataclass
class ResumoLimpeza:
    """Quantas linhas entraram, quantas saíram e por quê."""
    linhas_lidas: int = 0
    duplicadas: int = 0
    data_invalida: int = 0
    quantidade_invalida: int = 0
    preco_invalido: int = 0
    desconto_invalido: int = 0
    linhas_usadas: int = 0

    @property
    def descartadas(self) -> int:
        return self.linhas_lidas - self.linhas_usadas


def _texto(serie: pd.Series) -> pd.Series:
    """Tira espaços, padroniza a caixa e troca vazio por 'Não informado'."""
    limpo = serie.astype("string").str.strip().str.title()
    return limpo.mask(limpo.isna() | (limpo == ""), NAO_INFORMADO).astype(object)


def _numero(serie: pd.Series) -> pd.Series:
    """Converte texto em número aceitando vírgula decimal."""
    texto = serie.astype("string").str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(texto, errors="coerce").astype("float64")


def _datas(serie: pd.Series) -> pd.Series:
    """Aceita dd/mm/aaaa e aaaa-mm-dd."""
    s = serie.astype("string").str.strip()
    br = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    return br.fillna(iso)


def limpar(bruto: pd.DataFrame):
    """Devolve (dados_limpos, resumo)."""
    resumo = ResumoLimpeza(linhas_lidas=len(bruto))
    df = bruto.copy()

    for coluna in ("produto", "regiao", "vendedor"):
        df[coluna] = _texto(df[coluna])

    # 1. linhas repetidas (depois de padronizar o texto)
    antes = len(df)
    df = df.drop_duplicates()
    resumo.duplicadas = antes - len(df)

    # 2. conversões
    df["data"] = _datas(df["data"])
    df["quantidade"] = _numero(df["quantidade"])
    df["preco_unitario"] = _numero(df["preco_unitario"])
    desconto_vazio = (df["desconto"].isna()
                      | (df["desconto"].astype("string").str.strip() == ""))
    df["desconto"] = _numero(df["desconto"])

    # 3. regras de validade (uma linha pode quebrar mais de uma regra)
    data_ruim = df["data"].isna()
    qtd_ruim = (df["quantidade"].isna() | (df["quantidade"] <= 0)
                | (df["quantidade"] % 1 != 0))
    preco_ruim = df["preco_unitario"].isna() | (df["preco_unitario"] <= 0)
    # desconto vazio vale 0; texto que não é número ou fora de 0 a 100 é inválido
    desconto_ruim = ~desconto_vazio & (df["desconto"].isna()
                                       | (df["desconto"] < 0) | (df["desconto"] > 100))
    df["desconto"] = df["desconto"].where(~desconto_vazio, 0)

    resumo.data_invalida = int(data_ruim.sum())
    resumo.quantidade_invalida = int(qtd_ruim.sum())
    resumo.preco_invalido = int(preco_ruim.sum())
    resumo.desconto_invalido = int(desconto_ruim.sum())

    df = df[~(data_ruim | qtd_ruim | preco_ruim | desconto_ruim)].copy()
    df["quantidade"] = df["quantidade"].astype(int)

    # 4. coluna calculada
    df["receita"] = (df["quantidade"] * df["preco_unitario"]
                     * (1 - df["desconto"] / 100))

    resumo.linhas_usadas = len(df)
    return df.reset_index(drop=True), resumo

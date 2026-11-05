"""Formatação em pt-BR, sem depender da configuração do computador."""


def brl(valor: float) -> str:
    """1234.5 -> 'R$ 1.234,50'"""
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def inteiro(valor) -> str:
    return f"{int(valor):,}".replace(",", ".")
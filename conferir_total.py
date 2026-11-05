"""Conferência independente: recalcula quantidade de vendas e receita total
SEM pandas e SEM banco, só com a biblioteca padrão.

Uso: python conferir_total.py
Compare com: SELECT COUNT(*), SUM(receita) FROM vendas;
"""
import csv
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

SINONIMOS = {"data": "data", "produto": "produto", "regiao": "regiao", "região": "regiao",
             "vendedor": "vendedor", "quantidade": "quantidade", "qtd": "quantidade",
             "preco_unitario": "preco_unitario", "preço": "preco_unitario",
             "desconto": "desconto", "desconto (%)": "desconto"}


def ler(caminho, separador):
    with open(caminho, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f, delimiter=separador):
            yield {SINONIMOS[k.strip().lower()]: (v or "").strip()
                   for k, v in linha.items() if k.strip().lower() in SINONIMOS}


def data_valida(texto):
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    return None


vendas = {}   # chave -> receita (a mesma venda em duas fontes conta uma vez)
fontes = [(c, ";") for c in sorted(Path("dados").glob("*.csv"))]
fontes += [(c, ",") for c in sorted(Path("planilha").glob("*.csv"))]
for caminho, sep in fontes:
    for l in ler(caminho, sep):
        try:
            qtd = int(l["quantidade"])
            preco = Decimal(l["preco_unitario"].replace(",", "."))
            desc = Decimal(l["desconto"].replace(",", ".") or "0")
        except (ValueError, ArithmeticError):
            continue
        dia = data_valida(l["data"])
        if dia is None or qtd <= 0 or preco <= 0 or not 0 <= desc <= 100:
            continue
        chave = (dia, l["produto"].title(), l["regiao"].title(), l["vendedor"].title(),
                 qtd, preco.quantize(Decimal("0.01")), desc.quantize(Decimal("0.01")))
        receita = (qtd * preco * (1 - desc / 100)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        vendas[chave] = receita

print(f"Vendas distintas: {len(vendas)}")
print(f"Receita total:    {sum(vendas.values())}")
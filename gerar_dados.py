"""
A planilha simula o Google Sheets: separador vírgula, cabeçalhos diferentes
(Região, Qtd, Preço) e 25 vendas que já estão num dos CSVs (para testar duplicadas
entre fontes).

"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)  # mesma planilha toda vez: resultados reproduzíveis

PRODUTOS = {
    "Camiseta": 49.99,
    "Bermuda": 69.99,
    "Moletom": 119.99,
    "Regata": 49.99,
    "Jaqueta": 159.99,
    "Vestido": 79.99,
    "Saia": 69.99,
    "Shorts": 89.99,
    "Blusa": 79.99,
    "Meias": 19.99,
    "Bone": 39.99,
    "Cinto": 29.99
}
REGIOES = ["Norte", "Sul", "Centro-Oeste", "Sudeste", "Nordeste"]
VENDEDORES = ["Ana", "Bruno", "Carla", "Diego", "João"]
CAMPOS = ["data", "produto", "regiao", "vendedor", "quantidade",
          "preco_unitario", "desconto"]


def gerar_linhas(n, inicio, dias, sujeira=True):
    """n vendas entre `inicio` e `inicio + dias`, com sujeira de propósito."""
    linhas = []
    for i in range(n):
        dia = inicio + timedelta(days=random.randint(0, dias))
        produto = random.choice(list(PRODUTOS))
        linha = {
            "data": dia.strftime("%d/%m/%Y"),
            "produto": produto,
            "regiao": random.choice(REGIOES),
            "vendedor": random.choice(VENDEDORES),
            "quantidade": str(random.randint(1, 10)),
            "preco_unitario": str(PRODUTOS[produto]).replace(".", ","),
            "desconto": str(random.choice([0, 0, 0, 5, 10])),
        }
        if sujeira:
            if i % 17 == 0:
                linha["data"] = dia.isoformat()          # outro formato de data
            if i % 29 == 0:
                linha["produto"] = f" {produto.lower()} "  # espaço e caixa
            if i % 23 == 0:
                linha["quantidade"] = ""                   # quantidade vazia
        linhas.append(linha)
    return linhas


def gravar_csv(caminho, linhas):
    caminho.parent.mkdir(exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} linhas em {caminho}")


def gravar_planilha(caminho, linhas):
    """Formato parecido com o de uma planilha do Google exportada em CSV."""
    caminho.parent.mkdir(exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)  # separador vírgula; campos com vírgula ficam entre aspas
        w.writerow(["Data", "Produto", "Região", "Vendedor", "Qtd", "Preço", "Desconto (%)"])
        for l in linhas:
            w.writerow([l["data"], l["produto"], l["regiao"], l["vendedor"],
                        l["quantidade"], l["preco_unitario"], l["desconto"]])
    print(f"{len(linhas)} linhas em {caminho}")


if __name__ == "__main__":
    jan_jun = gerar_linhas(600, date(2026, 1, 1), 180)
    jul_set = gerar_linhas(600, date(2026, 7, 1), 91)
    novas = gerar_linhas(275, date(2026, 9, 20), 22)

    # 25 vendas "limpas" de jul_set que também aparecem na planilha
    limpas = [l for l in jul_set
              if l["produto"] in PRODUTOS and l["quantidade"].isdigit()]
    repetidas = random.sample(limpas, 25)

    gravar_csv(Path("dados/vendas_jan_jun.csv"), jan_jun)
    gravar_csv(Path("dados/vendas_jul_set.csv"), jul_set)
    gravar_planilha(Path("planilha/planilha_filial.csv"), novas + repetidas)
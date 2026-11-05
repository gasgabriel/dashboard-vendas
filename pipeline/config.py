"""Configuração lida de variáveis de ambiente (nunca coloque senhas no código)."""
import os
from pathlib import Path

# categoria de cada produto (produto novo, que não está aqui, vira "Outros")
CATEGORIAS = {
    "Caneta": "Papelaria",
    "Caderno": "Papelaria",
    "Mochila": "Acessórios",
    "Garrafa": "Acessórios",
    "Fone": "Eletrônicos",
}


def database_url() -> str:
    return os.environ.get("DATABASE_URL",
                          "postgresql://vendas:vendas@localhost:5432/vendas")


def pasta_dados() -> Path:
    return Path(os.environ.get("PASTA_DADOS", "dados"))


def url_planilha() -> str:
    return os.environ.get("URL_PLANILHA", "").strip()
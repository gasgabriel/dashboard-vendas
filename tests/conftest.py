import functools
import threading
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

import pandas as pd
import psycopg
import pytest

from pipeline import config
from pipeline.carga import criar_tabelas

COLUNAS = ["data", "produto", "regiao", "vendedor",
           "quantidade", "preco_unitario", "desconto"]


@pytest.fixture
def linha_ok():
    """Uma venda válida, como o CSV entrega: tudo texto."""
    return {"data": "15/03/2026", "produto": "Caneta", "regiao": "Sul",
            "vendedor": "Ana", "quantidade": "2", "preco_unitario": "3,5",
            "desconto": "10"}


@pytest.fixture
def fazer_df():
    def _fazer(linhas):
        return pd.DataFrame(linhas, columns=COLUNAS, dtype=str)
    return _fazer


@pytest.fixture
def escrever_csv(tmp_path):
    """Escreve um CSV (separador ';') numa pasta de teste e devolve o caminho."""
    def _escrever(linhas, nome="vendas.csv", pasta=None):
        pasta = pasta or tmp_path
        pasta.mkdir(exist_ok=True)
        caminho = pasta / nome
        corpo = "\n".join(";".join(str(l[c]) for c in COLUNAS) for l in linhas)
        caminho.write_text(";".join(COLUNAS) + "\n" + corpo + "\n", encoding="utf-8")
        return caminho
    return _escrever


@pytest.fixture
def url_banco():
    """URL de um schema novo e vazio, só deste teste. Some no final."""
    url_base = config.database_url()
    schema = "teste_" + uuid.uuid4().hex[:8]
    try:
        admin = psycopg.connect(url_base, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("sem PostgreSQL disponível (suba com: docker compose up -d db)")
    admin.execute(f"CREATE SCHEMA {schema}")
    separador = "&" if "?" in url_base else "?"
    url = f"{url_base}{separador}options={quote('-c search_path=' + schema)}"
    with psycopg.connect(url) as conn:
        criar_tabelas(conn)
    yield url
    admin.execute(f"DROP SCHEMA {schema} CASCADE")
    admin.close()


@pytest.fixture
def conn(url_banco):
    with psycopg.connect(url_banco) as c:
        yield c


@pytest.fixture
def servidor_http(tmp_path):
    """Servidor HTTP local servindo uma pasta: simula a planilha do Google."""
    pasta = tmp_path / "web"
    pasta.mkdir()
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(pasta))
    handler.log_message = lambda *a, **k: None
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield pasta, f"http://127.0.0.1:{servidor.server_address[1]}"
    servidor.shutdown()
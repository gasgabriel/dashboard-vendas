from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from pipeline.executar import executar  # noqa: E402

import streamlit as st  # noqa: E402


@pytest.fixture(autouse=True)
def limpar_cache():
    """O painel guarda resultados em cache por 60 s; cada teste começa do zero."""
    st.cache_data.clear()


APP = str(Path(__file__).resolve().parent.parent / "painel" / "app.py")


def test_painel_mostra_os_numeros(url_banco, conn, tmp_path, escrever_csv, linha_ok, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url_banco)
    escrever_csv([linha_ok, dict(linha_ok, produto="Caderno", quantidade="1",
                                 preco_unitario="50,00", desconto="0")], pasta=tmp_path / "d")
    executar(tmp_path / "d", "", conn=conn)

    app = AppTest.from_file(APP, default_timeout=30).run()

    assert not app.exception
    valores = {m.label: m.value for m in app.metric}
    assert valores["Receita total"] == "R$ 56,30"   # 6,30 + 50,00
    assert valores["Vendas"] == "2"


def test_painel_avisa_quando_nao_ha_dados(url_banco, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url_banco)
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    assert "Ainda não há dados" in app.warning[0].value
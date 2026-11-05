"""Teste com os dados de exemplo de verdade (rode antes: python gerar_dados.py)."""
import subprocess
import sys
from pathlib import Path

import pytest

from pipeline import consultas
from pipeline.executar import executar

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def carregado(conn, servidor_http):
    if not (RAIZ / "dados").exists() or not list((RAIZ / "dados").glob("*.csv")):
        pytest.skip("rode primeiro: python gerar_dados.py")
    web, base = servidor_http
    (web / "planilha_filial.csv").write_bytes((RAIZ / "planilha" / "planilha_filial.csv").read_bytes())
    executar(RAIZ / "dados", f"{base}/planilha_filial.csv", conn=conn)
    return conn


def conferencia_independente():
    script = RAIZ / "tests" / "conferir_total.py"

    saida = subprocess.run(
        [sys.executable, str(script)],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    valores = dict(
        linha.split(":", 1)
        for linha in saida.strip().splitlines()
    )

    return (
        int(valores["Vendas distintas"]),
        float(valores["Receita total"]),
    )


def test_banco_e_conferencia_independente_concordam(carregado):
    vendas, receita = conferencia_independente()
    no_banco = carregado.execute("SELECT COUNT(*), SUM(receita) FROM vendas").fetchone()
    assert no_banco[0] == vendas
    assert float(no_banco[1]) == pytest.approx(receita)


def test_painel_e_banco_mostram_o_mesmo_total(carregado):
    inicio, fim = consultas.periodo_disponivel(carregado)
    regioes = consultas.regioes_disponiveis(carregado)
    k = consultas.kpis(carregado, inicio, fim, regioes)
    total = float(carregado.execute("SELECT SUM(receita) FROM vendas").fetchone()[0])
    assert k["receita_total"] == pytest.approx(total)
    assert consultas.receita_por_mes(carregado, inicio, fim, regioes)["receita"].sum() == pytest.approx(total)


def test_rodar_de_novo_nao_muda_nada(carregado, servidor_http):
    antes = carregado.execute("SELECT COUNT(*) FROM vendas").fetchone()[0]
    executar(RAIZ / "dados", "", conn=carregado)
    assert carregado.execute("SELECT COUNT(*) FROM vendas").fetchone()[0] == antes


def test_numeros_conhecidos_dos_dados_de_exemplo(carregado):
    n, soma = carregado.execute("SELECT COUNT(*), SUM(receita) FROM vendas").fetchone()
    assert n == 1409
    assert float(soma) == pytest.approx(536435.73)
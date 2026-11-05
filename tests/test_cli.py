from pipeline.cli import main


def test_cli_roda_e_devolve_0(url_banco, monkeypatch, tmp_path, escrever_csv, linha_ok):
    monkeypatch.setenv("DATABASE_URL", url_banco)
    escrever_csv([linha_ok], pasta=tmp_path / "d")
    assert main(["--pasta", str(tmp_path / "d")]) == 0


def test_cli_sem_fontes_devolve_1_e_explica(url_banco, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DATABASE_URL", url_banco)
    assert main(["--pasta", str(tmp_path / "nada")]) == 1
    assert "Nenhuma fonte" in capsys.readouterr().err
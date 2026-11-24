import pytest

from rpa_conciliacao.cli import main


@pytest.mark.parametrize("valor", ["0", "-5"])
def test_vigiar_nao_positivo_devolve_2(valor, capsys, tmp_path):
    assert main(["robo", "--entrada", str(tmp_path), "--saida", str(tmp_path / "s"), "--vigiar", valor]) == 2
    assert "maior que 0" in capsys.readouterr().err


@pytest.mark.parametrize("extra", [["--vigiar", "1", "--ciclos", "0"], ["--vigiar", "1", "--ciclos", "-2"], ["--ciclos", "3"]])
def test_ciclos_invalido_ou_sem_vigiar_devolve_2(extra, capsys, tmp_path):
    assert main(["robo", "--entrada", str(tmp_path), "--saida", str(tmp_path / "s"), *extra]) == 2
    assert "--ciclos" in capsys.readouterr().err


@pytest.mark.parametrize("n", ["0", "-3"])
def test_demo_com_n_menor_que_1_devolve_2(n, capsys, tmp_path):
    assert main(["demo", "--entrada", str(tmp_path / "e"), "--n", n]) == 2
    assert "1 ou mais" in capsys.readouterr().err

"""O robô em si: vigia uma pasta de entrada, processa cada par de arquivos e arquiva o resultado."""

from __future__ import annotations

import csv
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

from .conciliar import conciliar, resumo
from .ofx import ler_ofx
from .relatorio import gerar_html

CAMPOS = ("id", "data", "descricao", "valor")


def ler_csv(caminho: Path, obrigatorias: tuple[str, ...]) -> list[dict]:
    """Lê CSV validando colunas e valores; erro claro em vez de resultado errado."""
    with caminho.open(encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        faltam = [c for c in obrigatorias if c not in (leitor.fieldnames or [])]
        if faltam:
            raise ValueError(f"{caminho.name}: faltam colunas {faltam}")
        linhas = []
        for n, linha in enumerate(leitor, start=2):
            try:
                linha["valor"] = float(str(linha["valor"]).replace(",", "."))
                datetime.strptime(linha["data"], "%Y-%m-%d")
            except ValueError as e:
                raise ValueError(f"{caminho.name} linha {n}: valor ou data inválidos ({e})") from e
            linhas.append(linha)
    return linhas


def escrever_csv(caminho: Path, linhas: list[dict], campos: tuple[str, ...]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)


def log(pasta: Path, evento: str, **dados) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    reg = {"quando": datetime.now().isoformat(timespec="seconds"), "evento": evento, **dados}
    with (pasta / "robo.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")


def processar_par(extrato_csv: Path, pedidos_csv: Path, saida: Path) -> dict:
    """Concilia um par de arquivos e grava CSVs por status + relatório HTML."""
    extrato = ler_ofx(extrato_csv) if extrato_csv.suffix.lower() == ".ofx" else ler_csv(extrato_csv, CAMPOS)
    pedidos = ler_csv(pedidos_csv, ("id", "cliente", "valor", "data"))
    res = conciliar(pedidos, extrato)
    sumario = resumo(res, pedidos)
    linhas = [
        {**r.lancamento, "status": r.status, "pedido_id": r.pedido_id or "", "motivo": r.motivo}
        for r in res
    ]
    campos = (*CAMPOS, "status", "pedido_id", "motivo")
    for status in ("conciliado", "revisar", "sem_pedido"):
        escrever_csv(saida / f"{status}.csv", [x for x in linhas if x["status"] == status], campos)
    (saida / "relatorio.html").write_text(gerar_html(res, sumario), encoding="utf-8")
    return sumario


def rodar_uma_vez(entrada: Path, saida: Path, tentativas: int = 2) -> list[dict]:
    """Procura pares `<nome>.extrato.csv` + `<nome>.pedidos.csv` na entrada.

    Sucesso: arquivos vão para `processados/`. Erro de formato: vão para `erros/` com o motivo no log,
    e o robô segue com os demais (um arquivo ruim não derruba o lote).
    """
    resultados = []
    extratos = [*entrada.glob("*.extrato.csv"), *entrada.glob("*.extrato.ofx")]
    for extrato in sorted(extratos):
        nome = extrato.name.removesuffix(".extrato.csv").removesuffix(".extrato.ofx")
        pedidos = entrada / f"{nome}.pedidos.csv"
        if not pedidos.exists():
            log(saida, "aguardando", lote=nome, motivo="falta o arquivo de pedidos")
            continue
        destino = saida / nome
        for tentativa in range(1, tentativas + 1):
            try:
                sumario = processar_par(extrato, pedidos, destino)
                arquivar(extrato, pedidos, saida / "processados")
                log(saida, "ok", lote=nome, **sumario)
                resultados.append({"lote": nome, **sumario})
                break
            except ValueError as e:  # formato inválido: repetir não adianta
                arquivar(extrato, pedidos, saida / "erros")
                log(saida, "erro", lote=nome, motivo=str(e))
                break
            except OSError as e:  # arquivo travado (ex.: aberto no Excel): tenta de novo
                log(saida, "tentativa", lote=nome, n=tentativa, motivo=str(e))
                if tentativa == tentativas:
                    log(saida, "erro", lote=nome, motivo=f"falhou após {tentativas} tentativas")
                else:
                    time.sleep(0.2)
    return resultados


def arquivar(extrato: Path, pedidos: Path, pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for arq in (extrato, pedidos):
        shutil.move(str(arq), str(pasta / arq.name))


def vigiar(entrada: Path, saida: Path, intervalo: float = 5.0, max_ciclos: int | None = None, dormir=time.sleep) -> int:
    """Roda `rodar_uma_vez` em ciclos, como um robô de verdade: chegou arquivo novo, processa.

    `max_ciclos=None` roda até Ctrl+C. Devolve quantos lotes foram processados no total.
    """
    total, ciclo = 0, 0
    log(saida, "vigia_inicio", intervalo=intervalo)
    try:
        while max_ciclos is None or ciclo < max_ciclos:
            total += len(rodar_uma_vez(entrada, saida))
            ciclo += 1
            if max_ciclos is None or ciclo < max_ciclos:
                dormir(intervalo)
    except KeyboardInterrupt:
        pass
    log(saida, "vigia_fim", ciclos=ciclo, lotes=total)
    return total

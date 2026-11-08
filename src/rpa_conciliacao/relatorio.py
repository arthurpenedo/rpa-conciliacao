"""Relatório HTML da conciliação (texto dos dados sempre escapado)."""

from __future__ import annotations

from html import escape

ROTULO = {"conciliado": "Conciliado", "revisar": "Revisar (humano)", "sem_pedido": "Sem pedido"}


def gerar_html(resultados, sumario: dict) -> str:
    linhas = "".join(
        f"<tr class='{r.status}'><td>{escape(r.lancamento['id'])}</td><td>{escape(r.lancamento['data'])}</td>"
        f"<td>{escape(r.lancamento['descricao'])}</td><td>{r.lancamento['valor']:.2f}</td>"
        f"<td>{ROTULO[r.status]}</td><td>{escape(r.pedido_id or '')}</td><td>{escape(r.motivo)}</td></tr>"
        for r in resultados
    )
    return (
        "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Conciliação</title>"
        "<style>body{font-family:sans-serif;margin:2rem}td,th{border:1px solid #ccc;padding:4px 8px}"
        "table{border-collapse:collapse}.revisar{background:#fff3cd}.sem_pedido{background:#f8d7da}</style>"
        f"<h1>Conciliação</h1><p>{sumario['conciliado']} conciliados, {sumario['revisar']} para revisar, "
        f"{sumario['sem_pedido']} sem pedido, {sumario['pedidos_sem_pagamento']} pedidos sem pagamento "
        f"(de {sumario['lancamentos']} lançamentos).</p>"
        "<table><tr><th>ID</th><th>Data</th><th>Descrição</th><th>Valor</th><th>Status</th><th>Pedido</th>"
        f"<th>Motivo</th></tr>{linhas}</table></html>"
    )

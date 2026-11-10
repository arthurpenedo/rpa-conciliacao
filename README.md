# rpa-conciliacao

Robô de conciliação em Python (RPA sem ferramenta paga): cruza o **extrato bancário** com os **pedidos** e separa
o que bateu sozinho do que precisa de um humano.

## O problema
Quem vende por PIX (como a By.penas, palha italiana gourmet) confere à mão cada pagamento contra cada pedido.
É o tipo de tarefa repetitiva que vagas de RPA/automação pedem (RPA/Power Automate aparece em 36% das vagas de
estágio coletadas pelo [radar-skills-br](https://arthurpenedo.github.io/radar-skills-br/)).

## O que faz
- **Pasta de entrada:** o robô procura pares `<lote>.extrato.csv` + `<lote>.pedidos.csv`.
- **Regras, em duas passadas:** (1) código do pedido na descrição + valor igual; (2) valor igual + pagamento até 5 dias
  depois do pedido + nome parecido (aceita "ANA S" para Ana Souza). Um pedido nunca é usado duas vezes.
- **Dúvida vai para humano:** nome bate mas o valor difere, ou mais de um pedido possível → `revisar.csv` com o motivo.
- **Robusto:** CSV inválido vai para `erros/` (o lote seguinte continua); arquivo travado tenta de novo; tudo em
  `robo.jsonl`; nada é apagado.
- **Saída:** `conciliado.csv`, `revisar.csv`, `sem_pedido.csv` e `relatorio.html`.

## Como rodar
```bash
pip install -e ".[dev]"
rpa-conciliacao demo     # gera um lote fictício em entrada/ (use --formato ofx para extrato em OFX)
rpa-conciliacao robo     # processa e grava em saida/
rpa-conciliacao medir    # precisão e cobertura com gabarito
pytest -q
```
Sem dependências além da biblioteca padrão. Dados 100% fictícios.

## Números medidos (`rpa-conciliacao medir`, dados sintéticos com gabarito)
| lote | precisão | cobertura |
|---|---|---|
| 60 pedidos, semente 7 | 100% (46 conciliados) | 100% |
| 200 pedidos, semente 1 | 100% (143) | 97,3% |
| 200 pedidos, semente 2 | 100% (155) | 98,7% |

Precisão = dos conciliados, quantos casaram com o pedido certo. Cobertura = dos lançamentos que tinham pedido,
quantos o robô conciliou. 27 testes passando.

## Limites honestos
Os dados são sintéticos e feitos junto com as regras: em extrato real o texto das descrições varia mais.
Por isso a regra é conservadora (na dúvida, revisar). Lê extrato em CSV e OFX (`<lote>.extrato.ofx`, versões 1.x e 2.x); não lê PDF nem acessa banco.

MIT.

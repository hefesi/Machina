# Machina local prototype 0.1

This is the first runnable user-facing prototype that connects three real
pieces of the repository:

1. **VirtualBrain** — executes and audits a durable cognitive cycle.
2. **MNN** — processes normalized input features and emits a diagnostic signal.
   The signal is not yet used as the semantic decision-maker.
3. **FragmentMemory** — persists memory fragments in SQLite, ranks an active
   view by priority, and keeps archived records rather than deleting low-priority
   information.

## Requirements

Python 3.12. From the repository root:

```bash
python -m pip install -e .
python -m examples.machina_prototype
```

To select a custom data directory:

```bash
python -m examples.machina_prototype --data-dir ./machina-data
```

## Commands

- `/remember MNN precisa preservar memórias importantes` — save a durable memory fragment.
- `/recall memoria importante` — retrieve active fragments sharing those tags.
- `/think Precisamos testar a memória persistente` — run a complete VirtualBrain cycle and display its MNN signal and audit result.
- `/status` — show memory count, local database paths, and the current MNN timestep.
- `/help` and `/quit`.

Data is written only to the selected local directory. To start over, stop the
program and manually remove that directory after backing up anything important.

## What works now

- Local interactive command loop.
- SQLite persistence for memory fragments and VirtualBrain event journal.
- Priority-aware active memory view with non-destructive archive.
- MNN feature pass included in the cognitive artifact.
- Durable cycle and audit output.
- Automated tests for restart persistence and cognitive-cycle integration.

## Honest limitations

The default cognition engine is a deterministic placeholder that acknowledges
the observation. This prototype does not include an LLM, broad natural-language
understanding, autonomous external actions, or evidence of consciousness/AGI.
The MNN signal is inspectable telemetry, not a semantic conclusion. The
prototype is intended to provide an executable foundation for iterative
experimentation, not to be presented as a finished intelligent assistant.


## Autonomia operacional — experimento inicial

O comando `/autonomy` deixa o sistema gerar um objetivo interno a partir do
estado atual, comparar alternativas por urgência, benefício esperado, confiança,
custo e risco, registrar a justificativa e iniciar um ciclo cognitivo sem uma
nova instrução do usuário.

A primeira política é deliberadamente simples e auditável. Ela pode propor
revisar memórias importantes, refletir sobre o progresso, analisar falhas ou
inspecionar o estado interno. Objetivos que exigem ações externas são recusados
por padrão; a implementação ainda não possui permissão implícita para operar
contas, redes, arquivos externos ou outros sistemas.

Isso demonstra **autonomia operacional limitada**, não livre-arbítrio comprovado.
A geração de objetivos usa regras explícitas e a execução final continua sendo
o executor local de reconhecimento. O próximo passo experimental é substituir
sinais manuais por métricas reais do histórico, testar persistência dos objetivos
e avaliar se a seleção melhora resultados em tarefas definidas.


## Autonomia v0.2 — memória de decisões e feedback

O protótipo mantém um diário SQLite separado (`autonomy.sqlite3`) com
objetivos selecionados e feedback explícito. Depois de `/autonomy`, use
`/goal-feedback success`, `/goal-feedback failure` ou
`/goal-feedback skip` para avaliar o último objetivo ainda sem avaliação.

Feedback de sucesso/falha ajusta de forma limitada a prioridade futura do tipo
de objetivo (`drive`). A seleção também aplica uma pequena penalidade à
repetição recente. Esses ajustes são persistentes após reiniciar o programa,
limitados a ±0,15 e não podem superar as barreiras de risco ou autorização.
`/status` mostra a quantidade de objetivos, avaliações e ajustes aprendidos.

O sistema não considera um ciclo técnico concluído como prova de que o objetivo
foi alcançado. A avaliação depende de feedback explícito; o mecanismo atual
aprende preferências simples de seleção, não habilidades gerais nem livre-arbítrio.


## Autonomia v0.3 — ciclo de vida persistente dos objetivos

O arquivo `persistent_goals.sqlite3` mantém objetivos ao longo de reinicializações.
Estados possíveis: `active`, `completed`, `paused`, `needs_revision` e
`abandoned`. Objetivos do mesmo tipo são reutilizados enquanto ativos; depois
de concluídos, uma nova ocorrência pode iniciar outro registro.

Comandos novos:

- `/goal-status` — listar objetivos e contadores.
- `/goal-status active` — filtrar por estado.
- `/goal-feedback success Evidência observável` — concluir o objetivo com evidência.
- `/goal-feedback failure Experimento não atingiu a métrica` — registrar falha; após
  três falhas consecutivas registradas, o objetivo passa a `needs_revision`.
- `/goal-feedback skip Aguardar dados` — pausar o objetivo.
- `/goal-resume reflect_on_progress` — reativar um objetivo pausado ou que precisa
  de revisão. O argumento usa o `goal_id`, não o ID numérico do registro.

As evidências são acumuladas no registro do objetivo. Falha repetida não é
interpretada como sucesso: ela solicita revisão. O estado `abandoned` está
disponível para uma futura decisão explícita de abandono, mas não é aplicado
automaticamente pela política atual.

Limitação importante: o executor ainda executa um ciclo cognitivo determinístico
de reconhecimento, não realiza pesquisa aberta nem comprova que o objetivo foi
alcançado. O status só muda com feedback explícito; persistência de objetivos é
continuidade operacional, não consciência nem AGI.

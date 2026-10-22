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
- `/goal-abandon reflect_on_progress Motivo observável` — abandonar explicitamente
  um objetivo aberto e anexar a justificativa ao histórico. A justificativa é obrigatória.

As evidências são acumuladas no registro do objetivo. Falha repetida não é
interpretada como sucesso: ela solicita revisão. O estado `abandoned` só é aplicado pelo comando explícito de abandono; a política
não descarta objetivos automaticamente.

Limitação importante: o executor ainda executa um ciclo cognitivo determinístico
de reconhecimento, não realiza pesquisa aberta nem comprova que o objetivo foi
alcançado. O status só muda com feedback explícito; persistência de objetivos é
continuidade operacional, não consciência nem AGI.


## Autonomia v0.4 — planejamento hierárquico persistente

O protótipo agora pode decompor um objetivo persistente em etapas ordenadas,
com dependências explícitas, armazenadas em `plans.sqlite3`. A primeira versão
usa decomposições transparentes para tipos de objetivo conhecidos e um plano
genérico para os demais. Isso é planejamento por templates, não um planejador
semântico geral.

Comandos:

- `/plan GOAL_RECORD_ID` — criar ou recuperar o plano de um objetivo aberto.
  Use o ID numérico do registro mostrado por `/goal-status`, não o `goal_id`.
- `/plans` ou `/plans active` — listar planos e etapas.
- `/plan-next PLAN_ID` — mostrar somente as etapas cujas dependências já foram concluídas.
- `/plan-feedback PLAN_ID STEP_ID success|failure|skip [evidência]` — avaliar uma etapa.
- `/plan-resume PLAN_ID` — retomar um plano pausado ou que requer revisão.

Cada etapa registra estado e evidência. Uma falha pausa o avanço e marca o plano
para revisão; `resume` reabre a etapa que falhou, preservando as etapas concluídas.
Uma etapa pulada pausa o plano até que seja retomado. O plano só fica concluído
quando todas as etapas tiverem sido explicitamente avaliadas como sucesso.

Exemplo de fluxo:

1. `/autonomy`
2. `/goal-status` — identificar o ID numérico do objetivo criado.
3. `/plan 1` — substituir `1` pelo ID real do objetivo.
4. `/plan-next 1` — substituir `1` pelo ID do plano retornado.
5. Avaliar a etapa retornada usando `/plan-feedback`, incluindo evidência.
6. Repetir `/plan-next` e a avaliação para avançar pelas dependências.

Limitações: o protótipo ainda não executa automaticamente cada etapa nem realiza
pesquisa aberta. O usuário ou um avaliador externo fornece o resultado explícito.
Isso cria continuidade e estrutura de planejamento auditável, mas não demonstra
por si só raciocínio geral, consciência ou AGI.

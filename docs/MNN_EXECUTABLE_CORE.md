# MNN executable core (experimental)

Machina now contains a runnable, stateful graph substrate and an optional
adapter into the VirtualBrain cognitive cycle. This is an experimental
research implementation, not evidence of general intelligence.

## Core model

- **Unit**: stable ID, bias, activation function, and current state.
- **Connection**: directed edge with a bounded weight and enabled flag.
- **State transition**: `MNN.step(inputs)` uses a snapshot of the previous
  timestep, computes all targets, and commits states synchronously. Inputs
  clamp matching units for that timestep.
- **Weight plasticity**: `apply_hebbian(learning_rate, reward)` applies
  `Δw = learning_rate × reward × pre_state × post_state`; weights are clamped
  to `[-weight_limit, +weight_limit]`. This is a simple baseline, not a
  biologically complete or generally effective learning rule.
- **Structural plasticity primitives**:
  - `grow_connection(...)` adds an edge after validating endpoints and
    prevents duplicate directed source/target pairs.
  - `prune_connections(min_abs_weight, max_remove=...)` removes the weakest
    connections below a threshold, deterministically breaking ties by ID.
  - `remove_connection(...)` removes one edge; `remove_unit(..., cascade=True)`
    explicitly removes a unit and its incident edges.
  - These are explicit, testable topology-editing operations. The network does
    **not** yet autonomously choose when or where to grow/prune connections.
- **Snapshots**: `snapshot()` returns JSON-compatible topology and state;
  `from_snapshot()` restores it.

## VirtualBrain integration and durable learning

The optional `MNNCognitionAdapter` wraps the existing cognition component. It
extracts a small set of normalized numeric features from an observation, goal,
and retrieval count, runs one MNN timestep, and attaches activations and a
network snapshot to the persisted `cognition.completed` artifact.

The existing cognition engine remains responsible for candidate plans. MNN
activations are diagnostic and do not independently select actions.

After an evaluation and validation stage, the adapter can propose a reward
modulated Hebbian update: success receives reward `+1`, failure receives
reward `-1`. The proposed snapshot and weight deltas are written as an
`mnn.plasticity_applied` journal event before the live adapter restores that
snapshot. This journal-first ordering supports recovery and prevents the same
reward from being applied twice when a cycle resumes. The neural weight update
is distinct from semantic-memory consolidation; it does not automatically make
a failed proposal into a trusted memory.

Before the next cognitive cycle, VirtualBrain restores the latest MNN snapshot
from persisted cognition/plasticity events. Regression tests cover process
restart and exactly-once recovery behavior.

## Minimal example

```python
from machina.mnn import Connection, MNN, Unit

brain = MNN()
brain.add_unit(Unit("sensor", activation="identity"))
brain.add_unit(Unit("integrator", activation="tanh"))
brain.add_connection(Connection("sensor-to-integrator", "sensor", "integrator", 0.7))
print(brain.step({"sensor": 1.0}))
brain.apply_hebbian(learning_rate=0.01, reward=1.0)

# Explicit topology change, for a controlled experiment:
brain.grow_connection("feedback", "integrator", "sensor", weight=0.1)
checkpoint = brain.snapshot()
```

## Reproducible benchmark

Run the deterministic toy association experiment from the repository root:

```bash
python -m benchmarks.mnn_reward_learning
```

It compares initial fixed weights with reward-trained weights on two simple
contexts and reports accuracy, mean squared error, and final weights as JSON.
The test suite checks determinism and expected behavior. This is a smoke test
for the plasticity implementation, **not** a meaningful benchmark of language,
reasoning, broad generalization, or AGI. The baseline is deliberately simple
and is not a competitive model. See [MNN reward-learning benchmark](MNN_BENCHMARK.md).

Run tests with `python -m pip install -e .` followed by
`python -m unittest discover -s tests -v`.

## Current limitations

This remains an experimental graph substrate. It does not yet implement
gradient-based training, a validated general-purpose learning objective,
autonomous structural-growth policy, asynchronous neural dynamics, semantic
understanding grounded in the MNN signal, or evidence of AGI. The next research
step is to evaluate learning and generalization on diverse, held-out tasks
against stronger and clearly specified baselines.

## Enquadramento na hipótese fundamental

O núcleo executável da MNN deve ser entendido como um substrato experimental, não como uma mente completa nem como evidência de consciência. A documentação técnica precisa separar capacidades realmente implementadas, hipóteses ainda não testadas e capacidades que existem apenas como especificação. Relacionar cada experimento à contribuição para a dinâmica integrada e persistente de Machina. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).


## Integrated persistent organism cycle (experimental)

The new `MNNOrganism` coordinator joins three previously separate state
domains in one logical transition:

1. virtual chemical signaling updates its persistent concentrations and
   reward-prediction error;
2. configured chemical outputs can be routed into named MNN units before the
   synchronous neural transition;
3. optional reward-modulated Hebbian adaptation uses prediction error and the
   bounded virtual plasticity gain; and
4. the functional continuity ledger records the transition under one stable
   agent identifier.

The coordinator rejects mismatched neural/chemical clocks and identity IDs.
Its versioned snapshot includes topology, neural activations, chemical
concentrations, continuity history, routing configuration, and learning rate.
A restored instance can continue with the same deterministic next transition.

Example:

```python
from machina import ChemicalEvent, Connection, MNN, MNNOrganism, Unit

network = MNN()
network.add_unit(Unit("sensor", activation="identity"))
network.add_unit(Unit("dopamine", activation="identity"))
network.add_unit(Unit("integrator", activation="tanh"))
network.add_connection(Connection("sensor-integrator", "sensor", "integrator", 0.4))
network.add_connection(Connection("dopamine-integrator", "dopamine", "integrator", 0.2))

organism = MNNOrganism(
    "machina-01",
    network,
    chemical_inputs={"dopamine": "dopamine"},
    learning_rate=0.01,
)
state = organism.step(
    {"sensor": 0.7},
    ChemicalEvent(reward=0.8, novelty=0.6),
)
checkpoint = organism.snapshot()
```

This is a functional integration milestone, not an autonomous organism, a
complete cognitive architecture, or evidence of subjective experience. The
chemical variables are computational control signals, not simulated
neurotransmitter molecules. The coordinator does not yet integrate the VirtualBrain event journal. Episodic memory can be attached as a separate persistence domain, as described below.


## Episodic memory coupling

`MNNOrganism` can now receive an existing `FragmentMemory` instance. When
attached, every successful integrated transition writes one immutable episode
fragment containing the agent ID, logical timestep, neural activations,
virtual chemical concentrations, reward-prediction error, modulation outputs,
and any weight changes. Episode IDs are deterministic for an agent/timestep,
so a repeated write is rejected rather than silently overwriting a prior
experience.

The archive remains a separate SQLite persistence domain and is not embedded
inside the organism snapshot. This is deliberate: the organism checkpoint
captures dynamic internal state, while FragmentMemory owns durable episodic
records. Reopen the same memory database after process restart and attach it to
the restored organism to continue recording and recalling episodes.

`recall_experiences(query, limit, context)` delegates to the existing
explainable lexical/associative retrieval baseline. It does not imply semantic
understanding, autobiographical self-awareness, or that retrieved episodes
automatically influence cognition. The next integration experiment must test
whether retrieved experience changes a downstream decision and improves
held-out performance against a no-retrieval baseline.



## Explicit memory-to-neural guidance (experimental)

Memory retrieval can now be turned into an explicit neural input without
making retrieval an invisible side effect of every cycle:

```python
guidance = organism.prepare_memory_guidance(
    "prediction error",
    target_unit="memory_context",
)
state = organism.step(memory_guidance=guidance)
```

The returned `MemoryGuidance` contains the original query, target unit,
bounded signal, evidence fragment IDs, and per-fragment scores. The current
signal is a confidence-weighted lexical token-overlap baseline. It is not
semantic similarity, truth estimation, or proof that a recalled episode is
relevant to the present situation. If no evidence matches, the signal is zero
and the evidence list is empty.

The target must be an existing MNN unit and cannot conflict with another
input route in the same step. Preparing guidance does not advance the neural
clock or rewrite memory; only passing it explicitly to `step` routes it into
the designated unit. This keeps the causal path inspectable and makes
retrieval-versus-no-retrieval experiments possible.

Tests cover evidence routing, zero-signal abstention for unrelated queries,
route conflicts, and the fact that preparation itself does not change the
organism snapshot. This is an integration primitive, not yet evidence that
memory improves decisions or generalization. The next experiment is a
controlled task where memory-guided and no-memory conditions are compared on
held-out examples.


## Outcome-based contextual memory feedback (experimental)

The organism now exposes `evaluate_memory_guidance(...)` to record whether
specific retrieved fragments were useful in an explicitly named task context.
The caller supplies boolean outcomes; the organism does not infer usefulness
from neural activation, prediction error, or a successful-looking response.
Feedback is restricted to fragment IDs present in the corresponding
`MemoryGuidance` evidence set.

The operation delegates to FragmentMemory's context-specific feedback ledger.
Positive and negative labels adjust a bounded relevance score for that context
without changing the fragment's global importance or other task contexts. When
the same context is supplied to a later `prepare_memory_guidance(...,
context="route-planning")` call, its learned relevance scales the evidence
signal (neutral score 0.5 leaves the lexical signal unchanged). A stable
`operation_id` makes retries idempotent, and the feedback history is auditable. Example:

```python
scores, applied = organism.evaluate_memory_guidance(
    guidance,
    {guidance.evidence_ids[0]: True},
    context="route-planning",
    operation_id="route-planning-eval-0001",
)
```

This closes a minimal feedback loop: retrieve evidence, expose it to an
explicit neural input, evaluate its usefulness externally, and update
context-specific retrieval relevance. It does not yet establish that this
feedback improves decisions. That claim requires controlled, held-out
experiments with fixed datasets, repeated seeds, and retrieval/no-retrieval
baselines. The feedback label must come from a defined evaluator or outcome,
not from the model's own unsupported assertion that a memory was useful.


## Memory-informed alternative assessment (experimental)

The organism can now compare a caller-supplied set of candidate actions with
`assess_decisions(...)`. Each `DecisionOption` contains an action label, an
externally estimated base utility, and a query used to retrieve relevant
episodes. The assessment adds a bounded memory contribution to each base
utility and returns the selected action, per-action scores, evidence IDs, and
the selected option's `MemoryGuidance`.

This is deliberately a deliberation primitive, not an autonomous action
executor. It does not invent alternatives, estimate base utility, or execute
the winner. The caller can inspect the assessment and explicitly pass
`selected_guidance` to a subsequent organism step. Ties are resolved by
action name for deterministic behavior.

Example:

```python
from machina import DecisionOption

assessment = organism.assess_decisions(
    [
        DecisionOption("reuse-experience", 0.40, "prediction error"),
        DecisionOption("unfamiliar-route", 0.55, "volcano astronomy"),
    ],
    target_unit="memory_context",
    context="route-planning",
    memory_weight=0.25,
)
# Inspect assessment, then explicitly apply its selected memory guidance.
organism.step(memory_guidance=assessment.selected_guidance)
```

A higher score in this baseline only means the configured arithmetic favored
that option. It does not show that the action is objectively better. Base
utilities and usefulness labels need external ground truth. The next
validation must measure held-out task outcomes against a no-memory baseline,
including negative feedback, misleading memories, and cases where recalling
an experience should not change the decision.


## Persistent homeostatic motivation (experimental)

The module `machina.mnn_motivation` introduces explicit, persistent drive
variables. Each `MotivationalDrive` has a current deficit level, a setpoint,
a priority, a recovery rate, and a fulfillment sensitivity. On each logical
step, an unmet drive recovers toward its setpoint; an externally recorded
fulfillment outcome reduces its deficit. The `MotivationSystem` ranks drives
by priority-weighted urgency and supports versioned snapshots.

```python
from machina import MotivationalDrive, MotivationSystem

motivation = MotivationSystem([
    MotivationalDrive("curiosity", level=0.8, setpoint=0.8, priority=0.7),
    MotivationalDrive("stability", level=0.6, setpoint=0.6, priority=1.0),
])
print(motivation.ranked_drives())
motivation.step({"stability": 1.0})
```

Fulfillment is explicit input from an evaluator or environment; the system
does not declare its own actions successful. A drive is a computational
deficit variable, not a biological need or felt desire. Priority-weighted
urgency is a control signal, not evidence of intrinsic subjective motivation.

This first primitive is intentionally separate from `MNNOrganism` so that
its dynamics can be tested before coupling it to neural activity, chemical
signaling, persistent goals, and action selection. The next integration
experiment should test whether changing drive deficits causes measurable,
adaptive differences in goal selection without destabilizing the system.


### Motivation-to-goal selection coupling

`MotivationSystem.autonomy_adjustments()` exposes the current urgency of each
drive as bounded feedback keyed by drive name. Pass this mapping to
`AutonomyController.choose(..., drive_adjustments=...)` or
`AutonomyController.step(..., drive_adjustments=...)`. With the default gain,
urgency 0.5 is neutral and the extremes map to -0.15/+0.15, matching the
controller's existing feedback clamp.

```python
from machina import (
    AutonomyContext, AutonomyController,
    MotivationalDrive, MotivationSystem,
)

motivation = MotivationSystem([
    MotivationalDrive("curiosity", level=0.9, priority=1.0),
    MotivationalDrive("stability", level=0.3, priority=1.0),
])
controller = AutonomyController()
decision = controller.step(
    AutonomyContext(unresolved_questions=2),
    drive_adjustments=motivation.autonomy_adjustments(),
)
```

This coupling biases the ranking of goals that already exist in the autonomy
controller; it does not create a new goal for every drive. Goal generation
remains bounded by the controller's explicit candidate rules and safety
filters. The motivational state is still a separate persistence domain and
must be snapshotted/restored by its owner. Tests verify that changing drive
urgency changes goal ranking while retaining the controller's risk and
external-action restrictions.


### Internal motivation as a chemical-signaling input

`MotivationSystem.chemical_pressure` computes the mean urgency across its
configured drives (zero when no drives exist). A caller can pass that scalar
into `ChemicalEvent.motivational_pressure` on the next chemical transition:

```python
from machina import ChemicalEvent, ChemicalSignaling, MotivationSystem

pressure = motivation.chemical_pressure
chemical_update = ChemicalSignaling().step(
    ChemicalEvent(
        novelty=0.2,
        uncertainty=0.3,
        risk=0.1,
        motivational_pressure=pressure,
    )
)
```

Motivational pressure contributes to virtual acetylcholine and noradrenaline
targets and to the exploration-drive calculation. It is an additional internal
input, not a replacement for externally observed reward, novelty, uncertainty,
or risk. The mapping is deliberately explicit and inspectable; it is not a
claim that these neurotransmitters have been biologically reproduced. The
caller controls update order: evaluate current drive urgency, advance chemical
signaling with that pressure, then apply explicitly observed fulfillment to
the motivation system. This prevents the chemical layer from silently
declaring a drive satisfied.


### Synchronized motivation inside `MNNOrganism`

The organism can now receive an optional `MotivationSystem`. When attached,
its clock must match the neural and chemical clocks. Each call to
`MNNOrganism.step(..., fulfillment=...)` performs the following sequence:

1. Validate all fulfillment observations without changing state.
2. Read the current mean motivational urgency and inject it into the
   `ChemicalEvent.motivational_pressure` field.
3. Advance chemical signaling and route configured chemical concentrations
   into the MNN.
4. Advance the neural network and apply optional reward-modulated plasticity.
5. Apply the explicitly supplied fulfillment observations to motivational
   drives, advancing their clock once.
6. Record the integrated transition and its resulting motivational urgencies
   in continuity history and, when attached, episodic memory.

The caller-provided `motivational_pressure` is replaced by the attached
motivation system's measured pressure so the integrated path has one
authoritative source. If no motivation system is attached, the prior organism
behavior remains unchanged and `OrganismStep.motivation_urgencies` is empty.

Organism snapshots now use schema 2 and include the optional motivation
snapshot. The loader continues to accept schema 1 snapshots, restoring them
without a motivation subsystem. The motivation store remains in-memory state
captured by the organism snapshot; episodic SQLite memory remains a separate
persistence domain and must be reopened and attached by the caller after
restoration.

This is a synchronized software experiment, not a biological homeostasis
model. Fulfillment remains an explicit observation supplied by the caller;
neither neural activation nor chemical concentration silently declares a
need satisfied.


### Arbitragem de conflitos motivacionais (experimental)

A `MotivationSystem` agora permite registrar conflitos simétricos entre pares de drives por meio de `MotivationalConflict(first, second, strength)`. A intensidade fica limitada a [0, 1]. Referências desconhecidas, auto-conflitos e arestas duplicadas são rejeitados.

A urgência bruta de cada drive continua preservada como déficit interno. Para priorização, o método `effective_urgencies()` calcula uma urgência efetiva: para cada drive, obtém a média ponderada das urgências dos concorrentes conectados e subtrai uma inibição proporcional ao `conflict_gain`. O resultado é limitado a [0, 1]. A regra é simétrica e independente da ordem em que drives e conflitos foram registrados. Drives sem conflitos mantêm sua urgência original.

A arbitragem alimenta `ranked_drives()`, `autonomy_adjustments()` e `chemical_pressure`. Assim, uma necessidade concorrente pode reduzir a influência de outra na seleção de objetivos e na modulação química virtual, sem apagar seu déficit nem declarar qualquer necessidade satisfeita. A regra não escolhe automaticamente um vencedor: conflitos equilibrados podem reduzir ambas as urgências.

O snapshot da motivação passou para schema 2 e inclui conflitos e ganho de arbitragem. O carregador continua aceitando schema 1, que restaura drives sem conflitos. Testes cobrem simetria, independência de ordem, limites, validação, persistência e compatibilidade retroativa.

Este mecanismo é uma hipótese computacional simples de competição entre prioridades, não um modelo completo de motivação biológica. O próximo passo de validação é comparar decisões com e sem conflitos em tarefas controladas, incluindo casos em que a inibição ajuda, prejudica ou deve ser ignorada.


### Cooperação entre drives motivacionais (experimental)

Além de conflitos, `MotivationSystem` agora aceita relações positivas simétricas por `MotivationalCooperation(first, second, strength)`. A intensidade é limitada a [0, 1]. Uma mesma dupla não pode ter simultaneamente uma relação de conflito e de cooperação, evitando que a interpretação do vínculo dependa da ordem de registro.

A urgência efetiva é calculada em duas fases, sempre a partir das urgências brutas:
1. cada drive recebe um reforço limitado, proporcional à média ponderada da urgência de seus parceiros cooperativos e ao `cooperation_gain`;
2. a pressão dos concorrentes explicitamente conectados é subtraída usando `conflict_gain`.

O valor final é limitado a [0, 1]. As urgências brutas e os níveis dos drives não são alterados por essas relações. Cooperação não significa que uma necessidade foi satisfeita: significa apenas que a atividade computacional associada a um drive pode aumentar a prioridade efetiva de outro.

`ranked_drives()`, `autonomy_adjustments()` e `chemical_pressure` consomem a urgência efetiva, de modo que cooperação e competição podem influenciar a escolha de objetivos e a modulação química virtual. A regra é determinística e independente da ordem de registro. O snapshot passou ao schema 3 para registrar cooperação e ao schema 4 para persistir a pressão temporal; schemas 1, 2 e 3 continuam aceitos.

Os testes verificam reforço positivo, simetria, limites, conflito/cooperação mutuamente exclusivos, persistência e compatibilidade retroativa. Isso ainda é uma regra de acoplamento linear simplificada. Não representa sinergia biológica nem demonstra motivação subjetiva. A validação seguinte deve comparar tarefas com relações desativadas, cooperativas e competitivas, medindo qualidade da decisão, estabilidade e efeitos colaterais.


### Persistência temporal da pressão motivacional (experimental)

Cada drive possui agora um parâmetro `persistence` e um estado `pressure`. Após cada ciclo, a pressão integra a urgência efetiva do ciclo por um filtro de primeira ordem:

`pressure(t+1) = pressure(t) + (effective_urgency(t) - pressure(t)) × (1 - persistence)`

Com persistência zero, a pressão acompanha imediatamente a urgência efetiva. Valores maiores tornam a mudança mais lenta: a pressão demora mais para crescer e também para desaparecer depois de uma redução do déficit. Isso permite investigar continuidade temporal, acúmulo e dissipação sem confundir o estado instantâneo do drive com seu histórico recente.

A API mantém separados `effective_urgencies()` (arbitragem instantânea) e `temporal_urgencies()` (pressão integrada), com ranking temporal próprio em `ranked_temporal_drives()`. A pressão temporal é persistida no snapshot schema 4; schemas 1, 2 e 3 continuam aceitos. O mecanismo é um integrador matemático limitado, não uma emoção, sensação ou prova de experiência subjetiva. A etapa seguinte de validação deve medir como diferentes constantes temporais afetam estabilidade e seleção de objetivos em tarefas prolongadas.


### Formação de objetivos a partir de pressão motivacional persistente

A camada de autonomia agora pode receber uma instância compatível com `MotivationSystem` em `AutonomyController.step(..., motivation=...)`. Além dos objetivos derivados do contexto (memórias, questões abertas, falhas e reflexão), o controlador gera candidatos internos `sustain_drive:<nome>` quando a pressão temporal do drive atinge o limiar configurado (0,25 por padrão).

A urgência do candidato vem de `temporal_urgencies()`, e o feedback de seleção usa `temporal_autonomy_adjustments()`. Assim, uma pressão que persiste por vários ciclos pode continuar influenciando a agenda interna mesmo quando a urgência instantânea já mudou. O objetivo é candidato interno e explicável: a camada não executa ações externas nem declara que o drive foi satisfeito. O chamador ainda precisa registrar resultados observados e fornecer feedback explícito.

O gerador aceita o contrato estrutural de pressão temporal, sem importar a implementação concreta da MNN. Isso mantém a autonomia desacoplada da arquitetura neural. Testes cobrem geração acima do limiar, ausência abaixo dele e integração na seleção de objetivos. Trata-se de geração operacional de objetivos a partir de variáveis persistentes, não de prova de vontade própria ou experiência subjetiva.


### Progresso e prioridade persistentes dos objetivos

A `PersistentGoalStore` registra agora `progress` e `priority` para cada instância de objetivo. Ambos são valores limitados a [0, 1] e sobrevivem ao reinício do processo. `update_progress(goal_id, progress, evidence=..., priority=...)` exige evidência textual explícita; a prioridade é opcional e, quando omitida, permanece inalterada.

O progresso pode aumentar ou diminuir. Uma estimativa anterior não é tratada como verdade imutável: evidência posterior pode revelar que parte do trabalho não foi concluída ou que a avaliação inicial estava errada. Cada atualização acrescenta sua justificativa ao histórico textual do objetivo. Objetivos concluídos, pausados ou abandonados não aceitam atualização de progresso; é necessário retomar um objetivo pausado ou criar uma nova instância conforme o estado.

A migração adiciona as colunas sem apagar objetivos de bancos SQLite existentes. O valor inicial de progresso é zero e a prioridade inicial é neutra (0,5). O sistema não calcula progresso por contagem de ciclos, ativação neural ou autodeclaração: um avaliador ou ambiente deve fornecer a medida e sua evidência. Isso melhora a continuidade operacional de objetivos, mas não demonstra intenção subjetiva ou vontade própria.


### Priorização de objetivos persistentes

`PersistentGoalStore.ranked_open_goals()` expõe uma fila determinística de objetivos acionáveis. A ordenação considera prioridade explícita (maior primeiro), estado (ativos antes dos que exigem revisão) e progresso (menor primeiro, favorecendo objetivos ainda incompletos); a ordem de criação desempata. Objetivos pausados ficam fora da fila até uma retomada explícita. A fila não executa objetivos nem decide sozinha abandonar ou concluir nenhum deles.


### Ciclo de deliberação interna

O módulo `machina.deliberation` introduz `InternalDeliberator`, que reúne propostas geradas pelo contexto e pela pressão motivacional com os objetivos abertos recuperados da `PersistentGoalStore`. Todos passam pela mesma política explícita de pontuação e limite de risco do `AutonomyController`.

Quando uma proposta coincide com um objetivo já aberto, a representação persistente prevalece: progresso e prioridade registrados são convertidos em entradas explícitas da política, evitando duplicar a mesma instância lógica. Um objetivo novo só é persistido depois de ser selecionado. O resultado `DeliberationDecision` registra número do ciclo, origem (novo ou persistente), identificador da instância, alternativas, componentes de pontuação e justificativa.

O deliberador não executa o objetivo, não altera seu estado de ciclo de vida e não o considera concluído. Sucesso, falha, pausa, revisão e abandono continuam dependendo de evidência e operações explícitas. O ciclo é determinístico e auditável; não constitui demonstração de consciência fenomenal, desejo sentido ou livre-arbítrio filosófico.


### Deliberação conectada ao ciclo do Virtual Brain

O `VirtualBrain` pode receber um `InternalDeliberator` explicitamente configurado e executar `run_deliberated_cycle(observation, context, ...)`. Antes de iniciar a cognição, o deliberador escolhe um objetivo interno elegível e garante sua persistência. O cérebro então inicia o ciclo usando a descrição desse objetivo como foco operacional.

A escolha é registrada no diário append-only como evento `goal.deliberated`, ligado causalmente ao objetivo ativado. O registro contém o identificador lógico do objetivo, a instância persistente, a origem da proposta e o relatório completo da deliberação, incluindo alternativas e componentes de pontuação. Assim, a decisão pode ser inspecionada depois de reiniciar o processo e integra a trilha causal do ciclo.

A integração é opt-in: sem um deliberador configurado, o comportamento anterior do `VirtualBrain` permanece inalterado. A seleção não autoriza ações externas por si só; o ciclo posterior continua sujeito aos contratos e políticas existentes do executor. O evento adicional não substitui a auditoria do ciclo nem transforma uma decisão operacional em evidência de experiência subjetiva.


### Continuidade deliberativa entre reinicializações

A `PersistentGoalStore` agora mantém uma tabela append-only `deliberation_history`, separada do ciclo de vida dos objetivos. Cada deliberação registra objetivo selecionado (ou ausência de seleção), origem, justificativa, alternativas com pontuações e um retrato dos sinais contextuais usados. `recent_deliberations()` recupera esses registros em ordem cronológica inversa, inclusive depois de fechar e reabrir o armazenamento.

O `InternalDeliberator` consulta as três deliberações anteriores antes de escolher novamente. Os objetivos recentemente selecionados entram na política de repetição já existente do controlador, com penalidade explícita e limitada; não são proibidos. O resultado também informa `previous_goal_id` e `history_record_id`, permitindo identificar continuidade ou mudança de foco.

Isso cria memória do próprio processo decisório, distinta da memória episódica de experiências e do estado de progresso do objetivo. O histórico preserva o que foi considerado e por quê; não presume que o objetivo anterior foi concluído, que a decisão foi correta ou que existe uma experiência subjetiva contínua. A continuidade é operacional e verificável.


## Evidence-based goal self-review (experimental)

The new `GoalReviewer` compares an evaluator-supplied progress measurement with
the currently persisted goal record. It returns an immutable `GoalReview`
containing prior and observed progress, the delta, prior and proposed
priority, evidence, and an advisory recommendation:

- `continue` when measured progress increased;
- `revise` when progress regressed or the goal already needs revision;
- `reassess` when progress is unchanged.

Review is side-effect free. A recommendation never changes goal status by
itself. The caller must explicitly apply the review. Applying without an
outcome records the measured progress and optional priority; applying with an
explicit evaluator outcome (`success`, `failure`, or `skip`) delegates to
the existing lifecycle transition policy. Thus a successful cognitive cycle
is not silently treated as goal success, and repeated failures only flag
revision according to the configured threshold.

Example:

```python
from machina import GoalReviewer

reviewer = GoalReviewer(goal_store)
review = reviewer.review(
    "investigate_open_questions",
    observed_progress=0.4,
    evidence="Evaluator verified two of five milestones.",
    proposed_priority=0.7,
)
print(review.to_dict())  # inspect before committing
updated = reviewer.apply(review)  # persist measured progress
# Or provide explicit outcome feedback:
# updated = reviewer.apply(review, outcome="failure")
```

This creates a review-and-feedback boundary, not autonomous self-judgment:
progress, evidence, priority changes, and outcome labels must come from an
external evaluator or a separately validated process. The recommendation is
a transparent rule over measurements, not an understanding of why a goal
matters. It does not establish subjective agency or free will.


### Concorrência e validade temporal das revisões

Uma revisão agora fica vinculada ao identificador exato do registro de objetivo
e ao progresso observado quando foi criada. Ao aplicar a revisão, o
armazenamento verifica ambos. Se outro avaliador já tiver atualizado o
objetivo, ou se o registro tiver sido concluído e substituído por uma nova
instância, a aplicação é rejeitada e exige uma nova avaliação.

Essa proteção evita que uma recomendação antiga sobrescreva evidência mais
recente ou seja aplicada acidentalmente a uma nova instância com o mesmo
`goal_id`. O mecanismo é uma verificação otimista de concorrência; ele não
resolve conflitos semânticos entre avaliadores, mas impede uma classe
importante de corrupção temporal do estado.

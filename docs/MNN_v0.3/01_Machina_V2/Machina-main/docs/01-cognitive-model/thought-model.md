# Thought Model

> **Status:** Draft conceitual — Virtual Brain v0.1  
> **Escopo:** definir como o Virtual Brain representa, organiza, executa, avalia e encerra processos de pensamento.

O `Thought Model` define o pensamento como um processo cognitivo estruturado que transforma contexto, memória, evidência e objetivos em interpretações, hipóteses, decisões e planos.

O pensamento não é tratado como sinônimo de texto gerado por um LLM. Um LLM pode participar do processo de raciocínio, mas o `Thought` pertence ao sistema cognitivo como um todo.

---

# 1. Princípio central

O Virtual Brain deve pensar sobre algo, a partir de algum contexto, usando alguma evidência e orientado por algum objetivo ou necessidade.

O modelo mínimo é:

```text
Context
   +
Objective / Need
   +
Observations
   +
Retrieved Memories
   +
World Model
   +
Self Model
   ↓
Thought Process
   ↓
Interpretation
   +
Hypotheses
   +
Reasoning
   +
Decision
   ↓
Action / Plan / Belief Update
```

Um pensamento isolado não deve ser considerado inteligência. A capacidade cognitiva emerge do ciclo contínuo entre pensamento, memória, ação e aprendizado.

---

# 2. O que é um Thought

Um `Thought` é uma unidade rastreável de atividade cognitiva.

```text
Thought
├── id
├── type
├── trigger
├── context
├── objective
├── observations[]
├── retrieved_memories[]
├── relevant_beliefs[]
├── premises[]
├── hypotheses[]
├── reasoning_steps[]
├── alternatives[]
├── conclusion
├── decision
├── confidence
├── uncertainty
├── expected_outcome
├── disposition
├── parent_thought
├── child_thoughts[]
├── created_at
└── completed_at
```

O objeto representa o processo e seus resultados cognitivos relevantes, não necessariamente uma transcrição literal de todo o raciocínio interno.

---

# 3. Tipos de pensamento

O Virtual Brain deve distinguir diferentes funções cognitivas.

```text
perception_interpretation
question_answering
recall
analysis
comparison
inference
hypothesis_generation
planning
decision_making
problem_solving
reflection
evaluation
prediction
creative_generation
learning_analysis
self_assessment
```

Um processo complexo pode combinar vários tipos.

Exemplo:

```text
problem_solving
    ↓
analysis
    ↓
hypothesis_generation
    ↓
comparison
    ↓
decision_making
    ↓
planning
```

---

# 4. Trigger

Todo processo de pensamento deve possuir um gatilho identificável sempre que possível.

```text
ThoughtTrigger
├── type
├── source_id
├── reason
└── timestamp
```

Tipos:

```text
external_input
internal_goal
memory_retrieval
unexpected_event
scheduled_task
previous_thought
action_outcome
learning_event
self_reflection
system_event
```

Exemplo:

```text
User asks:
"Como melhorar a memória do Virtual Brain?"

Trigger:
external_input
```

Outro exemplo:

```text
Goal:
"Projetar Memory Retrieval Pipeline"

Trigger:
internal_goal
```

---

# 5. Context

O pensamento precisa de um contexto explícito.

```text
ThoughtContext
├── current_time
├── current_location
├── active_goals[]
├── recent_observations[]
├── world_state_ref
├── self_state_ref
├── working_memory_ref
├── active_plan_ref
└── constraints[]
```

O contexto é uma fotografia cognitiva do momento em que o pensamento ocorre.

Ele não deve duplicar toda a memória persistente. Deve conter apenas o estado necessário para orientar o processo atual.

---

# 6. Objetivo do pensamento

Nem todo pensamento precisa ter um objetivo explícito, mas processos orientados à ação devem possuir um.

```text
ThoughtObjective
├── goal_id
├── question
├── problem
├── desired_output
└── success_criteria[]
```

Exemplos:

```text
Pergunta:
"Qual memória é relevante para esta situação?"

Problema:
"Como resolver esta tarefa?"

Objetivo:
"Escolher a próxima ação mais adequada."
```

---

# 7. Premises

`Premises` são as informações consideradas como base do pensamento.

Uma premissa deve apontar para sua origem sempre que possível.

```text
Premise
├── content
├── source_ref
├── source_type
├── confidence
├── status
└── timestamp
```

Estados:

```text
observed
retrieved
inferred
assumed
hypothetical
```

Isso permite diferenciar:

```text
"Eu observei X"

vs.

"Eu lembro de X"

vs.

"Eu inferi X"

vs.

"Estou assumindo X"
```

---

# 8. Memory Retrieval dentro do pensamento

O pensamento não deve consultar toda a memória disponível.

O processo ideal é:

```text
Thought Trigger
      ↓
Context Formation
      ↓
Query Generation
      ↓
Memory Retrieval
      ↓
Relevance Ranking
      ↓
Conflict Detection
      ↓
Context Assembly
      ↓
Reasoning
```

As memórias recuperadas devem ser registradas como referências:

```text
RetrievedMemory
├── memory_id
├── relevance_score
├── retrieval_reason
├── confidence
└── position_in_context
```

O pensamento deve poder explicar funcionalmente:

```text
"Esta memória foi usada porque era relevante para o objetivo atual."
```

Isso não exige expor uma cadeia completa de raciocínio privado. Exige apenas manter rastreabilidade operacional suficiente para auditoria e depuração.

---

# 9. Premissas, hipóteses e conclusões

O pensamento deve separar três categorias fundamentais.

```text
Premise
    ↓
Hypothesis
    ↓
Conclusion
```

### Premise

Informação usada como base.

### Hypothesis

Possibilidade considerada pelo sistema.

```text
Hypothesis
├── proposition
├── supporting_evidence[]
├── contradicting_evidence[]
├── confidence
└── status
```

Estados:

```text
candidate
supported
weak
contradicted
rejected
```

### Conclusion

Resultado provisório ou final de um processo de pensamento.

Uma conclusão pode gerar:

```text
Belief
Decision
Plan
Action
Candidate Memory
Learning Event
```

---

# 10. Reasoning Step

O processo de raciocínio pode ser representado como uma sequência de operações cognitivas.

```text
ReasoningStep
├── id
├── operation
├── inputs[]
├── output
├── evidence[]
├── confidence
└── timestamp
```

Operações conceituais:

```text
retrieve
filter
compare
classify
infer
predict
simulate
abstract
generalize
specialize
verify
contradict
synthesize
```

Exemplo:

```text
Step 1: retrieve Memory A
Step 2: compare Memory A with Observation B
Step 3: detect contradiction
Step 4: retrieve Memory C
Step 5: synthesize updated hypothesis
```

O objetivo é representar o processo cognitivo de forma estruturada, não obrigatoriamente armazenar cada token gerado pelo modelo.

---

# 11. Hypothesis Space

Para problemas complexos, o sistema deve poder manter múltiplas hipóteses simultaneamente.

```text
Problem
   ├── Hypothesis A — confidence 0.60
   ├── Hypothesis B — confidence 0.25
   └── Hypothesis C — confidence 0.15
```

A confiança não precisa ser interpretada como probabilidade matemática rigorosa no v0.1. Ela representa suporte relativo disponível.

O sistema deve evitar escolher uma hipótese prematuramente quando a evidência ainda for insuficiente.

---

# 12. Conflict Detection

Pensamentos podem encontrar conflitos entre:

- observações;
- memórias;
- crenças;
- objetivos;
- planos;
- estado do mundo;
- conhecimento externo.

O conflito deve ser representado explicitamente.

```text
Conflict
├── id
├── subject_refs[]
├── type
├── severity
├── evidence[]
├── detected_at
└── resolution_status
```

Tipos:

```text
contradictory_facts
belief_conflict
memory_conflict
goal_conflict
plan_conflict
resource_conflict
temporal_conflict
identity_conflict
```

Estados:

```text
detected
under_investigation
resolved
unresolved
accepted_uncertainty
```

Uma contradição não deve ser apagada automaticamente. Ela pode ser um sinal de que o sistema precisa investigar mais.

---

# 13. Alternatives

Quando existirem múltiplas opções de ação ou interpretação, o pensamento pode registrar alternativas.

```text
Alternative
├── id
├── description
├── expected_outcome
├── advantages[]
├── disadvantages[]
├── risks[]
├── required_resources[]
├── confidence
└── selected
```

O processo pode ser:

```text
Generate Alternatives
       ↓
Evaluate Alternatives
       ↓
Compare
       ↓
Select
       ↓
Plan / Act
```

---

# 14. Decision

Uma `Decision` representa uma escolha produzida pelo pensamento.

```text
Decision
├── id
├── chosen_option
├── rejected_options[]
├── rationale_summary
├── evidence[]
├── confidence
├── risks[]
├── reversible
└── timestamp
```

A decisão deve preservar uma justificativa resumida e referências às evidências utilizadas.

O sistema não precisa armazenar uma cadeia privada completa de raciocínio para manter uma justificativa operacional útil.

---

# 15. Conclusion

A conclusão é o resultado cognitivo do pensamento.

```text
Conclusion
├── content
├── type
├── confidence
├── evidence[]
├── uncertainty
├── implications[]
└── next_actions[]
```

Tipos:

```text
answer
belief_update
prediction
decision
plan
hypothesis
assessment
unknown
```

Uma conclusão pode explicitamente ser:

```text
known
likely
uncertain
unknown
```

O estado `unknown` é importante: o sistema deve poder concluir que não possui informação suficiente.

---

# 16. Incerteza

O pensamento deve representar incerteza em múltiplas dimensões.

```text
Uncertainty
├── factual
├── contextual
├── predictive
├── causal
└── epistemic
```

Exemplo:

```text
Factual uncertainty:
"Não sei se X é verdadeiro."

Predictive uncertainty:
"Não sei qual será o resultado de X."

Causal uncertainty:
"Não sei se X causou Y."
```

Isso evita que o sistema transforme confiança linguística em certeza artificial.

---

# 17. Confidence

A confiança de um pensamento deve considerar, quando possível:

```text
Confidence
├── evidence_quality
├── evidence_quantity
├── source_reliability
├── consistency
├── recency
└── reasoning_quality
```

A confiança deve ser uma propriedade do resultado cognitivo, não uma garantia de verdade.

---

# 18. Thought State Machine

Um processo de pensamento pode seguir:

```text
created
   ↓
contextualized
   ↓
retrieving
   ↓
reasoning
   ↓
evaluating
   ↓
concluding
   ↓
committing
   ↓
completed
```

Possíveis interrupções:

```text
paused
cancelled
blocked
failed
superseded
```

### Significado

- `created`: pensamento iniciado.
- `contextualized`: contexto preparado.
- `retrieving`: memória sendo consultada.
- `reasoning`: análise em andamento.
- `evaluating`: hipóteses ou alternativas sendo avaliadas.
- `concluding`: conclusão sendo formada.
- `committing`: resultado sendo encaminhado para ação, memória ou aprendizado.
- `completed`: processo concluído.

---

# 19. Thought Hierarchy

Pensamentos complexos podem gerar subpensamentos.

```text
Parent Thought
│
├── Child Thought A
│   ├── Child Thought A.1
│   └── Child Thought A.2
│
├── Child Thought B
│
└── Child Thought C
```

Exemplo:

```text
Parent:
"Como projetar a memória do Virtual Brain?"

Child A:
"Quais tipos de memória precisamos?"

Child B:
"Como recuperar memórias?"

Child C:
"Como consolidar aprendizado?"
```

A hierarquia permite decomposição de problemas sem transformar todo o processo em um único contexto gigante.

---

# 20. Thought Cycle

O ciclo cognitivo de pensamento é:

```text
TRIGGER
   ↓
CONTEXTUALIZE
   ↓
FORMULATE QUESTION / OBJECTIVE
   ↓
RETRIEVE MEMORY
   ↓
BUILD PREMISES
   ↓
GENERATE HYPOTHESES
   ↓
REASON
   ↓
CHECK CONFLICTS
   ↓
EVALUATE ALTERNATIVES
   ↓
FORM CONCLUSION
   ↓
DECIDE
   ↓
PLAN / ACT / RESPOND
   ↓
EVALUATE OUTCOME
   ↓
CONSOLIDATE RELEVANT RESULT
```

Nem todo pensamento precisa executar todas as etapas.

Por exemplo:

```text
Pergunta simples
→ Contextualize
→ Recupere
→ Responda
```

Problema complexo:

```text
Contextualize
→ Recuperar
→ Hipóteses
→ Raciocinar
→ Simular
→ Comparar
→ Planejar
→ Agir
→ Avaliar
→ Aprender
```

---

# 21. Thought e LLM

O LLM deve ser tratado como um componente cognitivo possível.

```text
Virtual Brain
│
├── Context Builder
├── Memory Retrieval
├── Reasoning Orchestrator
│       │
│       ├── LLM
│       ├── Rule Engine
│       ├── Calculator
│       ├── Code Executor
│       └── Specialized Models
│
├── Evaluator
└── Learning Engine
```

O `Thought` deve sobreviver à substituição do LLM.

Isso significa que:

```text
LLM A
   ↓
Thought Model
   ↓
LLM B
```

deve ser possível sem alterar a semântica fundamental do sistema.

---

# 22. Thought e memória

O pensamento possui duas relações com a memória.

### Memória como entrada

```text
Memory
   ↓
Thought
```

### Pensamento como possível memória

```text
Thought
   ↓ avaliação
Candidate Memory
   ↓ consolidação
Memory
```

Nem todo pensamento deve ser armazenado.

Critérios possíveis:

```text
importance
novelty
future_relevance
learning_value
emotional_oral_significance
project_relevance
decision_significance
```

Para o v0.1, recomenda-se começar com:

```text
importance
novelty
future_relevance
learning_value
```

---

# 23. Thought e aprendizagem

O pensamento pode produzir conhecimento, mas o aprendizado deve ocorrer após avaliação.

```text
Thought
    ↓
Conclusion
    ↓
Outcome / Evidence
    ↓
Evaluation
    ↓
LearningEvent
    ↓
Validated Update
```

Isso evita transformar uma conclusão especulativa em conhecimento permanente.

Exemplo:

```text
Thought:
"A estratégia A parece funcionar."

Confidence:
0.60

Status:
hypothesis

Após 10 experiências:

Evaluation:
8 sucessos / 2 falhas

LearningEvent:
"A estratégia A possui alta taxa de sucesso neste contexto."

Skill Update:
v2
```

---

# 24. Thought e autoavaliação

O sistema deve possuir capacidade de avaliar o próprio processo cognitivo.

```text
Thought
   ↓
Self-Evaluation
   ├── Was context sufficient?
   ├── Were relevant memories retrieved?
   ├── Was uncertainty recognized?
   ├── Were alternatives considered?
   └── Was the conclusion reliable?
```

Isso não significa consciência. É uma capacidade funcional de monitoramento cognitivo.

---

# 25. Meta-cognition

O Virtual Brain deve poder produzir pensamentos sobre seus próprios processos.

```text
Object-level thought
"Qual solução devo escolher?"

Meta-level thought
"Tenho informação suficiente para escolher?"
```

A metacognição pode avaliar:

- qualidade da memória recuperada;
- confiança da conclusão;
- ausência de evidência;
- conflitos detectados;
- necessidade de buscar informação adicional;
- necessidade de pedir ajuda;
- necessidade de executar um experimento.

No v0.1, a metacognição deve ser limitada a avaliação e controle do processo, não autoalteração irrestrita do sistema.

---

# 26. Quando o pensamento deve parar

Um pensamento não deve continuar indefinidamente.

Critérios de parada:

```text
sufficient_confidence
sufficient_evidence
goal_satisfied
answer_found
action_selected
resource_limit
time_limit
uncertainty_irreducible
requires_external_information
requires_human_input
```

O sistema deve poder concluir:

```text
"Não tenho informação suficiente."

"Preciso buscar mais dados."

"Preciso perguntar ao usuário."

"As evidências são conflitantes."
```

Isso é preferível a gerar uma resposta artificialmente confiante.

---

# 27. Cognitive Context Window

A memória de trabalho não deve ser simplesmente o contexto máximo do LLM.

O `Cognitive Context` é uma composição dinâmica:

```text
Cognitive Context
├── Current Goal
├── Current World State
├── Current Self State
├── Recent Observations
├── Active Plan
├── Relevant Memories
├── Relevant Beliefs
├── Active Hypotheses
├── Constraints
└── Uncertainties
```

O sistema deve selecionar dinamicamente o que entra no contexto de raciocínio.

```text
Long-term Memory
       ↓
Retrieval
       ↓
Ranking
       ↓
Context Compression
       ↓
Cognitive Context
       ↓
Reasoning Engine
```

---

# 28. Raciocínio como orquestração

O Thought Engine não precisa depender de uma única técnica.

```text
Thought Engine
│
├── Retrieval
├── Symbolic Rules
├── LLM Reasoning
├── Tool Calls
├── Code Execution
├── Search
├── Simulation
└── Verification
```

A estratégia pode ser adaptativa:

```text
Simple question
→ Retrieval + LLM

Mathematical problem
→ Calculator + Verification

Complex research
→ Retrieval + Search + LLM + Synthesis

Planning
→ Memory + World Model + LLM + Simulation

Critical decision
→ Multiple candidates + Verification + Evaluation
```

O objetivo é permitir que o Virtual Brain escolha o processo cognitivo adequado ao problema.

---

# 29. Thought Commit

Antes de concluir um pensamento, o sistema deve decidir o destino do resultado.

```text
Thought Result
     ↓
┌────┼────────┬─────────┐
▼    ▼        ▼         ▼
Respond  Act   Remember  Learn
```

Possíveis destinos:

```text
response_only
action
candidate_memory
belief_update
plan_update
goal_update
learning_event
world_state_update
self_state_update
```

O commit deve ser explícito para evitar que qualquer saída de raciocínio altere automaticamente o estado persistente.

---

# 30. Auditoria do pensamento

Cada pensamento importante deve permitir reconstruir, em nível operacional:

```text
Qual foi o gatilho?
Qual era o objetivo?
Qual contexto foi usado?
Quais memórias foram recuperadas?
Quais evidências foram consideradas?
Quais hipóteses foram avaliadas?
Quais conflitos foram detectados?
Qual foi a conclusão?
Qual foi a confiança?
Qual ação foi tomada?
Qual resultado ocorreu?
O que foi aprendido?
```

Isso forma uma trilha:

```text
Trigger
  ↓
Thought
  ↓
Decision
  ↓
Action
  ↓
Outcome
  ↓
Evaluation
  ↓
Learning
```

---

# 31. Contrato mínimo do Thought Engine v0.1

O primeiro Thought Engine deve conseguir:

1. Receber um `Trigger`.
2. Construir um `ThoughtContext`.
3. Consultar a memória.
4. Formar premissas.
5. Produzir uma ou mais hipóteses quando necessário.
6. Raciocinar sobre as evidências disponíveis.
7. Detectar conflitos básicos.
8. Produzir uma conclusão.
9. Atribuir confiança e incerteza.
10. Escolher um destino para a conclusão.
11. Registrar o processo cognitivo em eventos.
12. Encaminhar resultados relevantes para ação, memória ou aprendizado.

Fluxo mínimo:

```text
Trigger
  ↓
Context
  ↓
Memory Retrieval
  ↓
Premises
  ↓
Reasoning
  ↓
Conclusion
  ↓
Confidence / Uncertainty
  ↓
Commit Decision
  ↓
Action / Response / Memory / Learning
```

---

# 32. Regras de consistência

1. Um `Thought` deve possuir um contexto identificável.
2. Pensamentos orientados à ação devem possuir objetivo ou necessidade explícita.
3. Memórias recuperadas devem ser registradas como referências, não copiadas integralmente sem necessidade.
4. Observações, inferências e hipóteses devem permanecer semanticamente distintas.
5. Conclusões incertas não devem ser promovidas automaticamente a crenças de alta confiança.
6. Conflitos relevantes devem ser preservados para investigação.
7. O resultado de um pensamento não deve alterar memória persistente sem um `commit` explícito.
8. Pensamentos transitórios podem ser descartados após o ciclo, mas eventos cognitivos relevantes devem permanecer auditáveis.
9. O Thought Engine deve poder declarar `unknown`.
10. O Thought Engine deve poder solicitar mais informação quando a evidência for insuficiente.
11. A arquitetura deve permitir múltiplos motores de raciocínio.
12. A substituição do LLM não deve alterar o modelo cognitivo.

---

# 33. Próxima etapa

O `Thought Model` define como o Virtual Brain pensa. O próximo documento deve definir como ele aprende:

1. `learning-model.md` — formação de aprendizado a partir de experiências.
2. `memory-retrieval.md` — mecanismo de consulta e recuperação.
3. `world-model.md` — representação dinâmica do mundo.
4. `self-model.md` — representação do próprio sistema.

A relação entre os três primeiros componentes será:

```text
Memory Model
     ↓
Memory Retrieval
     ↓
Thought Model
     ↓
Learning Model
     ↓
Memory Update
```

Esse ciclo forma a base cognitiva do Virtual Brain v0.1.

# Cognitive Data Model

> **Status:** Draft conceitual — Virtual Brain v0.1  
> **Escopo:** contrato conceitual antes da implementação de schemas, persistência e APIs.

Este documento define os objetos fundamentais do Virtual Brain, seus campos, estados, relações, ciclo de vida e regras de consistência. Ele é a referência conceitual para a futura implementação.

## 1. Princípios do modelo

1. **Observação não é fato absoluto.** Uma observação registra o que foi recebido ou percebido por uma fonte.
2. **Interpretação não é observação.** O sistema deve separar dados observados de inferências produzidas.
3. **Memória precisa de proveniência.** Toda informação persistente deve indicar de onde veio e como foi obtida.
4. **Crenças são revisáveis.** O sistema pode mudar sua confiança sem apagar o histórico da mudança.
5. **Estado atual é diferente de histórico.** `WorldState` e `SelfState` representam o presente; `Experience` representa o passado.
6. **Pensamento é transitório por padrão.** Apenas resultados relevantes devem ser consolidados.
7. **Aprendizado é uma proposta de alteração.** Um `LearningEvent` não deve modificar conhecimento crítico de forma irreversível sem validação.
8. **Identidade é estável, estado é mutável.** O sistema pode manter uma identidade persistente enquanto seu estado muda.
9. **Tudo relevante deve ser rastreável.** O sistema deve conseguir responder: o que sabe, por que sabe, quando aprendeu e o que mudou.
10. **Incerteza é parte do modelo.** Ausência de confiança não deve ser confundida com falsidade.

---

# 2. Convenções comuns

Todas as entidades persistentes devem, quando aplicável, possuir um envelope comum:

```text
BaseEntity
├── id: UUID
├── type: EntityType
├── schema_version: string
├── created_at: timestamp
├── updated_at: timestamp
├── status: Status
├── metadata: object
└── tags: string[]
```

### Identidade

`id` identifica uma instância específica e nunca deve ser reutilizado.

### Versão

`schema_version` indica a versão estrutural do objeto. Alterações no formato não devem destruir objetos antigos.

### Status

O status representa o ciclo de vida do objeto, por exemplo:

```text
active
inactive
archived
superseded
invalidated
```

### Metadados

Informações auxiliares que não fazem parte do significado cognitivo principal.

### Tags

Marcadores para organização e recuperação, sem substituir relações semânticas.

---

# 3. Tipos de fonte e proveniência

Toda informação relevante deve possuir proveniência explícita ou ser marcada como inferida.

```text
Source
├── id
├── type
├── name
├── uri
├── timestamp
└── reliability
```

Tipos possíveis:

```text
user
system
tool
document
sensor
external_api
memory
inference
self_generated
unknown
```

Uma informação pode ter múltiplas fontes.

A proveniência deve permitir distinguir:

```text
OBSERVED
    ↓
INTERPRETED
    ↓
INFERRED
    ↓
BELIEVED
```

Essas categorias não devem ser tratadas como equivalentes.

---

# 4. Observation

Uma `Observation` representa uma entrada recebida pelo sistema ou um evento percebido por um componente de percepção.

```text
Observation
├── id
├── source
├── content
├── modality
├── timestamp
├── context
├── confidence
├── reliability
├── raw_reference
└── extracted_entities
```

### Campos

- `source`: origem da observação.
- `content`: conteúdo estruturado ou não estruturado.
- `modality`: texto, imagem, áudio, evento, sensor etc.
- `timestamp`: momento associado ao evento observado.
- `context`: contexto conhecido no momento da percepção.
- `confidence`: confiança do componente de percepção na interpretação da entrada.
- `reliability`: confiabilidade estimada da fonte.
- `raw_reference`: referência ao dado original, quando existir.
- `extracted_entities`: entidades identificadas.

### Regra

Uma `Observation` não deve ser automaticamente convertida em `Belief`. Primeiro pode passar por interpretação, validação ou comparação com outras evidências.

---

# 5. Experience

Uma `Experience` representa um episódio cognitivo completo ou parcialmente completo vivido pelo sistema.

```text
Experience
├── id
├── observations[]
├── context
├── interpretation
├── thoughts[]
├── goals[]
├── plans[]
├── actions[]
├── outcomes[]
├── evaluation
├── learning_events[]
├── started_at
└── ended_at
```

Uma experiência pode conter:

```text
Observações
    ↓
Interpretação
    ↓
Pensamento
    ↓
Objetivo
    ↓
Plano
    ↓
Ação
    ↓
Resultado
    ↓
Avaliação
    ↓
Aprendizado
```

A `Experience` é a unidade principal de memória episódica, mas nem toda experiência precisa ser consolidada integralmente.

---

# 6. Thought

Um `Thought` representa um estado ou processo interno de raciocínio associado a contexto, objetivo ou problema.

```text
Thought
├── id
├── context
├── objective
├── premises[]
├── retrieved_memories[]
├── hypotheses[]
├── reasoning_trace
├── conclusion
├── confidence
├── uncertainty
├── created_at
└── disposition
```

### Disposition

Define o destino do pensamento:

```text
transient
candidate_memory
candidate_belief
decision
plan_input
consolidated
rejected
```

### Regra

O `Thought` não deve ser confundido com a saída textual de um LLM. O texto pode ser uma representação do pensamento, mas o objeto cognitivo deve registrar também contexto, premissas, evidências recuperadas, hipóteses e conclusão.

---

# 7. Memory

`Memory` é a unidade persistente de informação recuperável pelo sistema.

```text
Memory
├── id
├── type
├── content
├── source
├── evidence[]
├── provenance[]
├── confidence
├── importance
├── relevance
├── access_count
├── last_accessed_at
├── created_at
├── updated_at
├── supersedes[]
├── superseded_by[]
├── relationships[]
└── consolidation_state
```

### Tipos

```text
episodic
semantic
procedural
autobiographical
contextual
working
```

`working` representa memória operacional e, em geral, possui ciclo de vida diferente das memórias persistentes.

### Consolidação

```text
candidate
validated
consolidated
revised
superseded
archived
```

### Regra de atualização

Memórias não devem ser sobrescritas silenciosamente quando representam conhecimento relevante. Uma nova versão deve preservar a relação com a anterior.

---

# 8. Concept

Um `Concept` representa uma abstração semântica.

```text
Concept
├── id
├── name
├── description
├── aliases[]
├── properties{}
├── relationships[]
├── evidence[]
├── confidence
└── version
```

Exemplo:

```text
Concept: Virtual Brain
Type: system_architecture
Confidence: 0.92
```

---

# 9. Entity

Uma `Entity` representa algo identificável no mundo, no ambiente ou no próprio sistema.

```text
Entity
├── id
├── name
├── type
├── description
├── properties{}
├── identifiers[]
├── relationships[]
├── source_references[]
└── confidence
```

Entidades podem ser:

```text
person
organization
project
place
object
software
conceptual_system
agent
self
unknown
```

---

# 10. Belief

Uma `Belief` representa uma proposição que o sistema considera plausível ou verdadeira com determinado grau de confiança.

```text
Belief
├── id
├── proposition
├── subject
├── predicate
├── object
├── confidence
├── evidence[]
├── sources[]
├── supporting_beliefs[]
├── contradicting_beliefs[]
├── created_at
├── updated_at
└── revision_history[]
```

### Estado

```text
proposed
active
uncertain
contradicted
retracted
superseded
```

### Regra

Uma crença contradita não deve necessariamente ser apagada. Ela deve ser marcada como contradita ou supersedida, preservando a evidência histórica.

---

# 11. Goal

Um `Goal` representa um estado desejado que orienta o comportamento.

```text
Goal
├── id
├── description
├── type
├── priority
├── status
├── parent_goal
├── constraints[]
├── success_criteria[]
├── deadline
├── created_at
└── updated_at
```

### Estados

```text
proposed
active
paused
completed
failed
cancelled
superseded
```

Objetivos podem formar hierarquias:

```text
Goal A
├── Goal A.1
├── Goal A.2
└── Goal A.3
```

---

# 12. Plan

Um `Plan` representa uma estratégia para alcançar um ou mais objetivos.

```text
Plan
├── id
├── goal_ids[]
├── steps[]
├── assumptions[]
├── dependencies[]
├── expected_outcomes[]
├── risk_assessment
├── status
├── version
└── created_at
```

Cada etapa pode conter:

```text
PlanStep
├── id
├── order
├── action
├── preconditions[]
├── expected_outcome
├── actual_outcome
└── status
```

Planos podem ser revisados sem apagar versões anteriores.

---

# 13. Action

Uma `Action` representa uma operação executada pelo sistema.

```text
Action
├── id
├── type
├── actor
├── tool
├── input
├── authorization
├── timestamp
├── status
├── expected_outcome
└── outcome_id
```

### Estados

```text
proposed
approved
executing
completed
failed
cancelled
blocked
```

Ações externas devem ser auditáveis.

---

# 14. Outcome

Um `Outcome` representa o resultado observado de uma ação.

```text
Outcome
├── id
├── action_id
├── observations[]
├── expected
├── actual
├── success
├── deviation
├── impact
└── timestamp
```

O resultado pode ser:

```text
success
partial_success
failure
unknown
```

---

# 15. Skill

Uma `Skill` representa uma capacidade procedural aprendida ou fornecida ao sistema.

```text
Skill
├── id
├── name
├── description
├── prerequisites[]
├── procedure
├── preconditions[]
├── postconditions[]
├── success_rate
├── usage_count
├── confidence
├── version
├── source
└── revision_history[]
```

Uma habilidade pode evoluir através de experiências, mas alterações devem gerar uma nova versão quando forem significativas.

---

# 16. LearningEvent

Um `LearningEvent` registra uma oportunidade de aprendizado e uma possível alteração cognitiva.

```text
LearningEvent
├── id
├── experience_id
├── trigger
├── evidence[]
├── detected_pattern
├── proposed_updates[]
├── confidence
├── validation_status
├── applied_updates[]
└── timestamp
```

### Ciclo

```text
experience
    ↓
observation
    ↓
evaluation
    ↓
pattern_detection
    ↓
learning_candidate
    ↓
validation
    ↓
consolidation
```

### Regra

`LearningEvent` não é sinônimo de alteração aplicada. Uma proposta pode ser rejeitada, adiada ou parcialmente aplicada.

---

# 17. WorldState

`WorldState` representa a visão atual do sistema sobre o ambiente.

```text
WorldState
├── id
├── entities[]
├── relationships[]
├── events[]
├── beliefs[]
├── active_conditions[]
├── uncertainties[]
├── timestamp
└── version
```

O `WorldState` é uma projeção atualizada a partir de observações, memórias e inferências. Não substitui o histórico.

---

# 18. SelfState

`SelfState` representa o estado atual do próprio Virtual Brain.

```text
SelfState
├── identity
├── capabilities[]
├── limitations[]
├── active_goals[]
├── current_context
├── available_tools[]
├── resource_state
├── current_mode
├── health
└── timestamp
```

O `SelfState` deve responder funcionalmente:

```text
Quem sou?
O que consigo fazer?
O que não consigo fazer?
O que estou tentando alcançar?
Quais ferramentas tenho?
Qual é meu estado atual?
```

---

# 19. Evaluation

`Evaluation` registra a análise de um resultado ou experiência.

```text
Evaluation
├── id
├── target_id
├── criteria[]
├── expected
├── observed
├── score
├── success
├── errors[]
├── lessons[]
├── evaluator
└── timestamp
```

A avaliação é uma entidade explícita porque o aprendizado depende de saber se uma ação funcionou, falhou ou produziu resultado inesperado.

---

# 20. Relationship

As entidades cognitivas devem poder se relacionar através de relações tipadas.

```text
Relationship
├── id
├── subject_id
├── predicate
├── object_id
├── confidence
├── evidence[]
├── source
├── valid_from
├── valid_until
└── status
```

Exemplos:

```text
Entity A --is_part_of--> Entity B
Memory A --supports--> Belief B
Memory A --derived_from--> Experience B
Thought A --uses--> Memory B
Goal A --requires--> Skill B
Plan A --achieves--> Goal B
Action A --produces--> Outcome B
Outcome A --updates--> WorldState B
LearningEvent A --revises--> Belief B
```

Relações devem possuir identidade própria quando precisarem de evidência, confiança ou validade temporal.

---

# 21. Cognitive Event

Para permitir auditoria, o sistema deve possuir uma camada de eventos cognitivos.

```text
CognitiveEvent
├── id
├── type
├── actor
├── timestamp
├── input_refs[]
├── output_refs[]
├── context
└── metadata
```

Tipos iniciais:

```text
observation_received
memory_created
memory_retrieved
thought_created
belief_proposed
belief_updated
goal_created
plan_created
action_executed
outcome_observed
evaluation_completed
learning_detected
learning_applied
state_updated
```

Isso cria uma trilha de auditoria do ciclo cognitivo.

---

# 22. Relações fundamentais

O fluxo principal é:

```text
Observation
    ↓ gera
Experience
    ↓ contém
Thought / Goal / Plan / Action / Outcome
    ↓ pode consolidar
Memory
    ↓ influencia
Thought
    ↓ produz
Plan
    ↓ executa
Action
    ↓ gera
Outcome
    ↓ alimenta
Evaluation
    ↓ gera
LearningEvent
    ↓ após validação atualiza
Memory / Belief / Skill / WorldState / SelfState
```

O fluxo não é estritamente linear. Memórias podem influenciar objetivos; objetivos orientam recuperação; o estado do mundo modifica planos; resultados podem invalidar crenças.

---

# 23. Grafo cognitivo mínimo

O modelo pode ser representado como um grafo:

```text
          ┌────────────┐
          │ Observation│
          └─────┬──────┘
                │
                ▼
          ┌────────────┐
          │ Experience │
          └─────┬──────┘
                │
       ┌────────┼─────────┐
       ▼        ▼         ▼
    Thought   Memory    Learning
       │        │         │
       ▼        ▼         ▼
      Plan ←─ Belief ─→ Skill
       │
       ▼
     Action
       │
       ▼
    Outcome
       │
       ▼
  Evaluation
       │
       └────────────→ WorldState
                         │
                         ▼
                      SelfState
```

A implementação futura pode usar banco relacional, documentos, vetor, grafo ou combinação desses. O modelo conceitual não deve depender de uma tecnologia específica.

---

# 24. Ciclo de vida dos dados

```text
RECEIVE
  ↓
OBSERVE
  ↓
INTERPRET
  ↓
REPRESENT
  ↓
RETRIEVE
  ↓
REASON
  ↓
ACT
  ↓
OBSERVE OUTCOME
  ↓
EVALUATE
  ↓
LEARN
  ↓
VALIDATE
  ↓
CONSOLIDATE
  ↓
VERSION
```

## Estados de conhecimento

Uma informação pode evoluir entre estados:

```text
raw observation
    ↓
interpreted information
    ↓
candidate memory
    ↓
validated memory
    ↓
belief / concept / skill
    ↓
revised or superseded
```

O sistema deve preservar os vínculos entre essas transformações.

---

# 25. Proveniência e evidência

Toda afirmação relevante deve poder responder:

```text
O que é?
De onde veio?
Quando foi obtido?
Quem ou o que forneceu?
Qual evidência suporta?
Qual é a confiança?
Foi observado ou inferido?
Foi contradito?
Quando foi atualizado?
```

Isso é fundamental para evitar que o Virtual Brain transforme suas próprias inferências em fatos sem rastreabilidade.

---

# 26. Confiança e incerteza

A confiança deve ser representada separadamente da importância.

```text
confidence = quão bem suportada parece ser a informação
importance = quão relevante é preservar ou recuperar a informação
reliability = quão confiável é a fonte
```

Uma memória pode ser:

```text
alta importância + baixa confiança
```

Por exemplo, uma hipótese importante que ainda precisa ser validada.

A ausência de evidência não deve automaticamente produzir confiança zero, mas deve reduzir a capacidade do sistema de tratar a informação como fato estabelecido.

---

# 27. Versionamento cognitivo

Conhecimento mutável deve possuir histórico.

```text
Belief v1
    ↓ nova evidência
Belief v2
    ↓ revisão
Belief v3
```

A versão anterior deve continuar acessível como histórico, mesmo que deixe de ser a versão ativa.

O mesmo princípio se aplica a:

- `Memory`;
- `Belief`;
- `Skill`;
- `Plan`;
- modelos internos relevantes.

---

# 28. Regras de consistência

1. Nenhum `Memory` persistente sem proveniência ou indicação explícita de inferência.
2. Nenhum `Belief` ativo sem ao menos uma base de evidência ou uma indicação de que é uma hipótese inicial.
3. Nenhuma `Action` concluída sem tentativa de registrar `Outcome`.
4. Nenhum `LearningEvent` aplicado sem registro da alteração produzida.
5. Nenhuma atualização crítica deve destruir silenciosamente a versão anterior.
6. `WorldState` e `SelfState` devem ser reconstruíveis a partir do histórico quando tecnicamente possível.
7. Dados temporários não devem ser promovidos automaticamente a conhecimento permanente.
8. A mesma entidade real deve poder ser referenciada por múltiplas memórias sem duplicação desnecessária.
9. Conflitos de conhecimento devem ser representáveis explicitamente.
10. O sistema deve distinguir `unknown`, `uncertain`, `false` e `contradicted`.

---

# 29. Contrato mínimo do v0.1

A primeira implementação não precisa suportar todos os campos imediatamente. O núcleo mínimo recomendado é:

```text
Observation
Experience
Memory
Thought
Goal
Plan
Action
Outcome
Evaluation
LearningEvent
Belief
WorldState
SelfState
```

A implementação pode começar com armazenamento simples, desde que preserve os seguintes vínculos:

```text
Observation → Experience
Experience → Memory
Memory → Thought
Thought → Goal / Plan
Plan → Action
Action → Outcome
Outcome → Evaluation
Evaluation → LearningEvent
LearningEvent → Memory / Belief / WorldState / SelfState
```

Esse grafo de dependências é o contrato mínimo que permite construir o Cognitive Loop sem comprometer a evolução futura da arquitetura.

---

# 30. Próxima etapa

Depois deste documento, a arquitetura deve avançar para:

1. `thought-model.md` — como o sistema representa e organiza pensamentos.
2. `learning-model.md` — como experiências geram aprendizado e como alterações são validadas.
3. `world-model.md` — como o sistema representa entidades, relações, estados e causalidade.
4. `self-model.md` — como o sistema representa sua própria identidade, capacidades e limitações.
5. `memory-retrieval.md` — como consultas cognitivas recuperam memórias relevantes.
6. `schemas/` — transformar este contrato conceitual em schemas executáveis.

> **Nota:** este documento define a semântica do sistema, não a tecnologia de armazenamento. A decisão entre PostgreSQL, banco vetorial, grafo, documentos ou arquitetura híbrida deve ser tomada depois que o modelo cognitivo estiver estável.

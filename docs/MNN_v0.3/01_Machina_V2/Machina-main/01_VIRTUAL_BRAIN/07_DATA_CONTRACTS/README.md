# 07 — Data Contracts

## Contratos de dados e autoridade entre os componentes do Virtual Brain

> **Pergunta fundamental:** Como os componentes do Virtual Brain trocam informação sem criar responsabilidades sobrepostas, acesso irrestrito ou conflitos de estado?

Este documento transforma a teoria do Virtual Brain em contratos arquiteturais explícitos.

A regra central é:

> **Cada estado persistente possui exatamente um proprietário autoritativo. Outros componentes podem ler, consultar ou propor mudanças, mas apenas o proprietário pode validar, versionar e persistir o estado.**

Isso cria uma separação clara entre:

```text
READ
→ consultar informação.

QUERY
→ solicitar informação estruturada.

PROPOSE
→ sugerir uma mudança.

DECIDE
→ assumir uma decisão operacional.

EXECUTE
→ realizar uma operação.

VALIDATE
→ verificar se uma mudança é aceitável.

COMMIT
→ incorporar uma mudança persistente.
```

Nenhum componente recebe autoridade implícita sobre o estado de outro.

---

# 1. Arquitetura de contratos

```text
                    ┌─────────────┐
                    │    SELF     │
                    │ Identity /  │
                    │   Values    │
                    └──────┬──────┘
                           │ SelfState
                           ▼
PERCEPTION ────────▶ WORKSPACE ◀──────── MEMORY
                        │  ▲
                        │  │
               CognitiveRequest
                        │  │
                        ▼  │
                    COGNITION
                        │
                 CognitiveResult
                        │
                        ▼
                     AGENCY
                        │
                     Decision
                        │
                        ▼
                  ActionIntent
                        │
                        ▼
                 ACTION SYSTEM
                        │
                   ActionResult
                        │
                        ▼
                VIRTUAL ORGANISM
                        │
                        ▼
                   EXPERIENCE
                        │
                        ▼
                    LEARNING
                        │
                LearningProposal
                        │
                        ▼
                  CONSOLIDATION
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          MEMORY    WORLD MODEL   SELF MODEL
```

O fluxo acima representa o ciclo de dados. Não significa que cada componente tenha acesso direto ao armazenamento interno dos demais.

---

# 2. Princípio de ownership

Cada estado persistente possui um proprietário único.

```text
SELF MODEL
→ Self

MEMORY STORE
→ Memory

WORLD MODEL
→ World Model

STRATEGIES / LEARNED POLICIES
→ Learning / sistema persistente de estratégias

WORKSPACE STATE
→ Workspace

AGENCY STATE
→ Agency
```

O proprietário é responsável por:

```text
VALIDATE
VERSION
COMMIT
PERSIST
```

Outros componentes podem:

```text
READ
QUERY
PROPOSE
REQUEST
```

Mas não podem escrever diretamente no estado persistente de outro componente.

---

# 3. Regra de autoridade

```text
AUTHORITY
≠
UNLIMITED POWER
```

A autoridade de um componente é limitada ao seu domínio.

| Componente | Autoridade principal |
|---|---|
| Self | identidade, valores e continuidade do Self Model |
| Workspace | estado cognitivo transitório ativo |
| Memory | armazenamento e recuperação de memórias |
| Cognition | processos cognitivos transitórios |
| Agency | objetivos operacionais, prioridades, decisões e Action Intents |
| Action System | execução operacional autorizada |
| Learning | avaliação de experiências e propostas de mudança |
| Consolidation | incorporação persistente de mudanças aprovadas |
| World Model | representação persistente do mundo |

Nenhum componente pode conceder a si mesmo novas permissões apenas porque possui um objetivo.

---

# 4. WorkspaceState

O Workspace é o presente cognitivo integrado.

```text
WorkspaceState
├── workspace_id
├── timestamp
├── context
├── active_percepts
├── retrieved_memories
├── self_state
├── world_state
├── active_goals
├── cognitive_state
├── beliefs
├── uncertainties
├── action_context
└── attention_state
```

O Workspace mantém projeções contextuais. Ele não é a fonte definitiva dos dados persistentes.

```text
SELF MODEL
    ↓
SELF STATE
    ↓
WORKSPACE
```

```text
WORLD MODEL
    ↓
WORLD STATE
    ↓
WORKSPACE
```

```text
MEMORY
    ↓ retrieval
WORKSPACE
```

O Workspace pode atualizar seu próprio estado transitório, mas não deve alterar diretamente Self Model, World Model ou Memory Store.

---

# 5. SelfState

`SelfState` é a projeção contextual do Self no presente cognitivo.

```text
SelfState
├── self_id
├── identity_context
├── active_values
├── capabilities
├── limitations
├── current_commitments
├── relevant_history
├── self_assessment
└── confidence
```

Fluxo:

```text
SELF MODEL
    ↓ contextualization
SELF STATE
    ↓
WORKSPACE
```

Cognition e Agency podem consultar `SelfState`.

Learning pode propor mudanças no Self Model com base em evidências.

O Workspace apenas mantém a projeção contextual.

---

# 6. WorldState

`WorldState` é a projeção contextual do World Model relevante para o ciclo atual.

```text
WorldState
├── world_model_version
├── context
├── entities
├── relevant_relations
├── current_state
├── known_facts
├── inferred_facts
├── uncertainties
└── timestamp
```

O WorldState deve preservar distinções epistemológicas:

```text
OBSERVED
INFERRED
ASSUMED
UNCERTAIN
```

Fluxo:

```text
WORLD MODEL
    ↓ contextualization
WORLD STATE
    ↓
WORKSPACE
```

Cognition interpreta e simula sobre o WorldState.

Agency utiliza o WorldState para decisões.

Learning pode propor alterações no World Model.

---

# 7. MemoryQuery

Componentes não acessam diretamente o armazenamento interno da Memory.

Eles utilizam um contrato de consulta:

```text
MemoryQuery
├── query
├── context
├── goal_context
├── memory_types
├── time_range
├── relevance_threshold
├── confidence_threshold
└── limit
```

Resultado:

```text
MemoryRetrievalResult
├── memories[]
├── relevance
├── confidence
├── provenance
└── retrieval_metadata
```

Fluxo:

```text
WORKSPACE
    │
    │ MemoryQuery
    ▼
MEMORY
    │
    │ MemoryRetrievalResult
    ▼
WORKSPACE
```

A recuperação de uma memória não transforma automaticamente seu conteúdo em fato confirmado.

---

# 8. CognitiveRequest

O processamento cognitivo recebe um contexto explícito.

```text
CognitiveRequest
├── request_id
├── workspace_context
├── objective
├── problem
├── constraints
├── available_evidence
└── required_depth
```

O `workspace_context` representa o contexto relevante, não uma cópia obrigatória de todo o Workspace.

---

# 9. CognitiveResult

Cognition retorna resultados cognitivos, não decisões finais.

```text
CognitiveResult
├── request_id
├── understanding
├── hypotheses
├── inferences
├── candidate_solutions
├── candidate_plans
├── predictions
├── simulations
├── confidence
├── uncertainty
├── assumptions
└── provenance
```

Uma conclusão deve preservar, quando relevante:

```text
CONTENT
CONFIDENCE
EVIDENCE
ASSUMPTIONS
ALTERNATIVES
PROVENANCE
```

Fluxo:

```text
WORKSPACE
    ↓
CognitiveRequest
    ↓
COGNITION
    ↓
CognitiveResult
    ↓
WORKSPACE
```

O resultado cognitivo pode ser utilizado por Agency, mas não obriga Agency a adotá-lo.

---

# 10. DecisionRequest

Agency recebe informação suficiente para decidir dentro de suas responsabilidades.

```text
DecisionRequest
├── request_id
├── active_goal
├── context
├── cognitive_results
├── constraints
├── values
├── risks
└── permissions
```

Agency não deve depender de um resultado cognitivo único quando a decisão exigir comparação de alternativas ou avaliação de risco.

---

# 11. Decision

Uma decisão representa o compromisso operacional de Agency com uma alternativa.

```text
Decision
├── decision_id
├── goal_id
├── selected_option
├── selected_plan
├── rationale
├── expected_outcome
├── confidence
├── risk
└── reversibility
```

Fluxo:

```text
DecisionRequest
    ↓
AGENCY
    ↓
Decision
```

A decisão não garante o resultado esperado. Ela registra a alternativa escolhida com base nas informações disponíveis naquele momento.

---

# 12. ActionIntent

`ActionIntent` é a interface entre Agency e Action System.

```text
ActionIntent
├── intent_id
├── decision_id
├── goal_id
├── action
├── target
├── parameters
├── expected_outcome
├── constraints
├── risk_level
├── authorization
├── success_criteria
└── expiration
```

Fluxo:

```text
AGENCY
    ↓
ActionIntent
    ↓
ACTION SYSTEM
```

Agency define **o que foi decidido**.

Action System determina **como executar**, dentro das capacidades, políticas e permissões disponíveis.

---

# 13. ActionResult

O Action System retorna o resultado da execução.

```text
ActionResult
├── intent_id
├── execution_id
├── status
├── actual_action
├── observed_result
├── errors
├── side_effects
├── timestamp
└── evidence
```

Fluxo:

```text
ActionIntent
    ↓
ACTION SYSTEM
    ↓
ActionResult
```

O Action System não deve transformar automaticamente um resultado de execução em aprendizado persistente. O resultado é uma evidência que pode alimentar a construção de uma Experience.

---

# 14. Experience

Uma Experience contextualiza o que aconteceu.

```text
Experience
├── experience_id
├── context
├── observations
├── action_intent
├── action_result
├── expected_outcome
├── actual_outcome
├── prediction_error
├── consequences
└── timestamp
```

Fluxo:

```text
ACTION RESULT
    +
OBSERVATIONS
    +
EXPECTED OUTCOME
    ↓
EXPERIENCE
```

A Experience pode ser registrada em Episodic Memory e também encaminhada para Learning.

Registrar uma experiência não significa que uma mudança de conhecimento foi validada.

---

# 15. LearningProposal

Learning produz propostas de mudança, não escrita direta em qualquer armazenamento persistente.

```text
LearningProposal
├── proposal_id
├── source_experiences
├── proposed_change
├── target_system
├── evidence
├── confidence
├── expected_benefit
├── risks
└── validation_status
```

Exemplo conceitual:

```text
TARGET = WORLD_MODEL

PROPOSED_CHANGE =
"A ferramenta X falha quando o parâmetro Y está ausente."

EVIDENCE =
[experience_123, experience_129]

CONFIDENCE =
0.91
```

Fluxo:

```text
EXPERIENCE
    ↓
LEARNING
    ↓
LearningProposal
    ↓
VALIDATION
    ↓
CONSOLIDATION
```

Learning não possui autorização implícita para reescrever a mente.

---

# 16. ModelUpdate

Quando uma mudança é validada e consolidada, sua incorporação deve ser versionada.

```text
ModelUpdate
├── update_id
├── target
├── previous_version
├── new_version
├── change
├── evidence
├── confidence
├── reason
├── created_by
└── timestamp
```

Fluxo:

```text
MODEL v1
    ↓
LEARNING
    ↓
LearningProposal
    ↓
VALIDATION
    ↓
CONSOLIDATION
    ↓
MODEL v2
```

A arquitetura deve preservar proveniência e histórico suficiente para explicar como uma mudança ocorreu.

---

# 17. Contrato de Learning e Consolidation

A separação é:

```text
LEARNING
→ avalia experiência.
→ identifica possíveis mudanças.
→ justifica propostas.

CONSOLIDATION
→ valida o processo de incorporação.
→ aplica regras de persistência.
→ cria nova versão do estado persistente.
```

Fluxo:

```text
EXPERIENCE
    ↓
LEARNING
    ↓
LearningProposal
    ↓
VALIDATION
    ↓
ModelUpdate
    ↓
PERSISTENT STATE
```

A consolidação pode rejeitar, adiar ou limitar uma proposta quando evidências forem insuficientes ou conflitos forem detectados.

---

# 18. Contrato completo do ciclo

O Virtual Brain opera através de um ciclo arquitetural único:

```text
ENVIRONMENT
    ↓
VIRTUAL ORGANISM
    ↓
PERCEPTION
    ↓
WorkspaceState
    ↓
MemoryQuery
    ↓
MemoryRetrievalResult
    ↓
CognitiveRequest
    ↓
CognitiveResult
    ↓
DecisionRequest
    ↓
Decision
    ↓
ActionIntent
    ↓
ACTION SYSTEM
    ↓
ActionResult
    ↓
Experience
    ↓
LEARNING
    ↓
LearningProposal
    ↓
CONSOLIDATION
    ↓
ModelUpdate
    ↓
MEMORY / WORLD MODEL / SELF MODEL / STRATEGIES
    ↓
PRÓXIMO CICLO
```

O ciclo não significa que todos os contratos sejam necessariamente executados uma única vez ou em sequência rígida. Cognition pode solicitar múltiplas consultas, Agency pode solicitar novas análises e Learning pode avaliar experiências fora do ciclo imediato.

O princípio é que todos os fluxos retornam a contratos explícitos.

---

# 19. Contratos e responsabilidades

| Contrato | Produzido por | Consumido por | Persistência |
|---|---|---|---|
| `WorkspaceState` | Workspace | Cognition, Agency | Transitória |
| `SelfState` | Self | Workspace, Cognition, Agency | Projeção transitória |
| `WorldState` | World Model | Workspace, Cognition, Agency | Projeção transitória |
| `MemoryQuery` | Workspace/Cognition | Memory | Não persistente |
| `MemoryRetrievalResult` | Memory | Workspace/Cognition | Não persistente |
| `CognitiveRequest` | Workspace/Agency | Cognition | Não persistente |
| `CognitiveResult` | Cognition | Workspace/Agency | Normalmente transitória |
| `DecisionRequest` | Workspace/Agency | Agency | Não persistente |
| `Decision` | Agency | Workspace/Action System | Registro opcional |
| `ActionIntent` | Agency | Action System | Registro auditável |
| `ActionResult` | Action System | Workspace/Learning | Registro de execução |
| `Experience` | Ciclo de interação | Memory/Learning | Episódica |
| `LearningProposal` | Learning | Consolidation | Temporária/auditável |
| `ModelUpdate` | Consolidation | Owner do modelo | Persistente |

---

# 20. Fronteiras proibidas

Os seguintes padrões são proibidos arquiteturalmente:

```text
COGNITION → escrever diretamente em MEMORY
```

```text
AGENCY → executar diretamente uma ferramenta
```

```text
WORKSPACE → alterar diretamente SELF MODEL
```

```text
LEARNING → sobrescrever diretamente WORLD MODEL
```

```text
MEMORY → tomar decisões
```

```text
ACTION SYSTEM → escolher objetivos
```

```text
SELF → executar ações diretamente
```

A comunicação deve passar pelo contrato correspondente.

---

# 21. Princípio de proveniência

Todo dado persistente importante deve poder responder:

```text
DE ONDE VEIO?
QUANDO FOI CRIADO?
QUEM O PROPÔS?
QUAL EVIDÊNCIA O SUSTENTA?
QUAL ERA A VERSÃO ANTERIOR?
POR QUE FOI ALTERADO?
```

Isso é especialmente importante para:

```text
MEMORIES
BELIEFS
WORLD MODEL
SELF MODEL
STRATEGIES
LEARNED POLICIES
```

A proveniência é parte do contrato de confiança do sistema.

---

# 22. Princípio de versionamento

Todo estado persistente relevante deve possuir versão.

```text
MODEL v1
    ↓
UPDATE 001
    ↓
MODEL v2
    ↓
UPDATE 002
    ↓
MODEL v3
```

Uma atualização deve referenciar a versão sobre a qual foi construída.

Se duas atualizações conflitantes forem propostas sobre a mesma versão:

```text
MODEL v5
   ├── UPDATE A
   └── UPDATE B
```

O sistema deve detectar o conflito antes de consolidar uma nova versão.

Isso evita atualizações silenciosas e conflitos de estado.

---

# 23. Princípio de consistência

Cada contrato deve manter quatro propriedades:

```text
IDENTITY
→ quem produziu o dado.

PROVENANCE
→ de onde veio.

VERSION
→ contra qual estado foi produzido.

AUTHORITY
→ quem pode validá-lo e persistí-lo.
```

Um dado sem essas propriedades pode ser utilizado como contexto temporário, mas não deve ser tratado automaticamente como conhecimento persistente confiável.

---

# 24. Princípios invariantes

1. Todo estado persistente possui um proprietário autoritativo.
2. Nenhum componente pode escrever diretamente no estado persistente de outro.
3. Leitura não implica autoridade de escrita.
4. Proposta de mudança não implica aprovação.
5. Decisão não implica execução.
6. Execução não implica aprendizado.
7. Experiência não implica conhecimento consolidado.
8. Inferência não implica fato.
9. Memória recuperada não implica verdade.
10. Learning não possui autoridade irrestrita sobre o sistema.
11. Workspace mantém projeções contextuais, não fontes definitivas persistentes.
12. Cognition produz possibilidades e avaliações; Agency produz decisões.
13. Agency produz Action Intent; Action System executa.
14. ActionResult fornece evidência; Learning avalia a mudança.
15. Consolidation incorpora mudanças persistentes aprovadas.
16. Mudanças persistentes devem possuir versão e proveniência.
17. Conflitos de versão devem ser detectados antes da consolidação.
18. Cada contrato deve possuir limites claros de responsabilidade.

---

# 25. Definição final

> **Data Contracts são as interfaces formais que conectam os componentes do Virtual Brain. Eles definem quais dados circulam, quem os produz, quem pode consumi-los, quem possui autoridade sobre cada estado, como mudanças são propostas e como alterações persistentes são versionadas e consolidadas.**

A partir desses contratos, a arquitetura deixa de ser apenas uma coleção de módulos conceituais e passa a possuir uma regra operacional fundamental:

```text
EVERY COMPONENT
KNOWS

WHAT IT RECEIVES
WHAT IT PRODUCES
WHAT IT MAY READ
WHAT IT MAY CHANGE
WHAT IT MAY NOT CHANGE
WHO OWNS THE STATE
```

Esse princípio permite que o Virtual Brain evolua para uma implementação real sem perder as fronteiras conceituais estabelecidas na teoria.

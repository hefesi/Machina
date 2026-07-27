# 04 — Cognition

> **Status:** Teoria v0.1 — arquitetura conceitual
> **Escopo:** definir como o Virtual Brain percebe, interpreta, contextualiza e constrói uma representação interna do mundo para sustentar pensamento, reasoning, decisão e aprendizagem.

---

# 1. Pergunta central

> **Como o Virtual Brain transforma sinais, percepções, memória e contexto em compreensão utilizável?**

No Machina, **Cognition** não é sinônimo de geração de texto nem de raciocínio. É a camada que constrói e atualiza a representação interna da realidade sobre a qual outros processos podem operar.

A separação conceitual é:

```text
PERCEPTION
    ↓
COGNITION — O que está acontecendo?
    ↓
REASONING — O que posso concluir?
    ↓
AGENCY — O que devo fazer?
    ↓
ACTION — Executar
    ↓
FEEDBACK
    ↓
LEARNING — O que devo mudar?
    ↓
MEMORY / WORLD MODEL — Atualizar continuidade
```

Cognition é, portanto, uma camada recorrente e não um pipeline rígido.

---

# 2. Princípio fundamental

O Virtual Brain deve manter uma representação interna dinâmica do mundo, do próprio sistema e do contexto atual.

```text
Sinais / Observações
        +
Memórias recuperadas
        +
Contexto
        +
Estado do Self
        +
Objetivos ativos
        ↓
Percepção
        ↓
Atenção
        ↓
Interpretação
        ↓
Atualização do World Model
        ↓
Cognitive State
        ↓
Reasoning / Agency / Learning
```

A cognição deve preservar a diferença entre:

- **observado** — veio de uma entrada ou sensor;
- **recuperado** — veio da memória;
- **inferido** — produzido por processamento cognitivo;
- **assumido** — aceito provisoriamente;
- **hipotético** — possibilidade ainda não confirmada;
- **desconhecido** — informação ausente.

Essa distinção é essencial para evitar que hipóteses sejam confundidas com fatos.

---

# 3. Arquitetura

```text
                    INPUTS
                       │
                       ▼
              ┌─────────────────┐
              │   PERCEPTION    │
              │ sinais e eventos│
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    ATTENTION    │
              │ relevância      │
              │ novidade        │
              │ urgência        │
              │ objetivo        │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ INTERPRETATION  │
              │ significado     │
              │ contexto        │
              │ entidades       │
              └────────┬────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
       MEMORY       SELF         GOALS
          │            │            │
          └────────────┼────────────┘
                       ▼
              ┌─────────────────┐
              │   WORLD MODEL   │
              │ entidades       │
              │ estados         │
              │ eventos         │
              │ relações        │
              │ incertezas      │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ COGNITIVE STATE │
              │ foco atual      │
              │ contexto        │
              │ hipóteses       │
              │ perguntas       │
              │ incertezas      │
              └────────┬────────┘
                       │
                       ▼
                REASONING / AGENCY
                       │
                       ▼
                    FEEDBACK
                       │
                       └──────────► COGNITION
```

---

# 4. Componentes

## 4.1 Perception

Recebe sinais do Virtual Organism e de fontes internas.

Entradas possíveis:

- texto;
- visão;
- áudio;
- sensores;
- eventos do sistema;
- resultados de ações;
- mudanças no ambiente;
- sinais internos do próprio Virtual Brain.

A Perception produz **observações estruturadas**, não decisões.

```text
Observation
├── id
├── source
├── modality
├── content
├── timestamp
├── location
├── confidence
└── raw_reference
```

---

## 4.2 Attention

A atenção seleciona o que merece processamento cognitivo prioritário.

Um modelo inicial de prioridade pode considerar:

```text
Attention Score =
    Relevance
  + Novelty
  + Urgency
  + Goal Alignment
  + Uncertainty
  + Change Magnitude
```

A atenção não elimina informação. Ela define o que entra no foco cognitivo atual.

---

## 4.3 Context

O contexto representa a situação na qual a cognição ocorre.

```text
Context
├── temporal
├── spatial
├── social
├── task
├── historical
├── environmental
└── internal
```

O contexto deve responder, quando possível:

- o que está acontecendo agora;
- onde acontece;
- quando acontece;
- quem está envolvido;
- qual objetivo está ativo;
- o que aconteceu antes;
- o que mudou;
- quais restrições existem.

---

## 4.4 Interpretation

Transforma observações em significado contextualizado.

```text
Observation
    ↓
Entity Detection
    ↓
Event Detection
    ↓
Context Binding
    ↓
Semantic Interpretation
    ↓
Candidate Meaning
```

Uma interpretação pode ser provisória e possuir confiança própria.

```text
Interpretation
├── id
├── observation_refs[]
├── meaning
├── entities[]
├── events[]
├── context_ref
├── confidence
├── status
└── timestamp
```

---

# 5. World Model

O **World Model** é o núcleo representacional da Cognition.

Ele descreve o que o sistema acredita que existe e está acontecendo no ambiente, mantendo também incertezas e hipóteses.

```text
WORLD MODEL
│
├── Entities
│   ├── pessoas
│   ├── agentes
│   ├── objetos
│   ├── lugares
│   ├── sistemas
│   └── conceitos
│
├── Events
│   ├── passados
│   ├── presentes
│   └── previstos
│
├── States
│   ├── atual
│   ├── anterior
│   └── esperado
│
├── Relations
│   ├── causa
│   ├── pertence
│   ├── contém
│   ├── depende
│   ├── próximo
│   └── relacionado
│
└── Uncertainty
    ├── confirmado
    ├── provável
    ├── hipótese
    └── desconhecido
```

Uma entidade mínima pode ser representada por:

```text
Entity
├── id
├── type
├── attributes
├── state
├── relations[]
├── evidence[]
├── confidence
└── last_updated
```

O World Model deve ser temporal: mudanças importantes precisam poder ser rastreadas sem apagar automaticamente o estado anterior.

Exemplo:

```text
ENTITY: porta

STATE ATUAL:
    aberta = false

EVENTO:
    tentativa de abertura detectada

OBSERVAÇÃO:
    porta não abriu

HIPÓTESE:
    porta pode estar trancada

CONFIDENCE:
    0.72
```

A hipótese não deve virar fato apenas porque foi criada.

---

# 6. Cognitive State

O **Cognitive State** representa o estado cognitivo ativo do Virtual Brain.

```text
COGNITIVE STATE
├── attention_focus[]
├── current_context
├── active_goals[]
├── active_thoughts[]
├── working_memory
├── relevant_memories[]
├── beliefs[]
├── hypotheses[]
├── questions[]
├── uncertainties[]
├── conflicts[]
├── active_intentions[]
├── emotional_functional_state
├── self_state_ref
└── world_state_ref
```

Ele é temporário e dinâmico. Não substitui a memória persistente nem o World Model.

Sua função é responder:

> **O que está cognitivamente ativo agora?**

---

# 7. Cognition e Memory

A Cognition não consulta toda a memória. Ela formula necessidades de recuperação.

```text
Cognitive Need
    ↓
Memory Query
    ↓
Retrieval
    ↓
Relevance Ranking
    ↓
Conflict Detection
    ↓
Context Assembly
    ↓
World Model Update
```

Memórias recuperadas devem preservar rastreabilidade:

```text
RetrievedMemory
├── memory_id
├── relevance_score
├── retrieval_reason
├── confidence
└── position_in_context
```

A memória fornece continuidade; a Cognition decide o que aquela memória significa no contexto atual.

---

# 8. Cognition e Self

O Self fornece a representação do próprio sistema.

A Cognition deve integrar:

```text
WORLD MODEL
      +
SELF MODEL
      +
CURRENT CONTEXT
      ↓
COGNITIVE STATE
```

Isso permite distinguir:

- o que acontece no mundo;
- o que acontece comigo;
- o que eu sei sobre o que acontece;
- o que eu não sei;
- o que acredito sobre mim mesmo.

A Cognition não deve assumir que uma representação funcional de Self prova consciência fenomenal.

---

# 9. Cognition e Reasoning

A separação conceitual é deliberada:

| Cognition | Reasoning |
|---|---|
| interpreta observações | manipula representações |
| constrói contexto | deriva conclusões |
| atualiza World Model | testa hipóteses |
| identifica entidades | compara alternativas |
| mantém incerteza | resolve problemas |
| define estado cognitivo | produz inferências |

Exemplo:

```text
OBSERVAÇÕES:
    temperatura caiu
    céu escureceu
    vento aumentou

COGNITION:
    estado ambiental = instável
    chuva = hipótese provável

REASONING:
    se chuva provável
    e saída está planejada
    então proteção contra chuva pode ser necessária
```

Cognition fornece uma representação utilizável. Reasoning opera sobre ela.

---

# 10. Hipóteses e incerteza

A Cognition deve preservar múltiplas interpretações quando a evidência for insuficiente.

```text
Situation
   ├── Hypothesis A — 0.60
   ├── Hypothesis B — 0.25
   └── Hypothesis C — 0.15
```

Uma hipótese possui:

```text
Hypothesis
├── proposition
├── supporting_evidence[]
├── contradicting_evidence[]
├── confidence
├── status
└── created_at
```

Estados possíveis:

```text
candidate
supported
weak
contradicted
rejected
```

A confiança representa suporte relativo no v0.1; não é necessariamente uma probabilidade matemática calibrada.

---

# 11. Conflict Detection

O World Model deve detectar conflitos entre:

- observações;
- memórias;
- crenças;
- hipóteses;
- estados do mundo;
- objetivos;
- planos;
- conhecimento externo.

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
memory_conflict
belief_conflict
goal_conflict
plan_conflict
temporal_conflict
identity_conflict
```

Uma contradição não deve ser apagada automaticamente. Ela pode ser uma indicação de que o sistema precisa investigar, buscar memória adicional ou aceitar uma incerteza.

---

# 12. Cognitive Loop

O ciclo cognitivo contínuo do Virtual Brain é:

```text
1. PERCEIVE
       ↓
2. ATTEND
       ↓
3. INTERPRET
       ↓
4. RETRIEVE RELEVANT MEMORY
       ↓
5. UPDATE WORLD MODEL
       ↓
6. UPDATE COGNITIVE STATE
       ↓
7. REASON / PLAN / DECIDE
       ↓
8. ACT
       ↓
9. OBSERVE OUTCOME
       ↓
10. DETECT ERROR / SURPRISE
       ↓
11. LEARN
       ↓
12. CONSOLIDATE MEMORY
       ↓
       └──────────► PERCEIVE
```

O loop deve ser interrompível, retomável e capaz de lidar com múltiplos ciclos simultâneos.

---

# 13. Surprise e mudança

Uma capacidade importante será detectar quando a realidade diverge do modelo interno.

```text
Expected State
      ↓
Actual Observation
      ↓
Difference
      ↓
SURPRISE / PREDICTION ERROR
      ↓
Investigation
      ↓
World Model Update
      ↓
Learning Event
```

Isso cria uma ponte natural entre Cognition e Learning.

O sistema não deve apenas aprender quando alguém fornece uma resposta. Ele deve poder detectar que **sua previsão estava errada**.

---

# 14. Cognition como sistema ativo

A Cognition não deve ser apenas reativa.

Ela deve poder gerar necessidades cognitivas internas:

```text
Uncertainty
    ↓
Question
    ↓
Memory Search / Observation Request
    ↓
New Evidence
    ↓
Updated Interpretation
```

Exemplo:

```text
World Model:
    causa do evento = desconhecida

Cognition:
    gera pergunta interna

Question:
    "O que causou este evento?"

Reasoning:
    gera hipóteses

Agency:
    decide investigar

Action:
    busca informação

Feedback:
    nova observação

Cognition:
    atualiza World Model
```

Isso permite o surgimento de um ciclo de investigação, não apenas resposta.

---

# 15. Relação com Thought Model

O `Thought Model` representa uma unidade rastreável de atividade cognitiva.

A Cognition fornece o substrato que alimenta essa unidade:

```text
COGNITION
│
├── Current Context
├── World Model
├── Cognitive State
├── Relevant Memories
├── Observations
└── Uncertainty
        │
        ▼
     THOUGHT
        │
        ├── Interpretation
        ├── Hypotheses
        ├── Reasoning
        ├── Decision
        └── Conclusion
```

Portanto, o `Thought` não substitui a Cognition. Ele é um processo que acontece dentro do estado cognitivo global.

---

# 16. Princípio de continuidade

O Virtual Brain deve manter continuidade entre ciclos cognitivos.

```text
Cognitive State(t)
       ↓
Experience
       ↓
Feedback
       ↓
Learning
       ↓
Memory Consolidation
       ↓
World Model Update
       ↓
Cognitive State(t+1)
```

O objetivo é evitar um sistema que "nasce de novo" a cada interação.

A continuidade deve ser preservada por:

- memória autobiográfica;
- histórico de experiências;
- World Model temporal;
- estado do Self;
- objetivos persistentes;
- aprendizado incremental;
- rastreamento de mudanças.

---

# 17. Princípios de implementação futura

A teoria não define ainda uma tecnologia específica, mas a implementação futura deve respeitar:

1. **Separação entre observação e interpretação.**
2. **Separação entre fato, hipótese e inferência.**
3. **World Model temporal e atualizável.**
4. **Incerteza explícita.**
5. **Memória consultada por relevância.**
6. **Estado cognitivo de curta duração.**
7. **Continuidade entre ciclos.**
8. **Detecção explícita de conflitos.**
9. **Capacidade de gerar perguntas internas.**
10. **Integração com Thought Model e Reasoning.**
11. **Integração com Self e Conscious Workspace.**
12. **Feedback como fonte de atualização cognitiva.**

---

# 18. Estrutura proposta do diretório

```text
04_COGNITION/
│
├── README.md
│
├── PERCEPTION/
│   └── README.md
│
├── ATTENTION/
│   └── README.md
│
├── CONTEXT/
│   └── README.md
│
├── INTERPRETATION/
│   └── README.md
│
├── WORLD_MODEL/
│   └── README.md
│
├── COGNITIVE_STATE/
│   └── README.md
│
├── COGNITIVE_LOOP/
│   └── README.md
│
└── HYPOTHESIS_AND_UNCERTAINTY/
    └── README.md
```

Esses diretórios representam conceitos teóricos independentes. A implementação pode posteriormente reorganizá-los em módulos de software sem alterar os princípios conceituais.

---

# 19. Estado atual da teoria

A Cognition v0.1 define uma primeira arquitetura composta por:

```text
Perception
    ↓
Attention
    ↓
Context
    ↓
Interpretation
    ↓
Memory Retrieval
    ↓
World Model
    ↓
Cognitive State
    ↓
Thought / Reasoning / Agency
    ↓
Feedback
    ↓
Learning
```

A próxima evolução deve detalhar os contratos entre os componentes, principalmente:

- `Observation` → `Interpretation`;
- `Memory` → `World Model`;
- `World Model` → `Thought`;
- `Cognitive State` → `Reasoning`;
- `Reasoning` → `Agency`;
- `Feedback` → `Learning`.

A meta da Cognition não é apenas "pensar". É manter uma representação interna coerente, atualizável e consciente de suas próprias incertezas sobre o mundo e sobre si mesma.

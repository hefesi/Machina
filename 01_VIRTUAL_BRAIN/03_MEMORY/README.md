# 03 — Memory

## Persistência, recuperação e organização da experiência

> **Pergunta fundamental:** O que o Virtual Brain preserva, recupera e utiliza de sua história?

Memory é o sistema responsável por preservar e recuperar informações ao longo do tempo. Ela fornece continuidade informacional para Cognition, Workspace, Self e Learning.

Memory não é Working Memory, não é Cognition e não é Learning.

```text
MEMORY
→ preserva e recupera.

WORKSPACE
→ mantém o presente ativo.

COGNITION
→ interpreta e transforma informação.

LEARNING
→ decide e produz mudanças persistentes a partir da experiência.
```

---

# 1. Arquitetura

```text
MEMORY
│
├── EPISODIC MEMORY
│   └── experiências e eventos vividos
│
├── SEMANTIC MEMORY
│   └── fatos, conceitos e conhecimento
│
├── PROCEDURAL MEMORY
│   └── habilidades e procedimentos
│
├── AUTOBIOGRAPHICAL MEMORY
│   └── eventos relevantes para a história do Self
│
└── PROSPECTIVE MEMORY
    └── compromissos e intenções persistentes
```

A Working Memory não está nesta árvore. Ela pertence ao Conscious Workspace.

---

# 2. Episodic Memory

Preserva experiências contextualizadas:

```text
EPISODE
├── TIME
├── CONTEXT
├── OBSERVATION
├── ACTION
├── EXPECTED OUTCOME
├── ACTUAL OUTCOME
├── CONSEQUENCE
└── EVALUATION
```

A experiência pode ser registrada antes de qualquer interpretação completa.

---

# 3. Semantic Memory

Preserva conhecimento generalizado:

```text
CONCEPT
├── PROPOSITION
├── EVIDENCE
├── SOURCES
├── CONFIDENCE
├── CONTEXT
├── TIMESTAMP
└── REVISION HISTORY
```

Conhecimento pode possuir diferentes graus de confiança e não deve ser tratado como certeza absoluta.

---

# 4. Procedural Memory

Preserva formas aprendidas de executar tarefas:

```text
SKILL
├── PRECONDITIONS
├── STEPS
├── EXPECTED OUTCOMES
├── SUCCESS RATE
├── FAILURE MODES
└── CONTEXT OF VALIDITY
```

Procedural Memory pode ser atualizada por Learning, mas a decisão de que uma habilidade foi aprendida pertence ao processo de Learning.

---

# 5. Autobiographical Memory

Preserva episódios que possuem relevância para a história pessoal do sistema.

```text
AUTOBIOGRAPHICAL MEMORY
        ↓
SELF MODEL
        ↓
SELF STATE
```

A distinção é:

```text
MEMORY
→ "O que aconteceu comigo?"

SELF MODEL
→ "O que isso diz sobre quem eu sou?"

IDENTITY CONTINUITY
→ "Como isso se relaciona causalmente com minha trajetória?"
```

---

# 6. Prospective Memory

Preserva compromissos e intenções que precisam sobreviver ao tempo.

```text
AGENCY
→ cria objetivos e planos ativos.

PROSPECTIVE MEMORY
→ persiste compromissos e intenções relevantes.

AGENCY
→ recupera e reativa quando apropriado.
```

Prospective Memory não substitui Agency.

---

# 7. Memory e Workspace

```text
MEMORY
    ↓ retrieval
WORKSPACE
    ↓ active manipulation
COGNITION
    ↓ result
WORKSPACE
```

O Workspace possui Working Memory temporária. Memory fornece conteúdo persistente quando solicitado ou quando mecanismos de recuperação consideram relevante.

---

# 8. Memory e Cognition

Cognition consulta Memory para:

- recuperar experiências semelhantes;
- obter conhecimento;
- consultar habilidades;
- recuperar informações autobiográficas;
- encontrar evidências para hipóteses;
- comparar situações atuais com experiências anteriores.

```text
COGNITION
    ↓ query
MEMORY
    ↓ retrieval
WORKSPACE
    ↓
COGNITION
```

Memory não raciocina. Ela fornece material para o raciocínio.

---

# 9. Memory e Learning

A separação fundamental é:

```text
MEMORY
= preserva e recupera.

LEARNING
= avalia experiências e produz mudanças.
```

Uma experiência pode ser armazenada como episódio mesmo antes de qualquer aprendizado consolidado.

```text
EXPERIENCE
   ├──→ EPISODIC MEMORY
   │
   └──→ LEARNING
          ↓
      CHANGE PROPOSAL
          ├──→ SEMANTIC MEMORY
          ├──→ PROCEDURAL MEMORY
          ├──→ SELF MODEL
          └──→ WORLD MODEL
```

Learning não é simplesmente uma etapa posterior de armazenamento. É o processo que determina o que deve mudar e por quê.

---

# 10. Consolidação

Memory pode executar mecanismos de consolidação, mas a decisão de que uma experiência representa conhecimento aprendido pertence a Learning.

```text
EXPERIENCE
    ↓
EPISODIC MEMORY
    ↓
LEARNING
    ↓
VALIDATED CHANGE
    ↓
MEMORY CONSOLIDATION
    ↓
LONG-TERM KNOWLEDGE
```

Assim:

```text
LEARNING
→ decide a mudança.

MEMORY
→ persiste e organiza o resultado.
```

---

# 11. Estados de informação

Uma informação pode possuir estados epistemológicos:

```text
RAW
 ↓
UNVERIFIED
 ↓
VALIDATED
 ↓
CONFIRMED
 ↓
CONSOLIDATED
```

O sistema deve distinguir:

- o que sabe;
- o que acredita;
- o que suspeita;
- o que não sabe.

---

# 12. Belief Updating

```text
BELIEF
    +
NEW EVIDENCE
    ↓
EVALUATION
    ↓
BELIEF UPDATE
```

A confiança pode aumentar, diminuir, permanecer estável ou ser invalidada.

Belief updating é uma operação de Cognition/Learning que pode resultar em atualização da Semantic Memory.

---

# 13. Forgetting

Esquecer não precisa significar apagar.

```text
ACTIVE
  ↓
LOW PRIORITY
  ↓
ARCHIVED
```

O sistema pode reduzir:

- acessibilidade;
- prioridade;
- relevância;
- confiança.

O histórico pode permanecer preservado mesmo quando deixa de ser facilmente acessível.

---

# 14. Reconsolidation

Uma memória recuperada pode ser reinterpretada à luz de novas evidências.

```text
MEMORY
    ↓
RECALL
    ↓
REINTERPRETATION
    ↓
LEARNING
    ↓
RECONSOLIDATION
```

A reconsolidação deve preservar proveniência e histórico de revisão quando a informação original possui valor histórico.

---

# 15. Contrato de Memory

```text
WORKSPACE
→ mantém Working Memory temporária.

MEMORY
→ persiste e recupera informação.

COGNITION
→ interpreta e raciocina sobre informação recuperada.

LEARNING
→ avalia experiências e propõe mudanças.

SELF
→ utiliza memória autobiográfica para manter continuidade.

AGENCY
→ utiliza memória para informar objetivos e decisões.
```

> **Memory preserva a história informacional do Virtual Brain. Ela não é o lugar onde o sistema pensa; é o sistema que permite que o pensamento tenha passado.**

# 06 — Learning

## Transformação da experiência em mudança persistente

> **Pergunta fundamental:** O que o Virtual Brain deve mudar em si mesmo por causa do que experimentou?

Learning é o sistema responsável por transformar experiências e evidências em mudanças persistentes no Virtual Brain.

A distinção central é:

```text
MEMORY
→ preserva e recupera.

LEARNING
→ avalia experiências e produz mudanças.
```

Learning não é simplesmente armazenar mais dados. É o processo pelo qual o sistema se torna diferente por causa daquilo que viveu.

---

# 1. Estrutura

```text
LEARNING
│
├── EXPERIENCE EVALUATION
├── ERROR ANALYSIS
├── BELIEF UPDATING
├── MODEL UPDATING
├── SKILL ACQUISITION
├── STRATEGY UPDATE
├── SELF-MODEL UPDATE
├── CONSOLIDATION CONTROL
├── CONTINUAL LEARNING
└── META-LEARNING
```

---

# 2. Experiência

Uma experiência é uma transição relevante:

```text
STATE(t)
   ↓
ACTION(t)
   ↓
STATE(t+1)
```

Pode conter:

```text
EXPERIENCE
├── CONTEXT
├── OBSERVATION
├── ACTION
├── EXPECTED OUTCOME
├── ACTUAL OUTCOME
├── ERROR
├── CONSEQUENCE
└── EVALUATION
```

A experiência pode ser registrada na Episodic Memory, mas o registro não significa que aprendizado já ocorreu.

---

# 3. Experiência → Aprendizado

```text
EXPERIENCE
    ├──→ EPISODIC MEMORY
    │
    └──→ LEARNING
           ↓
      EVALUATION
           ↓
      CHANGE PROPOSAL
```

Learning determina se a experiência justifica alguma mudança e qual tipo de mudança é apropriado.

---

# 4. Destinos do aprendizado

Uma mudança aprendida pode afetar diferentes partes do sistema:

```text
LEARNING RESULT
      ├──→ MEMORY
      ├──→ WORLD MODEL
      ├──→ SELF MODEL
      ├──→ STRATEGIES
      └──→ AGENCY POLICIES
```

Portanto:

```text
LEARNING
≠
UPDATE MEMORY ONLY
```

Learning pode atualizar Memory, mas também pode atualizar modelos, habilidades, estratégias e autorrepresentação.

---

# 5. Learning e Memory

A separação é explícita:

```text
MEMORY
→ guarda a experiência e o conhecimento.

LEARNING
→ determina o significado da experiência e quais modelos devem mudar.

MEMORY CONSOLIDATION
→ persiste e organiza mudanças aprovadas.
```

Fluxo:

```text
EXPERIENCE
    ↓
EPISODIC MEMORY
    ↓
LEARNING
    ↓
VALIDATED CHANGE
    ├──→ SEMANTIC MEMORY
    ├──→ PROCEDURAL MEMORY
    ├──→ SELF MODEL
    └──→ WORLD MODEL
```

---

# 6. Error e Prediction Error

O aprendizado é fortemente influenciado pela diferença entre expectativa e resultado.

```text
EXPECTED OUTCOME
        ↓
ACTION
        ↓
ACTUAL OUTCOME
        ↓
PREDICTION ERROR
        ↓
EVALUATION
        ↓
LEARNING
```

Prediction Error não é necessariamente uma falha. Ele pode indicar que o modelo interno está incompleto ou incorreto.

---

# 7. Belief Updating

Learning pode atualizar crenças quando novas evidências justificam mudança.

```text
BELIEF
    +
NEW EVIDENCE
    ↓
EVALUATION
    ↓
BELIEF UPDATE
    ↓
SEMANTIC MEMORY / WORLD MODEL
```

Uma crença pode:

- ganhar confiança;
- perder confiança;
- permanecer estável;
- ser invalidada;
- ser substituída por uma hipótese melhor.

Cada mudança deve manter evidências e histórico quando apropriado.

---

# 8. Consolidação

Nem toda experiência deve alterar imediatamente os modelos centrais.

```text
EXPERIENCE
    ↓
EPISODIC MEMORY
    ↓
LEARNING
    ↓
REVIEW
    ↓
VALIDATION
    ↓
CHANGE PROPOSAL
    ↓
CONSOLIDATION
```

A consolidação é um mecanismo de persistência controlada. Ela não substitui Learning.

Estados possíveis:

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

---

# 9. Self Model Update

Learning pode atualizar o modelo que o sistema possui de si mesmo.

```text
EXPERIENCE
    ↓
EVIDENCE
    ↓
LEARNING
    ↓
SELF MODEL UPDATE
    ↓
SELF STATE
    ↓
WORKSPACE
```

O Self Model pode representar:

- conhecimento;
- habilidades;
- limitações;
- incertezas;
- histórico de erros;
- estratégias eficazes;
- estratégias ineficazes.

Learning é responsável pela atualização baseada em evidências; Self é responsável por manter identidade e continuidade.

---

# 10. Learning e Agency

Agency decide e emite Action Intent.

Action System executa.

Learning avalia o resultado.

```text
AGENCY
    ↓
ACTION INTENT
    ↓
ACTION SYSTEM
    ↓
VIRTUAL ORGANISM
    ↓
ENVIRONMENT
    ↓
OBSERVATION
    ↓
EXPERIENCE
    ↓
LEARNING
```

Learning pode descobrir que determinada estratégia funciona ou falha e atualizar o conhecimento utilizado por Agency.

---

# 11. Continual Learning

O Virtual Brain deve aprender continuamente sem destruir conhecimento importante.

```text
EXPERIENCE 1
    ↓
LEARNING
    ↓
EXPERIENCE 2
    ↓
LEARNING
    ↓
EXPERIENCE 3
    ↓
LEARNING
    ↓
...
```

O objetivo é:

```text
NEW KNOWLEDGE
      +
OLD KNOWLEDGE
      ↓
INTEGRATION
      ↓
STABLE ADAPTIVE KNOWLEDGE
```

Isso exige mecanismos contra **catastrophic forgetting**.

---

# 12. Forgetting e estabilidade

Learning pode determinar que uma informação perdeu relevância, mas isso não implica apagar imediatamente o registro histórico.

```text
LEARNING
    ↓
RELEVANCE CHANGE
    ↓
ACCESSIBILITY / PRIORITY UPDATE
    ↓
MEMORY
```

A arquitetura deve preservar histórico importante enquanto permite que conhecimento obsoleto tenha menor influência.

---

# 13. Reconsolidation

Quando conhecimento é recuperado e confrontado com novas evidências:

```text
MEMORY
    ↓
RECALL
    ↓
NEW EVIDENCE
    ↓
LEARNING
    ↓
REINTERPRETATION
    ↓
RECONSOLIDATION
```

A versão atualizada deve preservar proveniência e histórico de revisão quando necessário.

---

# 14. Meta-Learning

Learning também pode aprender sobre seu próprio processo.

```text
LEARNING
    ↓
MONITOR LEARNING
    ↓
IDENTIFY PATTERNS
    ↓
OPTIMIZE LEARNING STRATEGIES
```

Pode descobrir:

- quais fontes são mais confiáveis;
- quais estratégias funcionam melhor;
- onde ocorrem mais erros;
- quando buscar mais informação;
- quando pedir ajuda;
- quais tipos de problemas exigem mais raciocínio.

```text
LEARNING
    ↓
LEARN HOW TO LEARN
```

---

# 15. Learning como transformação

Uma formulação conceitual:

```text
LEARNING
=
EXPERIENCE
+
EVIDENCE
+
EVALUATION
+
ERROR
+
MODEL UPDATE
+
CONSOLIDATION
```

O resultado é uma mudança persistente:

```text
EXPERIENCE
    ↓
INTERPRETATION
    ↓
LEARNING
    ↓
MODEL / KNOWLEDGE / SKILL CHANGE
    ↓
FUTURE BEHAVIOR
```

O objetivo não é apenas saber mais.

> **É tornar-se diferente por causa do que foi aprendido.**

---

# 16. O ciclo cognitivo global

Learning não cria um segundo ciclo independente. Ele opera sobre as experiências produzidas pelo ciclo único do Virtual Brain.

```text
ENVIRONMENT
    ↓
VIRTUAL ORGANISM
    ↓
PERCEPTION
    ↓
WORKSPACE
    ↕
MEMORY ↔ COGNITION
    ↓
AGENCY
    ↓
ACTION INTENT
    ↓
ACTION SYSTEM
    ↓
VIRTUAL ORGANISM
    ↓
ENVIRONMENT
```

A experiência gerada pelo ciclo alimenta Learning:

```text
EXPERIENCE
    ↓
LEARNING
    ├──→ MEMORY
    ├──→ WORLD MODEL
    ├──→ SELF MODEL
    └──→ STRATEGIES
```

Assim, Learning altera o sistema que participará do próximo ciclo.

---

# 17. Trajetória do Virtual Brain

```text
BRAIN(t)
    ↓
EXPERIENCE(t)
    ↓
LEARNING(t)
    ↓
BRAIN(t+1)
```

O Brain em `t+1` é consequência das experiências e mudanças acumuladas em `t`.

Isso cria uma propriedade fundamental:

> **O Virtual Brain possui história e pode ser transformado por sua história.**

---

# 18. Contrato de Learning

```text
MEMORY
→ registra e preserva experiências.

COGNITION
→ interpreta, raciocina e produz hipóteses.

AGENCY
→ escolhe e age por meio de Action Intent.

ACTION SYSTEM
→ executa.

LEARNING
→ avalia a experiência e determina mudanças.

MEMORY / MODELS / SELF / STRATEGIES
→ recebem mudanças persistentes aprovadas.
```

> **Learning é a ponte entre experiência e transformação. Ele permite que o Virtual Brain preserve sua história, mas não permaneça preso a ela: o sistema aprende, atualiza seus modelos e entra no próximo ciclo como uma entidade modificada.**

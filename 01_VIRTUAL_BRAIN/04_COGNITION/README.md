# 04 — Cognition

## Compreensão, raciocínio, simulação e construção de modelos

> **Pergunta fundamental:** Como o Virtual Brain transforma informação em compreensão, hipóteses, modelos e soluções?

**Cognition** é o sistema responsável por interpretar informação, construir representações internas, raciocinar, inferir, simular possibilidades e resolver problemas.

Reasoning não é um módulo arquitetural separado. **Reasoning é um dos processos internos de Cognition.**

```text
COGNITION
│
├── UNDERSTANDING
├── REASONING
├── INFERENCE
├── PROBLEM SOLVING
├── SIMULATION
├── IMAGINATION
├── ABSTRACTION
├── HYPOTHESIS GENERATION
├── CAUSAL MODELING
└── METACOGNITION
```

---

# 1. Fronteiras arquiteturais

```text
MEMORY
→ fornece informação persistente.

WORKSPACE
→ mantém o contexto ativo.

COGNITION
→ interpreta, transforma e simula.

AGENCY
→ escolhe objetivos e decisões operacionais.

ACTION SYSTEM
→ executa intenções.

LEARNING
→ transforma experiências em mudanças persistentes.
```

Cognition pode produzir opções e recomendações, mas não decide autonomamente qual objetivo perseguir. Essa responsabilidade pertence a Agency.

---

# 2. Input e Output

```text
WORKSPACE
    ↓
COGNITION
    ├── compreensão
    ├── inferência
    ├── hipóteses
    ├── raciocínio
    ├── simulação
    └── solução de problemas
    ↓
WORKSPACE
    ↓
AGENCY
```

Cognition opera sobre o presente cognitivo e devolve resultados para o Workspace.

---

# 3. Understanding

Understanding transforma sinais e informações em representações estruturadas.

```text
OBSERVATION
    ↓
PARSE
    ↓
CONTEXTUALIZE
    ↓
REPRESENTATION
    ↓
UNDERSTANDING
```

Compreender não significa necessariamente estar correto. Uma representação pode ser revisada quando novas evidências surgem.

---

# 4. Reasoning

Reasoning é o processo de derivar conclusões a partir de informações, regras, evidências e modelos.

```text
PREMISES
    ↓
REASONING
    ↓
CONCLUSION
```

Pode incluir:

- raciocínio dedutivo;
- raciocínio indutivo;
- raciocínio abdutivo;
- raciocínio probabilístico;
- raciocínio causal;
- raciocínio analógico.

Reasoning é um componente de Cognition, não uma camada paralela entre Memory e Agency.

---

# 5. Inference

Inference produz conclusões que não estão explicitamente presentes nos dados de entrada.

```text
EVIDENCE
    ↓
INFERENCE
    ↓
HYPOTHESIS / CONCLUSION
```

Inferências devem manter distinção entre:

```text
OBSERVED
INFERRED
ASSUMED
UNCERTAIN
```

Essa distinção é importante para evitar que hipóteses sejam armazenadas como fatos.

---

# 6. Problem Solving

Problem Solving transforma um estado atual em um estado desejado através da busca de soluções.

```text
CURRENT STATE
    ↓
PROBLEM REPRESENTATION
    ↓
POSSIBLE SOLUTIONS
    ↓
EVALUATION
    ↓
CANDIDATE SOLUTION
```

Cognition pode propor soluções. Agency decide se uma solução será adotada como intenção operacional.

---

# 7. Simulation

Simulation permite explorar consequências hipotéticas antes da execução.

```text
CURRENT STATE
    ↓
HYPOTHETICAL ACTION
    ↓
SIMULATION
    ↓
PREDICTED OUTCOME
```

A simulação pode ser usada por Cognition para comparar alternativas e por Agency para apoiar decisões.

---

# 8. Imagination

Imagination gera representações que não precisam corresponder diretamente ao estado atual do ambiente.

```text
MEMORY + KNOWLEDGE + ABSTRACT CONCEPTS
              ↓
         IMAGINATION
              ↓
      NOVEL REPRESENTATION
```

Pode contribuir para criatividade, planejamento e descoberta de hipóteses.

---

# 9. Abstraction

Abstraction identifica estruturas gerais em experiências específicas.

```text
EXAMPLES
  ↓
PATTERNS
  ↓
ABSTRACTION
  ↓
GENERAL MODEL
```

Abstrações podem posteriormente ser consolidadas por Learning em modelos persistentes.

---

# 10. Hypothesis Generation

```text
OBSERVATION
    ↓
ANOMALY / QUESTION
    ↓
HYPOTHESIS GENERATION
    ↓
PREDICTION
    ↓
TEST
```

Uma hipótese não deve ser tratada como conhecimento confirmado apenas por ter sido gerada.

---

# 11. Causal Modeling

Cognition deve ser capaz de representar relações causais:

```text
CAUSE
  ↓
MECHANISM
  ↓
EFFECT
```

Isso permite prever consequências de ações e explicar resultados observados.

Causal models podem ser atualizados por Learning quando novas experiências fornecem evidência suficiente.

---

# 12. Metacognition

Metacognition é a capacidade de monitorar o próprio processamento cognitivo.

```text
COGNITION
    ↓
MONITOR
    ↓
ESTIMATE CONFIDENCE
    ↓
DETECT ERROR
    ↓
REQUEST MORE INFORMATION
```

Pode produzir estados como:

- alta confiança;
- baixa confiança;
- conflito entre hipóteses;
- informação insuficiente;
- necessidade de verificação.

Metacognition não substitui Learning. Ela fornece sinais que podem ser utilizados por Learning e Agency.

---

# 13. Cognition e Memory

```text
COGNITION
    ↓ query
MEMORY
    ↓ retrieval
WORKSPACE
    ↓
COGNITION
```

Memory fornece experiências, conhecimento e habilidades. Cognition determina como essas informações serão interpretadas e combinadas.

---

# 14. Cognition e Self

O Self fornece contexto de autorrepresentação:

```text
SELF STATE
    ↓
WORKSPACE
    ↓
COGNITION
```

Cognition pode utilizar o Self State para raciocinar sobre:

- capacidades próprias;
- limitações;
- histórico relevante;
- identidade;
- compromissos.

Isso não significa que Cognition seja responsável por manter o Self Model.

---

# 15. Cognition e Agency

A fronteira principal é:

```text
COGNITION
→ "Quais são as possibilidades e suas consequências?"

AGENCY
→ "Qual objetivo devo perseguir e qual intenção escolho?"
```

Fluxo:

```text
GOAL / CONTEXT
    ↓
COGNITION
    ↓
OPTIONS + PREDICTIONS + EVALUATIONS
    ↓
AGENCY
    ↓
DECISION
    ↓
ACTION INTENT
```

Agency pode solicitar novos raciocínios ou simulações quando a decisão exige mais informação.

---

# 16. Cognition e Learning

Learning pode utilizar resultados de Cognition para atualizar modelos.

```text
EXPERIENCE
    ↓
COGNITION
    ↓
INTERPRETATION
    ↓
LEARNING
    ↓
MODEL UPDATE
```

Cognition produz interpretações e hipóteses; Learning avalia evidências e determina quais mudanças devem persistir.

---

# 17. Limites e incerteza

Cognition deve representar incerteza explicitamente.

```text
KNOWN
    ↓
PROBABLE
    ↓
UNCERTAIN
    ↓
UNKNOWN
```

Uma conclusão cognitiva pode possuir:

```text
CONCLUSION
├── CONTENT
├── CONFIDENCE
├── EVIDENCE
├── ASSUMPTIONS
└── ALTERNATIVES
```

Isso reduz o risco de transformar inferências frágeis em crenças rígidas.

---

# 18. Contrato de Cognition

```text
WORKSPACE
→ fornece contexto ativo.

MEMORY
→ fornece informação recuperada.

SELF
→ fornece autorrepresentação contextual.

COGNITION
→ compreende, raciocina, infere e simula.

AGENCY
→ escolhe entre possibilidades e emite intenção.

LEARNING
→ utiliza experiências e resultados para atualizar modelos.
```

> **Cognition é o sistema que transforma informação em modelos, possibilidades e compreensão. Ele pensa sobre o que fazer, mas Agency decide o que perseguir e Action System executa a intenção.**

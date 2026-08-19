# 04 — Cognition

## Compreensão, raciocínio, simulação e construção de modelos

> **Pergunta fundamental:** Como o Virtual Brain transforma informação em compreensão, hipóteses, modelos e soluções?

**Cognition** é o sistema responsável por interpretar informação, construir representações internas, raciocinar, inferir, simular possibilidades e resolver problemas.

**Reasoning não é um módulo arquitetural separado. Reasoning é um dos processos internos de Cognition.**

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
→ mantém o contexto ativo e o estado cognitivo transitório.

COGNITION
→ interpreta, transforma, raciocina, infere e simula.

AGENCY
→ escolhe objetivos, prioriza e decide.

ACTION SYSTEM
→ executa intenções.

LEARNING
→ avalia experiências e produz mudanças persistentes.
```

Cognition pode produzir opções, recomendações, previsões e planos candidatos, mas não possui autoridade final para escolher qual objetivo perseguir ou qual intenção operacional emitir. Essa responsabilidade pertence a Agency.

---

# 2. Input e Output

```text
WORKSPACE
    ↓ contexto + evidências + estado
COGNITION
    ├── compreensão
    ├── inferência
    ├── hipóteses
    ├── raciocínio
    ├── simulação
    ├── soluções
    └── avaliações
    ↓ resultados cognitivos
WORKSPACE
    ↓ opções + previsões + avaliações
AGENCY
```

Cognition opera sobre o presente cognitivo disponibilizado pelo Workspace e devolve resultados para o Workspace.

O Workspace é o meio de integração; Cognition é o processo que transforma o conteúdo.

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

Reasoning é um processo de Cognition, não uma camada paralela entre Memory e Agency.

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

# 11. Causal Modeling e World Model

Cognition deve ser capaz de construir e utilizar modelos causais:

```text
CAUSE
  ↓
MECHANISM
  ↓
EFFECT
```

Isso permite prever consequências de ações e explicar resultados observados.

O **World Model** não é um módulo independente adicional do Virtual Brain. É um modelo persistente compartilhado que Cognition ajuda a construir, interpretar e utilizar.

```text
WORLD MODEL
    ↓ contextualization
WORLD STATE
    ↓
WORKSPACE
    ↓
COGNITION
    ↓
PREDICTIONS / SIMULATIONS / EXPLANATIONS
```

Cognition pode produzir atualizações candidatas para o World Model. Learning avalia evidências e determina quais mudanças devem persistir.

```text
COGNITION
→ constrói, interpreta e utiliza modelos.

LEARNING
→ avalia evidências e atualiza modelos persistentes.

MEMORY
→ preserva evidências, experiências e conhecimento que sustentam os modelos.
```

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
    ↓ contextualized information
COGNITION
```

Memory fornece experiências, conhecimento e habilidades. Cognition determina como essas informações serão interpretadas e combinadas.

Memory não raciocina. Ela fornece material para o raciocínio.

---

# 14. Cognition e Self

O Self fornece contexto de autorrepresentação através do Workspace:

```text
SELF MODEL
    ↓
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

# 16. Planning: fronteira entre Cognition e Agency

Planning é uma responsabilidade compartilhada, mas com funções diferentes.

```text
COGNITION
→ gera e explora planos candidatos.
→ simula consequências.
→ compara alternativas.
→ identifica riscos e dependências.

AGENCY
→ seleciona o plano adotado.
→ prioriza.
→ assume compromisso com o curso de ação.
→ emite Action Intent.
```

Fluxo:

```text
GOAL
    ↓
CURRENT STATE
    ↓
COGNITION
    ↓
CANDIDATE PLANS
    ↓
SIMULATION / EVALUATION
    ↓
AGENCY
    ↓
SELECTED PLAN
    ↓
ACTION INTENT
```

Assim, Cognition é responsável pela **exploração e avaliação de possibilidades**, enquanto Agency é responsável pelo **compromisso decisório**.

---

# 17. Cognition e Learning

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

Cognition produz interpretações, hipóteses e explicações; Learning avalia evidências e determina quais mudanças devem persistir.

A fronteira é:

```text
COGNITION
→ produz compreensão e hipóteses.

LEARNING
→ avalia a experiência e decide quais mudanças são justificadas.

PERSISTENT SYSTEMS
→ recebem mudanças aprovadas.
```

---

# 18. Limites e incerteza

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

# 19. Contrato de Cognition

```text
WORKSPACE
→ fornece contexto ativo, evidências e estado contextual.

MEMORY
→ fornece informação persistente recuperada.

SELF STATE
→ fornece autorrepresentação contextual.

WORLD STATE
→ fornece representação contextual relevante do mundo.

COGNITION
→ compreende, raciocina, infere, simula e produz possibilidades.

AGENCY
→ escolhe entre possibilidades, prioriza e emite intenção.

LEARNING
→ utiliza experiências e resultados para atualizar modelos persistentes.
```

Cognition é responsável por:

```text
INTERPRETAR
REPRESENTAR
RACIOCINAR
INFERIR
SIMULAR
IMAGINAR
ABSTRAIR
GERAR HIPÓTESES
RESOLVER PROBLEMAS
MONITORAR O PRÓPRIO PROCESSAMENTO
```

Cognition não é responsável por:

```text
PERSISTIR MEMÓRIAS
MANTER IDENTIDADE
ESCOLHER OBJETIVOS FINAIS
EMITIR AÇÃO POR CONTA PRÓPRIA
EXECUTAR FERRAMENTAS
DECIDIR O QUE DEVE SER APRENDIDO
```

> **Cognition é o sistema que transforma informação em compreensão, modelos e possibilidades. Ele pensa sobre o que pode ser feito, mas Agency decide o que perseguir, Action System executa a intenção e Learning transforma a experiência em mudanças persistentes.**

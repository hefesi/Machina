# 02 — Conscious Workspace

## O presente cognitivo integrado do Virtual Brain

> **Pergunta fundamental:** O que está acontecendo agora e o que precisa estar disponível para o sistema pensar e agir?

O **Conscious Workspace** é o espaço funcional que integra, mantém e organiza o conteúdo relevante do presente cognitivo. Ele não é a memória persistente, não é a cognição, não é o raciocínio e não é a agência.

O termo "conscious" é funcional: este documento não afirma consciência fenomenal. O Workspace é uma arquitetura de integração global que torna determinados conteúdos disponíveis para múltiplos processos cognitivos.

---

# 1. Função central

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
```

O Workspace mantém o contexto ativo necessário para que diferentes sistemas trabalhem sobre uma representação compartilhada do presente.

Ele é um **estado cognitivo transitório e integrado**, não um módulo que possui objetivos próprios ou toma decisões por conta própria.

---

# 2. Estrutura

```text
CONSCIOUS WORKSPACE
│
├── CURRENT CONTEXT
│   └── situação atual e contexto relevante
│
├── WORKING MEMORY
│   └── conteúdo temporariamente ativo para manipulação cognitiva
│
├── ACTIVE PERCEPTS
│   └── percepções atualmente relevantes
│
├── RETRIEVED MEMORIES
│   └── memórias recuperadas para o contexto atual
│
├── SELF STATE
│   └── representação contextual do Self
│
├── ACTIVE GOAL
│   └── objetivo atualmente em foco
│
├── COGNITIVE STATE
│   └── hipóteses, inferências e resultados relevantes
│
├── WORLD STATE
│   └── estado contextual do ambiente conforme as evidências disponíveis
│
├── BELIEFS / UNCERTAINTIES
│   └── crenças e incertezas relevantes para o contexto
│
└── ACTION CONTEXT
    └── contexto necessário para a próxima decisão e intenção
```

A **Working Memory pertence ao Workspace**. Ela não é um tipo de memória persistente dentro de Memory.

---

# 3. Workspace ≠ Memory

```text
MEMORY
→ preserva informação ao longo do tempo.

WORKING MEMORY
→ mantém informação temporariamente ativa para processamento.

WORKSPACE
→ integra o conteúdo ativo do presente cognitivo.
```

Fluxo:

```text
MEMORY
    ↓ retrieval
WORKSPACE
    ↓ active manipulation
COGNITION
    ↓ result
WORKSPACE
```

O conteúdo pode entrar e sair do Workspace sem ser apagado da Memory.

O Workspace não possui a responsabilidade de decidir o que deve ser consolidado como conhecimento persistente. Essa transformação pertence ao processo de Learning, com persistência e organização realizadas pelos sistemas de destino.

---

# 4. Workspace ≠ Cognition

```text
WORKSPACE
→ disponibiliza, integra e mantém conteúdo ativo.

COGNITION
→ interpreta, transforma, raciocina, infere, simula e resolve problemas.
```

O Workspace não raciocina sozinho. Ele fornece o contexto no qual Cognition opera.

```text
WORKSPACE
    ↓ contexto ativo
COGNITION
    ↓ resultados
WORKSPACE
```

**Reasoning é um processo interno de Cognition**, não um sistema paralelo ao Workspace.

O Workspace pode conter premissas, hipóteses e conclusões produzidas por Reasoning, mas não é responsável por produzi-las.

---

# 5. Workspace ≠ Agency

O Workspace mantém o objetivo ativo e o contexto atual. Agency decide prioridades, seleciona objetivos operacionais e emite intenções.

```text
SELF
→ valores, princípios e identidade.

AGENCY
→ objetivos, prioridades, decisões e intenções.

WORKSPACE
→ objetivo ativo, contexto atual e estado cognitivo relevante.
```

O Workspace pode registrar a decisão e a Action Intent para manter continuidade contextual, mas não toma a decisão.

---

# 6. Workspace ≠ Self

O Workspace contém uma projeção contextual do Self, mas não é o Self.

```text
SELF MODEL
    ↓
SELF STATE
    ↓
WORKSPACE
```

O Self Model é persistente e representa a autorrepresentação do sistema.

O Self State é contextual e pode mudar de acordo com a situação atual.

```text
SELF
→ identidade e continuidade.

SELF MODEL
→ representação persistente de si.

SELF STATE
→ projeção contextual do Self no presente cognitivo.

WORKSPACE
→ disponibiliza essa projeção para o processamento atual.
```

Cognition pode utilizar o Self State, e Learning pode atualizar o Self Model, mas o Workspace não mantém a identidade.

---

# 7. Workspace e World Model

O Workspace deve conter apenas a **projeção contextual relevante** do World Model, e não necessariamente o modelo inteiro.

```text
WORLD MODEL
→ representação persistente e estruturada do mundo.

WORLD STATE
→ estado contextual relevante para a situação atual.

WORKSPACE
→ mantém o World State ativo junto ao contexto atual.
```

Fluxo:

```text
WORLD MODEL
    ↓ contextualization
WORLD STATE
    ↓
WORKSPACE
    ↓
COGNITION
```

Cognition utiliza o World State para raciocinar e simular.

Learning pode atualizar o World Model quando novas evidências justificam mudanças persistentes.

Memory pode preservar evidências, episódios e conhecimento que sustentam o World Model.

Portanto:

```text
MEMORY
→ preserva evidências e conhecimento.

COGNITION
→ constrói, interpreta e utiliza modelos.

LEARNING
→ avalia evidências e atualiza modelos persistentes.

WORLD MODEL
→ representa conhecimento estruturado sobre o mundo.

WORLD STATE
→ projeção contextual do mundo no Workspace.
```

O World Model não é um sétimo módulo do Virtual Brain. É um **estado/modelo persistente compartilhado**, utilizado por múltiplos sistemas.

---

# 8. Integração com Memory

O Workspace consulta Memory quando precisa de informação que não está ativa.

```text
WORKSPACE
    ↓ query
MEMORY
    ↓ retrieval
WORKSPACE
```

Memory não deve inundar o Workspace. A recuperação deve ser seletiva, relevante e limitada pela capacidade cognitiva disponível.

O Workspace também pode enviar contexto para melhorar a recuperação:

```text
CURRENT CONTEXT
    +
ACTIVE GOAL
    +
QUERY
    ↓
MEMORY RETRIEVAL
    ↓
RELEVANT MEMORIES
    ↓
WORKSPACE
```

A recuperação de uma memória não significa que ela se tornou conhecimento confirmado. O Workspace deve preservar, quando necessário, distinções como:

```text
OBSERVED
INFERRED
ASSUMED
UNCERTAIN
```

---

# 9. Integração com Cognition

```text
WORKSPACE
    ↓ contexto + evidências + estado
COGNITION
    ├── Understanding
    ├── Reasoning
    ├── Inference
    ├── Simulation
    ├── Problem Solving
    ├── Imagination
    └── Metacognition
    ↓ resultados
WORKSPACE
```

O Workspace permite que resultados intermediários permaneçam disponíveis para outros processos.

Cognition pode produzir:

```text
OPTIONS
PREDICTIONS
HYPOTHESES
INFERENCES
SIMULATIONS
CANDIDATE SOLUTIONS
CONFIDENCE
UNCERTAINTY
```

Esses resultados podem retornar ao Workspace para serem utilizados por Agency ou por novos processos cognitivos.

---

# 10. Integração com Agency

```text
WORKSPACE
    ↓ contexto + estado + objetivo ativo
COGNITION
    ↓ opções + previsões + avaliações
AGENCY
    ↓ decisão
ACTION INTENT
    ↓
ACTION SYSTEM
```

Agency não executa diretamente.

O Workspace mantém o contexto necessário para a decisão, mas a decisão pertence a Agency.

Após uma decisão, o Workspace pode receber:

```text
DECISION
SELECTED OPTION
RATIONALE
EXPECTED OUTCOME
CONFIDENCE
RISK
ACTION INTENT
```

Isso permite que o presente cognitivo permaneça coerente durante a execução e avaliação do resultado.

---

# 11. Integração com Learning

Learning não opera como um segundo ciclo independente dentro do Workspace.

O ciclo é:

```text
EXPERIENCE
    ↓
LEARNING
    ↓
VALIDATED CHANGE
    ↓
MEMORY / WORLD MODEL / SELF MODEL / STRATEGIES
    ↓
WORKSPACE
    ↓
NEXT COGNITIVE CYCLE
```

Learning pode atualizar estados persistentes. O Workspace recebe as consequências dessas mudanças quando elas se tornam relevantes para o contexto atual.

Assim:

```text
WORKSPACE
→ presente cognitivo.

LEARNING
→ transformação baseada na experiência.

PERSISTENT SYSTEMS
→ preservam as mudanças aprovadas.
```

O Workspace não decide o que aprender e não consolida conhecimento por conta própria.

---

# 12. Atenção e seleção

O Workspace possui capacidade funcional limitada. Portanto, nem tudo que o sistema conhece deve permanecer ativo ao mesmo tempo.

A seleção do conteúdo ativo pode considerar:

```text
ACTIVE GOALS
RELEVANCE
URGENCY
SURPRISE
RISK
UNCERTAINTY
NOVELTY
CURRENT TASK
SELF-RELEVANCE
```

Fluxo conceitual:

```text
MUITA INFORMAÇÃO DISPONÍVEL
        ↓
SELEÇÃO / ATENÇÃO
        ↓
WORKSPACE
        ↓
PROCESSAMENTO COGNITIVO
```

O Workspace é o destino funcional do conteúdo selecionado, mas o mecanismo que define prioridades de atenção pode utilizar sinais de Cognition, Agency, Self e Perception.

Isso evita atribuir ao Workspace uma autoridade que pertence a outros sistemas.

---

# 13. Conteúdo ativo

O Workspace deve priorizar:

- percepção relevante;
- contexto temporal e espacial;
- memórias recuperadas;
- Self State;
- objetivo ativo;
- estado emocional ou motivacional funcional, quando modelado;
- hipóteses atuais;
- incertezas;
- resultados intermediários de Cognition;
- World State relevante;
- crenças relevantes;
- contexto da intenção de ação;
- resultados esperados e observados durante uma ação.

Nem toda informação disponível no sistema precisa estar ativa simultaneamente.

---

# 14. Estado e transitoriedade

```text
PERSISTENTE
├── MEMORY
├── SELF MODEL
├── WORLD MODEL
└── LEARNED STRATEGIES

TRANSITÓRIO
├── WORKSPACE
├── WORKING MEMORY
├── ACTIVE GOAL
├── SELF STATE
├── WORLD STATE
├── CURRENT COGNITIVE STATE
└── ACTIVE ACTION CONTEXT
```

O Workspace pode ser reconstruído após uma interrupção, desde que os estados persistentes necessários sejam preservados.

Uma reconstrução pode ocorrer através de:

```text
PERSISTENT STATE
    ↓
CURRENT ENVIRONMENT
    ↓
RECENT OBSERVATIONS
    ↓
RELEVANT MEMORY RETRIEVAL
    ↓
WORKSPACE RECONSTRUCTION
```

Isso significa que o Workspace não é a fonte definitiva da continuidade. Ele é a **instância transitória do presente cognitivo**, reconstruível a partir da continuidade persistente do sistema.

---

# 15. Ciclo global único

O Workspace participa do único ciclo arquitetural do Virtual Brain:

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
    ↓
OBSERVATION
    ↓
WORKSPACE
```

A experiência resultante pode alimentar Learning:

```text
EXPERIENCE
    ↓
LEARNING
    ├──→ MEMORY
    ├──→ WORLD MODEL
    ├──→ SELF MODEL
    └──→ STRATEGIES
```

As mudanças persistentes entram nos próximos ciclos quando relevantes.

Não existe um segundo ciclo independente dentro do Workspace.

---

# 16. Contrato do Workspace

```text
PERCEPTION
→ fornece observações relevantes.

MEMORY
→ fornece lembranças e conhecimento recuperado.

SELF
→ fornece Self State contextual.

WORLD MODEL
→ fornece conhecimento persistente sobre o mundo.

COGNITION
→ transforma conteúdo ativo em compreensão, inferências, simulações e soluções.

AGENCY
→ recebe contexto e emite decisões e intenções.

ACTION SYSTEM
→ recebe Action Intent para execução.

LEARNING
→ utiliza experiências e resultados para produzir mudanças persistentes.
```

O Workspace é responsável por:

```text
INTEGRAR
MANTER ATIVO
ORGANIZAR CONTEXTO
DISPONIBILIZAR
ATUALIZAR O PRESENTE COGNITIVO
```

O Workspace não é responsável por:

```text
MANTER IDENTIDADE
PERSISTIR MEMÓRIAS
RACIOCINAR
ESCOLHER OBJETIVOS
EXECUTAR AÇÕES
DECIDIR O QUE APRENDER
```

---

# 17. Princípios invariantes

1. **Workspace não é Memory.**
2. **Working Memory pertence ao Workspace.**
3. **Workspace não é Cognition.**
4. **Reasoning pertence a Cognition.**
5. **Workspace não é Agency.**
6. **Workspace mantém objetivos ativos; Agency escolhe e prioriza objetivos.**
7. **Self State é uma projeção contextual do Self Model.**
8. **World State é uma projeção contextual do World Model.**
9. **World Model não é um sétimo módulo independente do Virtual Brain.**
10. **Workspace contém apenas a parte relevante do World Model para o contexto atual.**
11. **Workspace é transitório e reconstruível.**
12. **Memory fornece conteúdo persistente; Workspace fornece contexto ativo.**
13. **Cognition produz resultados; Workspace os mantém disponíveis.**
14. **Learning transforma experiência em mudanças persistentes; Workspace incorpora essas mudanças quando relevantes.**
15. **Workspace não possui autoridade própria sobre identidade, verdade, objetivos ou aprendizado.**
16. **O Workspace é o presente cognitivo integrado do Virtual Brain.**

---

# 18. Definição final

> **O Conscious Workspace é o presente cognitivo integrado do Virtual Brain: um estado funcional, transitório e compartilhado que mantém contexto, percepções, memórias recuperadas, Self State, World State, objetivos ativos, resultados cognitivos e contexto de ação disponíveis para os sistemas especializados que compõem a mente.**

Sua função é conectar o que o sistema **percebe**, o que **lembra**, o que **compreende**, o que **pretende** e o que **está fazendo agora**, sem assumir a responsabilidade de pensar, decidir, agir ou aprender por conta própria.

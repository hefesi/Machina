# 05 — Agency

## Objetivos, prioridades, decisão e intenção de ação

> **Pergunta fundamental:** O que o Virtual Brain deve perseguir e qual intenção deve emitir para agir?

Agency é o sistema responsável por transformar valores, contexto e objetivos em prioridades, decisões e **Action Intents**.

Agency não executa ações diretamente.

```text
AGENCY
→ escolhe, prioriza, decide e emite intenção.

ACTION SYSTEM
→ traduz intenção em operações executáveis.

VIRTUAL ORGANISM
→ percebe e atua no ambiente.
```

---

# 1. Estrutura

```text
AGENCY
│
├── MOTIVATION CONTEXT
├── GOAL MANAGEMENT
├── PRIORITIZATION
├── PLAN SELECTION
├── DECISION MAKING
├── RISK EVALUATION
└── ACTION INTENT GENERATION
```

Agency possui autoridade decisória sobre objetivos e compromissos operacionais, mas depende de Cognition para explorar possibilidades e de Action System para executar intenções.

---

# 2. Self, Agency e Workspace

```text
SELF
→ valores, princípios e compromissos de identidade.

AGENCY
→ objetivos, prioridades, decisões e compromissos operacionais.

WORKSPACE
→ objetivo ativo, contexto atual e estado cognitivo relevante.
```

Agency pode ser influenciada pelo Self, mas não é responsável por manter identidade.

O Workspace mantém a projeção contextual do objetivo e da decisão, mas não possui autoridade para escolher por conta própria.

---

# 3. Goal Management

Agency organiza objetivos em diferentes horizontes:

```text
LONG-TERM GOALS
      ↓
MEDIUM-TERM GOALS
      ↓
SHORT-TERM GOALS
      ↓
ACTIVE GOAL
```

Objetivos operacionais podem ser criados, priorizados, suspensos, concluídos ou abandonados.

O objetivo ativo é projetado no Workspace para que Cognition possa operar sobre ele.

---

# 4. Prioritization

A prioridade de um objetivo pode considerar:

- valores do Self;
- urgência;
- importância;
- risco;
- recursos disponíveis;
- dependências;
- custo;
- probabilidade de sucesso;
- consequências futuras.

```text
GOALS
    ↓
EVALUATION
    ↓
PRIORITIZATION
    ↓
ACTIVE GOAL
```

Agency pode receber avaliações de Cognition e sinais do Self, Memory, Learning e Workspace, mas a priorização operacional pertence a Agency.

---

# 5. Cognition e Agency

Cognition e Agency possuem responsabilidades diferentes:

```text
COGNITION
→ explora possibilidades.
→ simula consequências.
→ raciocina sobre alternativas.
→ estima incertezas.
→ produz soluções e planos candidatos.

AGENCY
→ escolhe objetivos.
→ prioriza.
→ seleciona alternativas.
→ assume compromisso com um curso de ação.
→ decide.
→ emite Action Intent.
```

Fluxo:

```text
ACTIVE GOAL + CONTEXT
        ↓
COGNITION
        ↓
OPTIONS + PREDICTIONS + EVALUATIONS
        ↓
AGENCY
        ↓
DECISION
```

Agency pode solicitar novos processos cognitivos quando a informação disponível é insuficiente.

---

# 6. Planning: geração versus compromisso

Planning é uma responsabilidade compartilhada, mas não de forma indistinta.

```text
COGNITION
→ gera planos candidatos.
→ explora sequências possíveis.
→ simula consequências.
→ identifica riscos e dependências.

AGENCY
→ avalia o alinhamento com objetivos e valores.
→ seleciona o plano adotado.
→ prioriza.
→ assume compromisso operacional.
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

Portanto, Agency não precisa gerar sozinha todas as possibilidades de planejamento. Sua responsabilidade é selecionar e assumir o curso de ação que será transformado em intenção.

---

# 7. Decision Making

A decisão seleciona uma alternativa com base em objetivos, valores, evidências, riscos e consequências esperadas.

```text
OPTIONS
   ↓
EVALUATE
   ↓
COMPARE
   ↓
DECIDE
   ↓
ACTION INTENT
```

Uma decisão pode incluir:

```text
DECISION
├── GOAL
├── SELECTED OPTION
├── SELECTED PLAN
├── RATIONALE
├── EXPECTED OUTCOME
├── CONFIDENCE
├── RISK
└── REVERSIBILITY
```

A decisão é o compromisso de Agency com uma alternativa. Ela não significa que o resultado esperado ocorrerá, apenas que aquela alternativa foi escolhida com base nas informações disponíveis.

---

# 8. Action Intent

O produto final de Agency é uma intenção estruturada de ação.

```text
ACTION INTENT
├── GOAL
├── ACTION
├── TARGET
├── EXPECTED OUTCOME
├── CONSTRAINTS
├── RISK LEVEL
├── AUTHORIZATION
└── SUCCESS CRITERIA
```

Agency termina aqui.

```text
AGENCY
    ↓
ACTION INTENT
    ↓
ACTION SYSTEM
```

A Action Intent representa **o que foi decidido**, não a implementação de como executar.

---

# 9. Action System

O Action System é responsável por transformar intenção em execução.

```text
ACTION INTENT
    ↓
ACTION SYSTEM
    ├── VALIDATION
    ├── PERMISSION CHECK
    ├── TOOL SELECTION
    ├── EXECUTION
    └── RESULT CAPTURE
    ↓
VIRTUAL ORGANISM
```

Agency não controla diretamente APIs, ferramentas, hardware ou atuadores.

A distinção é:

```text
AGENCY
→ decide o que fazer.

ACTION SYSTEM
→ determina como executar dentro das capacidades e permissões disponíveis.
```

---

# 10. Virtual Organism

O Virtual Organism conecta o Virtual Brain ao ambiente.

```text
VIRTUAL BRAIN
    ↓
ACTION INTENT
    ↓
ACTION SYSTEM
    ↓
VIRTUAL ORGANISM
    ↓
ENVIRONMENT
```

O Organism executa operações e retorna observações.

---

# 11. Feedback e Learning

Após uma ação:

```text
EXPECTED OUTCOME
        ↓
ACTION
        ↓
ACTUAL OUTCOME
        ↓
OBSERVATION
        ↓
EXPERIENCE
        ↓
LEARNING
```

Learning avalia a experiência e pode atualizar Memory, World Model, Self Model e estratégias.

Agency não é responsável por executar Learning.

Quando mudanças aprendidas alteram prioridades ou estratégias futuras, Agency utiliza essas informações em ciclos posteriores.

---

# 12. World Model e Agency

Agency não mantém diretamente o World Model.

Ela utiliza, através do Workspace, uma representação contextual do mundo:

```text
WORLD MODEL
    ↓
WORLD STATE
    ↓
WORKSPACE
    ↓
AGENCY
```

Agency utiliza esse estado para avaliar decisões, mas Cognition é responsável por raciocinar sobre o estado e Learning pode atualizar o modelo persistente.

Assim:

```text
WORLD MODEL
→ conhecimento persistente sobre o mundo.

WORLD STATE
→ projeção contextual no Workspace.

COGNITION
→ interpreta e simula.

AGENCY
→ decide com base nas informações disponíveis.
```

---

# 13. Ciclo global único

Agency participa de um único ciclo arquitetural:

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

Não existe um segundo ciclo independente de `Perceive → Reason → Act → Learn` dentro de Agency.

---

# 14. Autonomia

Autonomia não significa ausência de controle.

Agency deve considerar:

- permissões disponíveis;
- limites de ação;
- avaliação de risco;
- reversibilidade;
- impacto potencial;
- necessidade de confirmação humana;
- monitoramento;
- possibilidade de interrupção;
- registro de decisões e resultados.

```text
LOW RISK
→ execução automática possível.

HIGH RISK
→ avaliação adicional.

CRITICAL
→ confirmação ou bloqueio conforme política.
```

Agency pode decidir autonomamente dentro das políticas e autorizações disponíveis, mas não pode conceder a si mesma novas permissões apenas porque possui um objetivo.

---

# 15. Contrato de Agency

```text
SELF
→ fornece valores e princípios.

WORKSPACE
→ fornece contexto, estado atual e objetivo ativo.

MEMORY
→ fornece histórico e conhecimento recuperável através do contexto atual.

COGNITION
→ fornece opções, planos candidatos, previsões e avaliações.

AGENCY
→ prioriza, seleciona, decide e emite Action Intent.

ACTION SYSTEM
→ valida e executa a intenção.

LEARNING
→ avalia os resultados e atualiza o sistema.
```

Agency é responsável por:

```text
GERENCIAR OBJETIVOS
PRIORIZAR
SELECIONAR ALTERNATIVAS
ASSUMIR COMPROMISSOS OPERACIONAIS
DECIDIR
GERAR ACTION INTENTS
```

Agency não é responsável por:

```text
MANTER IDENTIDADE
ARMAZENAR MEMÓRIAS
RACIOCINAR SOBRE O MUNDO
EXECUTAR FERRAMENTAS
ATUALIZAR DIRETAMENTE MODELOS DE APRENDIZADO
```

> **Agency transforma objetivos, valores e contexto em compromisso decisório e Action Intent. Ela torna o Virtual Brain capaz de escolher um curso de ação, mas não é a camada de raciocínio nem de execução.**

# 05 — Agency

## Objetivos, prioridades, decisão e intenção de ação

> **Pergunta fundamental:** O que o Virtual Brain deve perseguir e qual intenção deve emitir para agir?

Agency é o sistema responsável por transformar valores, contexto e objetivos em prioridades, decisões e **Action Intents**.

Agency não executa ações diretamente.

```text
AGENCY
→ decide e emite intenção.

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
├── PLANNING
├── DECISION MAKING
├── RISK EVALUATION
└── ACTION INTENT GENERATION
```

---

# 2. Self, Agency e Workspace

```text
SELF
→ valores, princípios e compromissos de identidade.

AGENCY
→ objetivos, prioridades e decisões operacionais.

WORKSPACE
→ objetivo ativo e contexto atual.
```

Agency pode ser influenciada pelo Self, mas não é responsável por manter identidade.

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

---

# 5. Cognition e Agency

Cognition e Agency possuem responsabilidades diferentes:

```text
COGNITION
→ explora possibilidades.
→ simula consequências.
→ raciocina sobre alternativas.
→ estima incertezas.

AGENCY
→ escolhe objetivos.
→ prioriza.
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

# 6. Planning

Planning transforma objetivos em sequências possíveis de ações.

```text
GOAL
  ↓
CURRENT STATE
  ↓
PLANNING
  ↓
PLAN
  ↓
CANDIDATE ACTIONS
```

O planejamento pode ser feito em conjunto com Cognition, que fornece simulações e previsões.

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
├── RATIONALE
├── EXPECTED OUTCOME
├── CONFIDENCE
├── RISK
└── REVERSIBILITY
```

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

Learning avalia a experiência e pode atualizar Memory, World Models, Self Model e estratégias.

Agency não é responsável por executar Learning.

---

# 12. Ciclo global único

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

Não existe um segundo ciclo independente de `Perceive → Reason → Act → Learn` dentro de Agency.

---

# 13. Autonomia

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

---

# 14. Contrato de Agency

```text
SELF
→ fornece valores e princípios.

WORKSPACE
→ fornece contexto e objetivo ativo.

MEMORY
→ fornece histórico e conhecimento recuperável.

COGNITION
→ fornece opções, previsões e avaliações.

AGENCY
→ prioriza, decide e emite Action Intent.

ACTION SYSTEM
→ executa a intenção.

LEARNING
→ avalia os resultados e atualiza o sistema.
```

> **Agency transforma intenção em decisão e decisão em Action Intent. Ela torna o Virtual Brain capaz de escolher um curso de ação, mas não é a camada de execução.**

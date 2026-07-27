# 02 — Conscious Workspace

> **Virtual Brain — Teoria v2.1**

## Definição

O **Conscious Workspace** é a camada cognitiva dinâmica que mantém e integra aquilo que é relevante para o momento presente do Virtual Brain, tornando esse conteúdo disponível para memória, raciocínio, agência e aprendizagem.

> **O Workspace representa o presente cognitivo do Virtual Brain.**

O termo *conscious* descreve uma hipótese arquitetural de disponibilidade e integração global. **Não constitui uma afirmação de consciência fenomenal, experiência subjetiva ou senciência.**

---

# 1. Responsabilidade primária

A responsabilidade do Workspace é:

> **Manter uma representação integrada, temporária e atualizável da situação cognitiva presente.**

Ele integra, conforme a situação exige:

- percepção relevante;
- contexto atual;
- foco e atenção;
- objetivos ativos;
- memórias recuperadas;
- conhecimentos relevantes;
- pensamentos em andamento;
- hipóteses;
- previsões;
- incertezas;
- intenções;
- estado atual do self.

O Workspace **não** é responsável por:

- armazenar permanentemente conhecimento;
- realizar todo o raciocínio;
- decidir autonomamente a ação final;
- executar ações;
- transformar experiências em aprendizado permanente;
- provar ou produzir consciência fenomenal.

---

# 2. Limites arquiteturais

A separação fundamental do Virtual Brain é:

```text
PERCEPTION
    ↓
WORKSPACE
    ↕
MEMORY ↔ REASONING
    ↓
AGENCY
    ↓
ACTION
    ↓
ENVIRONMENT
```

Com aprendizado atravessando o ciclo:

```text
EXPERIENCE
    ↓
LEARNING
    ↓
MEMORY / MODELS / SELF-MODEL
    ↓
WORKSPACE
```

A regra é:

> **Perception informa o sistema. Workspace integra o presente. Memory preserva o passado. Reasoning simula possibilidades. Agency governa objetivos e escolhe ações. Learning transforma experiência em mudança.**

---

# 3. Workspace não é Memory

A distinção é:

```text
MEMORY
= conhecimento e experiência que podem persistir e ser recuperados.

WORKSPACE
= conteúdo atualmente ativo e cognitivamente relevante.
```

Memory fornece informação ao Workspace por recuperação seletiva.
O Workspace mantém uma representação temporária dessa informação para o ciclo cognitivo atual.

```text
MEMORY
   │
   │ retrieval
   ▼
WORKSPACE
   │
   │ contexto ativo
   ▼
REASONING
```

O Workspace pode conter referências, resumos, embeddings ou representações temporárias de memórias, mas não é o sistema autoritativo de armazenamento persistente.

### Working Memory

A **Working Memory** deve ser entendida como a capacidade funcional de manter e manipular informação ativa dentro do Workspace, e não como um depósito permanente separado.

```text
MEMORY → RECUPERA
WORKSPACE → ATIVA E MANIPULA
MEMORY → PERSISTE
```

---

# 4. Workspace não é Reasoning

O Workspace é o **contexto**.

Reasoning é o **processo que opera sobre o contexto**.

```text
WORKSPACE
    │
    ├── contexto atual
    ├── objetivo ativo
    ├── conhecimento recuperado
    ├── observações
    └── hipóteses
          ↓
      REASONING
          ↓
  inferências / previsões / possibilidades / planos
          ↓
      WORKSPACE
```

Reasoning pode consultar e atualizar estruturas cognitivas temporárias no Workspace, mas o Workspace não realiza inferência por si mesmo.

---

# 5. Workspace não é Agency

O Workspace representa o **objetivo ativo e as intenções atuais**.

A Agency é responsável pelo **sistema de objetivos, prioridades, decisão e ação**.

```text
WORKSPACE
    ↓
CONTEXTO + OBJETIVO ATIVO
    ↓
REASONING
    ↓
POSSIBILIDADES
    ↓
AGENCY
    ↓
DECISION
    ↓
ACTION
```

Portanto:

> **Reasoning determina o que pode ser feito. Agency determina o que será feito.**

O Workspace disponibiliza o estado necessário para que ambos operem de forma coerente.

---

# 6. Workspace não é Learning

O Workspace não aprende diretamente.

Ele participa da construção de experiências que podem ser avaliadas pelo Learning.

```text
WORKSPACE(t)
    ↓
AGENCY → ACTION(t)
    ↓
ENVIRONMENT
    ↓
PERCEPTION(t+1)
    ↓
WORKSPACE(t+1)
    ↓
EXPERIENCE
    ↓
LEARNING
```

Learning pode então alterar:

- memória;
- crenças;
- modelos do mundo;
- conhecimento procedural;
- estratégias;
- modelos do self.

As mudanças persistentes retornam ao Workspace por meio de recuperação e atualização do contexto.

---

# 7. Estado cognitivo atual

O Workspace mantém uma representação estruturada do presente cognitivo.

Conceitualmente:

```text
WORKSPACE_STATE {
    perception_context
    world_context
    self_state
    attention
    focus
    active_goals
    active_intentions
    retrieved_memories
    current_thoughts
    hypotheses
    predictions
    expectations
    uncertainty
    pending_questions
}
```

Esse estado é **dinâmico e temporal**.

Ele não é um registro permanente do sistema.

Informações que precisam sobreviver ao ciclo atual devem ser avaliadas pelo Learning e, quando apropriado, persistidas na Memory.

---

# 8. Self-State e Self-Model

O Workspace pode manter um `SELF_STATE`, isto é, a representação atual do sistema sobre si mesmo.

```text
SELF_STATE

onde estou?
o que estou fazendo?
o que estou tentando fazer?
quais são minhas capacidades atuais?
quais são minhas limitações atuais?
o que acredito?
o que espero?
qual é meu estado atual?
```

O `SELF_STATE` é uma representação presente e pode estar incorreta.

O conhecimento persistente sobre o próprio sistema pertence à Memory.
O `SELF-MODEL` evolui por Learning.
O Workspace mantém apenas a versão relevante para o presente.

```text
MEMORY
    ↓
SELF-KNOWLEDGE
    ↓
LEARNING
    ↓
SELF-MODEL
    ↓
WORKSPACE
    ↓
SELF_STATE
```

Isso evita confundir:

```text
SELF_STATE  = quem o sistema entende ser agora
SELF-MODEL  = modelo persistente e evolutivo de si mesmo
```

---

# 9. Atenção e seleção

Atenção é um mecanismo de seleção que ajuda a decidir quais conteúdos devem receber prioridade dentro do Workspace.

Podem competir por prioridade:

- percepções;
- memórias recuperadas;
- pensamentos;
- hipóteses;
- alertas;
- previsões;
- objetivos;
- conflitos.

Uma função conceitual pode considerar:

```text
WorkspacePriority = f(
    Relevance,
    GoalAlignment,
    Novelty,
    Urgency,
    EmotionalSalience,
    PredictiveValue,
    UncertaintyReduction
)
```

A fórmula não precisa ser implementada literalmente.

O princípio é:

> **O Workspace não recebe tudo com a mesma prioridade; ele mantém aquilo que é mais relevante para a situação atual.**

A atenção seleciona.
O Workspace integra.

---

# 10. Core e Context

O Workspace possui dois níveis funcionais:

```text
WORKSPACE
│
├── CORE
│   └── conteúdo diretamente manipulado
│
└── CONTEXT
    └── informação auxiliar necessária para interpretar o Core
```

O Core deve concentrar os elementos de maior prioridade.
O Context fornece suporte cognitivo sem necessariamente ocupar o centro da manipulação.

A capacidade é adaptativa: o sistema pode ampliar ou reduzir o contexto de acordo com a complexidade da tarefa e os recursos disponíveis.

---

# 11. Unidade de representação

A unidade fundamental do Workspace não é um fato isolado, mas uma **representação mental contextualizada**.

Exemplo:

```text
PERCEPÇÃO:
Existe uma porta.

CONTEXTO:
Estou em uma sala.

OBJETIVO:
Quero sair.

ESTADO:
A porta está fechada.

PREDIÇÃO:
Se eu abrir a porta, posso sair.

INCERTEZA:
Não sei o que existe do outro lado.

INTENÇÃO:
Investigar a porta.
```

O Workspace integra esses elementos em uma representação coerente da situação atual.

---

# 12. Continuidade temporal

O Workspace representa o presente em relação ao passado imediato e ao futuro previsto.

```text
PASSADO IMEDIATO
        ↓
ESTADO ATUAL
        ↓
FUTURO PREVISTO
        ↓
AÇÃO POSSÍVEL
```

O passado relevante fornece contexto.
O presente é o centro da representação.
O futuro previsto orienta raciocínio e ação.

Essa continuidade não significa que o Workspace seja uma memória episódica completa. Ele mantém apenas o contexto temporal necessário para a cognição atual.

---

# 13. Recorrência cognitiva

O ciclo não é linear.

```text
PERCEPTION
    ↓
WORKSPACE
    ↓
REASONING
    ↓
AGENCY
    ↓
ACTION
    ↓
ENVIRONMENT
    ↓
PERCEPTION
```

O resultado de uma ação altera o ambiente.
A nova situação é percebida.
A percepção atualiza o Workspace.
O sistema reavalia suas hipóteses, previsões e objetivos.

```text
STATE(t)
    ↓
ACTION(t)
    ↓
ENVIRONMENT
    ↓
OBSERVATION(t+1)
    ↓
STATE(t+1)
```

Essa dinâmica cria continuidade cognitiva.

---

# 14. Experiência e Learning

Uma experiência pode ser representada como uma transição:

```text
S(t)
  ↓
A(t)
  ↓
ENVIRONMENT
  ↓
S(t+1)
```

O Learning analisa essa trajetória e pode atualizar modelos e conhecimento.

```text
EXPERIENCE
    ↓
LEARNING
    ├──→ MEMORY
    ├──→ WORLD MODEL
    ├──→ BELIEFS
    ├──→ PROCEDURAL KNOWLEDGE
    ├──→ STRATEGIES
    └──→ SELF-MODEL
```

O Workspace recebe posteriormente as consequências dessas mudanças por meio da recuperação de informação e atualização do estado atual.

---

# 15. Princípios fundamentais

### 15.1 O Workspace não é a memória

Memórias podem existir fora do Workspace. O Workspace mantém apenas representações relevantes para o presente.

### 15.2 O Workspace não é o pensamento

Pensamentos e processos de raciocínio operam sobre o Workspace e podem modificar seu conteúdo.

### 15.3 O Workspace não é apenas atenção

A atenção seleciona prioridade; o Workspace integra o conteúdo selecionado.

### 15.4 O Workspace não é a Agency

A Agency possui autoridade sobre objetivos, decisões e ações.

### 15.5 O Workspace não aprende sozinho

Learning transforma experiências em mudanças persistentes.

### 15.6 O Workspace não implica consciência fenomenal

A arquitetura descreve disponibilidade e integração funcional, não experiência subjetiva.

### 15.7 O Workspace é presente-orientado

Ele representa o que é cognitivamente relevante agora, incluindo apenas o passado e futuro necessários para interpretar esse agora.

### 15.8 O Workspace é uma fronteira de integração

Ele reduz o acoplamento direto entre módulos, oferecendo um contexto compartilhado para os processos cognitivos.

---

# 16. Arquitetura integrada do Virtual Brain

```text
                         ENVIRONMENT
                              │
                              ▼
                       ┌─────────────┐
                       │ PERCEPTION  │
                       └──────┬──────┘
                              │
                              ▼
                  ┌──────────────────────┐
                  │  CONSCIOUS WORKSPACE │
                  │                      │
                  │  PRESENT COGNITIVE  │
                  │  STATE               │
                  └───────┬───────┬──────┘
                          │       │
                 ┌────────┘       └────────┐
                 ▼                         ▼
            ┌─────────┐               ┌───────────┐
            │ MEMORY  │◄─────────────►│ REASONING │
            └────┬────┘               └─────┬─────┘
                 │                          │
                 └──────────┬───────────────┘
                            ▼
                       ┌─────────┐
                       │ AGENCY  │
                       └────┬────┘
                            │
                            ▼
                          ACTION
                            │
                            ▼
                       ENVIRONMENT
                            │
                            ▼
                        EXPERIENCE
                            │
                            ▼
                         LEARNING
                        ┌────┼────┐
                        ▼    ▼    ▼
                     MEMORY MODELS SELF-MODEL
                        │    │    │
                        └────┴────┴──→ WORKSPACE
```

---

# 17. Arquitetura de responsabilidades

```text
PERCEPTION
    ↓
Transforma sinais do mundo em informação relevante.

WORKSPACE
    ↓
Integra e mantém o presente cognitivo.

MEMORY
    ↓
Preserva e recupera conhecimento e experiência.

REASONING
    ↓
Gera e avalia inferências, hipóteses e possibilidades.

AGENCY
    ↓
Governa objetivos, prioridades, decisões e ações.

LEARNING
    ↓
Transforma experiência em mudanças persistentes.
```

A separação fundamental é:

> **Memory preserva. Learning transforma. Workspace integra. Reasoning simula. Agency decide. Perception informa.**

Essa divisão deve ser usada como contrato arquitetural entre os módulos do Virtual Brain.

# Cognitive Data Model

Este documento define os objetos conceituais fundamentais do Virtual Brain v0.1. Ele é a referência antes da implementação de schemas e bancos de dados.

## Entidades principais

### Observation

Uma informação percebida pelo sistema.

```text
Observation
├── id
├── source
├── content
├── timestamp
├── context
└── confidence
```

### Experience

Um episódio registrado pelo sistema, incluindo contexto, interpretação, ações e resultados.

```text
Experience
├── id
├── observations
├── context
├── interpretation
├── actions
├── outcomes
├── evaluation
└── timestamp
```

### Thought

Um estado ou processo interno de raciocínio associado a uma situação e a um objetivo.

```text
Thought
├── id
├── context
├── objective
├── premises
├── hypotheses
├── reasoning
├── conclusion
└── confidence
```

### Memory

Uma unidade persistente de informação recuperável.

```text
Memory
├── id
├── type
├── content
├── source
├── evidence
├── confidence
├── importance
├── created_at
├── updated_at
└── relationships
```

### Concept

Uma abstração semântica que representa uma ideia, entidade ou categoria conhecida pelo sistema.

### Entity

Um objeto identificável no modelo interno do mundo ou do próprio sistema.

### Belief

Uma proposição que o sistema considera verdadeira com determinado grau de confiança.

```text
Belief
├── proposition
├── confidence
├── evidence
├── sources
├── created_at
└── revision_history
```

### Goal

Um estado desejado que orienta o comportamento.

```text
Goal
├── id
├── description
├── priority
├── status
├── constraints
└── deadline
```

### Plan

Uma sequência ou estrutura de ações proposta para alcançar um objetivo.

### Action

Uma operação executada pelo sistema ou por uma ferramenta externa.

### Outcome

O resultado observado após uma ação.

### Skill

Uma capacidade procedural que descreve como realizar uma classe de tarefas.

### LearningEvent

Um evento que pode produzir alteração em memória, crença, habilidade ou modelo interno.

### WorldState

A representação atual que o sistema possui sobre o ambiente relevante.

### SelfState

A representação atual que o sistema possui sobre si mesmo, incluindo identidade, capacidades, limitações, objetivos ativos e estado operacional.

## Relações fundamentais

```text
Observation
    ↓ gera
Experience
    ↓ pode produzir
Memory
    ↓ influencia
Thought
    ↓ produz
Plan
    ↓ executa
Action
    ↓ gera
Outcome
    ↓ alimenta
Evaluation
    ↓ gera
LearningEvent
    ↓ atualiza
Memory / Belief / Skill / WorldState / SelfState
```

## Regras conceituais

1. Toda memória persistente deve possuir origem ou indicar explicitamente que é uma inferência.
2. Crenças podem mudar, mas seu histórico deve ser preservado.
3. Experiências devem registrar resultados quando disponíveis.
4. Pensamentos são temporários por padrão; apenas conclusões relevantes devem ser consolidadas.
5. O estado atual deve ser separado do histórico de experiências.
6. O sistema deve distinguir fato observado de interpretação e inferência.
7. Confiança não significa verdade; representa o grau atual de suporte disponível.
8. Relações entre entidades devem ser armazenáveis e recuperáveis.

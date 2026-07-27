# World Model

> **Status:** Teoria v0.1

O World Model é a representação interna dinâmica do mundo mantida pelo Virtual Brain.

## Função

Representar entidades, eventos, estados, relações e incertezas de forma temporal e rastreável.

```text
Observations
    ↓
Interpretations
    ↓
World Model Update
    ↓
Current World State
    ↓
Reasoning / Planning / Decision
```

## Estrutura

```text
WORLD MODEL
├── Entities
├── Events
├── States
├── Relations
├── Predictions
├── Hypotheses
├── Evidence
└── Uncertainty
```

## Princípios

1. Observação não é fato absoluto.
2. Fato, inferência e hipótese devem ser diferenciáveis.
3. O modelo deve preservar histórico suficiente para compreender mudanças.
4. Conflitos não devem ser apagados automaticamente.
5. Toda atualização relevante deve possuir evidência ou origem rastreável.
6. O modelo deve representar desconhecimento explicitamente.

## Entity

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

## Event

```text
Event
├── id
├── type
├── participants[]
├── cause_refs[]
├── effects[]
├── timestamp
├── location
├── evidence[]
└── confidence
```

## State

O estado deve ser temporal:

```text
Previous State
      ↓
Event / Observation
      ↓
Current State
      ↓
Expected State
```

## Uncertainty

```text
confirmed
probable
hypothesis
unknown
contradicted
```

O World Model não precisa estar correto para ser útil; precisa ser capaz de reconhecer quando pode estar errado e permitir atualização.

## Exemplo

```text
ENTITY: porta

OBSERVATION:
    tentativa de abertura

RESULT:
    porta permaneceu fechada

CURRENT STATE:
    aberta = false

HYPOTHESIS:
    porta pode estar trancada

CONFIDENCE:
    0.72

NEXT COGNITIVE NEED:
    buscar evidência adicional
```

## Relações

O modelo deve suportar relações explícitas entre entidades e eventos:

```text
Pessoa -- possui --> Objeto
Evento -- alterou --> Estado
Evento -- pode_causar --> Evento
Objeto -- localizado_em --> Lugar
Agente -- interage_com --> Agente
```

O objetivo é formar uma estrutura que possa ser consultada pelo Thought Model e manipulada pelo Reasoning sem depender exclusivamente de texto livre.

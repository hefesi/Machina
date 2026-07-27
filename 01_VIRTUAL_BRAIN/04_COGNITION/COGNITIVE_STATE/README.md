# Cognitive State

> **Status:** Teoria v0.1

O Cognitive State representa o estado cognitivo ativo do Virtual Brain em um determinado momento.

## Pergunta central

> **O que está cognitivamente ativo agora?**

## Estrutura

```text
COGNITIVE STATE
├── attention_focus[]
├── current_context
├── active_goals[]
├── active_thoughts[]
├── working_memory
├── relevant_memories[]
├── beliefs[]
├── hypotheses[]
├── questions[]
├── uncertainties[]
├── conflicts[]
├── active_intentions[]
├── emotional_functional_state
├── self_state_ref
└── world_state_ref
```

## Características

O estado cognitivo é:

- dinâmico;
- temporário;
- atualizável;
- contextual;
- limitado pelo foco de atenção;
- conectado à memória e ao World Model.

Ele não substitui memória persistente nem o modelo do mundo.

## Ciclo

```text
Observation
    ↓
Attention
    ↓
Context Formation
    ↓
Memory Retrieval
    ↓
Cognitive State Update
    ↓
Thought / Reasoning
    ↓
Decision / Action
    ↓
Feedback
    ↓
Cognitive State Update
```

## Princípio de continuidade

O estado atual deve poder apontar para o estado anterior e para mudanças relevantes:

```text
Cognitive State(t)
      ↓
Experience
      ↓
Update
      ↓
Cognitive State(t+1)
```

A continuidade de longo prazo, entretanto, pertence à integração entre Self, Memory, World Model e Learning.

## Incerteza

O Cognitive State deve manter explicitamente:

```text
known
uncertain
unknown
conflicted
hypothetical
```

Isso evita que a ausência de informação seja confundida com certeza negativa ou positiva.

## Relação com Thought

```text
Cognitive State
      │
      ├── Context
      ├── Attention
      ├── Memories
      ├── World Model
      └── Goals
            ↓
         Thought
            ↓
      State Update
```

O Thought é uma atividade cognitiva rastreável dentro do estado cognitivo, não o estado cognitivo inteiro.

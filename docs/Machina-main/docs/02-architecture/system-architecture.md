# Arquitetura Conceitual do Sistema

## Visão

```text
                         ENVIRONMENT
                              │
                              ▼
                        ┌───────────┐
                        │ PERCEPTION │
                        └─────┬─────┘
                              ▼
                     ┌────────────────┐
                     │ WORKING MEMORY │◄──────────────┐
                     └───────┬────────┘               │
                             │                        │
               ┌─────────────┼─────────────┐          │
               ▼             ▼             ▼          │
          MEMORY SYSTEM   WORLD MODEL   SELF MODEL     │
               │             │             │          │
               └─────────────┼─────────────┘          │
                             ▼                        │
                        ┌───────────┐                 │
                        │ REASONING │                 │
                        └─────┬─────┘                 │
                              ▼                       │
                        ┌───────────┐                 │
                        │  PLANNER  │                 │
                        └─────┬─────┘                 │
                              ▼                       │
                        ┌───────────┐                 │
                        │   ACTOR   │                 │
                        └─────┬─────┘                 │
                              ▼                       │
                        ┌───────────┐                 │
                        │ EVALUATOR │                 │
                        └─────┬─────┘                 │
                              ▼                       │
                        ┌───────────┐                 │
                        │ LEARNING  │─────────────────┘
                        └───────────┘
```

## Componentes

### Perception

Converte entradas externas em observações estruturadas.

### Working Memory

Mantém o estado cognitivo necessário para a atividade atual.

### Memory System

Armazena e recupera experiências, conhecimento, habilidades e histórico.

### World Model

Representa entidades, relações, estados e hipóteses sobre o ambiente.

### Self Model

Representa identidade, capacidades, limitações, objetivos e estado do próprio sistema.

### Reasoning

Combina contexto, memória e modelos internos para produzir interpretações, hipóteses e conclusões.

### Planner

Transforma objetivos em planos executáveis.

### Actor

Executa ações internas ou externas através de ferramentas e interfaces autorizadas.

### Evaluator

Compara resultados observados com objetivos e expectativas.

### Learning

Converte experiências avaliadas em atualizações candidatas de memória, crenças, habilidades e modelos.

## Dependências conceituais

```text
Perception → Working Memory
Working Memory → Retrieval
Memory → Reasoning
World Model → Reasoning
Self Model → Reasoning
Reasoning → Planning
Planning → Action
Action → Environment
Environment → Perception
Outcome → Evaluation
Evaluation → Learning
Learning → Memory / Models
```

## Regra de modularidade

Nenhum componente deve depender diretamente de detalhes internos de outro componente. A comunicação deve ocorrer através de contratos e estruturas de dados bem definidos.

# Modelo de Memória

## Visão geral

A memória do Virtual Brain é composta por sistemas especializados que cooperam, mas não devem ser confundidos.

```text
                    MEMORY SYSTEM
                         │
      ┌──────────────────┼──────────────────┐
      │                  │                  │
      ▼                  ▼                  ▼
Working Memory      Episodic Memory   Semantic Memory
      │                  │                  │
      │                  └────────┬─────────┘
      │                           │
      ▼                           ▼
Procedural Memory         Autobiographical Memory
      │                           │
      └──────────────┬────────────┘
                     ▼
               Context Builder
```

## Working Memory

Mantém o contexto necessário para o ciclo cognitivo atual.

Inclui:

- objetivo ativo;
- contexto recente;
- observações relevantes;
- memórias recuperadas;
- hipóteses atuais;
- plano em execução;
- restrições.

É limitada e temporária.

## Episodic Memory

Armazena experiências específicas.

Exemplo conceitual:

```text
Situação
→ Interpretação
→ Decisão
→ Ação
→ Resultado
→ Avaliação
```

## Semantic Memory

Armazena conceitos, fatos, relações e conhecimento generalizado.

Cada item deve manter, quando possível:

- evidência;
- fonte;
- confiança;
- relações;
- histórico de atualização.

## Procedural Memory

Armazena habilidades e procedimentos aprendidos.

Uma habilidade pode possuir:

- descrição;
- passos;
- pré-condições;
- pós-condições;
- taxa histórica de sucesso;
- contexto de aplicação;
- versão.

## Autobiographical Memory

Representa a continuidade histórica do próprio sistema.

Inclui eventos importantes sobre:

- origem;
- objetivos;
- projetos;
- decisões;
- mudanças relevantes;
- capacidades adquiridas.

## Formação de memória

Nem toda observação vira memória permanente.

```text
Observation
    ↓
Interpretation
    ↓
Importance Assessment
    ↓
Candidate Memory
    ↓
Deduplication / Conflict Check
    ↓
Indexing
    ↓
Consolidation
```

## Recuperação

A recuperação deve combinar múltiplos critérios:

- similaridade semântica;
- entidades e conceitos;
- relações;
- relevância para o objetivo;
- recência;
- importância;
- confiança;
- contexto temporal;
- memória episódica relacionada;
- habilidades aplicáveis.

## Consolidação

A consolidação transforma experiências e informações temporárias em conhecimento persistente quando existe evidência suficiente ou valor futuro relevante.

## Esquecimento

O sistema não deve apagar conhecimento importante apenas por idade. Itens podem perder prioridade de recuperação por baixa relevância, mas devem permanecer preservados quando possuírem valor histórico ou evidencial.

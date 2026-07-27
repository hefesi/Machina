# Hypothesis and Uncertainty

> **Status:** Teoria v0.1

A Cognition deve tratar incerteza como parte explícita do estado interno, não como ausência de dados escondida.

## Princípio

```text
Evidence
   ↓
Candidate Interpretation
   ↓
Hypothesis Space
   ├── A
   ├── B
   └── C
   ↓
Support / Contradiction
   ↓
Updated Confidence
```

## Hypothesis

```text
Hypothesis
├── id
├── proposition
├── supporting_evidence[]
├── contradicting_evidence[]
├── confidence
├── status
└── created_at
```

## Estados

```text
candidate
supported
weak
contradicted
rejected
```

A confiança no v0.1 representa suporte relativo disponível. Não deve ser tratada automaticamente como probabilidade matemática calibrada.

## Unknown

O sistema deve distinguir:

```text
KNOWN
    informação disponível e suficientemente sustentada

UNCERTAIN
    informação disponível, mas insuficiente ou conflitante

UNKNOWN
    informação necessária ainda não disponível

HYPOTHETICAL
    possibilidade sendo considerada

CONTRADICTED
    evidência atual entra em conflito com a hipótese
```

## Múltiplas hipóteses

O Virtual Brain não deve colapsar prematuramente para uma única interpretação quando a evidência for insuficiente.

```text
Situation
   ├── Hypothesis A — 0.60
   ├── Hypothesis B — 0.25
   └── Hypothesis C — 0.15
```

A escolha de uma hipótese dominante pode ocorrer quando a evidência, o objetivo e o custo de investigação justificarem.

## Conflitos

```text
Observation A
      │
      ├── conflicts with ── Memory B
      │
      └── conflicts with ── Belief C
```

Conflitos devem ser registrados e investigados.

```text
Conflict
├── id
├── subject_refs[]
├── type
├── severity
├── evidence[]
├── detected_at
└── resolution_status
```

Estados:

```text
detected
under_investigation
resolved
unresolved
accepted_uncertainty
```

## Princípio de segurança cognitiva

Uma hipótese não deve se tornar fato apenas por repetição, alta frequência de recuperação ou geração linguística. Sua força deve depender da evidência disponível, do contexto e da consistência com o modelo interno.

## Investigação

```text
Unknown / Uncertainty
        ↓
Generate Question
        ↓
Retrieve Memory
        ↓
Request Observation
        ↓
Compare Evidence
        ↓
Update Hypothesis
        ↓
Update World Model
```

Essa estrutura conecta diretamente Cognition, Reasoning, Memory, Agency e Learning.

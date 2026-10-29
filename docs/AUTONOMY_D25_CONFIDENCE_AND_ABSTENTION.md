# D2.5 — Confidence-aware decisions and abstention

## Goal

Autonomy should not mean always producing an answer. When available evidence is
missing or contradictory, Machina should be able to stop and report uncertainty
instead of inventing a result.

## Current behavior

- A single unique value matching the requested entity and field is returned.
- No matching structured evidence yields `abstained_no_evidence`.
- Multiple conflicting values yield `abstained_ambiguous`.
- The decision includes candidate values and a transparent evidence score.

## Validation

Run:

```bash
python -m examples.autonomy_d25_confidence_demo
python -m unittest discover -s tests -p 'test_autonomy_d25*.py'
```

The demo tests supported D2.4 formats, conflicting records, and a free-form
unsupported note.

## Limitations

The score is a deterministic evidence indicator, not a calibrated probability.
The policy only understands the explicit record formats implemented in the
transfer benchmark. It does not establish general language understanding,
consciousness, or free will. The next step is to evaluate abstention on larger,
randomized, adversarially constructed test sets and measure coverage versus
error rate.

## Enquadramento na hipótese fundamental

Confiança e abstenção são mecanismos funcionais de calibração e controle de incerteza. Não devem ser interpretados como sentimentos subjetivos de dúvida. Investigar se a incerteza estimada influencia de forma estável atenção, exploração, decisão, aprendizagem e revisão de objetivos. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).

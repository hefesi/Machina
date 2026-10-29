# MNN v0.10 — Chemical Signaling & Motivation

## Status

Initial executable research prototype. This module is a deterministic computational abstraction inspired by neuromodulation; it is not a biochemical simulation and does not establish emotion, pleasure, sentience, or consciousness.

## Responsibilities

- Maintain bounded virtual concentrations for dopamine-, acetylcholine-, noradrenaline-, and serotonin-inspired signals.
- Compute reward prediction error from received reward and a running expected-value estimate.
- Expose explicit modulation outputs for exploration, plasticity, and attention.
- Serialize state and parameters so experiments can be resumed and reproduced.

## API

ChemicalSignaling.step(ChemicalEvent(...)) returns a ChemicalUpdate.

All event inputs are normalized to [0, 1]. Reward is currently normalized to [0, 1] in this first prototype. Each call advances one logical timestep and does not depend on wall-clock time or randomness.

The concentration update combines event-driven production with concentration-dependent decay:

C_next = clamp(C + gain * target * (1 - C) - decay * C, 0, 1)

The prediction error is reward - expected_value; expected value is updated using a bounded learning rate. Outputs are signals for other systems, not direct commands to execute actions.

## Integration contract

- **Learning:** may use prediction_error and plasticity_gain as inputs to its own update policy.
- **Memory:** may use relevance/attention signals when ranking or consolidating fragments; memory policy remains independent.
- **Agency:** may consider exploration_drive alongside goal progress, cost, risk, and constraints.
- **Cognition:** may use attention_gain to modulate processing priorities.

No consumer is required to accept a chemical signal as the sole decision criterion. Safety constraints and goal checks must remain authoritative.

## Limitations and validation plan

The coefficients are initial hypotheses, not biologically calibrated parameters. Unit tests verify determinism, bounded concentrations, prediction-error direction, novelty response, and snapshot round-tripping. They do not prove that the mechanism improves learning. A follow-up benchmark should compare matched agents with and without chemical modulation on reward exploitation, task completion, generalization, retention, and compute cost.

## Enquadramento na hipótese fundamental

A sinalização química é uma abstração computacional inspirada em processos neuromodulatórios, não uma reprodução bioquímica literal nem evidência de emoção ou sentimento. Seus sinais devem ser tratados como variáveis regulatórias com origem, dinâmica, efeitos e limites mensuráveis. Investigar como estados moduladores alteram atenção, exploração, plasticidade, persistência e prioridades na dinâmica integrada de Machina. Ver [Hipótese Fundamental](../00-vision/central-hypothesis.md).

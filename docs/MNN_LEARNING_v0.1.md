# MNN Learning v0.1 — Delayed reward with eligibility traces

## Why this step

The existing \`MNN.apply_hebbian(learning_rate, reward)\` updates weights from
the units' current states. That is useful for immediate feedback, but a reward
arriving after the relevant activity has ended needs a short-lived record of
which connections were active. This module adds that record without replacing
the existing plasticity API or modifying the VirtualBrain cycle.

## Rule

For each enabled connection i -> j, after a relevant network step:

\`e_ij(t) = clamp(trace_decay * e_ij(t-1) + state_i(t) * state_j(t), -trace_limit, trace_limit)\`

When feedback arrives:

\`w_ij <- clamp(w_ij + learning_rate * reward * e_ij, -weight_limit, weight_limit)\`

Positive reward reinforces eligible co-activity; negative reward reverses the
update direction. Eligibility can be cleared after applying a reward. Disabled
connections neither accumulate eligibility nor learn. New edges start with zero
eligibility, and removed edges lose their trace.

## Example

\`\`\`python
from machina.mnn import Connection, MNN, Unit
from machina.mnn_learning import EligibilityTraceLearner

network = MNN()
network.add_unit(Unit("sensor", activation="identity"))
network.add_unit(Unit("response", activation="identity"))
network.add_connection(Connection("sensor-response", "sensor", "response", 0.4))
learner = EligibilityTraceLearner(network, learning_rate=0.05, trace_decay=0.8)

network.step({"sensor": 1.0})
network.step({"sensor": 1.0})
learner.record_activity()
# Later, after the outcome is observed:
learner.apply_reward(1.0, clear=True)
checkpoint = learner.snapshot()
\`\`\`

Call \`record_activity()\` after the state update whose activity should receive
credit. Persist \`snapshot()\` alongside the network snapshot or event journal
if eligibility must survive a process restart; the learner does not silently
write to the existing journal.

## Boundaries and validation

- This is a transparent, deterministic three-factor learning baseline, not a
  complete learning algorithm or a biological model.
- It does not assign credit to actions automatically; callers decide when to
  record activity and which outcome/reward to apply.
- Reward design and causal attribution remain external responsibilities.
- Trace snapshots are rejected if their connection IDs do not match the live
  topology, avoiding silent misapplication after structural changes.
- Tests cover delayed reward, positive/negative reward, bounds, disabled edges,
  topology changes, and checkpoint restoration.

Run tests from the repository root with \`python -m unittest discover -s tests -v\`.

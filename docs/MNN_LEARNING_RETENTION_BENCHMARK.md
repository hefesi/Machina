# MNN Learning and Retention Benchmark v0.1

## Research question

Does the reward-learning rule improve a measurable behavior on a controlled
task, and does the learned behavior survive serializing and restoring the
network and learner state?

## Task and baseline

The task contains two contexts and one response:
- positive context should produce a high response (target 1);
- negative context should produce a low response (target 0).

The untrained baseline has zero connection weights. Training repeatedly
presents both contexts, records connection co-activity in eligibility traces,
clears the transient network state, and then supplies a delayed positive or
negative reward. The benchmark reports accuracy and mean squared error (MSE)
before training, after training, and after restoring a checkpoint into fresh
objects.

## Persistence criterion

The benchmark snapshots both the MNN (topology, states, and learned weights)
and the eligibility learner (parameters and traces). It restores both into new
objects and checks that weights and test predictions are identical. This
checks serialization round-trip retention; it does not prove long-term memory
under every process, storage, or software failure.

## Run

From the repository root:

\`\`\`bash
python -m benchmarks.mnn_learning_retention
python -m unittest tests.test_mnn_learning_retention -v
\`\`\`

The benchmark emits JSON containing:
- baseline and trained accuracy;
- baseline and trained mean squared error;
- post-restore metrics;
- whether performance improved;
- whether weights and predictions were retained.

## Acceptance criteria

1. Trained accuracy is greater than baseline accuracy.
2. Trained MSE is lower than baseline MSE.
3. Restored weights equal the pre-restart weights.
4. Predictions after restore equal predictions before restore.
5. Tests pass reproducibly.

A failed criterion is a failed experiment, not something to explain away.

## Limitations

This is a tiny deterministic association task with fixed contexts and known
targets. It does not test transfer to unseen contexts, robust credit assignment,
language, reasoning, autonomous goal selection, or AGI. A next experiment
should add held-out combinations, distractors, repeated episodes, ablations
against fixed weights and immediate Hebbian learning, and multiple random seeds.

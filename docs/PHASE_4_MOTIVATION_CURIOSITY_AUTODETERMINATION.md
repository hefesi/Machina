# Phase 4 — Motivation, curiosity and operational self-determination

## Existing architecture

Phase 4 already contains distinct, tested mechanisms:

- `SelfModelLearningBridge` proposes investigations only for unknown, stale,
  or explicitly eligible low-confidence inferred beliefs, preserving belief
  status and evidence provenance.
- `curiosity_policy.CuriositySelector` ranks caller-authored questions using
  uncertainty, expected information gain, relevance, novelty, cost and risk.
- `AutonomyController` generates internal goals and applies bounded utility,
  risk, repetition and drive-feedback rules.
- `MotivationSystem` maintains persistent drive pressure through
  `temporal_urgencies()`; the coordinator maps each pressure to a bounded
  adjustment using `(pressure - 0.5) * 0.3`.
- `HomeostaticRegulator` proposes drive corrections only after observed
  deviations persist across distinct cycles.
- `CuriosityInvestigationStore` keeps an append-only investigation and
  evidence lifecycle, suppressing questions already present in its history.

## Integrated coordination

`CuriosityGoalCoordinator` composes those existing components without
introducing a second curiosity scoring policy.

For each deliberation it:

1. asks `SelfModelLearningBridge` for evidence/status-gated curiosity goals;
2. converts the proposals and their provenance into the existing
   `CuriosityQuestion` contract;
3. ranks those questions with `curiosity_policy.CuriositySelector`;
4. derives a transparent stability-pressure heuristic from the current
   `HomeostaticProposal`, unless an explicit pressure value is supplied;
5. combines homeostatic drive adjustments with temporal motivational
   adjustments derived from `(temporal_urgency - 0.5) * 0.3`, bounded to
   [-0.3, 0.3];
6. places the selected curiosity proposal alongside optional context- and
   motivation-generated goals for final selection by `AutonomyController`;
7. starts an investigation in `CuriosityInvestigationStore` only if the
   final autonomy decision actually selects that curiosity goal.

The derived homeostatic pressure is the maximum absolute observed deviation
multiplied by its persistence fraction. It is an engineering heuristic, not a
biological measurement. The caller may supply an explicit
`stability_pressure` when a different calibrated signal is appropriate.
Homeostatic proposals must belong to the same cycle as the deliberation.

The coordinator combines its inputs within [-0.3, 0.3]. The existing
`AutonomyController` then applies its narrower final feedback clamp of
[-0.15, 0.15] during goal scoring. This is intentional: upstream proposals
retain their bounded magnitude for inspection, while the autonomy policy
limits their influence on the final choice.

The standalone coordinator records the selected goal, provenance, scoring
decisions, pressure source, drive adjustments and investigation. It never
executes a goal or grants permission for external actions. Previously
investigated questions are suppressed by the existing store before ranking.

## VirtualBrain integration

When configured with a `CuriosityGoalCoordinator` and an investigation store,
`VirtualBrain.run_deliberated_cycle` accepts `curiosity_gap_mappings`. The
coordinator prepares the highest-ranked eligible curiosity candidate without
persisting it. `InternalDeliberator` then compares that candidate in the same
`AutonomyController` decision as context-generated goals, motivation-generated
goals and durable open commitments from `PersistentGoalStore`.

Only after this unified decision selects the curiosity candidate does
`VirtualBrain` start the investigation and append the corresponding event to
its cycle journal. If another goal wins, no curiosity investigation is opened.
The selected cycle ID is shared by the homeostatic proposal, investigation and
brain journal; when a homeostatic proposal is supplied and no explicit cycle
ID is given, its cycle ID anchors the integrated deliberation.

The bridge, outcome learner and coordinator are injected explicitly. This
keeps self-model evidence policy and persistence configuration under the
caller's control.

## Example

```python
from machina import (
    AutonomyController,
    CuriosityGoalCoordinator,
    CuriosityInvestigationStore,
    GoalOutcomeLearner,
    SelfModel,
    SelfModelLearningBridge,
)

model = SelfModel()
learner = GoalOutcomeLearner("outcomes.sqlite3")
store = CuriosityInvestigationStore("curiosity.sqlite3")
bridge = SelfModelLearningBridge(model, learner)
coordinator = CuriosityGoalCoordinator(bridge, AutonomyController())

result = coordinator.deliberate(
    {
        "memory.coherence": {
            "question": "Which evidence explains this contradiction?",
            "hypothesis": "The observations may refer to different contexts.",
            "information_gain": 0.9,
            "impact": 0.8,
            "urgency": 0.7,
            "estimated_cost": 0.2,
            "risk": 0.05,
        }
    },
    cycle_id="cycle-001",
    investigation_store=store,
)

assert result["execution_performed"] is False
```

For a full brain cycle, inject the same controller into the deliberator and
coordinator, then pass the gap mappings to `run_deliberated_cycle`:

```python
from machina import (
    AutonomyContext, AutonomyController, CuriosityGoalCoordinator,
    GoalOutcomeLearner, InternalDeliberator, PersistentGoalStore,
    SelfModel, SelfModelLearningBridge, VirtualBrain,
)

controller = AutonomyController()
goals = PersistentGoalStore("goals.sqlite3")
learner = GoalOutcomeLearner("outcomes.sqlite3")
coordinator = CuriosityGoalCoordinator(
    SelfModelLearningBridge(SelfModel(), learner), controller
)
brain = VirtualBrain(
    "brain.sqlite3",
    internal_deliberator=InternalDeliberator(controller, goals),
    curiosity_investigation_path="curiosity.sqlite3",
    curiosity_goal_coordinator=coordinator,
)
result = brain.run_deliberated_cycle(
    "Review an unresolved memory gap.",
    AutonomyContext(memory_count=1),
    curiosity_gap_mappings={
        "memory.coherence": {
            "question": "Which evidence explains this gap?",
            "hypothesis": "A missing retrieval relation may be involved.",
            "information_gain": 0.9,
            "impact": 0.8,
            "urgency": 0.7,
            "estimated_cost": 0.2,
            "risk": 0.05,
        }
    },
)
```

## Validation and research boundary

Unit and integration tests must verify that:

- homeostatic pressure reduces exploration weighting and its drive adjustments
  reach the final autonomy policy within the controller's stricter clamp;
- temporal motivational pressure combines with homeostatic feedback without
  exceeding configured bounds;
- prior questions are suppressed by persistent investigation history;
- an investigation is persisted only when autonomy selects the curiosity goal;
- belief evidence references remain visible in selection provenance;
- risky and external-action goals remain rejected by the existing policies.

These mechanisms demonstrate operational goal generation, selection and
persistence. They do not establish subjective curiosity, desire, consciousness
or metaphysical free will. Any consciousness claim remains an experimental
hypothesis requiring independent operationalization and falsifiable tests.
```

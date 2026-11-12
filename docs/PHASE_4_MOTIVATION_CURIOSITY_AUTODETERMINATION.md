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

## Follow-up curiosity across investigation cycles

A closed investigation can record unresolved questions in remaining_unknowns.
SelfModelLearningBridge.propose_follow_up_curiosity_goals() turns only those
recorded unknowns into bounded candidates and suppresses questions already
present in the investigation history.

CuriosityGoalCoordinator.deliberate_follow_up() adds the same integrated
selection path used for initial gaps: it converts follow-up candidates to the
existing CuriosityQuestion contract, ranks them with CuriositySelector under
the current homeostatic stability pressure, combines bounded homeostatic and
motivational drive adjustments, and submits the selected candidate alongside
context-generated goals to the same AutonomyController.

A child investigation is persisted only when the final autonomy decision
selects that curiosity candidate. The child record stores
`parent_investigation_id` as a self-referential foreign key, so lineage remains
queryable after restart rather than existing only in a goal ID or free-text
selection rationale. A child may reference only an existing closed parent.
Existing SQLite databases receive an additive nullable-column migration;
historical investigations remain root records and their data is preserved.
Its goal ID and selection rationale also retain the source investigation ID
and exact unresolved question. A caller may supply an explicit hypothesis;
otherwise the record states that no explanation is presumed. Follow-up
selection does not execute research or external actions.

For end-to-end operation, VirtualBrain.run_deliberated_cycle() accepts
curiosity_follow_up_investigation_id together with
curiosity_follow_up_mappings. It prepares the follow-up candidate without
persisting it, submits that candidate to the same unified deliberation as
context-generated goals and durable commitments, then persists the child
investigation only if the unified winner is that candidate. The brain journal
links the new investigation event to evidence already recorded by the parent.
Initial gap mappings and follow-up mappings are mutually exclusive in one
cycle, preventing two independent curiosity previews from competing under
ambiguous provenance.

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

## Experience-backed strategic review and causal experiment registration

`ExperienceMemoryStore` produces evaluator-grounded autobiographical reports. Their repeated
patterns are descriptive and explicitly non-causal. `StrategySelfReviewStore`
accepts a caller-authored, testable alternative only when the report includes
enough evaluated repetitions, matching evidence references and explicit
confounders.

A strategy proposal must receive an explicit `approved` decision before it can be
registered with `CausalExperimentStore`. Registration maps the current strategy to the
control arm and the proposed alternative to the treatment arm. The registration
also stores a durable proposal-to-experiment link and is idempotent for matching
inputs; conflicting reuse of either identity is rejected.

Registration creates only an experiment definition. It does not assign trials,
execute either strategy, infer a causal effect or change policy. A separately
defined protocol must be carried out and evaluator-backed outcomes recorded
before `CausalExperimentStore.report()` can estimate a comparison. When a
confirmed strategy outcome is projected into a trial, its recorded action must
match the experiment's configured treatment or control label for the requested
arm; mismatches are rejected before persistence. For matched designs, the
caller-supplied context key must also equal the normalized context recorded in
the outcome event, so a trial cannot be assigned to an unrelated comparison
pair. Observational associations
and insufficient samples remain ineligible for causal belief updates. Eligible
randomized or matched reports can be passed explicitly to
`SelfModelLearningBridge.update_belief_from_causal_experiment()`, which records a
bounded inferred belief with its evidence references; it does not prove an
individual counterfactual.

The intended review path is therefore:

1. record and evaluate repeated experiences;
2. propose a testable strategy alternative with confounders;
3. record an explicit approval or rejection;
4. register an approved experiment and its protocol reference;
5. collect trials separately and review the resulting evidence;
6. update inferred beliefs only when the causal-design and uncertainty gates
   are satisfied.

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


## Concurrent curiosity review integrity

Curiosity evidence review holds an SQLite `BEGIN IMMEDIATE` transaction from the review-ID lookup through the optional self-model update and immutable report write. Independent connections therefore serialize the same review ID: one call applies the update and records the report, while a matching retry observes the stored fingerprint and does not apply a second revision. The transaction is released on failure, and the existing fingerprint-based retry path remains necessary because the self-model and investigation ledger are separate stores rather than one atomic database transaction.

## Curiosity review replay and belief restoration

A curiosity review report and a `SelfModel` snapshot are separate persistence
artifacts. When a caller restores a snapshot from before a successfully recorded
review and replays the same review ID and request fingerprint, the bridge
reconciles the reviewed belief into that restored model if the review marker is
absent from its current belief and revision history. A matching replay against
a model that already contains the review marker remains idempotent and does not
create another revision.

Recovery also checks both the previous and new belief records in revision
history. This matters when a review updated the model but its report write
failed, a later review superseded that belief, and the first review is retried:
the earlier review is recognized in the later revision's previous value, so
recovery does not overwrite the newer belief.

The model snapshot and investigation ledger are still not one atomic storage
transaction. Callers remain responsible for persisting and restoring
`SelfModel.snapshot()`; replay reconciles a restored snapshot with the durable
review report rather than claiming cross-store atomicity.

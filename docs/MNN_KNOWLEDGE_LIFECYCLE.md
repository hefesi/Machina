# MNN Knowledge Lifecycle v0.1

## Purpose

`MNNKnowledgeLifecycle` coordinates the existing evidence-grounded concept builder
and concept reviewer into one inspectable maintenance pass. It does not add a
new semantic inference engine.

## Pipeline

1. Review persisted concepts against the current evidence archive.
2. Discover recurring tag-based concept hypotheses.
3. Optionally materialize refreshed concept snapshots.
4. Review the archive again so callers can inspect current, stale, conflicted,
   and unverified concepts.
5. Optionally persist idempotent review audit fragments.

## Usage

```python
from machina import FragmentMemory, MNNKnowledgeLifecycle

with FragmentMemory("memory.sqlite3") as memory:
    lifecycle = MNNKnowledgeLifecycle(memory, min_support=2)
    result = lifecycle.run()
    print(len(result.hypotheses))
    print(result.conflicted_count)
```

Use `run(refresh=False, persist_audit=False)` for an observational pass that
does not write to memory. The two flags can also be controlled independently.

## Safety and semantics

- Source evidence fragments are never rewritten or deleted.
- Previous concept snapshots remain archived when evidence changes.
- Discovery uses explicit shared tags; it is not open-ended language understanding.
- Contradictions come from explicit evidence polarity or persisted explicit
  concept relations, not from wording similarity.
- Confidence is a ranking heuristic inherited from the builder, not a calibrated
  probability.
- Repeated runs over an unchanged archive are idempotent for concept and audit IDs.
- The coordinator exposes intermediate results instead of collapsing the cycle
  into an opaque score.

## Validation target

Tests cover discovery and materialization, idempotent repeated runs, read-only
observation mode, conflict surfacing, and input validation. A later integration
step should connect this lifecycle to the durable `VirtualBrain` cycle only
after defining transaction and recovery semantics across `EventStore` and
`FragmentMemory`.

## Contextual knowledge-use feedback (v0.2)

`MNNKnowledgeUseFeedback` connects an externally confirmed strategy outcome
with the existing contextual relevance scores in `FragmentMemory`.

```python
from machina import MNNKnowledgeUseFeedback

feedback = MNNKnowledgeUseFeedback(memory, strength=0.1)
result = feedback.apply(
    proposal,
    {"fragment-id-1": True, "fragment-id-2": False},
    execution_confirmed=True,
    executed_action=proposal["action"],
    operation_id="unique-outcome-id",
)
```

The caller must explicitly label each cited fragment as useful or not useful.
The adapter rejects unconfirmed execution, action mismatch, uncited fragment IDs,
and non-boolean labels. Feedback changes only relevance for the supplied task
context; global memory importance is unchanged. The underlying SQLite batch is
atomic and idempotent: retrying the same operation returns the original scores,
while reusing the operation ID with changed labels is rejected.

Reward is deliberately not translated automatically into per-fragment
usefulness. A high-reward action does not prove every cited source was useful,
and a low-reward action does not prove every source was irrelevant.

## Coordinated strategy learning cycle (v0.3)

`MNNStrategyLearningCycle` provides one explicit entry point for the existing
contextual advisor and the two distinct learning channels:

- `propose(context, campaign_ids)` delegates to the evidence-gated advisor.
  It returns a proposal or abstention and never executes an action.
- `learn_strategy_outcome(...)` sends a confirmed, matching action and
  normalized observed reward to `MNNOrganism` through
  `MNNStrategyFeedbackAdapter`.
- `learn_evidence_use(...)` applies caller-labelled usefulness only to cited
  fragments through `MNNKnowledgeUseFeedback`.

The channels are deliberately separate. Reward trains the organism's bounded
neural/chemical dynamics; explicit usefulness labels update task-relative
retrieval relevance. Neither signal is silently inferred from the other.

This facade is not a distributed transaction: organism state and SQLite memory
do not share a commit boundary. Callers should persist snapshots and reconcile
the two feedback operations independently after failures. No method executes
the proposed external action or changes the advisor's policy automatically.

## Persistent strategy outcome journal (v0.4)

`MNNStrategyOutcomeJournal` stores strategy proposals and outcomes as separate
SQLite-backed memory fragments. A proposal records its context, evidence IDs,
and caller-supplied expected reward; it is explicitly marked as not executed.
An outcome is accepted only after explicit execution confirmation and an exact
match between the proposed and executed action.

Evidence IDs must be a sequence of unique, non-empty strings. They are trimmed
and persisted in the proposal; malformed strings, duplicate IDs, and empty
entries are rejected before any fragment is written. Proposal status is also
validated as a string so malformed values fail with a domain validation error.

The journal records the prediction error as:

`prediction_error = observed_reward - expected_reward`

Both rewards must be normalized to [0, 1] by the caller. This difference is a
descriptive learning signal, not a causal estimate or proof that the strategy
caused the result. Stable proposal and operation IDs make sequential retries
idempotent and reject reuse with changed payloads. Records survive reopening
the same FragmentMemory database. The current read-then-add idempotency check
is intended for sequential retries; concurrent writers should serialize access
to a shared journal until a database-level uniqueness/transaction boundary is
added for the complete operation.

The journal does not automatically execute actions, change policies, update
the organism, or provide a distributed transaction across independent stores.


## VirtualBrain strategy event integration (v0.5)

VirtualBrain exposes MNNStrategyEventBridge through its strategy_events attribute. The bridge writes proposal and confirmed-outcome artifacts directly to the append-only EventStore. It does not dual-write to FragmentMemory, so the EventStore remains the authoritative causal journal for these events.

Proposal events preserve status, action, context, expected reward and evidence IDs, and are always marked as not executed. Outcome events require explicit execution confirmation, an exact action match and a normalized observed reward. The outcome artifact references its proposal and the event records the proposal as its cause. Both events participate in the EventStore hash chain.

Stable proposal and operation IDs support sequential retries and reject changed payloads. Concurrent callers using the same IDs must be serialized. The bridge does not execute actions, infer execution from a proposal, or automatically update FragmentMemory or organism weights.


## Replayable autobiographical event projection (v0.6)

`MNNEventMemoryProjector` materializes immutable `EventStore` events as searchable episodic fragments in `FragmentMemory`. The EventStore remains authoritative; FragmentMemory is a derived read model that can be rebuilt by replaying the journal.

Each fragment receives a deterministic ID derived from its source event ID. The projection preserves event hash, sequence, cycle, event type, artifact identity, epistemic status, provenance references and causal reference. Replaying the same range is idempotent. Existing fragments are checked against the source event and conflicting data raises an error rather than overwriting memory.

`project(after_sequence=..., limit=...)` supports bounded replay. The returned `last_sequence` advances over all scanned events, including events excluded by an optional event-type filter. Persist that cursor only after the call succeeds; after a crash, retry from the previous cursor. This is at-least-once replay with deterministic deduplication, not a distributed transaction across the two SQLite databases.

The projector is explicit and opt-in. It does not execute actions, infer new facts, modify source events, or automatically reinforce memory importance.


## Autobiographical event recall (v0.7)

`MNNAutobiographicalRecall` retrieves prior EventStore events from the replayable episodic projection in FragmentMemory. It delegates lexical ranking to `FragmentMemory.recall` and restricts candidates to `episodic_event` fragments, so ordinary notes and other memory kinds cannot crowd out event matches. The memory API now supports an optional kind filter that also constrains one-hop associated results.

Each returned episode carries the source event ID, sequence, cycle, event type, hash, causation reference, artifact identity, epistemic status and decoded artifact. The recall layer checks the projection version and artifact identity before returning a record.

This is a lexical retrieval baseline, not semantic understanding. It does not infer that a remembered event caused a later outcome, that a strategy was successful, or that a reward value proves usefulness. Contextual relevance may adjust retrieval ranking through the existing memory mechanism, without changing global importance.


## Autobiographical strategy review (v0.8)

`MNNAutobiographicalStrategyAdvisor` compares strategy outcomes from replayed EventStore episodes for one exact normalized context. It considers only `strategy.outcome.recorded` events with explicit `execution_confirmed=True`, a configured action, and a finite observed reward within [0, 1]. Proposals, unconfirmed records, other event types and other contexts do not count as outcomes.

A recommendation requires the configured minimum number of distinct cognitive cycles for every compared action and at least two cycle-level samples per action so sample variability can be estimated. Multiple outcomes within one cycle are averaged first, giving each cycle equal weight. The observed mean difference must clear both a minimum reward margin and a configurable variance-based noise guard. The result includes source event IDs and per-action outcome/cycle counts.

This is an observational comparison, not a causal estimate or statistical significance test. It never executes a candidate, modifies policy, or treats one high reward as proof. Insufficient or ambiguous evidence produces an inconclusive result rather than a recommendation.

## Reversible long-term plasticity proposals (v0.9)

`MNNPlasticityController` introduces a separate proposal/apply/rollback lifecycle
for long-term Hebbian weight changes.

```python
from machina import MNNPlasticityController

plasticity = MNNPlasticityController()
proposal = plasticity.propose_hebbian(
    network,
    proposal_id="plasticity-cycle-42",
    learning_rate=0.05,
    reward=0.8,
    max_delta=0.02,
)
# Inspect proposal.deltas and its evidence/context in the caller's audit log.
# Applying is a separate explicit action:
plasticity.apply(network, proposal)
# Roll back only if those exact applied weights have not since changed:
plasticity.rollback(network, proposal.proposal_id)
```

Proposal generation does not mutate the network. Each delta is bounded by
`max_delta`, each final weight is clamped to the network's configured weight
limit, and disabled edges are left unchanged. Application checks a fingerprint
of the complete edge topology and the exact base weights for all selected
connections before changing any weight. A stale proposal is rejected before
any partial update.

Rollback is conditional: it restores the original values only while every
affected edge still has exactly the proposed value. If later learning or an
external edit changed an affected weight, rollback refuses to overwrite it.
The controller snapshot stores both base and proposed weights so this guard can
be restored after restart when persisted together with the network snapshot.

This controller is deliberately not automatically wired to strategy review.
A caller must inspect the proposal and explicitly call `apply`. The controller
is in-memory and does not itself append EventStore records; production
integration should persist proposal, approval, application and rollback events
in the authoritative event journal. The current Hebbian proposal is a bounded
engineering mechanism, not proof that an edge is causally useful or that a
strategy caused a reward.


## Experience-guided reversible plasticity (v1.0)

`MNNExperiencePlasticityAdvisor` connects the autobiographical strategy
review to the reversible `MNNPlasticityController`. It only prepares a
synaptic proposal when the strategy advisor returns a candidate supported by
its configured minimum number of distinct cycles and variability guard.

The integration requires an explicit `action_connection_map` from the caller.
For example, the caller may configure that a named action is associated with a
specific set of connection IDs. This is an engineering hypothesis, not a
causal discovery: the adapter does not infer which synapses produced an
observed reward. Unknown or unmapped candidate actions produce no proposal.

```python
from machina import MNNExperiencePlasticityAdvisor

experience_plasticity = MNNExperiencePlasticityAdvisor(
    strategy_advisor,
    plasticity_controller,
    network,
    action_connection_map={"candidate-action": ["edge-17", "edge-21"]},
)
proposal = experience_plasticity.review_and_propose(
    "motor maintenance",
    current_action="baseline-action",
    proposal_id="experience-plasticity-42",
    learning_rate=0.05,
    max_delta=0.01,
)
if proposal is not None:
    # Inspect action, context, event IDs, cycles, connection IDs and deltas.
    experience_plasticity.apply(proposal)  # explicit approval boundary
```

The proposal preserves the exact outcome event IDs and distinct cycle IDs
used by the strategy review, plus the configured connection IDs and the
candidate action's mean observed reward. Review never changes weights.
Application delegates to the controller's topology/base-weight checks;
rollback delegates to its conditional guard and refuses to overwrite later
weight changes.

This adapter does not persist its own lifecycle events yet. The caller should
retain the proposal and controller/network snapshots until an EventStore
plasticity-event contract is introduced. The reward is used as a bounded
Hebbian modulation input, not as proof that the mapped connections caused the
outcome. No candidate means no proposal, and no proposal is automatically
applied.

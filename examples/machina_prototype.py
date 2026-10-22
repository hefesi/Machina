"""Runnable local CLI prototype combining MNN, VirtualBrain, and fragment memory.

Run from the repository root:
    python -m examples.machina_prototype --data-dir .machina-data

This is a transparent research prototype. The default cognition component is
deterministic and acknowledges observations; it is not a language model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from machina import (
    AutonomyContext, AutonomyController, AutonomyExperienceStore, Connection, FragmentMemory, MNN,
    MNNCognitionAdapter, PersistentGoalStore, Unit, VirtualBrain,
)


def _terms(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"[\wÀ-ÿ]+", text.casefold())))


def build_network() -> tuple[MNN, dict[str, str]]:
    network = MNN(weight_limit=5.0)
    features = {
        "input_text_length": "text_length",
        "input_token_count": "token_count",
        "input_memory_count": "memory_count",
        "input_reliability": "source_reliability",
    }
    for unit_id in features:
        network.add_unit(Unit(unit_id, activation="identity"))
    network.add_unit(Unit("integration", bias=0.0, activation="sigmoid"))
    for unit_id, weight in (
        ("input_text_length", 0.8),
        ("input_token_count", 0.6),
        ("input_memory_count", 0.3),
        ("input_reliability", 0.5),
    ):
        network.add_connection(
            Connection(f"{unit_id}_to_integration", unit_id, "integration", weight)
        )
    return network, features


class MachinaPrototype:
    """Small user-facing facade over durable MNN, journal, and fragment memory."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        network, input_features = build_network()
        adapter = MNNCognitionAdapter(network, input_features=input_features)
        self.brain = VirtualBrain(self.data_dir / "virtual_brain.sqlite3", cognition=adapter)
        self.memory = FragmentMemory(self.data_dir / "fragment_memory.sqlite3")
        self.autonomy = AutonomyController()
        self.autonomy_memory = AutonomyExperienceStore(self.data_dir / "autonomy.sqlite3")
        self.goal_store = PersistentGoalStore(self.data_dir / "persistent_goals.sqlite3")
        self._cycles_since_reflection = 0
        self._cycles_since_memory_review = 0

    def close(self) -> None:
        self.brain.close()
        self.memory.close()
        self.autonomy_memory.close()
        self.goal_store.close()

    def __enter__(self) -> "MachinaPrototype":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def remember(
        self, content: str, *, importance: float = 0.5, tags: list[str] | None = None
    ) -> dict[str, Any]:
        fragment = self.memory.add(
            content,
            source_uri="machina://local-user",
            importance=importance,
            confidence=1.0,
            tags=tags if tags is not None else _terms(content),
        )
        return {
            "id": fragment.id,
            "content": fragment.content,
            "importance": fragment.importance,
            "tags": list(fragment.tags),
        }

    def recall(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        query_tags = _terms(query)
        fragments = self.memory.active(limit=max(limit, 1), query_tags=query_tags)
        if query_tags:
            requested = set(query_tags)
            fragments = [
                item for item in fragments if requested.intersection(item.tags)
            ]
        return [
            {
                "id": item.id,
                "content": item.content,
                "importance": round(item.importance, 4),
                "priority": round(item.priority, 4),
                "tags": list(item.tags),
                "pinned": item.pinned,
            }
            for item in fragments[:limit]
        ]

    def think(self, observation: str, *, goal: str = "Process and record this observation") -> dict[str, Any]:
        result = self.brain.run_cycle(
            observation,
            goal,
            source={"type": "user", "name": "local_cli", "reliability": 1.0},
        )
        cognition = next(
            (event.artifact for event in result.events if event.event_type == "cognition.completed"),
            None,
        )
        understanding = cognition.data.get("understanding", {}) if cognition else {}
        return {
            "cycle_id": result.cycle_id,
            "status": result.status,
            "observation": observation,
            "goal": goal,
            "mnn_signal": understanding.get("mnn_signal", {}),
            "memory_ids_retrieved": next(
                (
                    event.artifact.data.get("memory_ids", [])
                    for event in result.events
                    if event.event_type == "memory.retrieved"
                ),
                [],
            ),
            "audit_valid": self.brain.audit_cycle(result.cycle_id).valid,
            "note": "The default cognition is deterministic; MNN activations are diagnostic, not semantic understanding.",
        }

    def autonomy_step(self) -> dict[str, Any]:
        """Generate a goal, persist its lifecycle, and execute one local cognitive cycle."""
        fragments = self.memory.active(limit=100)
        important_count = sum(1 for item in fragments if item.importance >= 0.75)
        history = self.autonomy_memory.summary()
        context = AutonomyContext(
            memory_count=self.memory.count(),
            important_memory_count=important_count,
            failed_cycles=history["failures"],
            cycles_since_reflection=self._cycles_since_reflection,
            cycles_since_memory_review=self._cycles_since_memory_review,
        )
        decision = self.autonomy.step(
            context,
            drive_adjustments=self.autonomy_memory.drive_adjustments(),
            recent_goal_ids=self.autonomy_memory.recent_goal_ids(),
        )
        selected = decision.selected_goal
        if selected is None:
            return {
                "status": "no_safe_goal",
                "decision": decision.to_dict(),
                "note": "No eligible internal goal was found; no action was executed.",
            }

        experience_id = self.autonomy_memory.record_selection(selected)
        persistent_goal = self.goal_store.register(selected)
        self._cycles_since_reflection += 1
        self._cycles_since_memory_review += 1
        if selected.drive == "self_reflection":
            self._cycles_since_reflection = 0
        if selected.drive == "memory_maintenance":
            self._cycles_since_memory_review = 0

        cycle = self.think(
            f"Machina iniciou uma tarefa interna: {selected.description}",
            goal=selected.description,
        )
        return {
            "status": "goal_executed_in_prototype",
            "decision": decision.to_dict(),
            "experience_id": experience_id,
            "persistent_goal": persistent_goal,
            "feedback_command": "/goal-feedback success|failure|skip [evidence]",
            "cycle": cycle,
            "autonomy_scope": (
                "The goal was self-generated, but execution remains a local "
                "cognitive cycle with the acknowledge-only executor."
            ),
        }

    def record_goal_feedback(self, outcome: str, evidence: str = "") -> dict[str, Any]:
        """Record feedback in both the selection-learning and goal-lifecycle ledgers."""
        experience = self.autonomy_memory.record_feedback(outcome)
        goal = self.goal_store.record_outcome(
            experience["goal_id"], outcome, evidence or f"Explicit feedback: {outcome}"
        )
        return {
            "feedback_recorded": experience,
            "persistent_goal": goal,
            "autonomy_learning": self.autonomy_memory.summary(),
        }

    def status(self) -> dict[str, Any]:
        return {
            "prototype": "Machina local prototype 0.1",
            "memory_fragments": self.memory.count(),
            "brain_journal": str(self.data_dir / "virtual_brain.sqlite3"),
            "fragment_database": str(self.data_dir / "fragment_memory.sqlite3"),
            "mnn_timestep": getattr(self.brain.cognition.network, "timestep", 0),
            "autonomy": self.autonomy_memory.summary(),
            "persistent_goals": self.goal_store.summary(),
        }


def run_cli(data_dir: str | Path) -> None:
    print("Machina — protótipo local 0.1")
    print("Comandos: /remember TEXTO | /recall CONSULTA | /think TEXTO | /autonomy | /goal-feedback success|failure|skip [evidência] | /goal-status [status] | /goal-resume ID | /goal-abandon ID MOTIVO | /status | /help | /quit")
    with MachinaPrototype(data_dir) as machina:
        while True:
            try:
                line = input("\nVocê> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nEncerrando. Os dados locais foram preservados.")
                break
            if not line:
                continue
            if line in {"/quit", "/exit"}:
                print("Encerrando. Os dados locais foram preservados.")
                break
            try:
                if line == "/help":
                    output: Any = {
                        "/remember TEXTO": "Salvar um fragmento persistente de memória",
                        "/recall CONSULTA": "Buscar fragmentos pelos termos/tags",
                        "/think TEXTO": "Executar um ciclo cognitivo e mostrar o sinal da MNN",
                        "/autonomy": "Gerar e executar um objetivo interno e mantê-lo no diário persistente",
                        "/goal-feedback success|failure|skip [evidência]": "Registrar resultado explícito, atualizar prioridades e estado do objetivo",
                        "/goal-status [status]": "Listar objetivos persistentes; status: active, completed, paused, needs_revision, abandoned",
                        "/goal-resume ID": "Reativar objetivo pausado ou que precisa de revisão (ID é o goal_id, por exemplo reflect_on_progress)",
                        "/goal-abandon ID MOTIVO": "Abandonar explicitamente um objetivo aberto e registrar a justificativa",
                        "/status": "Mostrar estado, memória, autonomia e objetivos persistentes",
                        "/quit": "Encerrar",
                    }
                elif line == "/autonomy":
                    output = machina.autonomy_step()
                elif line.startswith("/goal-feedback "):
                    parts = line[len("/goal-feedback "):].strip().split(maxsplit=1)
                    if not parts:
                        raise ValueError("use /goal-feedback success|failure|skip [evidência]")
                    evidence = parts[1] if len(parts) > 1 else ""
                    output = machina.record_goal_feedback(parts[0].casefold(), evidence)
                elif line.startswith("/goal-status"):
                    parts = line.split(maxsplit=1)
                    status_filter = parts[1].strip() if len(parts) > 1 else None
                    output = {
                        "goals": machina.goal_store.list_goals(status=status_filter),
                        "summary": machina.goal_store.summary(),
                    }
                elif line.startswith("/goal-resume "):
                    goal_id = line[len("/goal-resume "):].strip()
                    if not goal_id:
                        raise ValueError("use /goal-resume GOAL_ID")
                    output = machina.goal_store.resume(goal_id)
                elif line.startswith("/goal-abandon "):
                    parts = line[len("/goal-abandon "):].strip().split(maxsplit=1)
                    if len(parts) != 2:
                        raise ValueError("use /goal-abandon GOAL_ID MOTIVO")
                    output = machina.goal_store.abandon(parts[0], parts[1])
                elif line == "/status":
                    output = machina.status()
                elif line.startswith("/remember "):
                    output = machina.remember(line[len("/remember "):])
                elif line.startswith("/recall"):
                    query = line[len("/recall"):].strip()
                    output = machina.recall(query)
                elif line.startswith("/think "):
                    output = machina.think(line[len("/think "):])
                else:
                    output = {"error": "Comando não reconhecido. Digite /help.", "input": line}
                print(json.dumps(output, ensure_ascii=False, indent=2))
            except (ValueError, KeyError, RuntimeError) as error:
                print(json.dumps({"error": str(error)}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        default=".machina-data",
        help="Diretório local para persistência (padrão: .machina-data)",
    )
    args = parser.parse_args()
    run_cli(args.data_dir)


if __name__ == "__main__":
    main()

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

from machina import Connection, FragmentMemory, MNN, MNNCognitionAdapter, Unit, VirtualBrain


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

    def close(self) -> None:
        self.brain.close()
        self.memory.close()

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
        # Keep only fragments sharing at least one requested token when a query
        # is provided; an empty query intentionally returns the active view.
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
            "memory_ids_retrieved": (
                next(
                    (
                        event.artifact.data.get("memory_ids", [])
                        for event in result.events
                        if event.event_type == "memory.retrieved"
                    ),
                    [],
                )
            ),
            "audit_valid": self.brain.audit_cycle(result.cycle_id).valid,
            "note": "The default cognition is deterministic; MNN activations are diagnostic, not semantic understanding.",
        }

    def status(self) -> dict[str, Any]:
        return {
            "prototype": "Machina local prototype 0.1",
            "memory_fragments": self.memory.count(),
            "brain_journal": str(self.data_dir / "virtual_brain.sqlite3"),
            "fragment_database": str(self.data_dir / "fragment_memory.sqlite3"),
            "mnn_timestep": getattr(self.brain.cognition.network, "timestep", 0),
        }


def run_cli(data_dir: str | Path) -> None:
    print("Machina — protótipo local 0.1")
    print("Comandos: /remember TEXTO | /recall CONSULTA | /think TEXTO | /status | /help | /quit")
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
                        "/status": "Mostrar estado e caminhos dos bancos locais",
                        "/quit": "Encerrar",
                    }
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
                    output = {
                        "error": "Comando não reconhecido. Digite /help.",
                        "input": line,
                    }
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

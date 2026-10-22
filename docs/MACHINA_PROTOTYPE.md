# Machina local prototype 0.1

This is the first runnable user-facing prototype that connects three real
pieces of the repository:

1. **VirtualBrain** — executes and audits a durable cognitive cycle.
2. **MNN** — processes normalized input features and emits a diagnostic signal.
   The signal is not yet used as the semantic decision-maker.
3. **FragmentMemory** — persists memory fragments in SQLite, ranks an active
   view by priority, and keeps archived records rather than deleting low-priority
   information.

## Requirements

Python 3.12. From the repository root:

```bash
python -m pip install -e .
python -m examples.machina_prototype
```

To select a custom data directory:

```bash
python -m examples.machina_prototype --data-dir ./machina-data
```

## Commands

- `/remember MNN precisa preservar memórias importantes` — save a durable memory fragment.
- `/recall memoria importante` — retrieve active fragments sharing those tags.
- `/think Precisamos testar a memória persistente` — run a complete VirtualBrain cycle and display its MNN signal and audit result.
- `/status` — show memory count, local database paths, and the current MNN timestep.
- `/help` and `/quit`.

Data is written only to the selected local directory. To start over, stop the
program and manually remove that directory after backing up anything important.

## What works now

- Local interactive command loop.
- SQLite persistence for memory fragments and VirtualBrain event journal.
- Priority-aware active memory view with non-destructive archive.
- MNN feature pass included in the cognitive artifact.
- Durable cycle and audit output.
- Automated tests for restart persistence and cognitive-cycle integration.

## Honest limitations

The default cognition engine is a deterministic placeholder that acknowledges
the observation. This prototype does not include an LLM, broad natural-language
understanding, autonomous external actions, or evidence of consciousness/AGI.
The MNN signal is inspectable telemetry, not a semantic conclusion. The
prototype is intended to provide an executable foundation for iterative
experimentation, not to be presented as a finished intelligent assistant.

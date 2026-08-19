# Virtual Brain v0.1 — núcleo executável

Esta implementação transforma o contrato conceitual em um primeiro loop
executável, sem alegar resolver a cognição ou a autonomia do Machina.

## Como executar

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 examples/basic_loop.py
```

O núcleo usa apenas Python 3.12+ e SQLite da biblioteca padrão.

## Garantias implementadas

```text
Observation
  → WorkspaceState
  → MemoryQuery / MemoryRetrieval
  → CognitiveRequest / CognitiveResult
  → DecisionRequest / Decision / ActionIntent
  → ActionResult
  → Experience / Episodic Memory / Evaluation
  → LearningProposal
  → Validation
  → versioned MemoryRecord / ModelUpdate
```

Cada objeto é um `Artifact` imutável com:

- identificador único, `cycle_id`, produtor e versão de schema;
- referências de entrada que formam o grafo causal;
- referências de fonte/proveniência;
- status epistemológico (`observed`, `inferred`, `believed`, etc.);
- timestamp, status e confiança quando aplicável.

Cada transição é persistida em SQLite antes de a etapa seguinte começar. A
tabela de eventos é append-only por trigger e cada evento participa de uma
cadeia SHA-256. `verify_integrity()` recomputa a cadeia inteira.

Além da verificação criptográfica, `brain.audit_cycle(cycle_id)` confere a
ordem das etapas obrigatórias, referências causais, distinções epistemológicas
e a regra `LearningProposal → Validation → ModelUpdate`.

O journal é a fonte de verdade. Workspace é uma projeção transitória e pode
ser reconstruído a partir do journal depois de reiniciar o processo.

## Interrupção e retomada

```python
cycle_id = brain.start_cycle("entrada", "objetivo")
brain.advance(cycle_id, stop_after="action.result")
# processo pode encerrar aqui

brain = VirtualBrain("brain.sqlite", action_executor=executor)
brain.resume(cycle_id)
```

Uma etapa já persistida não é repetida. Antes de chamar uma ferramenta, o
núcleo persiste `action.execution_started`; portanto implementações reais de
`ActionExecutor` devem usar `ActionIntent.id` como chave de idempotência. Se
o processo morrer entre a chamada externa e o registro de `ActionResult`, a
retomada chama a ferramenta com a mesma chave — ela deve devolver o resultado
anterior, e não repetir o efeito externo.

Falha de ferramenta não descarta o ciclo: produz `ActionResult(status=failed)`,
`Experience`, memória episódica, avaliação e uma proposta rejeitada quando a
evidência não basta. Learning só propõe; Consolidation valida; Memory persiste
uma nova versão sem apagar a anterior.

## Limites intencionais desta fase

- A cognição padrão é determinística e segura (`acknowledge`); modelos/LLMs
  entram por interfaces `CognitionEngine`, `AgencyPolicy` e `ActionExecutor`.
- A recuperação usa sobreposição de tokens apenas como mecanismo mínimo
  observável. Embeddings, grafos e ranking mais rico podem ser substituídos
  dentro de `MemoryRepository` sem alterar os contratos.
- O núcleo não concede permissões externas por padrão.

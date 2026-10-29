# MNN — Ciclo de experiência e recompensa atrasada

## Objetivo

Unificar atividade neural, acúmulo de elegibilidade e consequência atrasada em um
componente serializável. A rede não altera pesos antes de conhecer o resultado;
quando o resultado chega, ele é atribuído às conexões que participaram da
atividade original.

## API

- `MNNExperienceCycle(network, modulator=None, learning_rate=0.1)` cria o ciclo.
- `step(inputs)` avança a MNN e acumula traços de elegibilidade usando recompensa
  neutra, sem reforçar ou punir pesos.
- `resolve(reward)` aplica o erro de previsão aos traços acumulados, retorna as
  mudanças de peso e os snapshots, e então limpa os traços.
- `snapshot()` / `from_snapshot(...)` preservam rede, modulador e uma experiência
  em andamento para retomada após reinício.
- `MNNExperienceCheckpointStore(path)` grava o snapshot completo com substituição
  atômica (`save(cycle)`) e o restaura com validação (`load()`). Assim, uma
  recompensa atrasada pode chegar depois de um reinício e ainda ser aplicada
  uma única vez às conexões que participaram da experiência original.

Snapshots inválidos, esquema desconhecido, `pending_steps` inválido, recompensa
não finita e traços ligados a conexões inexistentes são rejeitados. O checkpoint
também rejeita JSON malformado, conteúdo que não seja objeto e snapshots
incompletos antes de substituir um arquivo válido.

## Integração com o VirtualBrain

`MNNCognitionAdapter(..., delayed_reward=True)` ativa o ciclo no adaptador
cognitivo. Nesse modo:

- `analyze` usa `MNNExperienceCycle.step`, acumula elegibilidade com recompensa
  neutra e persiste o `experience_snapshot` completo no artefato
  `cognition.completed`;
- `propose_evaluated_outcome` resolve a recompensa somente depois da avaliação,
  aplica o erro de previsão aos traços persistidos e devolve tanto o snapshot da
  rede quanto o snapshot do ciclo já fechado;
- o `VirtualBrain` restaura o snapshot do ciclo antes de retomar uma execução,
  inclusive quando a pausa ocorreu depois de `cognition.completed` e antes de
  `mnn.plasticity_applied`;
- o mesmo estado fechado é restaurado depois de `mnn.plasticity_applied`, sem
  aplicar a recompensa duas vezes.

O padrão continua sendo `delayed_reward=False`, que preserva a plasticidade
Hebbiana imediata existente.

## Validação

```bash
python -m unittest tests.test_mnn_experience -v
python -m unittest tests.test_mnn_experience_checkpoint -v
python -m benchmarks.mnn_delayed_reward
python -m unittest tests.test_mnn_delayed_reward -v
python -m unittest discover -s tests -v
```

Os testes de checkpoint cobrem round-trip exato, experiência pendente que
sobrevive ao reinício, aplicação única da recompensa atrasada e rejeição de
arquivos inválidos.

O benchmark compara uma regra Hebbiana imediata com a regra de elegibilidade:
com atraso, a coatividade no instante da recompensa é zero, mas o traço anterior
ainda permite uma atualização. Aumentar o atraso deve reduzir a contribuição do
traço. Esse resultado valida o mecanismo em um caso controlado, não aprendizado
geral, equivalência biológica ou consciência.

## Limites

O ciclo não escolhe ações, não constrói um modelo de mundo e não prova
inteligência. A baseline e os traços são variáveis computacionais abstratas.
Próximos experimentos devem incluir recompensa negativa, atraso variável,
interferência entre experiências, retenção após reinício e comparação com uma
linha de base sem elegibilidade.

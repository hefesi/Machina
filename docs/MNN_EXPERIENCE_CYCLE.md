# MNN — Ciclo de experiência e recompensa atrasada

## Objetivo

Unificar atividade neural, acúmulo de elegibilidade e consequência atrasada em um
componente serializável. A rede não altera pesos antes de conhecer o resultado;
quando o resultado chega, ele é atribuído às conexões que participaram da
atividade original.

## API

- `MNNExperienceCycle(network, modulator=None, learning_rate=0.1,
  max_pending_steps=None, growth_policy=None, growth_min_reward=0.0,
  prune_after_negative_outcomes=None)` cria o ciclo. O limite opcional impede
  que uma única experiência acumule passos sem limite; ao atingi-lo, `step`
  falha antes de alterar estados, pesos ou traços.
- `step(inputs)` avança a MNN e acumula traços de elegibilidade usando recompensa
  neutra, sem reforçar ou punir pesos.
- `resolve(reward)` aplica o erro de previsão aos traços acumulados, retorna as
  mudanças de peso e os snapshots, e então limpa os traços. Se houver
  `growth_policy` e `reward >= growth_min_reward`, também cresce conexões
  limitadas e retorna `grown_connections`. Conexões crescidas podem ser podadas
  após falhas consecutivas; `resolve` retorna `pruned_connections`.
- `abort()` descarta uma experiência pendente sem aplicar resultado. Os pesos e
  a baseline de recompensa são preservados; apenas os traços de elegibilidade
  daquela experiência são removidos. É a operação explícita para resultados que
  nunca chegarão.
- `snapshot()` / `from_snapshot(...)` preservam rede, modulador, política de
  crescimento, contador `structural_utility` e uma experiência em andamento para
  retomada após reinício.
- `MNNExperienceCheckpointStore(path)` grava o snapshot completo com substituição
  atômica (`save(cycle)`) e o restaura com validação (`load()`). Assim, uma
  recompensa atrasada pode chegar depois de um reinício e ainda ser aplicada
  uma única vez às conexões que participaram da experiência original.

Snapshots inválidos, esquema desconhecido, `pending_steps` inválido, recompensa
não finita e traços ligados a conexões inexistentes são rejeitados. O limite
`max_pending_steps` é persistido no snapshot; snapshots antigos sem esse campo
continuam válidos e recebem limite `None`. Um snapshot com
`pending_steps > max_pending_steps` é rejeitado. O checkpoint também rejeita
JSON malformado, conteúdo que não seja objeto e snapshots incompletos antes de
substituir um arquivo válido.

## Integração com o VirtualBrain

`MNNCognitionAdapter(..., delayed_reward=True, max_pending_steps=...)` ativa o
ciclo no adaptador cognitivo. Nesse modo:

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
  aplicar a recompensa duas vezes;
- `abort_pending_experience()` descarta uma experiência órfã no adaptador sem
  alterar pesos nem baseline;
- `growth_policy`, `growth_min_reward` e `prune_after_negative_outcomes` podem
  ser configurados no adaptador; nesse caso, um desfecho que atinja o limite
  pode criar conexões e o resultado persistido inclui `grown_connections` e
  `pruned_connections`.

O padrão continua sendo `delayed_reward=False`, que preserva a plasticidade
Hebbiana imediata existente. Política de crescimento e poda exigem
`delayed_reward=True`.

A poda considera apenas conexões criadas pela política, não altera conexões
preexistentes e usa falhas negativas consecutivas. Um desfecho positivo zera o
contador; um desfecho neutro não o altera. O contador e o limite são persistidos
no snapshot e sobrevivem ao reinício.

## Validação

```bash
python -m unittest tests.test_mnn_experience -v
python -m unittest tests.test_mnn_experience_checkpoint -v
python -m benchmarks.mnn_delayed_reward
python -m unittest tests.test_mnn_delayed_reward -v
python -m benchmarks.mnn_experience_learning
python -m unittest tests.test_mnn_experience_learning -v
python -m benchmarks.mnn_rewarded_structural_growth
python -m unittest tests.test_mnn_rewarded_structural_growth -v
python -m benchmarks.mnn_structural_pruning
python -m unittest tests.test_mnn_structural_pruning -v
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

## Benchmark de aprendizado e retenção

`python -m benchmarks.mnn_experience_learning` executa uma associação
determinística de dois contextos. Cada tentativa apresenta um contexto por dois
passos, recebe recompensa neutra e só depois resolve o resultado; a
recompensa atrasada atualiza as conexões elegíveis. O experimento mede acurácia
antes e depois do aprendizado, salva o ciclo em checkpoint e mede a retenção
após reconstruir o ciclo a partir do arquivo.

O resultado esperado é acurácia `0.5` com pesos fixos, `1.0` após o aprendizado
e `1.0` após a recarga, com pesos idênticos e `pending_steps == 0`. Isso
demonstra apenas a mecânica em uma tarefa minúscula; não demonstra
generalização ampla, raciocínio semântico, consciência ou inteligência geral.

## Limites

O ciclo não escolhe ações, não constrói um modelo de mundo e não prova
inteligência. A baseline, os traços e o crescimento estrutural são variáveis
computacionais abstratas. Próximos experimentos devem incluir recompensa
negativa, atraso variável, interferência entre experiências, retenção após
reinício, crescimento sob recompensa ruidosa e comparação com uma linha de base
sem elegibilidade.

# MNN — crescimento estrutural limitado

## Objetivo

Adicionar uma política explícita e determinística para escolher onde criar
novas conexões a partir da co-atividade atual das unidades. Isso complementa as
operações primitivas `grow_connection` e `prune_connections`, que já existiam,
sem alegar que a MNN descobre sozinha uma topologia ótima.

## API

```python
from machina import ActivityGrowthPolicy

policy = ActivityGrowthPolicy(
    max_new_connections=1,
    initial_weight=0.75,
    min_activity=0.1,
    max_connections=20,
    max_out_degree=4,
    max_in_degree=4,
    allowed_sources={"cue"},
    allowed_targets={"response"},
)
grown = policy.grow(network)
```

- Candidatos são pares direcionados de unidades com atividade absoluta acima de
  `min_activity`.
- A pontuação é `abs(pre_state * post_state)`.
- A ordem é determinística: maior pontuação, depois ID de origem, depois ID de
  destino.
- Auto-conexões, pares já existentes e unidades silenciosas são excluídos.
- `max_new_connections`, `max_connections`, `max_out_degree` e `max_in_degree`
  limitam o crescimento total e por unidade.
- `allowed_sources` e `allowed_targets` restringem a direção do crescimento.
- Pesos de conexões existentes nunca são alterados.
- `initial_weight` é positivo e limitado pelo `weight_limit` da rede.
- Cada item retornado é um `GrownConnection` com a conexão criada e a pontuação.

A política também pode ser acoplada ao ciclo de experiência:

```python
cycle = MNNExperienceCycle(
    network,
    growth_policy=policy,
    growth_min_reward=0.0,
)
```

Nesse caso, `resolve(reward)` só invoca a política quando
`reward >= growth_min_reward`. O resultado inclui `grown_connections`, e o
snapshot do ciclo persiste a configuração da política. `abort()` nunca cresce
conexões. A política ainda não escolhe objetivos nem decide sozinha quando
aprender; o limite de recompensa e o momento da resolução são explícitos.

### Poda de conexões crescidas

```python
cycle = MNNExperienceCycle(
    network,
    growth_policy=policy,
    prune_after_negative_outcomes=2,
)
```

- Apenas conexões criadas pela política de crescimento entram no contador.
- Cada desfecho negativo consecutivo decrementa a utilidade da conexão.
- Um desfecho positivo zera o contador; um desfecho neutro não altera.
- Quando a utilidade chega a `-prune_after_negative_outcomes`, a conexão é
  removida e seus traços de elegibilidade são descartados.
- `resolve` retorna `pruned_connections`, e o contador é persistido em
  `structural_utility` no snapshot do ciclo.
- A poda exige `growth_policy`; sem ela, a configuração é rejeitada.

## Benchmarks

```bash
python -m benchmarks.mnn_structural_growth
python -m benchmarks.mnn_rewarded_structural_growth
python -m benchmarks.mnn_structural_pruning
python -m unittest tests.test_mnn_structure \
  tests.test_mnn_structural_growth_benchmark \
  tests.test_mnn_rewarded_structural_growth \
  tests.test_mnn_structural_pruning -v
```

Protocolo:

1. a rede começa sem conexões entre `cue` e `response`;
2. no treino, ambas as unidades são ativadas ao mesmo tempo por teacher forcing;
3. a política cria uma única aresta `cue -> response`;
4. na avaliação, apenas `cue` recebe entrada;
5. a resposta deve ser produzida pela nova aresta, antes e depois de salvar e
   recarregar o checkpoint.

O benchmark `mnn_rewarded_structural_growth` repete a associação dentro do ciclo
de recompensa atrasada: a experiência pendente é salva, recarregada, resolvida
com recompensa `+1` e só então cresce. Um controle com recompensa `-1` não pode
criar a aresta.

O benchmark `mnn_structural_pruning` cresce a aresta com recompensa `+1` e aplica
duas falhas consecutivas com `learning_rate=0`, isolando a manutenção estrutural
da plasticidade de pesos. A primeira falha preserva a aresta e persiste utilidade
`-1`; após reinício, a segunda falha remove a aresta e a resposta volta a `0.0`.
Um controle sem poda mantém a aresta após as mesmas falhas.

Critérios de aprovação:

- resposta inicial: `0.0`;
- controle com recompensa negativa: `0.0` e nenhuma conexão criada;
- resposta após o crescimento: `0.75`;
- resposta após reinício: `0.75`;
- exatamente uma conexão criada, com origem `cue`, destino `response`;
- pesos e topologia preservados após o checkpoint;
- poda somente após o número configurado de falhas consecutivas;
- contador de utilidade preservado após checkpoint.

## Limitações

Este experimento demonstra apenas uma associação estrutural pequena com teacher
forcing, recompensa explícita e uma regra simples de poda. Ele não demonstra
descoberta autônoma de topologia, seleção de objetivos, generalização entre
tarefas, compreensão semântica, consciência ou inteligência geral. O próximo
passo é validar se o crescimento melhora uma tarefa mantida fora do treino e se
a manutenção evita crescimento inútil sob recompensa ruidosa, sinais
contraditórios e ambientes não estacionários.

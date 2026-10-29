# MNN — Ciclo de experiência e consequência

## Objetivo

Unificar a atividade da rede e a modulação por recompensa atrasada em um
componente executável, com estado serializável mesmo quando uma experiência
ainda está aguardando seu resultado.

## Ciclo

1. `step(inputs)` avança a MNN e acumula traços de elegibilidade usando a
   recompensa neutra atual (igual à baseline), para não reforçar nem punir antes
   do resultado.
2. Passos intermediários sem entrada podem representar o atraso entre ação e
   consequência; os traços decaem conforme `trace_decay`.
3. `resolve(reward)` calcula o erro em relação à baseline e aplica esse sinal
   aos traços acumulados.
4. O resultado inclui alterações de peso e snapshots. Os traços temporários são
   limpos ao fechar a experiência.
5. `snapshot()` / `from_snapshot(...)` preservam a rede, o modulador e a
   experiência em andamento para retomar após reinício.

## Execução

```bash
python -m unittest tests.test_mnn_experience -v
python -m unittest tests.test_mnn_reward -v
python -m unittest discover -s tests -v
```

## Limites

Este componente é um mecanismo de atribuição de crédito, não uma política de
ação, modelo de mundo completo ou prova de inteligência geral. A baseline e os
traços são variáveis computacionais abstratas. Antes de usar em um agente
persistente, comparar com uma linha de base sem elegibilidade e avaliar tarefas
repetidas, recompensa negativa, atraso variável, retenção e interferência.

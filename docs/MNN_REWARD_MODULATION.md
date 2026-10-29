# MNN — Etapa: modulação de recompensa e traços de elegibilidade

## Objetivo

Permitir que um resultado recebido depois de uma atividade influencie as conexões
que estavam ativas durante essa atividade. Isso é um mecanismo computacional
inspirado, de forma abstrata, na modulação neuromodulatória; não simula dopamina
biológica nem implica sentimento ou consciência.

## Regra

Para cada conexão e em cada atualização:

`e(t) = decay * e(t-1) + pre(t) * post(t)`

`erro(t) = recompensa(t) - baseline(t-1)`

`w(t+1) = clip(w(t) + taxa * erro(t) * e(t), -limite, +limite)`

A baseline é atualizada por média móvel exponencial depois do cálculo do erro.
Na primeira recompensa, o erro é a própria recompensa. Isso deixa o comportamento
determinístico e configurável, mas não equivale a um sistema biológico completo.

## API

- `RewardModulator.update(network, reward, learning_rate=0.1)`: atualiza os
  traços e aplica a recompensa/erro de previsão aos pesos.
- `reset_traces()`: limpa traços de curto prazo sem apagar a baseline.
- `snapshot()` / `from_snapshot(...)`: serializa estado do modulador para
  persistência explícita.
- Traços de conexões removidas ou desabilitadas são descartados.

## Validação

```bash
python -m unittest tests.test_mnn_reward -v
python -m unittest discover -s tests -v
```

Os testes cobrem recompensa positiva, recompensa atrasada, erro negativo,
limites de peso, conexões desabilitadas e restauração de snapshot. A eficácia
cognitiva mais ampla ainda precisa ser avaliada em benchmarks de tarefas e
comparada com uma linha de base sem modulação.

## Enquadramento na hipótese fundamental

Modulação por recompensa é uma abstração funcional inspirada em mecanismos biológicos. Não deve ser descrita como dopamina real, prazer ou sentimento. Investigar como sinais de valor e erro de previsão afetam plasticidade, exploração, persistência e escolha, e se essas alterações se integram a uma dinâmica interna estável. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).

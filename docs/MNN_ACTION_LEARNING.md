# MNN — Aprendizado de valor e seleção de ações

## Por que esta etapa

A MNN já possui estados, conexões, plasticidade e traços para recompensa
atrasada. Esta etapa acrescenta um experimento controlado de decisão: cada ação
tem uma conexão cujo peso representa a recompensa média prevista. A diferença
entre previsão e consequência ajusta o peso.

## Uso mínimo

```python
from machina import MNNActionLearner

learner = MNNActionLearner(["explorar", "conservar"], learning_rate=0.2)
action = learner.choose()
reward = 1.0 if action == "explorar" else 0.0
update = learner.observe(reward)
state = learner.snapshot()
```

O seletor experimenta cada ação uma vez, depois escolhe a maior previsão e
realiza exploração periódica determinística. O estado serializado preserva os
pesos aprendidos, a contagem de observações e o calendário de exploração.

## Experimentos e limites

```bash
python -m unittest tests.test_mnn_action_learning -v
python -m unittest discover -s tests -v
```

Os testes cobrem preferência por maior recompensa, adaptação quando a recompensa
muda e restauração após reinício. É uma baseline de bandit sem estado contextual:
não faz planejamento de múltiplas etapas, não aprende sem receber feedback e
não demonstra inteligência geral. O peso é um valor preditivo simplificado; em
etapas futuras deve ser comparado com previsão contextual e com o ciclo de
elegibilidade/recompensa atrasada.

## Enquadramento na hipótese fundamental

Aprender a partir das consequências de ações é relevante para o acoplamento contínuo entre Machina e seu ambiente. O experimento deve distinguir correlação, atribuição causal e adaptação persistente, medindo se os resultados alteram políticas futuras. A capacidade de aprender com ação não implica, isoladamente, experiência consciente. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).

# MNN — Etapa F2: combinações de características não vistas

## Objetivo

Testar se a MNN aplica uma associação aprendida a combinações de características
que não apareceram juntas no treinamento, e se esse comportamento persiste após
a restauração de um checkpoint.

## Execução

```bash
python -m pip install -e .
python -m benchmarks.mnn_compositional_transfer
python -m unittest tests.test_mnn_compositional_transfer -v
python -m unittest discover -s tests -v
```

## Protocolo

A rede possui duas unidades de entrada e uma unidade de resposta. O treinamento
contém apenas os pares alinhados (-1,-1) -> classe -1 e (1,1) -> classe +1.
A avaliação usa pares mistos e inéditos, como (1,-0.25) e (0.25,-1), cuja classe
esperada corresponde ao sinal da soma das características.

O benchmark compara pesos fixos, pesos após plasticidade Hebbiana modulada por
recompensa e o mesmo estado depois de salvo e recarregado. Nenhum peso é
atualizado durante a avaliação.

## Critérios

- baseline com pesos fixos: acurácia 0.5;
- rede treinada: acurácia 1.0 nas seis combinações reservadas;
- após restauração: previsões e pesos idênticos aos da rede treinada.

## Limitações

A tarefa foi escolhida para ser solucionável por uma combinação linear e usa
poucos exemplos. O resultado indicaria composição limitada dentro de uma tarefa
simples, não transferência geral entre tarefas nem raciocínio semântico. Para
uma avaliação mais forte, será necessário testar tarefas não lineares, múltiplas
distribuições, controles e conjuntos de avaliação maiores.

## Enquadramento na hipótese fundamental

Transferência composicional é uma medida de recombinação funcional e generalização. Demonstrar que componentes aprendidos podem ser combinados em situações novas, com controles contra memorização. Esse resultado informa capacidades cognitivas do substrato, mas não demonstra experiência subjetiva. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).

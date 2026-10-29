# MNN — Etapa F1: generalização em exemplos não vistos

## Pergunta

A MNN consegue usar uma associação aprendida para classificar valores que não
foram usados no treinamento, e conservar esse comportamento depois de recarregar
o estado salvo?

## Executar

Na raiz do repositório:

```bash
python -m pip install -e .
python -m benchmarks.mnn_generalization
python -m unittest tests.test_mnn_transfer -v
python -m unittest discover -s tests -v
```

## Protocolo

A rede possui uma unidade de sinal, uma unidade de resposta e uma conexão com
peso inicial zero. O treinamento usa somente os dois exemplos extremos:

- entrada -1, classe esperada -1;
- entrada +1, classe esperada +1.

Os valores intermediários -0.75, -0.5, -0.25, +0.25, +0.5 e +0.75 ficam
reservados para avaliação. Os pesos não são atualizados durante essa avaliação.
O benchmark mede a rede com pesos fixos, após o treinamento e após salvar e
recarregar o checkpoint.

## Critérios de aprovação

- baseline de pesos fixos: acurácia de 0.5 nos exemplos balanceados;
- rede treinada: acurácia de 1.0 nos valores intermediários reservados;
- rede recarregada: mesmas previsões e mesmos pesos da rede treinada;
- nenhum exemplo de avaliação é usado no treinamento.

## Limites de interpretação

Este protocolo demonstra apenas interpolação em uma associação linear simples.
Como a tarefa é pequena e alinhada à regra Hebbiana, não é evidência de
generalização ampla, composição de conceitos, transferência entre tarefas,
raciocínio semântico, consciência ou inteligência geral. O próximo passo é
testar representações com múltiplas características, combinações inéditas e
tarefas de transferência com controles adequados.

## Enquadramento na hipótese fundamental

Generalização deve ser demonstrada em tarefas e contextos não vistos, com controles contra memorização e vazamento de dados. Seus resultados caracterizam competência do substrato e não são, por si, evidência de consciência ou livre-arbítrio. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).

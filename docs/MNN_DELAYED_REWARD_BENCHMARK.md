# MNN — Benchmark de recompensa atrasada

## Pergunta experimental

Uma recompensa que chega depois da atividade consegue alterar a conexão que
participou da atividade original?

## Comparação

- **Referência Hebbiana:** atualiza pesos a partir da coatividade no instante em
  que a recompensa é aplicada.
- **Com elegibilidade:** mantém um traço por conexão e utiliza esse traço quando
  o sinal de recompensa chega, mesmo que a coatividade atual seja zero.

O benchmark é determinístico e não usa dependências externas. A atividade inicial
é seguida por passos sem coatividade; depois disso, chega uma recompensa positiva.
O resultado esperado é que a regra de referência não altere o peso e a regra com
elegibilidade altere o peso na direção positiva. Aumentar o atraso deve reduzir a
contribuição do traço, para o decaimento configurado.

## Execução

```bash
python -m benchmarks.mnn_delayed_reward
python -m unittest tests.test_mnn_delayed_reward -v
python -m unittest tests.test_mnn_reward -v
python -m unittest discover -s tests -v
```

## Limitações

Esse é um teste de mecanismo, não uma demonstração de que a arquitetura aprende
tarefas complexas ou é superior a outras redes. O sinal é uma abstração
computacional inspirada em modulação por recompensa, não uma simulação da
química cerebral. Os resultados devem ser acompanhados de benchmarks de tarefa,
ablação, retenção, generalização e controle de interferência.

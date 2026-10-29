# MNN v0.1 — Aprendizado persistente verificável

## Objetivo

Esta etapa verifica uma propriedade mais forte que salvar uma lembrança: a
plasticidade altera os pesos da MNN, os pesos são persistidos em um checkpoint,
e uma instância reconstruída a partir desse checkpoint mantém o desempenho na
mesma tarefa controlada.

## Experimento executável

Na raiz do repositório, execute:

```bash
python -m pip install -e .
python -m benchmarks.mnn_persistent_learning
python -m unittest tests.test_mnn_persistent_learning -v
python -m unittest discover -s tests -v
```

O benchmark começa com duas conexões de peso zero e dois contextos de entrada.
A plasticidade Hebbiana modulada por recompensa fortalece a associação positiva
e enfraquece a negativa. O modelo é salvo em JSON usando substituição atômica
e recarregado como uma nova instância da MNN.

O resultado deve mostrar:

- acurácia inicial: `0.5`;
- acurácia após aprendizado: `1.0`;
- acurácia após recarga do checkpoint: `1.0`;
- pesos antes e depois da recarga idênticos.

O benchmark é determinístico e pode ser executado com um caminho de checkpoint
explícito usando `run_benchmark(checkpoint_path=...)`.

## Garantias e limites

- O checkpoint armazena topologia, pesos, estados das unidades, funções de
  ativação, limite de peso e timestep do snapshot versionado.
- A gravação usa arquivo temporário no mesmo diretório, sincronização do arquivo
  e substituição atômica para evitar que uma gravação parcial substitua um
  checkpoint válido.
- O carregamento valida o snapshot por meio de `MNN.from_snapshot`.
- Isso demonstra persistência de pesos e retenção de comportamento em uma tarefa
  associativa pequena. Não demonstra generalização ampla, raciocínio semântico,
  consciência ou inteligência geral.
- O checkpoint é um arquivo de estado; não é um mecanismo completo de versionamento,
  migração de esquemas, concorrência multi-processo ou recuperação de todos os
  tipos de falha de hardware.

## Próximo passo experimental

Após confirmar o teste de reinicialização, medir transferência para combinações
não vistas e testar se a MNN consegue melhorar o resultado de uma tarefa sem
apenas memorizar os dois contextos de treinamento.

## Enquadramento na hipótese fundamental

O aprendizado persistente deve ser documentado com estado anterior e posterior, dados de experiência, critérios de atualização, regressões e retenção após reinicialização. O objetivo é demonstrar transformação funcional duradoura, sem extrapolar para alegações sobre experiência subjetiva. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).

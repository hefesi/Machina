# Machina — Virtual Brain e MNN

Machina é um projeto experimental para construir uma arquitetura cognitiva executável com memória persistente, ciclos de decisão e aprendizado. A MNN é um dos subsistemas em desenvolvimento; não deve ser confundida com o orquestrador inteiro.

> **Estado do projeto:** protótipo de pesquisa em evolução. Os resultados atuais são evidências de mecanismos específicos em testes controlados, não uma demonstração de inteligência geral, consciência ou autonomia irrestrita.

## Comece aqui

- [Mapa da arquitetura, estado e versões](docs/ROADMAP_AND_VERSIONS.md)
- [Aprendizado de valor e seleção de ações](docs/MNN_ACTION_LEARNING.md)
- [Agente MNN: ação, consequência e memória](docs/MNN_LEARNING_AGENT.md)
- [Ciclo de experiência e recompensa atrasada](docs/MNN_EXPERIENCE_CYCLE.md)
- [Benchmark de adaptação persistente](docs/MNN_PERSISTENT_ADAPTATION.md)

## Requisitos

- Python 3.12 ou superior.
- O pacote declara não ter dependências de runtime externas no `pyproject.toml`.

## Instalação e testes

Na raiz do repositório:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Executar o experimento de adaptação persistente:

```bash
python -m benchmarks.mnn_persistent_adaptation
```

O comando imprime métricas JSON e retorna código de falha se os critérios do benchmark não forem cumpridos.

## O que já pode ser medido

O aprendiz de ações atualiza pesos de previsão após receber uma recompensa. O benchmark de adaptação persistente testa duas ações em um ambiente determinístico, inverte o mapeamento de recompensa, verifica a restauração do snapshot e confirma que registros de memória SQLite sobrevivem a fechar e reabrir o banco. O teste de regressão correspondente fica em `tests/test_mnn_measurable_learning.py`.

## Limitações conhecidas

- O benchmark de duas ações é sintético e determinístico.
- Memória persistida e estado numérico do aprendiz são artefatos distintos; a presença de uma lembrança não muda automaticamente a política.
- `MNNLearningAgent`, `MNNExperienceCycle` e o ciclo durável de `VirtualBrain` ainda precisam de um contrato de integração validado de ponta a ponta.
- Antes de promover uma versão estável, validar compatibilidade da API pública, recuperação após falhas, aprendizado em múltiplas sementes, comparação com baselines e testes no commit integrado.

## Versionamento

O número do pacote em `pyproject.toml` é a versão declarada do pacote, não uma certificação de estabilidade da arquitetura. Consulte [ROADMAP_AND_VERSIONS.md](docs/ROADMAP_AND_VERSIONS.md) para distinguir versão do pacote, maturidade funcional, benchmarks e critérios de release.

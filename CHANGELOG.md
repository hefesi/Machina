# Changelog

Mudanças relevantes do projeto, organizadas por versão declarada ou estágio de desenvolvimento. Enquanto não houver releases publicados, as entradas de desenvolvimento descrevem capacidades observadas nos branches e não garantem que estejam disponíveis na `main`.

## [Unreleased] — validação e consolidação

- Adicionada uma regressão automatizada para aprendizado mensurável, inversão da recompensa, restauração do estado e memória persistente no branch de validação.
- Documentação planejada para separar capacidades implementadas, experimentos, limitações e critérios de release.
- Integração entre a cadeia `MNNLearningAgent` e o ciclo durável `VirtualBrain` continua pendente de validação e não deve ser presumida.

## [0.1.0] — versão declarada do pacote

A versão `0.1.0` é a versão declarada em `pyproject.toml` no branch de referência usado para esta documentação. Ela indica o metadado do pacote, não significa que todos os branches experimentais foram integrados ou que a arquitetura seja estável.

Capacidades documentadas em branches de desenvolvimento incluem:
- rede MNN com unidades, conexões e atualização de pesos;
- aprendiz de valor para seleção de ações com recompensa observada;
- serialização/restauração de snapshot do aprendiz;
- agente experimental que coordena decisão, resolução de resultado e memória de fragmentos;
- benchmark sintético para adaptação após inversão de recompensa e persistência em JSON/SQLite.

Consulte [ROADMAP_AND_VERSIONS.md](docs/ROADMAP_AND_VERSIONS.md) antes de interpretar a lista como disponibilidade na branch `main`.

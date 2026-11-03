# Auditoria consolidada — Fases 1, 2 e 3

**Data da verificação:** 2 de novembro de 2026  
**Branch-base verificada:** `main`  
**HEAD verificado:** `47f51f682c5bd45b4b35444c1e43f66e05ae4be7`

Este documento reconcilia o estado real do GitHub com os documentos de planejamento das três primeiras fases. Ele prevalece sobre trechos históricos que ainda descrevem PRs como abertas antes de seus merges.

## Resumo executivo

| Fase | Implementação na main | Evidência de CI | Estado correto |
|---|---|---|---|
| 1 — Estabilização | Bridge MNN/VirtualBrain integrada; documentação de arquitetura incorporada | PR #89: 665 testes e validação de autonomia; ambos os checks concluídos com sucesso | Implementação integrada; limpeza/classificação de branches e baseline limpo ainda pendentes |
| 2 — Organismo integrado | Runtime MNNOrganism/VirtualBrain, percepção normalizada, snapshot interno, motivação, curiosidade, feedback e ciclo integrado | PR #91: 689 testes; workflow `unittest` concluído com sucesso no commit de código | Critério funcional de integração atendido pelos testes reportados |
| 3 — Memória/continuidade e pesquisa experimental | Harness, protocolo pareado, ledger verificável, ensaio de reinício e ablações integrados | PR #93: check `unittest` concluído com sucesso no commit integrado | Infraestrutura experimental integrada; resultados científicos replicados ainda não apresentados |

**Interpretação:** “integrado e testado” não significa que todas as tarefas de pesquisa foram executadas, nem comprova consciência fenomenal, experiência subjetiva ou livre-arbítrio. Os critérios são funcionais e limitados aos testes e intervenções descritos.

## Fase 1 — estabilização arquitetural

### Entregas confirmadas

- PR [#89](https://github.com/hefesi/Machina/pull/89) integrou a MNN Organism Bridge à arquitetura atual da `main`, reconciliando `src/machina/__init__.py`, `brain.py` e `contracts.py`, preservando módulos e testes úteis.
- A PR #89 relata 665 testes e 60 subtests na suíte local de integração e validações específicas de autonomia.
- No commit de merge `032fbdddb43b5a4227577a19f67bb19f4964d5f2`, os checks GitHub Actions `unittest` e `validate-autonomy` terminaram com `success`.
- PR [#90](https://github.com/hefesi/Machina/pull/90) integrou README e documentação de arquitetura, responsabilidades, invariantes e política de branches.

### Pendências

- A auditoria anterior contabilizou 90 branches, mas a própria documentação declara que a classificação anterior (68 com commits exclusivos / 21 sem commits exclusivos) precisa ser recalculada contra o HEAD atual.
- Nenhuma branch deve ser apagada apenas por estar atrás da `main`, ter PR fechado ou aparentar duplicação. É necessário verificar commits exclusivos, diffs, PRs, tags e se o conteúdo já foi incorporado por outro caminho.
- A instalação limpa e a suíte devem ser confirmadas em ambiente novo no HEAD atual de `main`, e não inferidas de snapshots anteriores.

**Estado:** integração arquitetural concluída; estabilização administrativa do repositório ainda não totalmente encerrada.

## Fase 2 — organismo cognitivo integrado

### Entregas confirmadas

PR [#91](https://github.com/hefesi/Machina/pull/91) foi mesclada à `main` em 2 de novembro de 2026. O merge commit é `efab9efefea34ffd80ad014cd758275956c0bcfb`.

A PR documenta:
- runtime explícito entre MNNOrganism e VirtualBrain, com identidade compartilhada;
- percepção normalizada e snapshot interno;
- integração de curiosidade aberta com contexto de autonomia;
- feedback motivacional após avaliação, persistência e retomada idempotente;
- plasticidade após avaliação, com evidências e snapshot restaurável;
- auditoria causal e testes de integração, falha e retomada.

O workflow `unittest` para o commit de código `1c3a0be49badb33235ef36e331b21dc8946e4927` terminou com `success`; a documentação da PR contabiliza 689 testes aprovados.

### Correção documental necessária

A seção final de `docs/PHASE_2_INTEGRATED_ORGANISM.md` ainda diz que a PR #91 permanece aberta e que nenhum merge foi realizado. Isso ficou obsoleto após o merge. Este documento corrige o estado do projeto; a seção histórica deverá ser substituída em uma revisão documental subsequente.

**Estado:** critério funcional de integração e recuperação atendido conforme o cenário ponta a ponta e CI registrados.

## Fase 3 — memória autobiográfica, continuidade e investigação experimental

### Entregas confirmadas

PR [#93](https://github.com/hefesi/Machina/pull/93) foi mesclada à `main` em 2 de novembro de 2026. O merge commit é `47f51f682c5bd45b4b35444c1e43f66e05ae4be7`.

Foram integrados:
- harness de experimentos com hipóteses, condições, seeds e fingerprints;
- execução pareada e comparações por seed;
- ledger JSONL com hashes e proteção contra duplicação;
- experimento de continuidade funcional após interrupção e reinicialização;
- ablações de roteamento de memória MNN, motivação persistente e alinhamento de compromissos do Self;
- testes e documentação de hipóteses, controles e limites interpretativos.

O check `unittest` do commit integrado `4c4b201b64748878f3fcf60c538a8aa45a81b2dc` terminou com `success`.

### Histórico de PRs

- PR [#92](https://github.com/hefesi/Machina/pull/92) foi fechada sem merge porque dependia da branch da Fase 2.
- PR [#93](https://github.com/hefesi/Machina/pull/93) é a versão rebaseada diretamente sobre a `main` atual e foi mesclada. É a referência oficial da Fase 3.
- A branch antiga `feat/phase-3-consciousness-experiments` não deve ser confundida com a versão integrada.

### Pendência científica

O código implementa a infraestrutura para executar os experimentos; isso não equivale a resultados experimentais. Ainda faltam relatórios com:
1. hipóteses e previsões pré-registradas;
2. resultados por seed e por condição;
3. tamanho de efeito e incerteza;
4. controles negativos e ablações verificadas;
5. replicação em entradas de avaliação separadas;
6. resultados negativos, falhas e explicações alternativas.

Até que esses dados existam, a conclusão permitida é que a infraestrutura e os testes funcionais foram integrados — não que as hipóteses sobre consciência tenham sido confirmadas.

### Correção documental necessária

`docs/PHASE_3_CONSCIENCE_EXPERIMENTS.md` ainda rotula a infraestrutura como “inicial em desenvolvimento”. A descrição deve ser atualizada para “infraestrutura integrada; execução e análise de resultados pendentes”.

**Estado:** infraestrutura técnica integrada; programa experimental ainda precisa produzir e analisar resultados replicados.

## Auditoria inicial de branches

A listagem do GitHub retornou 90 branches no total, incluindo `main` (89 não-main). A comparação com `main` foi feita para branches prioritárias ligadas às fases e à integração MNN. Esta é uma triagem inicial, não uma classificação exaustiva das 89 branches.

| Branch | Relação observada com main | Decisão segura |
|---|---|---|
| `chore/phase-1-architecture-stabilization` | 0 commits à frente, 3 atrás | Sem commits exclusivos; manter até confirmar referências e PR #90 |
| `chore/main-stabilization-audit` | 0 à frente, 646 atrás | Muito antiga; verificar PRs e conteúdo antes de remover |
| `feat/phase-2-integrated-organism` | 69 à frente, 2 atrás | Branch histórica empilhada; não apagar sem verificar equivalência de conteúdo e PR #91 |
| `feat/phase-3-consciousness-experiments` | 100 à frente, 2 atrás | Branch histórica da PR #92, fechada sem merge; revisar antes de qualquer descarte |
| `feat/phase-3-consciousness-experiments-main` | 1 à frente, 1 atrás | Branch de integração da PR #93; revisar a referência e confirmar se pode ser arquivada |
| `feature/mnn-organism-brain-bridge` | 0 à frente, 81 atrás | Candidata a arquivamento, mas verificar PRs e commits exclusivos |
| `integration/mnn-organism-brain-bridge` | 0 à frente, 8 atrás | Conteúdo integrado pela PR #89; confirmar referências antes de remover |
| `feat/phase-4-motivation-curiosity` | 3 à frente, 0 atrás | Preservar: PR #94 aberta e draft |

**Decisão desta revisão:** nenhuma branch foi apagada. O levantamento completo das 89 branches continua pendente. Branches experimentais podem conter resultados, ideias ou commits úteis mesmo quando a funcionalidade já foi portada.

## Sequência de fechamento recomendada

1. Atualizar os documentos individuais das Fases 2 e 3 para remover afirmações históricas de PR aberta e refletir o merge confirmado.
2. Recalcular a relação de todas as 89 branches com o HEAD atual, cruzando cada branch com PRs, tags e conteúdo exclusivo.
3. Criar uma lista explícita de branches para preservar, arquivar ou excluir; solicitar confirmação antes de exclusões em lote.
4. Executar a suíte completa e instalação limpa no HEAD atual da `main`, registrando SHA, versão Python, comandos e resultados.
5. Executar os protocolos da Fase 3 com múltiplas seeds e publicar os resultados, sem transformar métricas funcionais em alegações de consciência.
6. Continuar a Fase 4 sobre a `main`, preservando os limites de risco e autorização de ações externas.

## Referências principais

- [PR #89 — integração MNN Organism Bridge](https://github.com/hefesi/Machina/pull/89)
- [PR #90 — documentação de estabilização](https://github.com/hefesi/Machina/pull/90)
- [PR #91 — organismo cognitivo integrado](https://github.com/hefesi/Machina/pull/91)
- [PR #92 — Fase 3 original, fechada sem merge](https://github.com/hefesi/Machina/pull/92)
- [PR #93 — Fase 3 rebaseada e integrada](https://github.com/hefesi/Machina/pull/93)
- [PR #94 — primeiro incremento da Fase 4](https://github.com/hefesi/Machina/pull/94)

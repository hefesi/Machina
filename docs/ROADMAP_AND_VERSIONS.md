# Consolidação de arquitetura, documentação e versões

## Objetivo

Este documento separa quatro conceitos que não devem ser confundidos:

1. **Versão do pacote** — valor `project.version` em `pyproject.toml`.
2. **Estado de integração** — quais alterações estão realmente incorporadas a `main`.
3. **Maturidade da funcionalidade** — implementação, testes, validação experimental ou integração end-to-end.
4. **Release publicado** — tag/release criada a partir de um commit verificado.

A presença de um módulo ou benchmark em um branch de desenvolvimento não prova que ele esteja na versão distribuída da `main`.

## Fotografia de referência

Na auditoria desta etapa:

- `pyproject.toml` declara `machina-virtual-brain`, versão `0.1.0`, Python `>=3.12` e nenhuma dependência de runtime declarada.
- `main` estava no commit `5f02635407db24a7fd565b73b13dde2522ed3a8d`.
- `feat/mnn-strategy-experiment-log` estava 140 commits à frente e 12 atrás de `main`; o histórico é divergente. Isso é um branch de trabalho, não um release integrado.
- O PR #67 é um rascunho de auditoria da integração e não deve ser mesclado enquanto estiver marcado como não mesclável.
- O PR #68 acrescenta um teste de regressão para o benchmark de adaptação persistente. A execução Python Tests do GitHub Actions terminou com sucesso no commit de teste `8947844ea2e7f8de60e2fabdb9f898a6f26b290d`. O PR #68 tem como base o branch experimental, não `main`; portanto, esse sucesso não certifica a integração completa em `main`.

Esta fotografia é um registro da auditoria, não um indicador dinâmico. Revalidar os SHAs e o estado dos PRs antes de um release.

## Mapa de arquitetura

### Componentes e responsabilidade

| Componente | Responsabilidade atual | Limite conhecido |
|---|---|---|
| `MNN` | Rede de unidades e conexões com estados e pesos ajustáveis | Não é, isoladamente, um sistema cognitivo completo |
| `MNNActionLearner` | Seleção de ações e atualização de valor a partir da recompensa observada | Baseline de bandit simples; não planeja sequências longas |
| `MNNLearningAgent` | Coordena decisão, resultado, atualização do aprendiz e registro em memória | Subsistema experimental separado do orquestrador durável |
| `FragmentMemory` | Guarda e recupera fragmentos de experiência em SQLite | Recuperar uma lembrança não atualiza automaticamente a política |
| `MNNExperienceCycle` | Ciclo de rede, traços de elegibilidade e resolução de recompensa atrasada | Ainda precisa de contrato end-to-end com o ciclo principal |
| `VirtualBrain` | Orquestração durável com eventos, política, aprendizado e memória | A ponte para o novo agente MNN ainda não foi validada de ponta a ponta |

### Fluxo de aprendizado já demonstrado em experimento controlado

```text
escolha de ação
    ↓
ambiente sintético fornece recompensa
    ↓
erro = recompensa - valor previsto
    ↓
atualização do peso da ação
    ↓
snapshot JSON + registro de experiência em SQLite
    ↓
reinicialização e restauração
    ↓
inversão da recompensa e medição da adaptação
```

Esse fluxo demonstra um mecanismo de aprendizado mensurável em uma tarefa pequena. Não prova generalização semântica, causalidade, consciência ou inteligência geral.

## Evidência e testes

### Comandos básicos

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m benchmarks.mnn_persistent_adaptation
```

### Teste de regressão mensurável

```bash
python -m unittest discover -s tests -p 'test_mnn_measurable_learning.py' -v
```

Critérios do benchmark:
- taxa de recompensa nas últimas 10 decisões de cada fase >= 0.8;
- valor previsto da ação correta superior ao da alternativa ao fim de cada fase;
- snapshot preservado após serialização/restauração JSON;
- memória de ambiente preservada e recuperável após reabrir SQLite.

O resultado é reproduzível para a configuração fixa; para conclusões mais robustas, executar várias sementes e incluir ambientes probabilísticos e baselines.

## Plano de versões

Usar SemVer quando houver releases: `MAJOR.MINOR.PATCH`. Até a primeira release estável, `0.y.z` indica que interfaces e comportamento ainda podem mudar.

| Marco | Estado | Critérios para avançar |
|---|---|---|
| `0.1.0` — base do pacote | Metadado declarado no `pyproject.toml`; não equivale à integração de todos os branches | Confirmar o conteúdo exato publicado/empacotado e a cobertura de testes da tag |
| `0.2.0` — aprendizado mensurável | Em validação nos branches experimentais | Teste de regressão integrado à branch escolhida; CI verde no SHA de destino; relatório de métricas reproduzíveis |
| `0.3.0` — integração do agente | Planejado | Contrato explícito entre agente MNN e VirtualBrain; teste ponta a ponta; persistência e recuperação verificadas |
| `0.4.0` — aprendizado contextual | Planejado | Experimentos com múltiplas sementes, contextos novos, baselines e medição de transferência |
| `1.0.0` — API estável | Não planejado para declarar agora | Compatibilidade pública definida; migrações e snapshots versionados; falhas e recuperação testadas; documentação e release reproduzíveis |

Os marcos acima são uma proposta de roadmap, não releases existentes. Não criar tags nem publicar uma versão até que os critérios sejam atendidos.

## Portões obrigatórios antes de release

- [ ] Escolher a branch de integração e reconciliar seus 12 commits ausentes de `main`, sem perder histórico.
- [ ] Preservar os exports públicos atuais de `main`, incluindo `ChemicalSignaling` e `SelfModel`.
- [ ] Definir e documentar a relação entre `VirtualBrain`, `MNNLearningAgent` e `MNNExperienceCycle`.
- [ ] Testar observação → memória/contexto → decisão → ação → recompensa → atualização → persistência → reinício.
- [ ] Testar falhas parciais entre escrita de evento, atualização de pesos e gravação de memória.
- [ ] Executar a suíte completa e os benchmarks no SHA candidato final, não somente em branches isolados.
- [ ] Confirmar `python -m pip install -e .`, empacotamento, versão e compatibilidade de snapshots.
- [ ] Atualizar o changelog com fatos verificáveis e criar uma tag apenas depois da aprovação.

## Política de documentação

- `README.md`: entrada rápida, instalação, testes e limites principais.
- `docs/ROADMAP_AND_VERSIONS.md`: arquitetura, estado de integração, critérios de versão e roadmap.
- `docs/MNN_*.md`: documentação específica de subsistemas e seus limites.
- `CHANGELOG.md`: mudanças relevantes por release ou seção `Unreleased`.
- CI: evidência de execução automatizada para o commit exato; nunca tratar sucesso de um branch como prova de integração de outro.

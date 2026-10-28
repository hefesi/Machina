# Auditoria e estabilização da `main`

**Data da auditoria:** 2026-10-28  
**Branch auditada:** `main`  
**HEAD observado:** `7b02d97e9818d012015c1ea37f56e81ebf9f040b` (`feat: add D2.5 confidence-aware autonomy`)

Este documento registra o estado observado do repositório e define critérios conservadores para estabilizar a branch principal. Ele não substitui a execução local/CI nem afirma que todos os testes de runtime passaram.

## Estado confirmado

- O pacote Python está configurado em `pyproject.toml`, com `requires-python = ">=3.12"`, `setuptools` e dependências de execução vazias.
- A workflow `.github/workflows/tests.yml` executa em pull requests e em pushes para `main`: checkout, Python 3.12, `pip install -e .` e `python -m unittest discover -s tests -v`.
- A API pública em `src/machina/__init__.py` exporta o substrato MNN, memória de fragmentos, Virtual Brain, sinalização química, modulação por recompensa, SelfModel, autonomia, planejamento e armazenamento de conhecimento.
- O código de `MNN` documenta atualizações síncronas de estado e plasticidade explícita limitada.
- A memória de fragmentos usa SQLite e distingue arquivo persistente da projeção ativa por prioridade.
- A sinalização química é uma abstração computacional determinística inspirada em neuromodulação; não é uma simulação bioquímica nem evidência de emoção ou consciência.
- Os commits recentes observados na `main` incluem a integração da sinalização química e dos rastros de elegibilidade, o SelfModel e decisões D2.5 com abstenção baseada em evidências.

## Validação desta auditoria

- A execução local da suíte não foi possível neste ambiente: a tentativa de clonar o repositório falhou por indisponibilidade de resolução de rede.
- O PR de documentação [#66](https://github.com/hefesi/Machina/pull/66), no SHA `04316d2008de86bf3f3ad8fefc8b14bc9aff59e8`, tem uma execução GitHub Actions observada como `completed / success` (workflow `Python tests`, run #155). Como esse PR altera apenas documentação, esse resultado valida o fluxo do PR, não o comportamento dos módulos de runtime nem os branches de funcionalidades.
- A consulta de status de commit retornou lista de statuses vazia; a execução de workflow acima é a evidência positiva disponível. Não inferir sucesso/falha de runtime para outros SHAs a partir dela.
- Não foram alterados pesos, algoritmos de aprendizagem, políticas de agência nem dados persistentes como parte desta auditoria.

## Resultado da auditoria de branches empilhadas

Foram comparados os endpoints de algumas cadeias de PRs com `main`. O resultado confirma que o estado `merged` em PRs de funcionalidade nem sempre significa merge em `main`: PRs podem ter sido mesclados somente em uma branch-base de funcionalidade.

### Cadeia de conceitos e política contextual

- PRs #53–#57 foram mesclados sucessivamente entre branches `feat/mnn-evidence-concepts`, `feat/mnn-concept-revision`, `feat/mnn-concept-guidance` e `feat/mnn-contextual-outcome-policy`, não diretamente em `main`.
- PRs #58–#65 continuaram a cadeia por `feat/mnn-agent-outcome-policy`, `feat/mnn-recency-adaptation`, `feat/mnn-reward-drift-detection`, `feat/mnn-agent-drift-review`, `feat/mnn-strategy-review` e `feat/mnn-strategy-experiment-log`.
- A comparação de `main` com `feat/mnn-strategy-evaluation` reportou branches divergentes: 139 commits à frente e 9 atrás, com 53 arquivos no diff da comparação. Isso é uma cadeia grande demais para integrar diretamente sem revisar o grafo e os diffs por etapa.
- A comparação também reportou divergência para endpoints intermediários, incluindo `feat/mnn-concept-guidance` (84 à frente, 9 atrás) e `feat/mnn-agent-experience-loop` (22 à frente, 9 atrás). Esses números são relações de commits, não prova de que cada funcionalidade é defeituosa.
- **Decisão:** não mesclar o endpoint da cadeia diretamente em `main`. Reconstruir uma branch de integração a partir do HEAD atual de `main`, trazendo cada unidade em ordem de dependência, ou abrir PRs de integração menores e independentes. Para cada unidade, revisar conflitos, exports, persistência, testes e comportamento padrão.

### Correções de autonomia e SelfModel

- `fix/autonomy-d25-rebased` diverge de `main` (5 commits à frente, 2 atrás); o diff contém workflow, documentação, exemplo, implementação de política de confiança e testes.
- `fix/mnn-self-model-rebased` diverge de `main` (3 commits à frente, 2 atrás); o diff contém exports, implementação do SelfModel e testes.
- Embora PRs #54 e #55 apareçam como mesclados em histórico, os estados e SHAs observados não bastam para declarar esses branches equivalentes ao HEAD atual. Antes de qualquer novo merge, verificar presença dos arquivos e dos testes no HEAD atual, e comparar o conteúdo efetivo em vez de confiar apenas no estado do PR.
- Não promover esses branches de correção inteiros sem verificar se o conteúdo já está na `main`, para evitar duplicação ou regressão.

## Riscos prioritários

1. **Integração em cadeia:** branches de funcionalidades relacionadas têm bases diferentes. Mesclar fora de ordem pode deixar funcionalidades ausentes da `main`, duplicar mudanças ou causar conflitos.
2. **Validação de runtime:** CI verde em PR de documentação não prova que o código de branches empilhadas passa nos testes.
3. **Benchmarks confundidos com capacidade geral:** benchmarks sintéticos validam contratos e mecanismos, não generalização no mundo real, causalidade, consciência ou livre-arbítrio.
4. **Mudanças acopladas:** memória, sinais de recompensa e seleção de ações devem permanecer auditáveis; integrações que mudam comportamento padrão precisam de testes explícitos.
5. **Recuperação e compatibilidade:** snapshots persistentes precisam de testes de round-trip, rejeição de dados inválidos e compatibilidade com versões anteriores.

## Portões de estabilização

### Gate 1 — Baseline
- [ ] Confirmar que a workflow `Python tests` está verde para o HEAD atual de `main`.
- [ ] Confirmar instalação editável em Python 3.12 e suíte completa de testes.
- [ ] Registrar o SHA exato validado; não usar um resultado de outro commit como substituto.

### Gate 2 — Pull requests
- [ ] Conferir base, head, ancestral comum, arquivos alterados e conflitos.
- [ ] Para PRs empilhados, integrar na ordem das dependências ou rebasear em branch de integração sem descartar commits.
- [ ] Exigir testes relevantes e a suíte completa verde após a última alteração de código.
- [ ] Revisar alterações em exports públicos, snapshots, persistência e comportamento padrão.
- [ ] Não habilitar merge automático nem mesclar PRs apenas porque estão fechados ou marcados como merged em outra branch.

### Gate 3 — Aprendizagem e memória
- [ ] Testar recompensa atrasada, erro de previsão positivo/negativo e limites de pesos.
- [ ] Testar reinicialização e restauração de snapshots incluindo uma ação pendente.
- [ ] Testar que o histórico persistente não é apagado pela redução da prioridade ativa.
- [ ] Executar benchmarks determinísticos e registrar métricas, sementes/regras e limitações.
- [ ] Demonstrar retenção após reinício e comparar com uma baseline antes de alegar melhoria de aprendizagem.

### Gate 4 — Merge para `main`
- [ ] CI verde no último SHA do PR de código.
- [ ] Diff revisado e sem arquivos/alterações não intencionais.
- [ ] Dependências de branches anteriores satisfeitas.
- [ ] Merge explícito; depois, verificar novamente CI no novo HEAD de `main`.

## Sequência operacional recomendada

1. Confirmar o baseline de CI da `main`.
2. Reconstruir o grafo de dependências dos PRs empilhados e escolher unidades pequenas de integração.
3. Conferir presença dos arquivos dos PRs de correção já mesclados, em especial `confidence_policy.py` e `self_model.py`, no HEAD atual.
4. Resolver primeiro correções de integração/compatibilidade; depois integrar mecanismos fundamentais; por último, integrações de política e avaliação.
5. Não fechar branches antigas até confirmar que suas mudanças foram incorporadas ou deliberadamente descartadas.
6. Após cada merge, registrar SHA e resultado de CI antes de avançar.

## Resultado

A `main` tem uma base executável e uma workflow de testes configurada. A execução do PR #66 passou no GitHub Actions, mas é um PR de documentação e não valida as branches de runtime. **A estabilização não deve ser declarada concluída até que a suíte completa esteja verde no SHA exato que será mantido como baseline e que as dependências das branches em série tenham sido verificadas.**

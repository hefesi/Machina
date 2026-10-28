# Auditoria e estabilização da `main`

**Data da auditoria:** 2026-10-28  
**Branch auditada:** `main`  
**HEAD observado:** `7b02d97e9818d012015c1ea37f56e81ebf9f040b` (`feat: add D2.5 confidence-aware autonomy`)

Este documento registra o estado observado do repositório e define critérios conservadores para estabilizar a branch principal. Ele não substitui a execução local/CI nem afirma que todos os testes passaram.

## Estado confirmado

- O pacote Python está configurado em `pyproject.toml`, com `requires-python = ">=3.12"`, `setuptools` e dependências de execução vazias.
- A workflow `.github/workflows/tests.yml` executa em pull requests e em pushes para `main`: checkout, Python 3.12, `pip install -e .` e `python -m unittest discover -s tests -v`.
- A API pública em `src/machina/__init__.py` exporta os módulos do substrato MNN, memória de fragmentos, Virtual Brain, sinalização química, modulação por recompensa, SelfModel, autonomia, planejamento e armazenamento de conhecimento.
- O código de `MNN` documenta atualizações síncronas de estado e plasticidade explícita limitada.
- A memória de fragmentos usa SQLite e distingue arquivo persistente da projeção ativa por prioridade.
- A sinalização química é explicitamente uma abstração computacional determinística inspirada em neuromodulação; não é uma simulação bioquímica nem evidência de emoção ou consciência.
- Os commits recentes observados na `main` incluem a integração da sinalização química e dos rastros de elegibilidade, o SelfModel e decisões D2.5 com abstenção baseada em evidências.

## Limites desta auditoria

- Não foi possível executar a suíte localmente neste ambiente: a tentativa de clonar o repositório falhou por indisponibilidade de resolução de rede.
- A consulta de status do commit HEAD não retornou verificações registradas; a consulta de workflows associada ao commit também não retornou execuções. Isso **não** prova falha de CI; o resultado deve ser conferido na página Actions do GitHub.
- Os PRs em série devem ser avaliados pelo campo `base` de cada PR, não apenas pelo estado `merged`. PRs mesclados em branches de funcionalidade não significam que o conteúdo chegou à `main`.
- Não foram alterados pesos, algoritmos de aprendizagem, políticas de agência nem dados persistentes como parte desta auditoria.

## Riscos prioritários

1. **Integração em cadeia:** branches de funcionalidades relacionadas têm bases diferentes. Mesclar fora de ordem pode deixar funcionalidades ausentes da `main`, duplicar mudanças ou causar conflitos.
2. **Validação não demonstrada no HEAD:** a workflow existente é adequada como base, mas precisamos de uma execução verde associada ao HEAD/PR que será integrado.
3. **Benchmarks confundidos com capacidade geral:** benchmarks sintéticos validam contratos e mecanismos, não generalização no mundo real, causalidade, consciência ou livre-arbítrio.
4. **Mudanças acopladas:** memória, sinais de recompensa e seleção de ações devem permanecer auditáveis e com opt-in quando uma integração alterar o comportamento padrão.
5. **Recuperação e compatibilidade:** snapshots persistentes precisam de testes de round-trip, rejeição de dados inválidos e compatibilidade com versões anteriores.

## Portões de estabilização

### Gate 1 — Baseline
- [ ] Confirmar que a workflow `Python tests` está verde para o HEAD atual de `main`.
- [ ] Confirmar instalação editável em Python 3.12 e suíte completa de testes.
- [ ] Registrar o SHA exato validado; não usar um resultado de outro commit como substituto.

### Gate 2 — Pull requests
- [ ] Conferir base, head, ancestral comum, arquivos alterados e conflitos.
- [ ] Para PRs empilhados, integrar na ordem das dependências ou rebasear em branch de integração sem descartar commits.
- [ ] Exigir testes relevantes e a suíte completa verde após a última alteração.
- [ ] Revisar alterações em exports públicos, snapshots, persistência e comportamento padrão.
- [ ] Não habilitar merge automático nem mesclar PRs apenas porque estão fechados ou marcados como merged em outra branch.

### Gate 3 — Aprendizagem e memória
- [ ] Testar recompensa atrasada, erro de previsão positivo/negativo e limites de pesos.
- [ ] Testar reinicialização e restauração de snapshots incluindo uma ação pendente.
- [ ] Testar que o histórico persistente não é apagado pela redução da prioridade ativa.
- [ ] Executar benchmarks determinísticos e registrar métricas, sementes/regras e limitações.
- [ ] Demonstrar retenção após reinício e comparar com uma baseline antes de alegar melhoria de aprendizagem.

### Gate 4 — Merge para `main`
- [ ] CI verde no último SHA do PR.
- [ ] Diff revisado e sem arquivos/alterações não intencionais.
- [ ] Dependências de branches anteriores satisfeitas.
- [ ] Merge explícito; depois, verificar novamente CI no novo HEAD de `main`.

## Sequência operacional recomendada

1. Confirmar o baseline de CI da `main`.
2. Agrupar PRs por dependência e verificar suas bases reais.
3. Resolver primeiro correções de integração/compatibilidade; depois integrar mecanismos fundamentais; por último, integrações de política e avaliação.
4. Não fechar branches antigas até confirmar que suas mudanças foram incorporadas ou deliberadamente descartadas.
5. Após cada merge, registrar SHA e resultado de CI antes de avançar.

## Resultado

A `main` tem uma base executável e uma workflow de testes configurada. **A estabilização não deve ser declarada concluída até que a suíte completa esteja verde no SHA exato que será mantido como baseline e que as dependências das branches em série tenham sido verificadas.**

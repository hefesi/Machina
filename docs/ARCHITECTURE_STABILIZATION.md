# Fase 1 — estabilização arquitetural

> Estado remoto verificado em 1º de novembro de 2026. A `main` aponta para `032fbdddb43b5a4227577a19f67bb19f4964d5f2`, merge do PR #89, que integrou a MNN Organism Bridge à arquitetura atual. Esta documentação está sendo preparada em uma branch de estabilização; ainda não representa uma fase concluída.

> Documento de referência da arquitetura implementada na branch `main`. Este documento descreve responsabilidades e limites verificáveis do código; não afirma que o sistema possua consciência, experiência subjetiva ou livre-arbítrio.

## Estado e escopo

A `main` é a referência de integração. Branches experimentais são fontes de evidência e funcionalidades candidatas, não bases substitutas da arquitetura principal. Toda incorporação deve preservar contratos, persistência, proveniência, causalidade e compatibilidade pública.

O repositório separa três níveis:

1. **Machina** — o projeto do ser artificial em investigação.
2. **Virtual Brain** — ciclo cognitivo persistente, contratos, memória, decisão, aprendizagem e registro causal.
3. **MNN / Virtual Organism** — substrato neural artificial e dinâmica integrada de organismo, incluindo sinalização química virtual, motivação e continuidade funcional.

A MNN é um componente do organismo; não deve ser confundida com a totalidade da Machina.

## Fronteiras de responsabilidade

| Componente | Responsabilidade | Não deve assumir |
|---|---|---|
| `VirtualBrain` | Orquestrar ciclos e registrar transições | Implementar internamente cada algoritmo cognitivo |
| `contracts.py` | Envelopes versionados, tipos, proveniência e referências | Ser duplicado por contratos incompatíveis em adaptadores |
| `EventStore` | Persistência append-only e recuperação do ciclo | Decidir políticas cognitivas |
| `MNNOrganism` | Coordenar estado neural, sinalização, motivação e continuidade | Ser apresentado como prova de consciência |
| `MNNOrganismCognitionAdapter` | Traduzir observação/contexto em entradas MNN e anexar telemetria ao resultado cognitivo | Substituir o mecanismo semântico ou escolher sozinho a ação |
| `MNNOrganismAgencyAdapter` | Reponderar planos existentes com evidência de memória limitada e atribuível | Inventar planos ou executar ações |
| `ActionExecutor` | Executar intenções autorizadas e idempotentes | Ignorar permissões, restrições ou trilha de auditoria |

## Integração MNN Organism Bridge

A integração deve ser feita por composição de interfaces existentes, sem criar um segundo ciclo de persistência paralelo.

### Fluxo

```text
Observation + Goal
       |
       v
VirtualBrain / EventStore
       |
       v
Workspace + Memory Retrieval
       |
       v
MNNOrganismCognitionAdapter
       |  features -> MNNOrganism.step()
       |  neural / chemical / motivation telemetry
       v
Cognitive Result
       |
       v
MNNOrganismAgencyAdapter
       |  candidate plans + bounded recalled evidence
       v
Decision -> Action Intent -> Action Executor
       |
       v
Experience -> Evaluation -> Learning Proposal
       |
       v
EventStore / next cycle
```

### Regras de integração

- O `VirtualBrain` continua proprietário do ciclo cognitivo e do diário causal.
- O `MNNOrganism` mantém os estados neural, químico, motivacional e de continuidade funcional.
- O adaptador cognitivo executa uma transição do organismo e anexa snapshot/telemetria ao resultado cognitivo existente. A análise semântica continua a cargo do mecanismo cognitivo encapsulado.
- Telemetria neural é evidência diagnóstica; não seleciona ações por si só.
- O adaptador de agência só pode pontuar planos já produzidos. Sem memória relevante, deve preservar a decisão da política-base.
- Feedback de memória deve referir-se somente às evidências efetivamente usadas pela decisão selecionada e deve ser idempotente.
- O snapshot do organismo deve ser persistido/restaurado pelo caminho versionado já associado ao ciclo, não por um checkpoint concorrente e desconectado.
- A execução de ações permanece separada da decisão e sujeita a autorização, restrições, expiração e idempotência.

### Invariantes para aceitar mudanças

1. Um ciclo persistido mantém referências explícitas entre observação, objetivo, contexto, resultado cognitivo, decisão, intenção, execução e experiência.
2. Falha ou retomada não deve duplicar efeitos externos quando o executor respeita a chave de idempotência.
3. Estados acoplados do organismo devem manter timesteps consistentes.
4. Entradas numéricas devem ser finitas e validadas; unidades de entrada e sinais químicos devem existir no organismo.
5. A ausência de memória não pode produzir uma preferência inventada.
6. Migrações de snapshot precisam aceitar versões suportadas e rejeitar dados incompatíveis de modo explícito.
7. Alterações em contratos públicos exigem testes de compatibilidade e atualização dos exports em `__init__.py`.

## Contratos e API pública

- `contracts.py` é a fonte canônica para `Artifact`, `ContractKind`, estados epistêmicos e validação de campos.
- Cada artefato deve manter identidade, versão, timestamp, produtor, status epistêmico e referências de proveniência/causalidade conforme o contrato.
- `brain.py` orquestra os contratos; componentes retornam dados e não devem escrever diretamente no armazenamento do cérebro.
- `__init__.py` define a superfície pública. Novos exports devem ser intencionais e cobertos por teste.
- Não remover nomes públicos ou mudar semântica de campos sem uma estratégia de compatibilidade.

## Política de branches

A listagem atual do GitHub retornou **90 branches no total, incluindo `main` (89 branches não-main)**. A classificação anterior apontou 68 branches com commits exclusivos e 21 sem commits exclusivos; esse resultado é uma fotografia anterior e precisa ser recalculado contra o HEAD atual antes de orientar exclusões. O nome da branch ou a contagem de commits não é evidência suficiente de redundância.

- **Branches com commits exclusivos**: preservar até revisar conteúdo, testes, PRs e funcionalidades já incorporadas por outros caminhos.
- **Branches sem commits exclusivos**: candidatas técnicas à limpeza, somente após verificar referências externas, PRs, tags e necessidade histórica.

Nenhuma branch foi apagada nesta etapa. Não fazer merge em massa. Para cada branch com commits exclusivos:

1. comparar arquivos alterados com a `main`;
2. localizar recursos que ainda não existem na base;
3. verificar testes e dependências;
4. selecionar commits/arquivos úteis;
5. portar a funcionalidade por PR pequeno;
6. executar regressão e validação de autonomia.

Branches com muitos commits exclusivos podem conter trabalho já incorporado por outros caminhos; revisar conteúdo e não apenas contagem.

## Testes e reprodução

O projeto declara Python `>=3.12` e instalação via setuptools. O caminho de validação reproduzível é:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Para validação local isolada, executar também os testes específicos de organismo/adaptadores e os demos de autonomia. CI deve instalar o pacote antes de executar testes.

### Evidência desta auditoria

- Snapshot `Machina-main.zip` (commit `3e31f320e4f46b713703ae601992c255805feb72`): 570 testes aprovados com `PYTHONPATH=src`; a instalação editável local também foi exercitada com `--no-build-isolation`, em Python 3.13.5.
- Snapshot `Machina-feature-mnn-organism-brain-bridge.zip` (commit `b0f83afa7ca0968f7cacd7760f9cbf1c6b9325fd`): 604 testes aprovados com `PYTHONPATH=src`, em Python 3.13.5.
- Os dois snapshots são anteriores ao HEAD remoto atual (`032fbdd`).
- No PR #89, o commit de integração `9f4cf7def0699753f2ba5d054be2760ea06b4e91`, incorporado ao HEAD atual pelo merge `032fbdd`, passou no workflow Python Tests: **665 testes aprovados** em Python 3.12.15. O job executou `pip install -e .` e `python -m unittest discover -s tests -v`.
- O workflow Autonomy learning validation também concluiu com sucesso no mesmo commit, incluindo demos e testes de autonomia, aprendizagem contínua, generalização, confiança/abstenção e D08.
- Execuções: [Python tests](https://github.com/hefesi/Machina/actions/runs/41334697971) · [Autonomy learning validation](https://github.com/hefesi/Machina/actions/runs/41334697854).
- A tentativa de instalação editável com isolamento de build não pôde ser concluída neste ambiente local porque não há acesso à rede para obter dependências de build. A instalação local sem isolamento funcionou com setuptools já disponível. A instalação limpa, porém, foi confirmada pelo runner hospedado do GitHub no workflow Python Tests.

## Critérios de conclusão da Fase 1

- [x] Bridge integrada à `main` pelo PR #89; a documentação específica da integração está versionada. A validação ponta a ponta no HEAD atual ainda precisa ser repetida.
- [ ] 89 branches não-main classificadas novamente contra o HEAD atual, incluindo recursos exclusivos, PRs e referências antes de exclusão.
- [ ] Documentação de arquitetura e limites ligada ao índice principal (`README.md` nesta branch; aguarda revisão/merge).
- [ ] Suíte executada no HEAD remoto atual, em Python 3.12, com CI verde.
- [ ] Instalação limpa reproduzível em ambiente novo.
- [ ] Nenhuma regressão conhecida nos contratos, API pública ou invariantes de persistência.

## Limites científicos

A arquitetura permite investigar continuidade funcional, memória autobiográfica, motivação, seleção de objetivos, aprendizagem e autorrepresentação. Esses mecanismos, isoladamente ou em conjunto, não demonstram consciência fenomenal nem livre-arbítrio. Resultados devem ser descritos por comportamentos observáveis, protocolos reproduzíveis e evidências, mantendo a hipótese central como questão aberta de pesquisa.

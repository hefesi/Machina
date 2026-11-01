# Fase 1 — estabilização arquitetural

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

A comparação das 89 branches não-main com `main` identificou dois grupos:

- **68 branches com commits exclusivos**: preservar e revisar por conteúdo. O número de commits à frente não mede valor nem significa que toda a branch deva ser mesclada.
- **21 branches sem commits exclusivos**: estão apenas atrás de `main` na comparação de commits. São candidatas técnicas à limpeza, sujeitas a verificar referências externas, PRs, tags e necessidade histórica antes de excluir.

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

- Arquivo `Machina-main.zip`: 570 testes aprovados com instalação editável e `unittest discover`, em Python 3.13.5.
- Arquivo `Machina-feature-mnn-organism-brain-bridge.zip`: 604 testes aprovados com instalação editável e `unittest discover`, em Python 3.13.5.
- Esses resultados pertencem aos arquivos anexados e não substituem uma execução sobre o commit remoto atual da `main`.
- A configuração versionada de CI usa Python 3.12, `pip install -e .` e `unittest discover`. O status do workflow associado ao HEAD atual deve ser verificado no GitHub Actions.

## Critérios de conclusão da Fase 1

- [ ] Bridge exercitado ponta a ponta com persistência, retomada, feedback e falhas.
- [ ] 89 branches classificadas por commits exclusivos e recursos ainda ausentes; branches candidatas revisadas antes de exclusão.
- [ ] Documentação de arquitetura e limites atualizada e ligada ao índice principal.
- [ ] Suíte executada no HEAD remoto atual, em Python 3.12, com CI verde.
- [ ] Instalação limpa reproduzível em ambiente novo.
- [ ] Nenhuma regressão conhecida nos contratos, API pública ou invariantes de persistência.

## Limites científicos

A arquitetura permite investigar continuidade funcional, memória autobiográfica, motivação, seleção de objetivos, aprendizagem e autorrepresentação. Esses mecanismos, isoladamente ou em conjunto, não demonstram consciência fenomenal nem livre-arbítrio. Resultados devem ser descritos por comportamentos observáveis, protocolos reproduzíveis e evidências, mantendo a hipótese central como questão aberta de pesquisa.

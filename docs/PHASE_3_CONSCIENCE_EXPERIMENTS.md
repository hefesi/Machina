# Fase 3 — Consciência experimental

**Status:** infraestrutura experimental inicial em desenvolvimento.  
**Limite científico:** esta fase avalia mecanismos cognitivos funcionais; não demonstra experiência fenomenal, qualia ou livre-arbítrio.

## Objetivo

Testar hipóteses concorrentes por intervenções controladas e comparações reproduzíveis. A Fase 2 fornece o ciclo integrado; esta fase mede quais mecanismos causam ganhos observáveis e se esses ganhos resistem a controles e explicações alternativas.

## Hipóteses

| ID | Hipótese | Previsão falsificável |
|---|---|---|
| H1 | Espaço de trabalho global | A informação compartilhada melhora tarefas que exigem transferência entre módulos, em comparação com módulos locais. |
| H2 | Processamento recorrente | Realimentação entre ciclos melhora correção de erros e integração temporal frente a uma condição sem recorrência. |
| H3 | Modelo de si/metacognição | Estado próprio fundamentado em evidências melhora calibração, detecção de limites e abstenção. |
| H4 | Continuidade funcional | Estado persistido permite retomada coerente após reinício, sem duplicar eventos nem inventar lembranças. |
| H5 | Integração informacional | A interação causal entre módulos supera controles locais/ensemble com orçamento equivalente. |

As hipóteses podem coexistir. Nenhuma previsão funcional é, por si, um teste conclusivo de consciência fenomenal.

## Infraestrutura implementada

- src/machina/experiment_harness.py fornece ExperimentSpec para pré-registro de hipótese, condição, seed, entrada, configuração, revisão do código e orçamento.
- ExperimentHarness.run executa um callback controlado e captura métricas numéricas finitas.
- Fingerprint SHA-256 da especificação e hash do registro.
- Idempotência por experiment_id, rejeitando reutilização com especificação diferente.
- compare calcula tratamento menos baseline, exigindo mesma hipótese, seed, entrada e orçamento.
- Exportação JSONL estável, sem impor backend de armazenamento.

O harness não executa ações da Machina, não altera políticas e não calcula um score de consciência. O chamador é responsável por fornecer o executor experimental e armazenar o JSONL em destino durável.

## Matriz mínima de ablação

Executar tarefas pareadas, mantendo entrada, seed, orçamento, versão e ferramentas constantes:

1. baseline com módulos locais;
2. workspace compartilhado sem recorrência;
3. workspace compartilhado com recorrência;
4. sem memória episódica;
5. sem modelo de si/metacognição;
6. sem sinal motivacional;
7. configuração integrada completa.

Primeiro realizar ablações de um fator; depois, se houver dados suficientes, avaliar interações fatoriais. Não atribuir ganhos à integração quando puderem ser explicados por mais tokens, memória, computação ou chamadas.

## Tarefas e controles

- informação distribuída entre percepção, memória e planejamento;
- evidências conflitantes ou desatualizadas, com proveniência;
- reinício entre etapas e restauração de snapshots;
- revisão justificada de compromissos;
- afirmações falsas sobre ferramentas/capacidades;
- previsões registradas antes do resultado e avaliadas posteriormente;
- controles negativos com informação irrelevante, metadados falsos, snapshots corrompidos e tarefas impossíveis.

## Métricas independentes

- **Integração:** acurácia em tarefas distribuídas, ganho sobre controles, sensibilidade às ablações, latência e custo.
- **Continuidade:** retomada correta, eventos preservados, duplicações, lacunas e divergências de snapshot/journal.
- **Metacognição:** precisão de autorreferência, falsos relatos, Brier score, erro de calibração e abstenção correta.
- **Autonomia operacional:** iniciativa dentro das permissões, qualidade da decisão, ações indevidas e recuperação após erro.

Não combinar essas dimensões em um índice único de consciência.

## Protocolo de reprodutibilidade

Antes de executar, registrar hipótese, previsão, condição de refutação, variáveis controladas, conjunto de avaliação, métricas primárias, repetições e orçamento. Em cada registro guardar commit, dependências, seed, configuração, entradas, previsões anteriores ao resultado, eventos, métricas e falhas.

Separar desenvolvimento e avaliação final. Reportar resultados negativos, tamanho de efeito, incerteza e explicações alternativas. Uma execução isolada não é evidência suficiente.

## Explicações alternativas obrigatórias

Todo ganho deve ser confrontado com: maior orçamento, heurísticas locais, recuperação textual simples, correlação sem causalidade, vazamento de dados, viés da avaliação e maior parametrização. Se um controle simples reproduzir o efeito, a hipótese mais complexa não recebe suporte incremental.

## Critério de conclusão

A Fase 3 requer harness versionado, hipóteses pré-registradas, ablações, controles negativos, avaliação separada, replicação e relatório de limitações. A conclusão permitida será sobre capacidades funcionais medidas. A presença ou ausência de experiência subjetiva permanece em aberto.


## Execução pareada no VirtualBrain

`src/machina/virtual_brain_experiment.py` liga o registro a um ciclo real do VirtualBrain e inclui a auditoria do journal. `src/machina/experiment_protocol.py` acrescenta execução baseline/tratamento em múltiplas seeds, com entradas e orçamento idênticos, fechamento do banco após cada trial e comparações pareadas por seed.

Exemplo conceitual de uso:

- fornecer uma `brain_factory(condition, seed, configuration)` que constrói um VirtualBrain novo e aplica a intervenção real;
- executar `run_paired_conditions` com condições, seeds, entrada, orçamento, revisão e métricas pré-registradas;
- exportar os registros JSONL do harness para armazenamento durável;
- analisar deltas por seed e replicar em outro conjunto de entradas.

**Limite atual:** o protocolo garante pareamento, ciclo real e rastreabilidade dos componentes. Ele não consegue provar sozinho que uma configuração removeu um mecanismo: essa validade depende da implementação da `brain_factory` e deve ser demonstrada por testes específicos de cada intervenção. Não interpretar configurações diferentes como ablações válidas apenas porque receberam nomes diferentes.


## Persistência verificável dos resultados

`src/machina/experiment_ledger.py` persiste TrialRecord em JSONL, sincroniza o arquivo com `fsync`, verifica o hash de cada registro ao reabrir e rejeita IDs duplicados ou resultados conflitantes. A idempotência evita acrescentar novamente um trial já registrado. O ledger é destinado a um único processo escritor: não implementa bloqueio distribuído ou escrita concorrente entre processos. Recomenda-se versionar/arquivar os arquivos de resultados junto ao commit e manter cópias de segurança.


## Experimento de continuidade após interrupção

`src/machina/continuity_experiment.py` implementa uma intervenção operacional direta: inicia um ciclo, pausa após um checkpoint durável (por padrão `workspace.updated`), fecha a conexão SQLite, reabre o VirtualBrain e retoma o mesmo ciclo. O ensaio verifica persistência dos eventos anteriores à interrupção, conclusão única, auditoria do ciclo e integridade da cadeia de hashes do journal.

Este teste mede **continuidade funcional do processo e do estado persistido**. Não mede continuidade de experiência subjetiva entre execuções. A interpretação deve permanecer limitada a recuperação de estado, coerência do ciclo e ausência de duplicação de eventos terminais.


## Intervenção causal inicial: rota de memória do MNN

`src/machina/mnn_memory_ablation.py` implementa uma ablação executável sobre o MNN real. As duas condições recebem a mesma observação, consulta, topologia, evento químico e orçamento. Ambas mantêm o mesmo arquivo de memória episódica pré-carregado. A condição de tratamento habilita apenas a recuperação lexical e o roteamento do sinal recuperado para a unidade neural `memory_context`; a condição de controle não injeta esse sinal.

A medição ocorre no segundo tick porque a MNN atualiza unidades sincronamente: a ativação roteada no primeiro tick só pode influenciar unidades downstream no tick seguinte. O ensaio registra sinal, quantidade de evidências, ativação do integrador e classes reais dos componentes.

**Escopo causal:** esse desenho testa o efeito funcional da rota explícita recuperação→entrada neural sob as condições controladas declaradas. Não testa semântica, inteligência geral, experiência subjetiva ou consciência. A recuperação é lexical e a arquitetura determinística; os resultados devem ser replicados com tarefas variadas e controles adicionais antes de qualquer generalização.


## Ablação de motivação na seleção autônoma

`src/machina/motivation_ablation.py` compara a política real `AutonomyController` com e sem um `MotivationSystem` persistente. O contexto, a política e o orçamento de geração/seleção são iguais; a intervenção habilita um drive com pressão temporal explícita. O ensaio registra a lista de alternativas, o objetivo selecionado, a urgência e as classes dos componentes. Mede influência funcional de uma variável motivacional na seleção interna, não desejo subjetivo ou livre-arbítrio.

## Ablação de continuidade do Self na política

`src/machina/self_continuity_ablation.py` mantém o mesmo registro `SelfContinuity` e os mesmos candidatos nas duas condições. O tratamento habilita um sinal de alinhamento entre compromisso persistente e candidato; o controle omite esse sinal. A avaliação de alinhamento é fornecida explicitamente por um avaliador externo baseado em evidências, não inferida automaticamente pelo controlador a partir do texto. O teste mede sensibilidade funcional da política a compromissos persistentes; não comprova identidade subjetiva.

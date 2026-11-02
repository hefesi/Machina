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

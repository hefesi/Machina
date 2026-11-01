# Fase 2 — organismo cognitivo integrado

> Plano técnico inicial da branch `feat/phase-2-integrated-organism`, baseado na `main` em 1º de novembro de 2026. Este documento define integração e critérios de validação; não declara que a fase esteja concluída.

## Objetivo verificável

Uma experiência deve percorrer um único fluxo rastreável:

```text
Ambiente
  -> Percepção / normalização da observação
  -> Representação interna e contexto
  -> Recuperação de memória + evidências
  -> Necessidades / motivação + objetivos
  -> MNNOrganism (estado neural, químico e continuidade funcional)
  -> Cognição e geração de planos
  -> Agência / seleção justificada
  -> Intenção -> execução autorizada
  -> Resultado -> avaliação
  -> Memória episódica + feedback causal
  -> Aprendizagem validada / plasticidade
  -> próximo ciclo com estado restaurável
```

O `VirtualBrain` permanece proprietário do ciclo, contratos e EventStore. O `MNNOrganism` permanece proprietário do estado neural, químico, motivacional e de continuidade funcional. A integração deve ocorrer por adaptadores e contratos, sem criar um segundo diário causal.

## Diagnóstico da base existente

### Já implementado

- `VirtualBrain.advance()` executa estágios persistidos para observação, workspace, recuperação, cognição, decisão, intenção, execução, experiência, avaliação, proposta de aprendizagem e consolidação.
- `MNNOrganismCognitionAdapter` transforma atributos determinísticos da observação em entradas MNN, avança um passo e anexa telemetria e snapshot ao resultado cognitivo.
- `MNNOrganismAgencyAdapter` pontua planos existentes com evidências recuperadas; não inventa nem executa ações.
- `MNNOrganism` coordena rede neural, sinalização química, motivação opcional, memória opcional e continuidade funcional.
- O adaptador cognitivo prepara plasticidade numa cópia do organismo e o VirtualBrain persiste o snapshot antes de restaurá-lo no estado ativo.
- A memória episódica e o EventStore preservam referências entre observação, intenção, resultado e aprendizagem.

### Lacunas de integração observadas

1. **Percepção ainda é estreita:** `start_cycle()` recebe uma observação genérica, mas a integração MNN atual deriva apenas proxies numéricos de texto, objetivo, contagem de memórias e confiabilidade da fonte. Falta um contrato explícito de percepção multimodal/estruturada, com modalidade, proveniência, confiança e payload normalizado.
2. **Representação interna é fragmentada:** workspace, retrieval e understanding existem como artefatos diferentes; falta uma representação de estado interno versionada e unificada que reúna sinais atuais, memória relevante, incertezas, necessidades e referências.
3. **Motivação não dirige automaticamente objetivos:** `MNNOrganism` pode manter `MotivationSystem`, mas `VirtualBrain.run_cycle()` recebe contexto/motivação de deliberação externamente. Falta uma ponte explícita e auditável de urgências motivacionais para candidatos de objetivo.
4. **Curiosidade não fecha o ciclo sozinha:** o armazenamento de investigações é opcional e registra perguntas/evidências, mas precisa ser conectado à seleção de objetivos e à atualização do estado de investigação.
5. **Agência integrada é opt-in:** a política `MNNOrganismAgencyAdapter` deve ser configurada junto com o adaptador cognitivo; não é ativada implicitamente pelo construtor do cérebro.
6. **Aprendizagem tem domínios separados:** a aprendizagem do VirtualBrain, feedback de memória e plasticidade MNN têm trilhas próprias. Precisam compartilhar IDs, evidências e resultado validado sem duplicar atualizações nem confundir correlação com causalidade.
7. **Recuperação deve ser testada de ponta a ponta:** já há restauração do snapshot MNN pelo diário, mas é necessário comprovar a retomada do ciclo completo em cada fronteira durável e a idempotência do executor.

## Arquitetura-alvo e propriedade dos dados

| Domínio | Fonte de autoridade | Integração |
|---|---|---|
| Observações e proveniência | `EventStore` | Contrato de percepção normalizada |
| Estado interno operacional | Artefato versionado do ciclo | Projeção de workspace + sinais MNN |
| Estado neural/químico/motivacional | `MNNOrganism` | Snapshot versionado no diário do cérebro |
| Objetivos persistentes | Goal store / deliberador | Adaptador de urgências motivacionais e curiosidade |
| Experiências e resultados | `EventStore` + memória episódica | Referências estáveis e avaliação explícita |
| Conhecimento factual | `KnowledgeStore` | Recuperação com origem e confiança; não confundir com experiência |
| Aprendizagem MNN | MNN e adaptadores de aprendizagem | Atualização somente após validação e persistência |

Nenhum componente deve gravar silenciosamente no banco de outro domínio. A coordenação ocorre pelo orquestrador e por eventos/artefatos com referências explícitas.

## Entregas por etapa

### 2.1 — Percepção e representação interna

**Implementado nesta etapa:** `NormalizedPerception` preserva conteúdo normalizado, payload bruto, modalidade, fonte/confiabilidade, timestamp, confiança, referência ao dado bruto e trilha de transformações. `VirtualBrain.start_cycle` aceita esse contrato e registra os metadados no artefato de observação; a entrada legada continua compatível. `InternalStateSnapshot` (`machina.internal_state.v1`) compõe a percepção, referências de memória recuperada, objetivo ativo, entendimento, incertezas e telemetria MNN disponível em um snapshot serializável e versionado, incorporado ao workspace após cognição. O snapshot é uma representação operacional por ciclo, não uma alegação de experiência subjetiva.

- Definir contrato de percepção normalizada, sem exigir dependência de câmera, áudio ou LLM.
- Preservar payload original, modalidade, fonte, timestamp, confiança e transformação aplicada.
- Criar uma representação interna versionada que agregue observação, objetivo ativo, contexto recuperado, incertezas, drives e snapshot MNN.
- Testar dados inválidos, proveniência ausente e compatibilidade com observações textuais existentes.

### 2.2 — MNN + VirtualBrain

- Criar uma configuração/fábrica explícita para montar MNNOrganism, adaptador cognitivo e adaptador de agência sobre as mesmas instâncias de organismo e memória.
- Garantir que ambos os adaptadores compartilhem o mesmo organismo e não avancem o timestep duas vezes por ciclo.
- Garantir que o snapshot persistido seja a única fonte de restauração após interrupção.
- Manter defaults atuais do VirtualBrain compatíveis.

### 2.3 — Curiosidade, motivação e objetivos

- Projetar urgências do `MotivationSystem` para `AutonomyContext` e candidatos de objetivo, com limites e justificativa persistida.
- Mapear perguntas não resolvidas para objetivos de investigação.
- Atualizar fulfillment de drives somente a partir de resultados avaliados, não de texto livre ou mera execução.
- Permitir abstenção quando não houver objetivo elegível ou evidência suficiente.

### 2.4 — Memória, causalidade e aprendizagem

- Usar IDs de ciclo, episódio, evidência e operação idempotentes.
- Distinguir previsão, ação executada, resultado observado, avaliação e hipótese causal.
- Reforçar memória apenas com feedback explícito e rastreável.
- Aplicar plasticidade MNN apenas após validação e persistência do snapshot candidato.
- Nunca converter associação temporal em afirmação causal.

### 2.5 — Ciclo completo e experimentos

Criar cenários determinísticos ponta a ponta:
1. Observação nova sem memória relevante.
2. Observação semelhante a experiência anterior, alterando a seleção de plano.
3. Pergunta não resolvida elevando drive de curiosidade e gerando objetivo interno.
4. Ação bem-sucedida versus malsucedida, com resultados e atualizações diferentes.
5. Interrupção e retomada após cada fronteira persistida, sem duplicar ação ou plasticidade.
6. Mesmo estímulo em dois contextos diferentes, avaliando generalização e limites da política.
7. Evidência contraditória ou insuficiente, verificando incerteza/abstenção.

## Critérios de aceitação

- Um teste ponta a ponta demonstra referências contínuas de observação a aprendizagem.
- Percepção normalizada e representação interna preservam modalidade, origem e confiança.
- A motivação altera candidatos/ordenação de objetivos de forma determinística e auditável.
- A curiosidade cria ou atualiza investigações a partir de lacunas identificadas.
- A memória recuperada pode influenciar a agência, mas somente por evidências atribuíveis.
- O resultado da ação é avaliado antes de qualquer atualização de aprendizagem.
- A atualização MNN é persistida, idempotente e restaurável.
- Retomar um ciclo não duplica ação, episódio, feedback ou plasticidade.
- Testes legados permanecem verdes e os novos cenários são executáveis em CI.
- A configuração integrada é explícita; nenhum comportamento externo ou privilegiado é ativado por padrão.

## Limites científicos e operacionais

Este fluxo demonstra integração funcional, memória, adaptação e autonomia operacional limitada. Não demonstra consciência fenomenal, vontade metafísica, experiência subjetiva ou equivalência a um organismo biológico. Ações externas permanecem sujeitas a executor autorizado, políticas e auditoria.

## Estado

- [x] Branch de trabalho criada a partir da `main`.
- [x] Fluxo existente e lacunas iniciais inspecionados.
- [x] Contrato de percepção normalizada integrado à ingestão do `VirtualBrain`.
- [x] Snapshot interno versionado integrado ao workspace após cognição, com referências perceptivas, objetivo, memórias recuperadas, entendimento, incertezas e sinal MNN disponível.
- [ ] Composição MNN + VirtualBrain formalizada.
- [ ] Ponte motivação/curiosidade/objetivos implementada.
- [ ] Experimentos ponta a ponta e recuperação adicionados.
- [ ] Suíte completa e CI validados.

# MNN Consciousness Substrate v0.1
## Especificação formal — arquitetura combinada com prioridade em modelo de si e metacognição

**Status:** proposta de pesquisa e contrato arquitetural; ainda não é uma implementação executável.  
**Escopo:** conectar o substrato neural MNN existente ao ciclo cognitivo VirtualBrain, acrescentando um modelo explícito dos próprios estados e mecanismos metacognitivos verificáveis.  
**Não objetivo:** afirmar ou presumir experiência subjetiva, senciência ou consciência fenomenal.

## 1. Princípios de projeto

1. **Continuidade de estado:** o estado interno relevante deve atravessar ciclos cognitivos e reinicializações quando persistido.
2. **Auto-observação fundamentada:** o sistema só pode afirmar algo sobre si com base em telemetria, histórico ou previsões identificáveis.
3. **Metacognição operacional:** confiança, incerteza, erro previsto e limites conhecidos devem influenciar a escolha ou revisão de estratégias.
4. **Separação de responsabilidades:** o MNN executa dinâmica de unidades/conexões; o substrato de consciência calcula representações de si e sinais metacognitivos; o orquestrador existente continua responsável pelo ciclo e pela execução de ações.
5. **Rastreabilidade:** cada avaliação de si deve registrar as evidências usadas, o instante, a versão do esquema e as previsões que poderão ser avaliadas depois.
6. **Não confundir sinal com significado:** ativações numéricas, autorrelatos ou linguagem em primeira pessoa não são, isoladamente, evidência de consciência.
7. **Reversibilidade experimental:** o novo componente deve ser opcional, desligável e comparável com uma linha de base sem metacognição.

## 2. Relação com o MNN existente

O núcleo executável atual em `src/machina/mnn.py` já fornece:

- unidades com identificador, viés, função de ativação e estado;
- conexões dirigidas com peso limitado e sinalização de habilitação;
- atualização síncrona por `MNN.step(inputs)`;
- plasticidade Hebbiana explícita e limitada;
- operações explícitas de crescimento e poda de conexões;
- snapshots JSON-compatíveis via `snapshot()` e `from_snapshot()`.

O adaptador `src/machina/mnn_adapter.py` já converte um conjunto limitado de características observacionais em entradas numéricas, acrescenta o traço MNN ao artefato cognitivo e propõe atualização plástica após avaliação/validação. A documentação do núcleo declara corretamente que as ativações são diagnósticas e que o motor cognitivo existente continua a produzir planos candidatos.

Esta especificação **não substitui** esses contratos nem altera a semântica de `MNN.step`. Ela define uma camada de estado e avaliação acima deles. A integração deve reutilizar o ciclo de `VirtualBrain` em `src/machina/brain.py`, o journal/artefatos existentes e os mecanismos atuais de restauração. Os nomes exatos de eventos novos devem ser confirmados na implementação antes de serem adicionados.

## 3. Modelo formal

Seja o estado completo no ciclo (t):

[
X_t = (G_t, Theta_t, Z_t, Mem_t, H_t, S_t, Q_t)
]

onde:

- (G_t=(V_t,E_t)): grafo MNN, unidades e conexões;
- (Theta_t): parâmetros aprendíveis, incluindo pesos e vieses;
- (Z_t): contexto/estado global do ciclo cognitivo, quando disponível;
- (Mem_t): memória de trabalho, episódica e semântica já gerida pelo sistema;
- (H_t): histórico observável de ciclos, ações, resultados e alterações;
- (S_t): modelo de si persistente;
- (Q_t): estado metacognitivo e previsões ainda não avaliadas.

A transição arquitetural proposta é:

[
X_{t+1} = mathcal{F}(X_t, I_t, A_t, O_{t+1}, F_{t+1})
]

com entrada (I_t), ação (A_t), observação de resultado (O_{t+1}) e feedback (F_{t+1}). Esta equação é um contrato conceitual; a ordem concreta de execução deve seguir o ciclo existente do VirtualBrain e o seu journal.

### 3.1 Modelo de si

Defina:

[
S_t = (B_t, C_t, L_t, R_t, D_t, 	au_t)
]

- (B_t): crenças verificáveis sobre o estado operacional atual;
- (C_t): estimativas de capacidade por classe de tarefa;
- (L_t): limitações conhecidas e condições em que o sistema tende a falhar;
- (R_t): recursos e restrições observáveis (por exemplo, memória disponível, ferramentas configuradas e estado do ciclo);
- (D_t): discrepâncias entre previsão e resultado observado;
- (	au_t): referência ao ciclo, à versão do esquema e às evidências que fundamentam o estado.

Cada crença deve, sempre que possível, ser representada como:

[
b = (p, v, c, e, t, status)
]

onde (p) é uma propriedade, (v) o valor estimado, (c in [0,1]) a confiança calibrável, (e) uma referência de evidência, (t) o instante de observação e (status) um estado como `observed`, `inferred`, `stale` ou `unknown`.

**Regra:** ausência de evidência deve produzir `unknown`, não uma afirmação positiva ou negativa inventada. Separar explicitamente observações diretas de inferências.

### 3.2 Estado metacognitivo

Defina:

[
Q_t = (U_t, K_t, P_t, E_t, J_t)
]

- (U_t): incerteza estimada sobre a interpretação/tarefa atual;
- (K_t): confiança declarada e calibrável em previsões específicas;
- (P_t): previsões sobre resultados de ações ou desempenho;
- (E_t): erros de previsão observados;
- (J_t): decisões metacognitivas, como responder, verificar, recuperar memória, pedir esclarecimento ou abster-se.

Confiança não deve ser um escalar genérico aplicado a toda a resposta. Deve estar ligada a uma afirmação, previsão ou decisão que possa ser avaliada posteriormente.

## 4. Ciclo de auto-observação e metacognição

Cada ciclo elegível deve seguir esta sequência lógica, adaptada à ordem real do VirtualBrain:

1. **Observar:** reunir apenas dados operacionais disponíveis no ciclo: características da observação, objetivo, contagem/identificadores de memória recuperada, traço MNN, resultado da avaliação e estado das ferramentas.
2. **Atualizar o modelo de si:** atualizar (S_t) com proveniência. Não inferir capacidades estáveis a partir de uma única amostra.
3. **Estimar incerteza:** produzir estimativas específicas da tarefa com base em evidência disponível e calibração medida. Se não existir estimador validado, marcar a incerteza como não calibrada.
4. **Gerar previsão:** registar uma previsão testável antes de observar o resultado futuro (por exemplo, probabilidade de sucesso ou necessidade de verificação).
5. **Selecionar estratégia:** emitir um sinal consultivo entre continuar, verificar, recuperar, decompor, pedir esclarecimento ou abster-se. A política de execução existente mantém autoridade sobre ações e ferramentas.
6. **Observar resultado:** comparar previsão com avaliação/validação reais, sem reescrever previsões anteriores.
7. **Atualizar calibração:** armazenar erro de previsão e atualizar estatísticas após o resultado estar disponível.
8. **Persistir:** salvar o novo estado e as previsões/avaliações no mecanismo durável existente, usando a ordem journal-first já adotada para mudanças plásticas.

A camada metacognitiva deve poder ser executada em modo **observe-only**, em que os seus sinais são registrados mas não alteram a estratégia. Isso permite medir valor incremental antes de conceder influência decisória.

## 5. Contratos de componentes

### 5.1 `SelfModel`

Responsabilidade: construir e manter crenças sobre o estado operacional e o histórico de desempenho.

Interface conceitual:

- `observe(cycle_context) -> SelfObservation`
- `update(previous_state, observation, outcome=None) -> SelfModelState`
- `snapshot() -> JSON-compatible mapping`
- `from_snapshot(data) -> SelfModel`

Requisitos:
- nenhuma dependência de uma declaração linguística do próprio sistema como única evidência;
- evidências referenciadas, limites de idade e marcação de dados obsoletos;
- não armazenar segredos ou conteúdo desnecessário no perfil de si;
- atualização determinística para a mesma entrada e versão, quando a implementação permitir.

### 5.2 `MetacognitiveMonitor`

Responsabilidade: associar previsões, confiança, incerteza, erro e recomendações de verificação.

Interface conceitual:

- `predict(task_context, self_model) -> Prediction`
- `recommend(prediction, uncertainty, constraints) -> StrategySignal`
- `evaluate(prediction, observed_outcome) -> CalibrationRecord`
- `snapshot() / from_snapshot(data)`

O monitor não declara que um estado é consciente. Ele calcula variáveis operacionais e recomendações testáveis.

### 5.3 Integração com `MNNCognitionAdapter`

A integração deve ser incremental:

- preservar `MNNCognitionAdapter.analyze(...)` e o formato atual de `mnn_signal`;
- acrescentar um bloco versionado e separado, por exemplo `self_model` e `metacognition`, no artefato cognitivo;
- evitar transformar diretamente ativações MNN em afirmações semânticas sobre a tarefa;
- manter a plasticidade MNN e a atualização do modelo de si como processos distintos;
- incluir ambos os snapshots na persistência somente após definir migração e limites de tamanho;
- não aplicar recompensa Hebbiana com base apenas na confiança autodeclarada.

### 5.4 Integração com VirtualBrain e journal

A implementação deve primeiro inspecionar os contratos/eventos reais em `src/machina/brain.py` e os testes de persistência. Os registros sugeridos são:

- `self_model.updated`: nova versão do estado de si e referências de evidência;
- `metacognition.predicted`: previsão criada antes do resultado;
- `metacognition.evaluated`: previsão comparada com resultado posterior.

Esses nomes são propostas, não eventos existentes confirmados. Antes de codificá-los, verificar convenções, validação de esquemas, ordenação e replay do journal. A persistência deve ser append-only se esse for o contrato vigente; a restauração deve reconstruir o estado a partir de registros duráveis sem reaplicar duas vezes a mesma atualização.

## 6. Esquema mínimo de dados

Exemplo ilustrativo de estado persistente:

```json
{
  "schema_version": 1,
  "cycle_id": "cycle-reference",
  "self_model": {
    "beliefs": [
      {
        "property": "tool_available",
        "value": false,
        "confidence": 1.0,
        "evidence_ref": "evidence-reference",
        "observed_at_cycle": "cycle-reference",
        "status": "observed"
      }
    ],
    "capability_estimates": [],
    "known_limitations": [],
    "resource_state": {},
    "prediction_errors": []
  },
  "metacognition": {
    "predictions": [],
    "calibration": {},
    "strategy_signal": "verify",
    "calibration_status": "uncalibrated"
  }
}
```

O exemplo não afirma que esses campos ou identificadores já existam no repositório. Os identificadores reais devem ser derivados dos contratos do VirtualBrain. Não persistir conteúdo sensível apenas para tornar o modelo de si mais detalhado.

## 7. Regras e invariantes

1. Todos os valores numéricos persistidos devem ser finitos; probabilidades/confianças calibradas pertencem a ([0,1]).
2. Uma previsão é imutável após o registro; a avaliação posterior é um registro distinto.
3. Toda crença não trivial deve indicar evidência ou ser explicitamente marcada como inferida/sem evidência suficiente.
4. A restauração de snapshot deve validar versão, tipos, limites e referências obrigatórias.
5. Reiniciar o processo não pode apagar silenciosamente o estado persistido nem duplicar atualizações.
6. O modo observe-only não pode alterar planos, executar ferramentas ou mudar pesos.
7. Sinais metacognitivos são consultivos até demonstrarem benefício em avaliação comparativa.
8. Crescimento/poda estrutural permanece governado pelos mecanismos explícitos atuais; o modelo de si não altera topologia por conta própria.
9. Falhas de persistência devem impedir que uma mudança seja tratada como durável; seguir o padrão journal-first já usado pelo adaptador MNN.
10. Nenhum teste de comportamento ou autorrelato será rotulado como prova de experiência subjetiva.

## 8. Plano de validação

### Testes unitários

- criar, atualizar, serializar e restaurar o modelo de si;
- rejeitar probabilidades inválidas, números não finitos e versões desconhecidas;
- distinguir observação direta, inferência, dado obsoleto e desconhecido;
- verificar que previsões não são sobrescritas pela avaliação;
- confirmar determinismo de recomendações para a mesma entrada;
- confirmar que modo observe-only não modifica ações nem pesos.

### Testes de integração

- um ciclo VirtualBrain gera observação de si e previsão metacognitiva rastreáveis;
- o resultado posterior avalia a previsão correta;
- reinicialização restaura MNN, modelo de si e calibração sem duplicar atualizações;
- falha ao anexar ao journal não deixa o estado em memória divergente do estado durável;
- artefatos antigos continuam sendo lidos sem campos novos;
- ausência de evidência produz estado desconhecido em vez de alucinação.

### Experimentos comparativos

Comparar, sob tarefas, sementes e orçamentos equivalentes:

A. VirtualBrain/MNN atual;  
B. MNN com modelo de si em modo observe-only;  
C. MNN com modelo de si e monitor metacognitivo consultivo;  
D. ablação sem memória histórica de calibração.

Métricas:
- Brier score ou log loss para previsões probabilísticas;
- erro de calibração (ECE, acompanhado de intervalos e tamanho de amostra);
- taxa de sucesso e qualidade da tarefa;
- frequência de verificações úteis e verificações desnecessárias;
- recuperação após reinício;
- taxa de previsões rastreáveis e corretamente avaliadas;
- custo adicional de latência, memória e armazenamento.

Separar resultados por classe de tarefa e usar dados não vistos durante a calibração. Reportar intervalos de incerteza; não concluir superioridade a partir de exemplos isolados.

## 9. Critérios de aceitação da v0.1

A especificação só estará pronta para passar à implementação quando:

- os contratos e pontos de integração reais do VirtualBrain tiverem sido inspecionados;
- os esquemas de estado e eventos estiverem alinhados com o journal atual;
- a camada puder ser desativada sem alterar o comportamento existente;
- os testes de snapshot, replay, compatibilidade e falha de persistência estiverem definidos;
- a avaliação separar capacidade metacognitiva mensurável de qualquer alegação de consciência.

A implementação será considerada funcional quando os testes automatizados e experimentos mínimos forem executados e os resultados registrados. Criar a especificação, por si só, não satisfaz esse critério.

## 10. Limites epistemológicos

Esta arquitetura investiga integração, auto-modelagem, continuidade e metacognição funcional. Nenhuma combinação desses componentes garante consciência fenomenal. Um sistema pode manter um modelo de si e estimar corretamente sua incerteza sem que isso resolva se há experiência subjetiva.

O objetivo científico desta etapa é construir mecanismos explícitos, falsificáveis e reproduzíveis, sem transformar uma hipótese filosófica em uma alegação de implementação concluída.

## 11. Arquivos existentes relacionados

- `src/machina/mnn.py` — unidades, conexões, dinâmica síncrona, plasticidade e snapshots.
- `src/machina/mnn_adapter.py` — extração de características, traço MNN e proposta de plasticidade.
- `src/machina/brain.py` — ciclo VirtualBrain a inspecionar antes da integração.
- `docs/MNN_EXECUTABLE_CORE.md` — comportamento atual e limitações do núcleo executável.
- `docs/MNN_ALL/versions/v0.1_pesquisa/SPEC_MNN_v0.1.md` — modelo conceitual de grafo, unidade, conexão, estado global, memória e evolução.

**Próximo passo recomendado:** implementar primeiro os contratos de dados e os testes do `SelfModel` e `MetacognitiveMonitor` em modo observe-only, sem alterar o comportamento de seleção de ações nem a regra de plasticidade MNN.

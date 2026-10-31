# Revisão de evidências de investigações de curiosidade

A ponte `SelfModelLearningBridge.review_curiosity_investigation()` compara uma hipótese registrada com avaliações explícitas de evidências armazenadas em `CuriosityInvestigationStore`.

## Contrato

Cada item de `evidence_assessments` é indexado por um `evidence_ref` já registrado na investigação e contém:
- `classification`: `support`, `contradict` ou `neutral`;
- `rationale`: justificativa não vazia escrita pelo avaliador;
- `confidence`: confiança declarada pelo avaliador, entre 0 e 1.

O método não interpreta automaticamente o texto de `finding`. A autoria, a qualidade e a independência das avaliações continuam sendo responsabilidade do avaliador que as fornece.

## Resultados

O relatório distingue `supported`, `contradicted`, `mixed` e `insufficient`, preservando referências e contagens. Evidência neutra não é convertida em apoio nem contradição. Uma revisão mista permanece mista; não há votação que esconda conflito.

Por padrão, a revisão é apenas analítica. Para projetá-la no `SelfModel`, o chamador deve passar explicitamente `apply_to_self_model=True`. A atualização é marcada como `inferred`, mantém as referências e usa uma pontuação heurística de suficiência, não uma probabilidade de verdade. Se já existir uma crença, a alteração usa `revise_belief()` e preserva o histórico append-only.

## Persistência e idempotência

O `CuriosityInvestigationStore` mantém relatórios imutáveis identificados por `review_id`. Repetir o mesmo ID devolve o relatório existente e não reaplica a revisão. Um ID já associado a outra investigação é rejeitado.

A persistência do relatório e a atualização do SelfModel usam armazenamentos distintos e não formam uma transação distribuída. Uma interrupção entre as duas gravações pode exigir reconciliação; não há alegação de atomicidade entre bancos.

## Limites

- Uma classificação explícita não comprova que a fonte é correta.
- Contagens e confiança do avaliador não substituem replicação, desenho experimental ou revisão independente.
- Contradição é sinalizada no histórico, não apagada nem resolvida automaticamente.
- A revisão não cria objetivos, não altera políticas de autonomia, não executa ações e não demonstra consciência ou livre-arbítrio.

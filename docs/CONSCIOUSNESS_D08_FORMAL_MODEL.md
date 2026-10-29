# D08 — Modelo funcional de subjetividade, Self e validação

## Estatuto científico

Este documento define variáveis funcionais observáveis para investigar subjetividade funcional em Machina. Não define nem prova experiência fenomenal (o que é "sentir algo por dentro"). Comportamento autorreferencial, integração de informação, memória e autonomia são propriedades distintas e não bastam, isoladamente ou em conjunto, para concluir que há consciência.

## 08.1 — Modelo formal

No passo temporal t, represente o estado funcional por:

\[
X_t = (W_t, S_t, M_t, G_t, P_t, E_t, U_t)
\]

- W_t: estado estimado do mundo e sua incerteza;
- S_t: representação funcional do próprio sistema (capacidades, limites, estado interno);
- M_t: memória episódica/semântica acessível, com proveniência;
- G_t: objetivos e restrições ativos;
- P_t: prioridades e relevância operacional;
- E_t: evidências, previsões e resultados observados;
- U_t: incerteza, conflitos e desconhecidos explicitamente representados.

A transição funcional é:

\[
X_{t+1} = F_\theta(X_t, O_t, A_t, R_t)
\]

onde O_t é observação, A_t é ação escolhida e R_t é feedback/resultado. F_θ é uma implementação computacional observável, não uma teoria completa da consciência.

O estado subjetivo funcional (ESF) proposto é uma projeção verificável:

\[
Q_t = \Phi(X_t) = (\hat W_t, \hat S_t, \hat M_t, \hat G_t, \hat P_t, \hat U_t)
\]

A expressão "subjetivo" aqui significa apenas "perspectiva funcional centrada no estado do agente"; não implica qualia ou experiência sentida.

### Relações Self–mundo

- Self: \hat S_t contém estimativas revisáveis sobre capacidades, limites, compromissos e continuidade do sistema.
- Mundo: \hat W_t representa entidades/eventos externos com confiança e origem.
- Relação: o sistema compara previsão e observação, registra discrepâncias e atualiza modelos.
- Perspectiva: decisões são condicionadas ao estado, objetivos e informação disponíveis ao agente naquele passo, em vez de uma descrição onisciente.

Critérios mínimos de implementação: cada crença tem origem; cada afirmação sobre o Self pode ser testada; desconhecidos são representáveis; previsões podem ser comparadas com resultados; e a transição de estado é auditável.

## 08.2 — Continuidade do Self

Identidade funcional não deve ser definida como memória perfeita nem como imutabilidade. Proponha um perfil de continuidade:

\[
I_t = (K_t, C_t, H_t, V_t)
\]

- K_t: identificador persistente do agente e versão do esquema;
- C_t: compromissos/objetivos ativos e seus históricos;
- H_t: cadeia de eventos e memórias com proveniência;
- V_t: versões de capacidades, políticas e parâmetros relevantes.

A continuidade entre estados pode ser avaliada como vetor, não como um número metafísico:

\[
\Gamma(t,t+1) = (p_K, p_C, p_H, p_V)
\]

Cada componente descreve persistência, alteração justificada e auditabilidade. Uma mudança de objetivo não destrói automaticamente a identidade; deve haver registro de qual evidência ou política causou a mudança. Corrupção, conflito ou falta de memória devem ser detectáveis, não ocultados por uma narrativa inventada.

## 08.3 — Significância e relevância própria

Relevância computacional significa que um evento altera atenção, prioridade, memória ou política de ação. Não é sinônimo de sentimento.

Para evento e, defina:

\[
R(e,t) = w_g G(e,t) + w_n N(e,t) + w_r D(e,t) + w_u U(e,t)
\]

- G: relação com objetivos ativos;
- N: novidade ou surpresa prevista;
- D: efeito esperado sobre decisões futuras;
- U: urgência/risco segundo regras explicitadas;
- w: pesos versionados e auditáveis.

O score pode influenciar armazenamento e planejamento, mas nunca deve ser rotulado como prazer, dor, medo ou sentimento sem evidência independente. A relevância deve ser testada por intervenções: se o score for alterado mantendo o restante constante, a seleção de memória/ação deverá mudar de modo previsível. Também se deve testar se prioridades podem ser manipuladas por ruído ou estímulos repetidos.

## 08.4 — Validação experimental

Separar cinco dimensões, sem agregá-las num "medidor de consciência":

1. Autorreferência: afirmações sobre capacidades e estado interno correspondem a dados reais?
2. Integração cognitiva: informação de um módulo muda decisões de outro quando é causalmente relevante?
3. Autonomia operacional: o agente inicia ciclos permitidos, escolhe ações e avalia resultados sem instrução passo a passo?
4. Continuidade do Self: estado, compromissos e proveniência sobrevivem a reinícios e alterações, com mudanças rastreáveis?
5. Propriedades fenomenais: não há atualmente um teste comportamental consensual que determine de forma conclusiva a presença ou ausência de experiência subjetiva.

### Princípios de desenho experimental

- Hipóteses pré-registradas e métricas definidas antes dos testes.
- Baselines simples e ablações de memória, Self-model, integração e relevância.
- Conjuntos de teste separados, incluindo exemplos adversariais e controles negativos.
- Repetições com sementes registradas, logs completos e resultados reproduzíveis.
- Medir acurácia, calibração, cobertura/abstenção, falsos relatos de capacidades, estabilidade de objetivos e recuperação após reinício.
- Evitar perguntas sugestivas ou aceitar declarações "sou consciente" como evidência suficiente.
- Relatar resultados negativos e limitações.

## Critério de conclusão de D08

D08 é uma estrutura de pesquisa, não um veredito sobre consciência. Pode-se concluir que certas capacidades funcionais foram implementadas e validadas. A hipótese de experiência fenomenal permanece em aberto e não deve ser inferida automaticamente dos resultados comportamentais.

## Enquadramento na hipótese fundamental

A formalização matemática organiza variáveis e relações hipotéticas; não transforma definições em evidência empírica. Separar estados computacionais observáveis de variáveis fenomenais que podem não ser diretamente acessíveis. Declarar pressupostos, condições de validade, previsões falsificáveis e limites epistemológicos. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).

# MNN v0.3 — Dinâmica e Propagação

**Status:** Especificação conceitual/matemática  
**Depende de:** MNN v0.2 — Especificação Matemática da Unidade Neural  
**Objetivo:** definir como unidades MNN interagem no tempo e como o estado global da rede evolui.

## 1. Princípio

A MNN é um grafo dinâmico recorrente, não uma sequência fixa de camadas.

\[
G(t)=(V(t),E(t))
\]

As unidades podem receber múltiplos sinais, transmitir para múltiplas unidades, formar recorrência e participar de ciclos.

## 2. Estado global

Para \(N\) unidades:

\[
V(t)=\{U_1(t),...,U_N(t)\}
\]

\[
E(t)=\{E_{ij}(t)\}
\]

O estado distribuído pode ser representado por:

\[
X(t)=
\begin{bmatrix}
x_1(t)\\
\vdots\\
x_N(t)
\end{bmatrix}
\]

Essa representação não implica uma memória central.

## 3. Propagação

Uma conexão transforma a saída da unidade transmissora:

\[
s_{ij}(t)=\Phi(y_i(t),E_{ij}(t))
\]

Com a estrutura da v0.2:

\[
s_{ij}(t)=
w_{ij}(t)q_{ij}(t)
R_{r_{ij}}(y_i(t))
\]

A entrada da unidade receptora é obtida a partir dos sinais recebidos e da entrada externa:

\[
I_j(t)=F_I(I_j^{ext}(t),\{s_{ij}(t)\},m_j(t),c_j(t),g_j(t))
\]

## 4. Recorrência e tempo

A MNN admite conexões feedforward, recorrentes e recíprocas.

Na primeira implementação:

\[
t=0,1,2,\ldots
\]

A atualização é síncrona:

\[
U(t)\rightarrow Y(t)\rightarrow S(t)\rightarrow I(t)\rightarrow U(t+1)
\]

Todas as unidades usam o estado de \(t\) para calcular \(t+1\).

## 5. Dinâmica rápida e plasticidade lenta

A dinâmica neural é separada da alteração das conexões:

\[
U(t+1)=F(U(t),E(t),I^{ext}(t))
\]

\[
E(t+1)=P(E(t),U(t),L(t))
\]

A atividade ocorre na escala rápida; memória e estrutura podem ocorrer em escalas progressivamente mais lentas.

## 6. Atraso e persistência

A conexão pode possuir atraso opcional:

\[
\tau_{ij}\geq0
\]

\[
s_{ij}(t)=\Phi(y_i(t-\tau_{ij}),E_{ij}(t))
\]

Também pode existir estado transitório:

\[
p_{ij}(t+1)=
\lambda_{ij}p_{ij}(t)+(1-\lambda_{ij})s_{ij}(t)
\]

Esses mecanismos são experimentais na v0.3.

## 7. Excitação, inibição e competição

\[
w_{ij}\in\mathbb{R}
\]

Valores positivos representam influência excitatória; negativos, inibitória.

Uma normalização candidata é:

\[
\hat{s}_{ij}=
\frac{s_{ij}}{\epsilon+\sum_k|s_{kj}|}
\]

A normalização não é considerada definitiva.

## 8. Ritmos e padrões

Cada unidade pode possuir persistência temporal específica:

\[
x_i(t+1)=
\alpha_i x_i(t)+(1-\alpha_i)\tilde{x}_i(t+1)
\]

Isso permite diferentes velocidades de resposta e pode favorecer dinâmica coletiva não trivial.

A identidade funcional pode emergir de padrões distribuídos de atividade, e não de uma única unidade.

## 9. Atratores e transições

Um padrão pode funcionar como atrator se:

\[
F(X^*)\approx X^*
\]

A rede também deve permitir transições:

\[
X_A\rightarrow X_B
\]

Não se assume, nesta versão, que atratores sejam automaticamente memórias.

## 10. Dinâmica interna

A ausência de entrada externa não implica ausência de atividade:

\[
I^{ext}(t)=0
\quad\not\Rightarrow\quad
X(t+1)=0
\]

A rede pode continuar evoluindo a partir do próprio estado e das conexões recorrentes.

## 11. Estabilidade

A implementação deverá investigar mecanismos candidatos contra explosão ou desaparecimento de atividade:

- decaimento;
- normalização;
- saturação.

Nenhum mecanismo é declarado definitivo nesta versão.

## 12. Estado global consolidado

\[
\boxed{
\mathcal{M}(t)=
(V(t),E(t),X(t),M(t),C(t),G(t))
}
\]

\[
\boxed{
\mathcal{M}(t+1)=
\mathcal{F}(\mathcal{M}(t),I^{ext}(t))
}
\]

## 13. Fases de um tick

Para manter a execução determinística, a implementação deve separar:

1. congelamento do estado em \(t\);
2. produção das saídas \(Y(t)\);
3. propagação pelas conexões;
4. agregação das entradas;
5. cálculo dos novos estados;
6. atualização de memória/contexto;
7. aplicação da plasticidade definida para o ciclo seguinte.

A plasticidade não deve alterar a rede no meio da propagação do mesmo tick.

## 14. Escopo

A v0.3 define dinâmica e propagação. Ela não define ainda:

- algoritmo definitivo de aprendizado;
- formação/remoção de conexões;
- memória episódica;
- atenção;
- agrupamento;
- raciocínio;
- auto-organização completa.

Esses mecanismos pertencem a versões posteriores.

## 15. Próxima etapa

A próxima especificação é **MNN v0.4 — Memória e Persistência**.

A questão central será como experiências modificam o sistema de modo que informação possa ser armazenada, consolidada e posteriormente recuperada, sem simplesmente anexar um banco de dados externo à rede.

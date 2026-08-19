# MNN v0.2 — Especificação Matemática da Unidade Neural

**Status:** Especificação matemática mínima  
**Base:** MNN v0.1  
**Objetivo:** transformar a unidade neural conceitual em um objeto matemático posteriormente simulável.

## 1. Definição formal

Uma unidade neural \(u_i\), no instante \(t\), é:

\[
u_i(t)=\left(x_i(t),m_i(t),c_i(t),g_i(t),y_i(t)\right)
\]

onde:

- \(x_i(t)\): estado neural instantâneo;
- \(m_i(t)\): memória interna persistente;
- \(c_i(t)\): contexto;
- \(g_i(t)\): estado de modulação/ganho;
- \(y_i(t)\): saída produzida.

Os parâmetros da unidade são:

\[
\theta_i=(\theta_x,\theta_m,\theta_c,\theta_g)
\]

A unidade é, portanto, um sistema dinâmico com memória.

## 2. Entrada da unidade

Se \(\mathcal N_i(t)\) é o conjunto de unidades que enviam sinais para \(u_i\):

\[
I_i(t)=
\sum_{j\in\mathcal N_i(t)}
\Phi(y_j(t),E_{ji}(t),c_j(t))
\]

A entrada depende do sinal, da conexão e do contexto da unidade transmissora.

## 3. Conexão

Uma conexão \(j\rightarrow i\) é:

\[
E_{ji}(t)=
(w_{ji},r_{ji},q_{ji},h_{ji}(t))
\]

onde:

- \(w_{ji}\): força;
- \(r_{ji}\): tipo de relação;
- \(q_{ji}\): confiabilidade;
- \(h_{ji}\): histórico/plasticidade.

A transmissão pode ser:

\[
s_{ji}(t)=
w_{ji}(t)q_{ji}(t)
R_{r_{ji}}(y_j(t))
\]

e:

\[
I_i(t)=\sum_j s_{ji}(t)
\]

## 4. Estado instantâneo

\[
x_i(t+1)=
F_x(x_i(t),I_i(t),m_i(t),c_i(t),g_i(t))
\]

Uma forma experimental:

\[
x_i(t+1)=
\alpha_i x_i(t)
+(1-\alpha_i)
F\left(I_i(t)+W_m m_i(t)+W_c c_i(t)\right)
\]

com:

\[
0\leq\alpha_i<1
\]

Valores menores de \(\alpha_i\) favorecem resposta rápida; valores maiores preservam mais o estado anterior.

## 5. Memória interna

A memória possui atualização própria:

\[
m_i(t+1)=
F_m(m_i(t),x_i(t),I_i(t),c_i(t))
\]

Uma forma inicial:

\[
m_i(t+1)=
\lambda_i m_i(t)
+(1-\lambda_i)
F'_m(x_i(t),I_i(t),c_i(t))
\]

com:

\[
0\leq\lambda_i<1
\]

## 6. Contexto

\[
c_i(t+1)=
F_c(c_i(t),x_i(t),m_i(t),I_i(t))
\]

Assim, a mesma entrada pode produzir respostas diferentes dependendo do estado interno:

\[
\text{resposta}=F(X,m,c)
\]

## 7. Modulação

\[
g_i(t+1)=
F_g(g_i(t),x_i(t),c_i(t),M_i(t))
\]

Na v0.2, \(g\) é somente um mecanismo matemático de modulação. Interpretações como atenção, prioridade, confiança ou motivação ficam para versões posteriores.

## 8. Saída

\[
y_i(t)=
F_y(x_i(t),m_i(t),c_i(t),g_i(t))
\]

Uma forma experimental:

\[
y_i(t)=
g_i(t)\cdot\sigma
(W_xx_i(t)+W_mm_i(t)+W_cc_i(t)+b_i)
\]

A saída não é restringida a escalar. Na MNN:

\[
y_i(t)\in\mathbb R^d
\]

para evitar limitar prematuramente a arquitetura.

## 9. Equação fundamental

A unidade pode ser representada por:

\[
\boxed{
u_i(t+1)=
F_{\theta_i}
\left(
u_i(t),
\sum_{j\in\mathcal N_i}
\Phi(u_j(t),E_{ji}(t)),
I_i^{ext}(t)
\right)
}
\]

Ela recebe estado próprio, sinais da rede e entrada externa, produzindo novo estado, memória, contexto e saída.

## 10. Entrada externa e entrada interna

\[
I_i(t)=I_i^{ext}(t)+I_i^{net}(t)
\]

Entrada externa:

\[
I_i^{ext}
\]

pode vir de visão, áudio, texto, sensores ou feedback.

Entrada interna:

\[
I_i^{net}
\]

pode representar memória, raciocínio, objetivos, previsão ou estados internos.

Isso permite atividade interna mesmo sem nova entrada sensorial.

## 11. Atualização síncrona

Na primeira implementação, todas as unidades calculam o próximo estado usando o estado anterior:

\[
u_i(t+1)=F(u(t))
\]

A atualização ocorre somente depois de todos os cálculos, evitando dependência da ordem de execução.

## 12. Unidade como sistema dinâmico

Uma unidade convencional pode ser aproximada por:

\[
y=f(x)
\]

A unidade MNN é:

\[
\boxed{
u(t+1)=F(u(t),I(t),E(t))
}
\]

Portanto, a MNN é um sistema dinâmico, e não apenas uma função estática.

## 13. Aprendizado

O aprendizado poderá modificar:

\[
\theta_i
\]

as conexões:

\[
E_{ij}
\]

e eventualmente a estrutura:

\[
G=(V,E)
\]

Formalmente:

\[
\boxed{
\{estado,parâmetros,conexões,estrutura\}
\rightarrow
\{estado',parâmetros',conexões',estrutura'\}
}
\]

A forma concreta de aprendizado não é definida nesta versão.

## 14. Identidade da unidade

É necessário distinguir:

- estado: \(x_i(t)\), muda rapidamente;
- memória: \(m_i(t)\), muda mais lentamente;
- parâmetros: \(\theta_i(t)\), mudam durante aprendizado;
- identidade estrutural: \(ID_i\), relativamente estável.

A definição consolidada inclui:

\[
u_i=
(ID_i,x_i,m_i,c_i,g_i,y_i,\theta_i)
\]

O ID serve para rastreamento arquitetural e não constitui, por si só, conteúdo cognitivo.

## 15. Princípios fundamentais

**P1 — Estado:** a unidade possui estado persistente.

**P2 — Temporalidade:** o comportamento depende da história.

**P3 — Memória:** a unidade pode conservar informação além do ciclo atual.

**P4 — Relacionalidade:** a informação recebida depende da conexão.

**P5 — Plasticidade:** unidade e conexões podem mudar com a experiência.

## 16. Definição consolidada

\[
\boxed{
U_i(t)=
(ID_i,x_i(t),m_i(t),c_i(t),g_i(t),y_i(t),\theta_i(t))
}
\]

\[
\boxed{
E_{ij}(t)=
(w_{ij}(t),r_{ij}(t),q_{ij}(t),h_{ij}(t))
}
\]

com:

\[
\boxed{
u_i(t+1)=
F_{\theta_i}
\left[
u_i(t),
I_i^{ext}(t),
\sum_j\Phi(u_j(t),E_{ji}(t))
\right]
}
\]

Essa é a definição matemática mínima da unidade MNN v0.2.

## 17. Fora do escopo da v0.2

Ainda não são definidos:

- função de ativação definitiva;
- algoritmo definitivo de aprendizado;
- nascimento ou remoção de conexões;
- formação de grupos;
- atenção;
- memória episódica;
- mecanismo de raciocínio;
- auto-organização completa.

Esses pontos pertencem a versões posteriores.

## 18. Próxima etapa

A próxima etapa é **MNN v0.3 — Dinâmica e Propagação**, que define como sinais percorrem a rede e como a interação entre unidades produz dinâmica coletiva.

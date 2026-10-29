# 02 — Brain Graph

Definimos o cérebro no tempo `t` como:

`B_t = (V_t, E_t, S_t, M_t, C_t, P_t)`

- `V_t`: unidades e componentes ativos;
- `E_t`: relações/conexões;
- `S_t`: estados temporais;
- `M_t`: memória persistente;
- `C_t`: contexto cognitivo;
- `P_t`: políticas e parâmetros.

A topologia pode mudar:

`G_(t+1) != G_t`

## Unidade

A unidade herda a MNN v0.2:

`U_i(t) = [x_i, m_i, c_i, g_i, r_i, p_i]`

onde:
- `x`: estado/ativação;
- `m`: memória local;
- `c`: confiança;
- `g`: contexto/objetivo;
- `r`: relevância;
- `p`: plasticidade.

## Conexão

`E_ij = [w, r, q, h, tau, kappa]`

- `w`: força;
- `r`: tipo de relação;
- `q`: qualidade/confiança;
- `h`: histórico;
- `tau`: propriedades temporais;
- `kappa`: contexto de validade.

Tipos de relação podem incluir neural, associativa, episódica, semântica, preditiva e causal.

A lista é extensível e deve ser validada experimentalmente.

## Enquadramento na hipótese fundamental

O grafo neural representa relações estruturais entre unidades, mas sua existência não demonstra, isoladamente, processamento cognitivo integrado ou experiência subjetiva. Investigar propriedades topológicas e dinâmicas com controles e medidas funcionais, relacionando os resultados ao comportamento longitudinal do sistema. Ver [Hipótese Fundamental](../00-vision/central-hypothesis.md).

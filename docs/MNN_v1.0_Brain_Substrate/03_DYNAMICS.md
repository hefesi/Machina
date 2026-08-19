# 03 — Dinâmica Neural

A MNN mantém estado persistente:

`U_i(t+1) = F_U(U_i(t), Inputs_i(t), Z_t)`

Mensagens:

`M_ij(t) = F_M(x_i, m_i, E_ij, Z_t)`

A dinâmica deve suportar:
- processamento síncrono;
- processamento assíncrono;
- ciclos internos;
- estados de curta e longa duração;
- propagação limitada por contexto.

## Requisito de estabilidade

Cada experimento deve medir:
- divergência;
- saturação;
- oscilação;
- explosão de atividade;
- perda de sinal;
- custo computacional.

Não se assume que uma dinâmica específica é correta. `F_U` e `F_M` são objetos de pesquisa.

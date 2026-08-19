# MNN v0.1 — Especificação Consolidada

## 1. Grafo
G_t = (V_t, E_t)

## 2. Unidade
U_i(t) = [x_i(t), m_i(t), c_i(t), g_i(t)]

## 3. Conexão
E_ij(t) = [w_ij, r_ij, q_ij, h_ij]

## 4. Estado global
Z(t) = [P_t, W_t, S_t, O_t, G_t]

## 5. Memória
M_t = M_work ∪ M_epi ∪ M_sem

## 6. Mensagem
M_ij(t) = F_M(x_i, m_i, E_ij, Z_t)

## 7. Atualização
U_i(t+1) = F_U(U_i(t), Inputs_i(t), Z_t)

## 8. Aprendizado
Parâmetros, conexões e topologia são aprendíveis.

## 9. Plasticidade
G_(t+1) = F_G(G_t, experiência, desempenho)

## 10. Estado completo
Machina_t = (G_t, Θ_t, Z_t, Mem_t, H_t)

## 11. Evolução
Machina_(t+1) = F(Machina_t, Input_t, Action_t, Feedback_t)

## 12. Hipótese
Uma arquitetura neural especificamente projetada sobre o esqueleto cognitivo da Machina pode oferecer vantagens em memória, aprendizado contínuo, transferência, generalização e adaptação estrutural.

A hipótese deve ser validada experimentalmente.

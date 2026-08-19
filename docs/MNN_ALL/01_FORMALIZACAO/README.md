# Formalização consolidada

## Grafo
`G_t = (V_t, E_t)`

## Unidade
`U_i(t) = [x_i(t), m_i(t), c_i(t), g_i(t)]`

## Conexão
`E_ij(t) = [w_ij, r_ij, q_ij, h_ij]`

## Estado cognitivo
`Z(t) = [P_t, W_t, S_t, O_t, G_t]`

## Memória
`Mem_t = {M_work, M_epi, M_sem}`

## Estado completo
`Machina_t = (G_t, Θ_t, Z_t, Mem_t, H_t)`

## Evolução
`Machina_(t+1) = F(Machina_t, Input_t, Action_t, Feedback_t)`

## Hipótese de custo/objetivo
`L = L_task + λ1 L_memory + λ2 L_prediction + λ3 L_structure + λ4 L_stability`

Os termos devem ser operacionalizados experimentalmente antes de serem tratados como componentes definitivos da arquitetura.

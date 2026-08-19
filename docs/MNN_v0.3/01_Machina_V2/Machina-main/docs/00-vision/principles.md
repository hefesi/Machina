# Princípios Arquiteturais

## P1 — Modularidade

Cada capacidade cognitiva deve ser um módulo com interfaces claras.

## P2 — Persistência

O estado relevante do Virtual Brain deve sobreviver ao encerramento de uma execução.

## P3 — Separação de responsabilidades

Memória, raciocínio, aprendizado, planejamento e ação devem possuir responsabilidades distintas, mesmo quando cooperam estreitamente.

## P4 — Contexto antes da resposta

O sistema deve construir uma representação do estado atual antes de decidir como responder ou agir.

## P5 — Memória com evidência

Conhecimento relevante deve poder apontar para sua origem, evidência e nível de confiança.

## P6 — Aprendizado incremental

Novas experiências devem atualizar o sistema sem apagar indiscriminadamente conhecimento anterior.

## P7 — Versionamento cognitivo

Mudanças significativas em crenças, conhecimento e procedimentos devem poder ser rastreadas.

## P8 — Incerteza explícita

O sistema deve poder representar dúvida, conflito entre evidências e baixa confiança.

## P9 — Observabilidade

Os ciclos cognitivos devem ser inspecionáveis: percepção, recuperação, pensamento, decisão, ação e aprendizado.

## P10 — Segurança por construção

Ações externas, acesso a ferramentas e mudanças estruturais devem ser controláveis e auditáveis.

## P11 — Evolução gradual

A arquitetura deve permitir que o sistema evolua por versões sem exigir reconstrução completa.

## P12 — Agnosticismo de fornecedor

A arquitetura conceitual não deve depender de um único LLM, banco de dados ou provedor de infraestrutura.

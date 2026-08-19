# MNN v0.3 — Pacote Consolidado

Este pacote organiza a evolução do Machina/MNN sem substituir os documentos históricos.

## Estrutura

```text
01_Machina_V2/
    Arquitetura cognitiva do Machina

02_MNN_v0.1/
    Pesquisa e fundamentos originais da MNN

03_MNN_v0.3/
    MNN_v0.2_Especificacao_Matematica_da_Unidade_Neural.md
    MNN_v0.3_Dinamica_e_Propagacao.md

MANIFEST.txt
README.md
```

## Linha de evolução

```text
MNN v0.1
   ↓
fundamentos e conceitos
   ↓
MNN v0.2
   ↓
unidade matemática
   ↓
MNN v0.3
   ↓
dinâmica e propagação
```

### Contratos de consistência

- A v0.2 define a unidade e a conexão; a v0.3 utiliza essas definições sem redefini-las.
- A unidade mantém identidade estrutural (`ID`) separada de estado, memória e parâmetros.
- A MNN é um sistema dinâmico recorrente, não uma pilha fixa de camadas.
- A atualização inicial é síncrona e determinística.
- Entrada externa e atividade interna são separadas.
- Dinâmica rápida e plasticidade estrutural operam em escalas distintas.
- Atraso, persistência, normalização e mecanismos de estabilidade são hipóteses experimentais.
- Atrator não é automaticamente considerado memória.
- Aprendizado, memória episódica e auto-organização completa permanecem fora do escopo das primeiras especificações.

## Princípio

A v0.3 deve ser uma continuação matemática da v0.2, e não uma nova arquitetura independente.

A próxima etapa prevista é **MNN v0.4 — Memória e Persistência**.

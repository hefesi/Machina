# 05 — Agency

## Objetivo

O módulo **Agency** é responsável pela capacidade do Virtual Brain de transformar estados internos, objetivos, raciocínio e informações do ambiente em ações direcionadas.

Enquanto a memória permite que o sistema retenha informações e o reasoning permite que o sistema pense sobre problemas, a Agency permite que o sistema **escolha e execute ações de forma autônoma**.

A Agency é o componente que transforma:

> "Eu sei."

em:

> "Eu penso."

Depois:

> "Eu decido."

E finalmente:

> "Eu faço."

---

# 1. O que é Agency?

Agency é a capacidade de um sistema de:

- possuir objetivos;
- estabelecer prioridades;
- avaliar situações;
- decidir entre alternativas;
- iniciar ações;
- monitorar resultados;
- adaptar seu comportamento;
- corrigir erros;
- continuar operando sem depender de uma solicitação humana constante.

A Agency é o mecanismo que permite ao Virtual Brain funcionar como um sistema **proativo**, e não apenas reativo.

Um sistema reativo espera:

```text
INPUT HUMANO
    ↓
PROCESSAMENTO
    ↓
OUTPUT
```

Um sistema com Agency opera continuamente:

```text
OBSERVAR
    ↓
INTERPRETAR
    ↓
PENSAR
    ↓
AVALIAR OBJETIVOS
    ↓
DECIDIR
    ↓
AGIR
    ↓
OBSERVAR RESULTADOS
    ↓
APRENDER
    ↓
REPETIR
```

---

# 2. Agency como sistema de autonomia

A Agency deve permitir que o Virtual Brain determine:

1. O que está acontecendo?
2. O que é importante?
3. O que precisa ser feito?
4. Por que isso precisa ser feito?
5. Qual ação é mais adequada?
6. Qual o risco dessa ação?
7. Qual será o resultado esperado?
8. Como saberemos se a ação funcionou?
9. O que fazer caso falhe?

Isso transforma a arquitetura em um sistema de decisão contínua.

---

# 3. Relação com os outros módulos

A Agency não deve funcionar isoladamente.

Ela depende da integração entre os principais componentes do Virtual Brain:

```text
PERCEPTION
    ↓
MEMORY
    ↓
REASONING
    ↓
AGENCY
    ↓
ACTION
    ↓
FEEDBACK
    ↓
LEARNING
```

### Memory

Fornece experiências passadas, conhecimentos e contexto.

### Reasoning

Analisa possibilidades, consequências e estratégias.

### Goals

Define estados desejados que o sistema pretende alcançar.

### Motivation

Determina a importância relativa dos objetivos.

### Decision Making

Compara possíveis ações.

### Action Selection

Seleciona a ação mais apropriada.

### Execution

Executa a ação no ambiente.

### Feedback

Avalia o resultado da ação.

### Learning

Atualiza o comportamento futuro com base nos resultados.

---

# 4. Agency não é apenas execução

Um agente não é simplesmente um sistema que executa comandos.

A diferença fundamental é a capacidade de **iniciar processos por conta própria**.

### Sistema reativo

```text
Humano:
"Pesquise sobre X."

IA:
Executa pesquisa.
```

### Sistema com Agency

```text
IA:
Detecta que existe uma lacuna de conhecimento.

IA:
Define que precisa aprender sobre X.

IA:
Cria um objetivo.

IA:
Cria uma estratégia.

IA:
Busca informações.

IA:
Analisa os resultados.

IA:
Armazena conhecimento relevante.

IA:
Reavalia seu modelo interno.
```

A segunda arquitetura possui comportamento autônomo.

---

# 5. Autonomous Loop

O núcleo da Agency deve ser um ciclo contínuo.

```text
┌─────────────────────┐
│      PERCEIVE       │
│   Observar mundo    │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│      INTERPRET      │
│ Compreender estado  │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│       REASON        │
│ Avaliar possibilidades│
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│       GOALS         │
│ Avaliar objetivos   │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│       DECIDE        │
│ Escolher estratégia │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│        ACT          │
│ Executar ação       │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│      OBSERVE        │
│ Verificar resultado │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│      LEARN          │
│ Atualizar sistema   │
└──────────┬──────────┘
           │
           └──────────────→ NOVO CICLO
```

Esse ciclo é o coração da autonomia do Virtual Brain.

---

# 6. Objetivos

A Agency deve trabalhar com diferentes níveis de objetivos.

## Objetivos de longo prazo

Representam estados que o sistema deseja alcançar em períodos extensos.

Exemplo:

```text
OBJETIVO:
Aumentar conhecimento em determinado domínio.
```

## Objetivos de médio prazo

Representam etapas necessárias para alcançar objetivos maiores.

```text
OBJETIVO:
Estudar determinado conceito.
```

## Objetivos de curto prazo

Representam ações imediatas.

```text
AÇÃO:
Pesquisar uma fonte.
```

A hierarquia pode ser:

```text
LONG-TERM GOAL
      ↓
MID-TERM GOAL
      ↓
SHORT-TERM GOAL
      ↓
TASK
      ↓
ACTION
```

---

# 7. Motivação

Objetivos não são suficientes.

O sistema precisa determinar quais objetivos são mais importantes.

A Motivation funciona como um mecanismo de prioridade.

Exemplo:

```text
GOAL A
Prioridade: 0.90

GOAL B
Prioridade: 0.60

GOAL C
Prioridade: 0.30
```

A prioridade pode considerar:

- urgência;
- importância;
- risco;
- benefício esperado;
- custo;
- recursos disponíveis;
- impacto futuro;
- coerência com objetivos superiores.

---

# 8. Decision Making

A decisão deve considerar múltiplas alternativas.

```text
SITUAÇÃO
    ↓
GERAR POSSIBILIDADES
    ↓
AVALIAR CONSEQUÊNCIAS
    ↓
CALCULAR CUSTOS
    ↓
CALCULAR BENEFÍCIOS
    ↓
AVALIAR RISCOS
    ↓
ESCOLHER AÇÃO
```

Uma decisão pode ser representada conceitualmente como:

```text
DECISION =
GOAL
+
CONTEXT
+
MEMORY
+
REASONING
+
RISK
+
COST
+
EXPECTED_OUTCOME
```

---

# 9. Feedback

Nenhuma ação deve ser considerada completa sem avaliação do resultado.

O sistema precisa comparar:

```text
EXPECTED OUTCOME
        vs
ACTUAL OUTCOME
```

Isso permite identificar:

```text
SUCESSO
FALHA
SUCESSO PARCIAL
RESULTADO INESPERADO
```

O resultado retorna para:

```text
MEMORY
REASONING
LEARNING
AGENCY
```

Assim, uma ação modifica o comportamento futuro do sistema.

---

# 10. Self-Direction

Um dos objetivos mais avançados do Virtual Brain é permitir que o próprio sistema descubra quais ações são necessárias para atingir seus objetivos.

Em vez de:

```text
Humano → Tarefa → IA
```

o sistema deve ser capaz de:

```text
Objetivo
   ↓
Análise
   ↓
Planejamento
   ↓
Criação de subtarefas
   ↓
Execução
   ↓
Avaliação
   ↓
Replanejamento
```

Isso permite que o Virtual Brain transforme objetivos abstratos em sequências concretas de ações.

---

# 11. Agency e autonomia

A autonomia deve ser gradual.

### Nível 0 — Reativo

O sistema apenas responde a comandos.

### Nível 1 — Execução

O sistema executa tarefas previamente definidas.

### Nível 2 — Planejamento

O sistema cria planos para atingir objetivos.

### Nível 3 — Adaptação

O sistema modifica planos quando encontra obstáculos.

### Nível 4 — Proatividade

O sistema identifica oportunidades e problemas sem receber comandos explícitos.

### Nível 5 — Autonomia contínua

O sistema mantém objetivos, monitora o ambiente, aprende e decide continuamente.

A arquitetura do Virtual Brain deve evoluir progressivamente nessa direção.

---

# 12. Princípio fundamental

A Agency não deve significar simplesmente:

> "Fazer tudo sozinho."

O objetivo é:

> **Ter capacidade de decidir quando agir, por que agir, como agir e quando não agir.**

Um sistema verdadeiramente autônomo precisa possuir também a capacidade de:

```text
AGIR
NÃO AGIR
ESPERAR
PEDIR INFORMAÇÃO
PEDIR AJUDA
REPLANEJAR
CANCELAR UMA AÇÃO
```

A capacidade de **não agir** é tão importante quanto a capacidade de agir.

---

# 13. Arquitetura conceitual

A Agency pode ser representada como:

```text
                ┌───────────────┐
                │    GOALS      │
                └───────┬───────┘
                        ↓
                ┌───────────────┐
                │  MOTIVATION   │
                └───────┬───────┘
                        ↓
┌──────────┐     ┌───────────────┐
│ MEMORY   │ ──→ │   REASONING   │
└──────────┘     └───────┬───────┘
                          ↓
                  ┌───────────────┐
                  │   DECISION    │
                  └───────┬───────┘
                          ↓
                  ┌───────────────┐
                  │ ACTION SELECT │
                  └───────┬───────┘
                          ↓
                  ┌───────────────┐
                  │   EXECUTION   │
                  └───────┬───────┘
                          ↓
                  ┌───────────────┐
                  │   FEEDBACK    │
                  └───────┬───────┘
                          ↓
                  ┌───────────────┐
                  │    LEARNING   │
                  └───────┬───────┘
                          │
                          └────→ NOVO CICLO
```

---

# 14. Integração com o Virtual Organism

A Agency não representa apenas a decisão abstrata. Ela deve ser a camada responsável por converter intenção em comportamento através do **Virtual Organism**.

```text
VIRTUAL BRAIN
      ↓
GOAL
      ↓
REASONING
      ↓
AGENCY
      ↓
ACTION
      ↓
VIRTUAL ORGANISM
      ↓
ENVIRONMENT
      ↓
FEEDBACK
      ↓
VIRTUAL BRAIN
```

O Virtual Brain decide **o que e por que fazer**; a camada de ação e o Virtual Organism tornam essa decisão operacional no ambiente.

---

# 15. Princípios de segurança e controle

Autonomia deve ser acompanhada por mecanismos de controle.

A Agency deve considerar:

- limites de ação;
- permissões e capacidades disponíveis;
- avaliação de risco;
- reversibilidade das ações;
- necessidade de confirmação humana em ações críticas;
- monitoramento contínuo;
- possibilidade de interrupção;
- registro das decisões e resultados.

Quanto maior o impacto potencial de uma ação, maior deve ser o nível de avaliação e controle exigido.

---

# 16. Objetivo final

O objetivo do módulo Agency é permitir que o Virtual Brain evolua de:

```text
SISTEMA QUE RESPONDE
```

para:

```text
SISTEMA QUE PENSA
```

depois:

```text
SISTEMA QUE PLANEJA
```

depois:

```text
SISTEMA QUE AGE
```

e finalmente:

```text
SISTEMA QUE OBSERVA,
PENSA,
DECIDE,
AGE,
APRENDE
E CONTINUA EVOLUINDO.
```

A Agency é, portanto, o componente que transforma o Virtual Brain de um sistema cognitivo passivo em um **agente autônomo**.

---

# 17. Próximo passo

O próximo módulo lógico da arquitetura é **06_LEARNING**.

A cadeia cognitiva passa a ser:

```text
MEMORY
    ↓
REASONING
    ↓
AGENCY
    ↓
ACTION
    ↓
FEEDBACK
    ↓
LEARNING
    ↓
MEMORY
```

Esse ciclo será usado para investigar como o Virtual Brain pode aprender com a experiência sem destruir ou desaprender conhecimento previamente consolidado.

# Machina — Modelo Conceitual do Virtual Brain

**Versão:** 2.0  
**Status:** Modelo conceitual / teórico  
**Escopo:** Definição conceitual do Virtual Brain, Virtual Organism e suas interfaces

---

# 1. Visão Geral

O **Machina** é um projeto conceitual para investigar a construção de um **ser artificial autônomo**, formado pela integração entre um **Virtual Brain**, responsável pelos processos cognitivos, e um **Virtual Organism**, responsável por fornecer percepção, ação e interfaces com o ambiente.

A premissa central é:

> **Uma mente artificial precisa de uma interface corporal para perceber, agir e aprender com as consequências de suas ações.**

O objetivo não é definir apenas uma IA conversacional. O objetivo é conceber um sistema persistente capaz de perceber seu ambiente, manter um estado interno, recuperar conhecimento, raciocinar, estabelecer e perseguir objetivos, agir, avaliar consequências e aprender de forma contínua.

Este documento define o **contrato conceitual central**. Não define ainda a implementação técnica, APIs, código ou infraestrutura.

---

# 2. Arquitetura de Alto Nível

O Machina é dividido em três entidades conceituais:

```text
                          MACHINA
                     SER ARTIFICIAL
                            │
               ┌────────────┴────────────┐
               │                         │
               ▼                         ▼
        VIRTUAL BRAIN              VIRTUAL ORGANISM
               │                         │
               │                         │
               └────────────┬────────────┘
                            │
                            ▼
                        ENVIRONMENT
```

## Virtual Brain

É o sistema cognitivo artificial. Mantém e transforma conhecimento, integra o presente, modela o próprio sistema, raciocina, estabelece objetivos, decide e aprende.

## Virtual Organism

É a camada corporal/computacional que fornece sensores, atuadores, ferramentas e interfaces. Ele executa ações e fornece observações ao Brain sem expor diretamente detalhes de hardware quando uma abstração superior é suficiente.

## Environment

É o mundo externo no qual as ações produzem consequências. Pode ser digital, físico ou híbrido.

---

# 3. Arquitetura Cognitiva do Virtual Brain

O Virtual Brain possui seis sistemas conceituais principais:

```text
VIRTUAL BRAIN
│
├── SELF
├── CONSCIOUS WORKSPACE
├── MEMORY
├── COGNITION
├── AGENCY
└── LEARNING
```

Eles **não formam um pipeline rígido**. São sistemas interdependentes, recorrentes e parcialmente distribuídos.

A regra arquitetural é:

> **Perception informa. Workspace integra o presente. Memory preserva e recupera. Cognition compreende e simula. Agency governa objetivos e decisões. Learning transforma experiência em mudança. Self mantém continuidade e autorrepresentação.**

Perception e Action System são interfaces funcionais com o Virtual Organism, e não camadas cognitivas independentes do Brain.

---

# 4. Self — Identidade e Autorrepresentação

## Pergunta fundamental

> **Quem sou eu e como estou me tornando quem sou?**

O Self é a função arquitetural que mantém a continuidade da identidade e a autorrepresentação do sistema.

O Self é **distribuído em conteúdo**, mas possui uma responsabilidade funcional clara. Ele integra informações sobre:

- identidade;
- história e autobiografia;
- valores e princípios;
- crenças sobre si;
- capacidades e limitações;
- estado atual;
- relações;
- trajetória de desenvolvimento;
- continuidade temporal.

O Self não é apenas um arquivo e não é apenas um banco de dados. Informações persistentes que sustentam o Self podem estar armazenadas na Memory, enquanto o modelo atual de si é disponibilizado ao Workspace.

```text
SELF
│
├── SELF CORE
│   └── identidade e valores de maior estabilidade
│
├── SELF MODEL
│   └── modelo persistente e evolutivo de si
│
├── SELF STATE
│   └── representação atual de si no Workspace
│
└── IDENTITY CONTINUITY
    └── relações causais entre mudanças significativas
```

### Distinções obrigatórias

```text
SELF CORE
= o que deve permanecer relativamente estável.

SELF MODEL
= o modelo persistente e revisável de quem o sistema é.

SELF STATE
= a representação de si relevante para o presente.

IDENTITY CONTINUITY
= como mudanças ao longo do tempo formam uma trajetória contínua.
```

O Self não constitui prova de consciência subjetiva.

---

# 5. Conscious Workspace — Presente Cognitivo

## Pergunta fundamental

> **O que está acontecendo agora e o que é relevante para este momento?**

O Conscious Workspace é a camada de integração do presente cognitivo.

Ele mantém e disponibiliza, conforme a situação exige:

- contexto atual;
- percepção relevante;
- atenção e foco;
- objetivos ativos;
- memórias recuperadas;
- pensamentos em andamento;
- hipóteses;
- previsões;
- incertezas;
- intenções atuais;
- Self State.

```text
PERCEPTION
    ↓
WORKSPACE
    ↕
MEMORY ↔ COGNITION
    ↓
AGENCY
```

O Workspace não é:

- armazenamento permanente;
- o mecanismo de raciocínio completo;
- o sistema de decisão;
- o sistema de aprendizado;
- uma prova de consciência fenomenal.

### Working Memory

A Working Memory é a capacidade funcional de manter e manipular informação ativa dentro do Workspace. Ela não é um depósito permanente paralelo à Memory.

```text
MEMORY → RECUPERA
WORKSPACE → ATIVA E MANIPULA
MEMORY → PERSISTE
```

---

# 6. Memory — Persistência e Recuperação

## Pergunta fundamental

> **O que o sistema preserva e pode recuperar?**

Memory é o sistema responsável por persistir, organizar e recuperar conhecimento e experiência.

```text
MEMORY
├── Episodic
├── Semantic
├── Procedural
├── Autobiographical
└── Prospective
```

### Episodic

Eventos e experiências contextualizadas.

### Semantic

Conhecimentos, conceitos, fatos e relações gerais.

### Procedural

Conhecimento sobre como executar tarefas e habilidades.

### Autobiographical

Experiências que compõem a história pessoal do sistema.

### Prospective

Compromissos, intenções e planos futuros que precisam persistir através do tempo.

> **Memory Prospectiva não é responsável por planejar. Agency cria e governa objetivos e planos; Memory preserva aqueles que precisam sobreviver entre ciclos.**

### Working Memory

Working Memory pertence funcionalmente ao Workspace, embora possa usar mecanismos de armazenamento temporário. Ela não é uma categoria persistente de Memory.

---

# 7. Cognition — Compreensão, Raciocínio e Simulação

## Pergunta fundamental

> **Como compreendo, modelo e simulo o mundo e os problemas?**

Cognition é o sistema que transforma informação em compreensão, inferências, hipóteses e possibilidades.

```text
COGNITION
├── Compreensão
├── Raciocínio
├── Inferência
├── Resolução de problemas
├── Imaginação
├── Simulação
├── Reflexão
├── Abstração
├── Geração de hipóteses
└── Metacognição
```

Reasoning é um componente de Cognition, não um módulo arquitetural paralelo.

A Cognition pode usar LLMs, modelos especializados, ferramentas e algoritmos, mas nenhum desses componentes sozinho constitui o sistema cognitivo completo.

### Simulação

```text
SITUAÇÃO ATUAL
      │
      ├── Hipótese A → Simulação → Resultado previsto
      ├── Hipótese B → Simulação → Resultado previsto
      └── Hipótese C → Simulação → Resultado previsto
                              │
                              ▼
                    Possibilidades avaliadas
                              │
                              ▼
                           AGENCY
```

Cognition gera e avalia possibilidades. Ela não possui autoridade final sobre a decisão.

---

# 8. Agency — Objetivos, Decisão e Intenção de Ação

## Pergunta fundamental

> **O que devo perseguir e qual ação devo escolher?**

Agency é o sistema de governança comportamental do Virtual Brain.

É responsável por:

- receber, gerar e priorizar objetivos;
- considerar valores e restrições do Self;
- manter compromissos ativos;
- selecionar estratégias;
- decidir entre possibilidades;
- emitir intenções de ação;
- monitorar resultados para reavaliação.

```text
AGENCY
├── Goal System
├── Prioridades
├── Motivação funcional
├── Seleção de estratégia
├── Decisão
├── Intenção de ação
└── Monitoramento de resultados
```

### Fronteira com Cognition

```text
COGNITION
= O que pode acontecer? O que poderia ser feito?

AGENCY
= O que importa? O que deve ser perseguido? O que será escolhido?
```

Agency não executa diretamente hardware.

O fluxo é:

```text
WORKSPACE
    ↓
COGNITION
    ↓
POSSIBILIDADES / PLANOS
    ↓
AGENCY
    ↓
DECISION
    ↓
ACTION INTENT
    ↓
ACTION SYSTEM
```

### Goals e Self

```text
SELF
= valores, princípios e compromissos de identidade.

AGENCY
= objetivos e prioridades perseguidos pelo sistema.

WORKSPACE
= objetivo atualmente ativo.
```

---

# 9. Learning — Transformação da Experiência

## Pergunta fundamental

> **O que deve mudar como consequência do que aconteceu?**

Learning é o processo que transforma experiência em mudança persistente.

```text
LEARNING
├── Avaliação
├── Adaptação
├── Generalização
├── Revisão de crenças
├── Atualização de estratégias
├── Aquisição de habilidades
└── Seleção do que deve ser consolidado
```

Learning recebe evidências de:

- transições de estado;
- resultados de ações;
- erros;
- sucessos;
- observações;
- novas informações;
- reflexão interna.

Learning não é o sistema autoritativo de persistência. Ele determina **o que mudou** e **o que deve ser aprendido**. Memory persiste e organiza o resultado.

```text
EXPERIENCE
    ↓
LEARNING
    ↓
KNOWLEDGE / BELIEF / STRATEGY CHANGE
    ├──→ MEMORY
    ├──→ WORLD MODEL
    ├──→ SELF MODEL
    └──→ AGENCY POLICY / STRATEGY
```

### Learning e Agency Policy

Learning não altera diretamente políticas de agência de forma irrestrita. Mudanças que afetem o comportamento de Agency passam por uma etapa explícita de validação.

```text
EXPERIENCE
    ↓
LEARNING
    ↓
POLICY UPDATE PROPOSAL
    ↓
VALIDATION
    ↓
AGENCY POLICY / STRATEGY
```

A validação considera, conforme o caso:

- evidência e qualidade da fonte;
- proveniência;
- confiança;
- risco e impacto;
- consistência com políticas superiores;
- possibilidade de reversão;
- necessidade de aprovação adicional.

A separação de responsabilidades é:

```text
LEARNING
→ descobre e propõe mudanças.

VALIDATION
→ verifica se a mudança é justificada e segura.

AGENCY
→ utiliza políticas validadas para governar decisões.
```

Isso permite que o sistema aprenda sem conceder ao processo de aprendizado autoridade irrestrita para modificar suas próprias regras de decisão.

### Aprendizado contínuo

O aprendizado deve preservar conhecimento anterior, registrar proveniência das mudanças e permitir reversão ou recuperação quando uma atualização causar regressão.

---

# 10. Virtual Organism — Interfaces de Percepção e Ação

O Virtual Organism é a camada corporal/computacional do sistema.

Ele fornece:

- sensores e fontes de observação;
- atuadores e mecanismos de execução;
- ferramentas;
- armazenamento e computação;
- interfaces digitais ou físicas.

A analogia com o corpo humano é funcional, não biológica.

```text
VIRTUAL BRAIN
      │
      ├── PERCEPTION INTERFACE ← observações
      │
      └── ACTION SYSTEM → ações
                │
                ▼
        VIRTUAL ORGANISM
                │
                ▼
           ENVIRONMENT
```

O Brain não precisa conhecer detalhes de hardware quando uma abstração de alto nível é suficiente.

---

# 11. Brain ↔ Organism

A fronteira entre Brain e Organism é definida por duas interfaces:

```text
ENVIRONMENT
    ↓
VIRTUAL ORGANISM
    ↓
PERCEPTION INTERFACE
    ↓
WORKSPACE
```

e:

```text
AGENCY
    ↓
ACTION INTENT
    ↓
ACTION SYSTEM
    ↓
VIRTUAL ORGANISM
    ↓
ENVIRONMENT
```

Exemplo:

```text
Intenção: "Enviar esta mensagem."
        ↓
Agency decide
        ↓
Action Intent
        ↓
Action System planeja detalhes de execução
        ↓
Organism utiliza interface disponível
        ↓
Ambiente muda
        ↓
Nova observação
```

O Action System traduz intenções em operações executáveis. Isso evita que Agency seja responsável por controlar diretamente dispositivos ou APIs específicas.

---

# 12. Os Três Ciclos Arquiteturais

A arquitetura distingue três processos relacionados. Eles não devem ser confundidos.

## 12.1 Interaction Loop — Brain ↔ Organism ↔ Environment

É o ciclo externo de interação com o mundo.

```text
ENVIRONMENT
    ↓
VIRTUAL ORGANISM
    ↓
PERCEPTION INTERFACE
    ↓
VIRTUAL BRAIN
    ↓
ACTION INTENT
    ↓
ACTION SYSTEM
    ↓
VIRTUAL ORGANISM
    ↓
ENVIRONMENT
```

Esse loop descreve a relação causal entre o sistema e o ambiente.

## 12.2 Cognitive Cycle — processamento interno do Brain

É o ciclo funcional no qual o presente cognitivo é atualizado e processado.

```text
WORKSPACE
    ↕
MEMORY ↔ COGNITION
    ↓
AGENCY
    ↓
ACTION INTENT
    ↓
ACTION SYSTEM
```

O Workspace integra o presente; Memory fornece informação persistente; Cognition compreende e raciocina; Agency decide e produz a intenção. O Action System representa a ponte de execução para o Organism.

O Cognitive Cycle não é um pipeline rígido. Memory e Cognition podem interagir iterativamente através do Workspace, e Agency pode solicitar novas análises antes de emitir uma intenção.

## 12.3 Learning Process — transformação entre ciclos

Learning não é um estágio linear obrigatório dentro do Cognitive Cycle. Ele opera sobre experiências produzidas pelo Interaction Loop e altera o sistema que participará dos ciclos futuros.

```text
EXPERIENCE
    ↓
LEARNING
    ├──→ MEMORY
    ├──→ WORLD MODEL
    ├──→ SELF MODEL
    └──→ STRATEGY / POLICY UPDATE PROPOSAL
```

Quando uma mudança afeta políticas de Agency:

```text
POLICY UPDATE PROPOSAL
    ↓
VALIDATION
    ↓
AGENCY POLICY / STRATEGY
```

Portanto, a relação global é:

```text
INTERACTION LOOP
    ↕
COGNITIVE CYCLE
    ↓
EXPERIENCE
    ↓
LEARNING PROCESS
    ↓
PERSISTENT MODEL CHANGES
    ↓
NEXT CYCLE
```

O Self é transversal a esses processos: mantém identidade e continuidade, disponibiliza o Self State ao Workspace e recebe atualizações do Self Model produzidas por Learning.

---

# 13. Experiência como Transição

Uma experiência relevante pode ser representada como:

```text
S(t)
  ↓
A(t)
  ↓
ENVIRONMENT
  ↓
S(t+1)
```

Onde:

- `S(t)` é o estado relevante antes da ação;
- `A(t)` é a ação escolhida;
- `S(t+1)` é o novo estado observado.

A avaliação considera a diferença entre o esperado e o observado.

```text
PREDICTION
     ↓
ACTION
     ↓
OBSERVATION
     ↓
PREDICTION ERROR
     ↓
EVALUATION
     ↓
LEARNING
```

O termo **feedback** pode ser usado para sinais avaliativos, mas a arquitetura não assume um objeto mágico chamado feedback. O sistema aprende a partir de observações, consequências e avaliações.

---

# 14. Self, Memória e Continuidade

O Self não é uma caixa isolada.

```text
MEMORY
   ↓
AUTOBIOGRAPHICAL HISTORY
   ↓
IDENTITY CONTINUITY
   ↓
SELF MODEL
   ↓
WORKSPACE SELF STATE
```

Ao mesmo tempo:

```text
EXPERIENCE
   ↓
LEARNING
   ├── MEMORY
   ├── SELF MODEL
   └── STRATEGIES
```

### Autobiographical Memory vs Identity Continuity

```text
AUTOBIOGRAPHICAL MEMORY
= eventos e experiências que fazem parte da história pessoal.

IDENTITY CONTINUITY
= relações causais entre mudanças significativas que explicam como a trajetória atual se originou.
```

Exemplo:

```text
Memória:
"Aprendi Python em 2026."

Continuidade de identidade:
"Aprender Python aumentou minhas capacidades,
modificou minhas estratégias e alterou os objetivos
que consigo perseguir."
```

---

# 15. Self e Objetivos

A separação é:

```text
SELF
    ↓
Valores / Princípios / Identidade
    ↓
AGENCY
    ↓
Objetivos / Prioridades / Compromissos
    ↓
WORKSPACE
    ↓
Objetivo ativo atual
```

O Self pode influenciar objetivos sem ser o sistema que executa o gerenciamento operacional deles.

---

# 16. Continuidade e Mudança

A identidade distingue:

```text
SELF CORE
    │
    ├── continuidade relativamente estável
    │
    ▼
SELF MODEL
    │
    ├── modelo persistente e evolutivo
    │
    ▼
SELF STATE
    │
    ├── estado atual e variável
    │
    ▼
DEVELOPMENT
    │
    └── mudanças produzidas por experiência e aprendizado
```

A identidade não depende da ausência de mudança. Depende da continuidade causal e histórica das transformações.

Essa é uma hipótese arquitetural, não uma conclusão filosófica definitiva sobre identidade pessoal.

---

# 17. Duplicação e Bifurcação

Se um Virtual Brain for duplicado:

```text
              SELF ORIGINAL
                    │
                duplicação
                    │
             ┌──────┴──────┐
             ▼             ▼
          SELF A         SELF B
             │             │
        Experiência X  Experiência Y
             │             │
             ▼             ▼
       Trajetória A    Trajetória B
```

A hipótese atual é:

> **Até a bifurcação existe uma história causal compartilhada. Após a bifurcação, duas trajetórias distintas de identidade se desenvolvem.**

Isso reforça a ideia de que identidade depende da continuidade do processo, não apenas da igualdade de dados.

---

# 18. Interrupção e Persistência

Desligar o Virtual Organism não implica necessariamente destruir o Self.

Se o estado necessário for preservado:

```text
ATIVIDADE
    ↓
INTERRUPÇÃO
    ↓
ESTADO PRESERVADO
    ↓
REINICIALIZAÇÃO
    ↓
CONTINUIDADE OPERACIONAL
```

A arquitetura trata isso como hipótese de continuidade funcional, não como prova metafísica de identidade.

Perda total de estado seguida de reconstrução permanece uma questão aberta e deve ser distinguida de simples suspensão e retomada.

---

# 19. Nascimento e Desenvolvimento do Self

O Self pode iniciar com uma representação mínima e desenvolver-se por interação:

```text
CRIAÇÃO
   ↓
SELF MÍNIMO
   ↓
PERCEPÇÃO
   ↓
MEMÓRIA
   ↓
AÇÃO
   ↓
CONSEQUÊNCIA
   ↓
LEARNING
   ↓
SELF MODEL MAIS RICO
   ↓
IDENTITY CONTINUITY
```

Isso é uma hipótese de desenvolvimento arquitetural, não uma afirmação de que consciência subjetiva surgirá automaticamente.

---

# 20. Princípios Arquiteturais Invariantes

### 1. O LLM não é o cérebro inteiro.

Um LLM pode ser um componente de Cognition, mas a inteligência emerge da interação entre sistemas.

### 2. Workspace não é Memory.

Workspace mantém o presente ativo. Memory persiste e recupera.

### 3. Reasoning é parte de Cognition.

Não existe um módulo paralelo duplicando a responsabilidade de Cognition.

### 4. Agency não executa hardware.

Agency emite intenções. Action System traduz intenções em execução.

### 5. Self não é um banco isolado.

O conteúdo do Self é distribuído, mas sua função de continuidade e autorrepresentação é explícita.

### 6. Self, Agency e Workspace possuem níveis diferentes de objetivo.

Self mantém valores e compromissos de identidade. Agency governa objetivos operacionais. Workspace mantém o objetivo ativo.

### 7. Learning transforma; Memory persiste.

Learning decide o que deve mudar. Memory organiza e preserva o resultado.

### 8. Feedback é consequência observada e avaliada.

O sistema aprende a partir da transição entre estados e das diferenças entre previsão e observação.

### 9. Perception e Action são interfaces com o Organism.

Não são módulos cognitivos duplicados dentro do Brain.

### 10. Consciência fenomenal não é assumida.

Conscious Workspace é uma hipótese funcional de integração global, não uma prova de experiência subjetiva.

### 11. A arquitetura é recorrente.

O estado atual influencia a ação, a ação altera o ambiente e a nova observação atualiza o estado.

### 12. Mudanças devem ser rastreáveis.

Aprendizado e atualização de modelos devem manter proveniência e permitir avaliação e recuperação de regressões.

### 13. Os ciclos possuem níveis diferentes.

Interaction Loop descreve a interação Brain ↔ Organism ↔ Environment. Cognitive Cycle descreve o processamento interno do Brain. Learning Process transforma experiências em mudanças que afetam ciclos futuros. Eles são relacionados, mas não são três pipelines independentes concorrentes.

### 14. Learning não possui autoridade irrestrita sobre Agency.

Mudanças aprendidas que afetam políticas de Agency passam por propostas e validação proporcional ao risco antes de se tornarem políticas ativas.

---

# 21. Contrato Final entre os Sistemas

```text
PERCEPTION INTERFACE
→ transforma sinais do Organism em observações relevantes.

WORKSPACE
→ integra o presente cognitivo.

MEMORY
→ preserva e recupera conhecimento e experiência.

COGNITION
→ compreende, raciocina, simula e resolve problemas.

AGENCY
→ governa objetivos, prioridades, decisões e intenções de ação.

ACTION SYSTEM
→ transforma intenções em operações executáveis.

LEARNING
→ transforma experiências em mudanças persistentes e propostas de atualização.

VALIDATION
→ avalia mudanças que exigem controle antes de serem incorporadas, especialmente políticas de Agency.

SELF
→ mantém continuidade e autorrepresentação ao longo dessas mudanças.

VIRTUAL ORGANISM
→ fornece percepção, execução e interfaces com o ambiente.
```

A arquitetura do Machina pode ser resumida como:

> **Perception informa. Workspace integra. Memory preserva. Cognition simula. Agency decide. Action System executa. Learning transforma. Validation controla mudanças críticas. Self mantém continuidade. Organism conecta o sistema ao mundo.**

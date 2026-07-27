# Machina

> Projeto de pesquisa e desenvolvimento de um **Virtual Brain**: uma arquitetura cognitiva artificial modular na qual inteligência emerge da interação entre percepção, memória, cognição, agência, aprendizado e ação.

## Visão

O Machina não trata um LLM como um cérebro completo. Um LLM pode ser um componente de **Cognition**, especialmente para linguagem e raciocínio, dentro de uma arquitetura maior.

O objetivo inicial é construir o **Virtual Brain v0.1**, uma fundação cognitiva capaz de:

- perceber eventos e informações por meio do Virtual Organism;
- manter um presente cognitivo integrado;
- formar, recuperar e consolidar memórias;
- compreender e raciocinar sobre problemas;
- manter um modelo de si e continuidade de identidade;
- estabelecer, priorizar e perseguir objetivos;
- planejar e decidir ações;
- executar ações por meio de uma camada de Action System;
- avaliar consequências e atualizar previsões;
- aprender com experiências;
- atualizar conhecimento e modelos de forma controlada, rastreável e versionada.

## Arquitetura conceitual

O Machina possui três entidades de alto nível:

```text
                          MACHINA
                     SER ARTIFICIAL
                            │
               ┌────────────┴────────────┐
               │                         │
               ▼                         ▼
        VIRTUAL BRAIN              VIRTUAL ORGANISM
               │                         │
               └────────────┬────────────┘
                            │
                            ▼
                        ENVIRONMENT
```

O **Virtual Brain** contém seis sistemas conceituais:

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

As interfaces com o ambiente são fornecidas pelo Virtual Organism:

```text
ENVIRONMENT
    ↓
VIRTUAL ORGANISM
    ↓
PERCEPTION INTERFACE
    ↓
WORKSPACE
    ↓
COGNITION
    ↓
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

O Self atua como eixo de continuidade e autorrepresentação, enquanto Learning transforma as experiências produzidas pelo ciclo em mudanças persistentes.

## Responsabilidades

| Sistema | Responsabilidade principal |
|---|---|
| **Self** | Identidade, autorrepresentação e continuidade |
| **Conscious Workspace** | Integração do presente cognitivo |
| **Memory** | Persistência e recuperação de conhecimento e experiência |
| **Cognition** | Compreensão, raciocínio, simulação e resolução de problemas |
| **Agency** | Objetivos, prioridades, decisão e intenção de ação |
| **Learning** | Transformação da experiência em mudanças persistentes |
| **Action System** | Tradução de intenções em operações executáveis |
| **Virtual Organism** | Percepção, execução e interfaces com o ambiente |

## Ciclos arquiteturais

O Machina distingue três níveis relacionados, mas não idênticos:

### 1. Interaction Loop — Brain ↔ Organism ↔ Environment

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

### 2. Cognitive Cycle — processamento interno do Brain

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

O Workspace integra o presente; Memory fornece informação persistente; Cognition compreende e raciocina; Agency decide e produz a intenção. O Action System pertence à interface de execução com o Organism.

### 3. Learning Process — transformação entre ciclos

Learning não é um estágio linear obrigatório dentro do ciclo cognitivo. Ele opera sobre experiências produzidas pela interação e altera o sistema que participará dos ciclos futuros.

```text
EXPERIENCE
    ↓
LEARNING
    ├──→ MEMORY
    ├──→ WORLD MODELS
    ├──→ SELF MODEL
    └──→ STRATEGIES / POLICY UPDATE PROPOSALS
```

Portanto:

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

## Learning e Agency Policy

Learning não deve alterar diretamente políticas de agência de forma irrestrita.

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

A validação deve considerar evidência, proveniência, risco, confiança, impacto e possibilidade de reversão. Mudanças em políticas de alto impacto podem exigir aprovação adicional ou permanecer apenas como propostas.

Isso mantém a separação entre:

```text
LEARNING
→ descobre e propõe mudanças.

VALIDATION
→ verifica se a mudança é segura e justificada.

AGENCY
→ utiliza políticas validadas para governar decisões.
```

## Princípios

1. **O LLM não é o cérebro inteiro.**
2. **Workspace não é Memory:** o primeiro mantém o presente ativo; o segundo preserva e recupera.
3. **Reasoning é parte de Cognition**, não um módulo arquitetural paralelo.
4. **Agency não controla hardware diretamente:** emite intenções que são executadas pelo Action System.
5. **Self não é um banco isolado:** sua função é manter identidade e continuidade, com conteúdo distribuído pelo sistema.
6. **Self, Agency e Workspace possuem níveis diferentes de objetivo:** valores e compromissos, objetivos operacionais e objetivo ativo.
7. **Learning transforma; Memory persiste:** aprendizado produz mudanças que a memória organiza e preserva.
8. **Experiências registram transições relevantes:** estado, ação, observação, resultado e avaliação.
9. **Perception e Action são interfaces com o Organism**, evitando duplicação de responsabilidades cognitivas.
10. **Consciência fenomenal não é assumida:** Conscious Workspace é um conceito funcional de integração global.
11. **O sistema é recorrente:** ações alteram o ambiente, novas observações atualizam o Workspace e o ciclo continua.
12. **Mudanças devem ser controladas e rastreáveis:** aprendizado e atualização de modelos devem preservar proveniência e permitir recuperação de regressões.

## Roadmap conceitual

- **v0.1 — Cognitive Core:** percepção, Workspace, memória persistente, recuperação, cognição, ação e aprendizado básico.
- **v0.2 — Persistent Brain:** memória episódica, semântica, procedural, autobiográfica e modelos de mundo e self.
- **v0.3 — Autonomous Brain:** objetivos, agência, planejamento, execução autônoma e processos em background.
- **v0.4 — Learning Brain:** aprendizado contínuo, consolidação, atualização de crenças e aquisição de habilidades.
- **v0.5 — Adaptive Brain:** adaptação de estratégias, seleção dinâmica de ferramentas e autoavaliação.

## Documentação

A documentação conceitual está organizada em [`docs/`](docs/).

O contrato arquitetural central do Virtual Brain está em [`VIRTUAL_BRAIN_THEORETICAL_MODEL.md`](VIRTUAL_BRAIN_THEORETICAL_MODEL.md).

O próximo objetivo é definir completamente o modelo cognitivo e suas interfaces antes da implementação do código.
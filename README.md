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

## Ciclo cognitivo

```text
Environment
    ↓
Virtual Organism
    ↓
Perception Interface
    ↓
Conscious Workspace
    ↕
Memory ↔ Cognition
    ↓
Agency
    ↓
Action Intent
    ↓
Action System
    ↓
Virtual Organism
    ↓
Environment
    ↓
New Observation
    ↓
Workspace
```

Learning atua sobre as experiências produzidas por esse ciclo:

```text
Experience
    ↓
Learning
    ├──→ Memory
    ├──→ World Models
    ├──→ Self Model
    └──→ Strategies
```

O Self atravessa o ciclo como eixo de continuidade:

```text
Self
 ↕
Memory ↔ Workspace ↔ Cognition ↔ Agency
 ↕                                      ↕
Learning ────────────────────────────────┘
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

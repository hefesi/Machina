# Machina

> Projeto de pesquisa e desenvolvimento de um **Virtual Brain**: uma arquitetura cognitiva artificial modular na qual inteligência emerge da interação entre percepção, memória, raciocínio, aprendizado, planejamento e ação.

## Visão

O Machina não trata um LLM como um cérebro completo. O modelo de linguagem é um componente de raciocínio e linguagem dentro de uma arquitetura maior.

O objetivo inicial é construir o **Virtual Brain v0.1**, uma fundação cognitiva capaz de:

- perceber eventos e informações;
- manter estado e contexto;
- formar e recuperar memórias;
- raciocinar sobre objetivos e problemas;
- planejar e executar ações;
- avaliar resultados;
- aprender com experiências;
- atualizar conhecimento de forma controlada e versionada.

## Estrutura conceitual

```text
Ambiente
    ↓
Percepção
    ↓
Memória de Trabalho ←→ Sistema de Memória
    ↓                         ↓
Raciocínio ←→ Modelo de Mundo ←→ Modelo de Si
    ↓
Planejamento
    ↓
Ação
    ↓
Observação do Resultado
    ↓
Avaliação
    ↓
Aprendizado
    ↓
Consolidação
    └──────────────→ Memória / Modelos
```

## Princípios

1. **O LLM não é o cérebro inteiro.**
2. **Memória é persistente, estruturada e versionada.**
3. **Pensamento é um processo cognitivo, não apenas geração de texto.**
4. **Aprendizado deve preservar conhecimento anterior e evitar regressões.**
5. **Mudanças estruturais no próprio sistema devem ser controladas.**
6. **Experiências devem registrar contexto, ação, resultado e avaliação.**
7. **O sistema deve ser modular para permitir evolução independente dos componentes.**

## Roadmap conceitual

- **v0.1 — Cognitive Core:** percepção, memória de trabalho, memória persistente, recuperação, raciocínio, ação e aprendizado básico.
- **v0.2 — Persistent Brain:** memória episódica, semântica, procedural, autobiográfica e modelo de mundo.
- **v0.3 — Autonomous Brain:** objetivos, planejamento, execução autônoma e processos em background.
- **v0.4 — Learning Brain:** aprendizado contínuo, consolidação, atualização de crenças e aquisição de habilidades.
- **v0.5 — Adaptive Brain:** adaptação de estratégias, seleção dinâmica de ferramentas e autoavaliação.

## Documentação

A documentação conceitual está organizada em [`docs/`](docs/).

O primeiro objetivo é definir completamente o modelo cognitivo antes da implementação do código.

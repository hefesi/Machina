# Machina

**Machina é um programa de pesquisa sobre a possibilidade de um ser artificial emergir de uma organização computacional construída somente por código.** A hipótese permanece aberta: capacidades funcionais, continuidade operacional e autorrelatos não são, por si, evidência de experiência subjetiva ou livre-arbítrio.

## Arquitetura em três níveis

- **Machina** — o projeto de pesquisa e a hipótese central.
- **Virtual Brain** — coordena ciclos cognitivos persistentes, contratos, memória, decisão, avaliação, aprendizagem e registro causal.
- **MNN / Virtual Organism** — implementa a dinâmica neural artificial e integra estado, sinalização química virtual, motivação, continuidade funcional e adaptação.

O Virtual Brain é proprietário do ciclo cognitivo e do diário persistente. O MNN Organism é um subsistema acoplado por adaptadores explícitos; não substitui o cérebro virtual nem constitui, isoladamente, a Machina.

## Estado da integração MNN Organism Bridge

A integração do organismo com os contratos atuais do VirtualBrain foi incorporada à `main` pelo merge [#89](https://github.com/hefesi/Machina/commit/032fbdddb43b5a4227577a19f67bb19f4964d5f2).

Os adaptadores têm responsabilidades distintas:

- `MNNOrganismCognitionAdapter`: mapeia features explicitamente configuradas para entradas do organismo, executa um passo e anexa snapshot/telemetria ao resultado cognitivo.
- `MNNOrganismAgencyAdapter`: pode reponderar planos já existentes com evidência limitada de memória; não inventa planos nem executa ações.
- `VirtualBrain`: mantém o ciclo, os contratos e o EventStore como fonte persistente da sequência de eventos.

A integração é experimental e opt-in. Features numéricas simples não equivalem a compreensão semântica.

## Instalação

Requer Python 3.12 ou superior.

```bash
python -m pip install -e .
```

## Testes

```bash
python -m unittest discover -s tests -v
```

O workflow de CI usa Python 3.12, instala o pacote em modo editável e executa `unittest discover`.

## Documentação principal

- [Estabilização arquitetural](docs/ARCHITECTURE_STABILIZATION.md)
- [Programa de investigação](docs/00-vision/research-program.md)
- [Hipótese central](docs/00-vision/central-hypothesis.md)
- [Modelo de dados cognitivos](docs/01-cognitive-model/cognitive-data-model.md)
- [Bridge MNN Organism ↔ VirtualBrain](docs/MNN_ORGANISM_BRAIN_BRIDGE.md)
- [Aprendizagem causal baseada em evidências](docs/CAUSAL_LEARNING.md)
- [Ciclo de vida do conhecimento MNN](docs/MNN_KNOWLEDGE_LIFECYCLE.md)

## Princípios de engenharia

1. Contratos explícitos, versionados e com proveniência.
2. Persistência append-only e retomada verificável de ciclos.
3. Adaptadores estreitos; evitar ciclos paralelos e duplicação de estado.
4. Evidência, inferência e hipótese devem permanecer distinguíveis.
5. Experimentos negativos e regressões devem ser preservados como resultados.
6. Nenhuma ação externa deve contornar autorização, limites ou idempotência.
7. Nenhuma capacidade funcional deve ser descrita como prova de consciência.

## Desenvolvimento

A `main` é a base de integração. Branches experimentais devem ser avaliadas por funcionalidade única, compatibilidade, testes e evidência de que a contribuição ainda não foi incorporada. Não fazer merge em massa nem apagar branches antes de verificar commits, PRs e conteúdo exclusivo.

# Integração da memória por fragmentos ao VirtualBrain

A Machina já possui `FragmentMemory`, um arquivo SQLite com prioridade dinâmica,
associações e recuperação lexical. Esta integração reutiliza esse componente em vez
de manter uma segunda implementação de memória.

## Ativação

A memória por fragmentos é opcional. Para ativá-la, forneça um segundo caminho
SQLite ao `VirtualBrain`:

```python
from machina import VirtualBrain

with VirtualBrain(
    "data/brain.sqlite",
    fragment_memory_path="data/fragments.sqlite",
) as brain:
    result = brain.run_cycle(
        "The blue sensor detected a high temperature.",
        "Remember the sensor event",
    )
```

O banco do cérebro mantém o diário causal e os artefatos do ciclo. O banco de
fragmentos fornece uma projeção de memória pesquisável e persistente. O diário
continua sendo a fonte de verdade para os estágios do ciclo.

## Fluxo

1. A Machina recupera os episódios e as memórias consolidadas do diário.
2. Se a memória por fragmentos estiver habilitada, ela também recupera fragmentos
   lexicalmente relevantes para a observação, o objetivo e o contexto.
3. O resultado `memory.retrieved` inclui `fragment_context`, com conteúdo,
   importância, confiança, prioridade, etiquetas e origem dos fragmentos.
4. Depois de registrar `memory.episode_recorded`, o episódio é espelhado no
   arquivo de fragmentos. O ID do artefato é reutilizado como ID do fragmento,
   tornando a escrita idempotente durante a retomada de um ciclo.

## Limites e confiabilidade

- A integração é opt-in e não altera o comportamento padrão de quem não fornece
  `fragment_memory_path`.
- A recuperação é lexical; correspondência de palavras não é compreensão semântica.
- Os dois arquivos SQLite não participam de uma transação distribuída. Se a escrita
  no arquivo de fragmentos falhar depois do diário ter sido gravado, a retomada do
  ciclo pode tentar novamente a sincronização.
- O componente de cognição recebe `fragment_context` dentro do artefato de
  recuperação. Cabe ao mecanismo cognitivo decidir como usá-lo; o motor padrão
  continua sendo deliberadamente determinístico e simples.
- Persistir e recuperar uma memória não prova consciência, entendimento humano ou
  inteligência geral.

## Validação

Execute no repositório:

```bash
python -m unittest tests.test_brain_fragment_memory -v
python -m unittest discover -s tests -v
```

## Enquadramento na hipótese fundamental

Integração de memória fragmentada deve demonstrar relações recuperáveis entre experiências, contexto e conhecimento, bem como efeitos persistentes sobre decisões. Distinguir organização informacional de continuidade autobiográfica funcional e ambas de experiência subjetiva. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).

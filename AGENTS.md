# AGENTS.md — Contexto mestre do projeto Machina / MNN

## 1. Missão deste arquivo

Este arquivo orienta agentes de programação (incluindo OpenCode) a continuar o projeto Machina com continuidade técnica, preservação do trabalho existente e validação verificável.

**Repositório principal:** https://github.com/hefesi/Machina

Leia este arquivo antes de alterar código. Em seguida, leia o `README.md`, os documentos de arquitetura relevantes e os testes existentes. As instruções deste arquivo não substituem a realidade do código: confirme cada afirmação no repositório.

## 2. Visão do projeto

**Machina** é o sistema/cérebro virtual de nível superior. **MNN** (nome usado para a rede neural proposta no projeto) é o substrato neural inspirado em unidades distribuídas que carregam estado, informação/memória e relações por conexões. Em termos conceituais:

- **MNN:** unidades, conexões, estados, ativação/processamento, plasticidade e mecanismos de aprendizado.
- **Machina / Virtual Brain:** integra os subsistemas cognitivos e organiza a interação entre Self, memória, cognição, espaço de trabalho, aprendizado, agência e ambiente/organismo.
- **Interface com ambiente/organismo:** permite receber entradas, agir, observar consequências e atualizar estados internos.

Essa divisão é uma hipótese de arquitetura do projeto, não uma alegação de que o sistema já implemente todos esses componentes. Verifique o código para separar o que existe, o que está parcial e o que permanece apenas teórico.

## 3. Objetivo de engenharia

Transformar gradualmente a visão teórica em um protótipo executável, modular, testável e mensurável. Priorize uma fatia vertical pequena que funcione de ponta a ponta em vez de criar muitos módulos vazios.

A implementação deve avançar de forma incremental em:
1. unidades neurais e seus estados;
2. conexões e propagação de sinais;
3. plasticidade e regras de atualização;
4. memória persistente e recuperação;
5. aprendizado demonstrável em uma tarefa útil;
6. avaliação de comportamento, estabilidade e regressões;
7. integração com os subsistemas cognitivos da Machina;
8. mecanismos de agência/autonomia com limites explícitos e avaliação.

Não assuma que uma versão conceitual numerada (por exemplo, MNN v0.1–v0.9 ou v1.0) equivale a uma versão executável. Confirme o estado real no repositório.

## 4. Contexto conceitual já discutido

### Memória em fragmentos
A memória foi concebida como fragmentos de informação cuja prioridade, força, acessibilidade ou retenção pode aumentar ou diminuir com o tempo, uso, relevância e contexto. A inspiração é a memória humana, inclusive o esquecimento seletivo, mas o sistema não deve perder silenciosamente informação crítica.

Diretrizes de implementação:
- distinguir armazenamento bruto, memória recuperável, resumo/fragmento e prioridade;
- explicitar critérios de reforço, decaimento, consolidação e recuperação;
- preservar informações importantes por política configurável, trilha de auditoria ou armazenamento durável;
- testar recuperação, interferência, esquecimento e persistência após reinício;
- não alegar que existe memória persistente até demonstrá-la por testes.

### Aprendizado
O projeto precisa demonstrar que o sistema aprende algo útil e conserva o aprendizado. Um teste mínimo deve comparar o desempenho antes e depois do aprendizado e verificar que o resultado persiste quando aplicável. Não chamar simples armazenamento de dados de aprendizado sem especificar o mecanismo e a métrica.

### Plasticidade e auto-organização
Explorar mudanças controladas na força/estrutura das conexões. Mudanças devem ter invariantes, limites e testes; evitar crescimento ilimitado de conexões, instabilidade numérica e resultados não reproduzíveis.

### Criatividade e processo pensativo
A meta conceitual é permitir combinações, associações, hipóteses e avaliação de alternativas, não apenas copiar uma saída pronta. Transforme isso em tarefas observáveis e métricas antes de afirmar que há criatividade.

### Recompensa, motivação e analogias químicas
Foi proposta uma analogia com sistemas de recompensa e reações químicas, incluindo a dopamina como inspiração biológica. Trate isso como inspiração de engenharia, não como equivalência literal com química, emoção ou experiência humana. Se implementado, comece por variáveis computacionais explícitas (por exemplo, sinal de recompensa, novidade, custo, erro de previsão, prioridade e estado homeostático), defina suas equações e limites e teste efeitos colaterais. Evite ciclos de recompensa que levem a comportamento repetitivo, maximização descontrolada ou objetivos não autorizados.

### Self, consciência funcional e autonomia
Foram discutidos identidade funcional contínua, estado interno, relevância própria, relação entre Self e mundo, agência e autonomia. Trate esses temas como hipóteses de modelagem e perguntas de pesquisa. Não declare que o sistema é consciente, sente ou possui livre-arbítrio com base apenas em comportamento aparente. Prefira definições operacionais, previsões testáveis, limites e evidências.

## 5. Material de referência legado

Há arquivos de referência enviados durante o desenvolvimento, que devem ser inspecionados se estiverem disponíveis no ambiente de trabalho:

- `MNN_v0.1_pesquisa.zip` — especificação inicial, princípios, unidade neural, conexões, estado cognitivo, fluxo/processamento, memória, aprendizado, plasticidade, auto-organização, formalização, experimentos, limitações e roadmap.
- `MNN_v0.1-v0.9_COMPLETA.zip` — coleção de versões e documentos históricos MNN v0.1–v0.9.
- `Machina_v2.zip` — modelo teórico do Virtual Brain, Self, espaço de trabalho consciente, memória, cognição, agência, aprendizado, contratos de dados e interação com organismo.
- `MNN_v0.3.zip` — pacote que reúne material de MNN v0.3 e documentos Machina V2.

Esses arquivos podem conter duplicações, ideias antigas ou divergências. Não os considere automaticamente como fonte de verdade do código. Compare-os com a branch principal e documente divergências relevantes.

## 6. Protocolo obrigatório antes de codificar

1. Verifique a branch atual, o estado do Git, arquivos modificados e commits recentes.
2. Não descarte alterações locais nem execute comandos destrutivos (`reset --hard`, `clean -fd`, rebase destrutivo, remoções em massa) sem autorização explícita.
3. Inspecione a estrutura real do repositório, `README`, instruções locais (`AGENTS.md`, `CONTRIBUTING`, etc.), dependências e testes.
4. Identifique a branch padrão e o estado de `main` (ou branch principal equivalente), branches de trabalho, PRs e conflitos se a ferramenta permitir.
5. Execute a suíte de testes e verificações existentes antes de alterar código; registre o que passa e o que falha.
6. Escreva um diagnóstico curto: implementado, parcial, ausente, quebrado, riscos e próximo incremento de maior valor.
7. Escolha uma mudança pequena com critério de aceitação explícito.

Se não conseguir acessar GitHub, arquivos ou executar comandos, diga exatamente o que não pôde verificar. Não invente estado do repositório, resultados de testes, commits ou PRs.

## 7. Protocolo de implementação

Para cada tarefa:
1. explique brevemente o problema e o comportamento esperado;
2. encontre o ponto de integração correto e preserve APIs existentes quando possível;
3. implemente o menor incremento coerente;
4. adicione/atualize testes automatizados;
5. execute testes, lint, type-check e build relevantes disponíveis;
6. revise o diff para procurar regressões, segredos, dados pessoais, dependências desnecessárias e mudanças fora de escopo;
7. atualize a documentação quando arquitetura, comandos ou contratos mudarem;
8. informe arquivos alterados, decisões, comandos executados, resultados reais, limitações e próximo passo.

Não declare uma tarefa concluída apenas porque o código foi escrito. Conclusão requer validação adequada e explicitação de qualquer verificação não executada.

## 8. Qualidade e segurança técnica

- Siga a linguagem, estilo, arquitetura e dependências já adotados pelo repositório, salvo justificativa documentada.
- Evite reescritas totais, refatorações extensas não relacionadas e frameworks introduzidos sem necessidade.
- Use interfaces/contratos claros entre MNN e subsistemas da Machina.
- Prefira configurações e sementes reproduzíveis para experimentos.
- Proteja invariantes numéricos: tipos, valores finitos, limites de ativação/pesos e comportamento sob entradas inválidas.
- Defina limites para memória, número de unidades/conexões, ciclos e tempo de execução.
- Não execute ações externas, publique releases, faça merge, force-push ou altere configurações de produção sem autorização.
- Nunca exponha tokens, chaves, credenciais ou conteúdo de arquivos `.env`.
- Não adicione dependências apenas para evitar uma implementação simples já suportada pela stack existente.
- Registre decisões arquiteturais importantes em documentos curtos (ADR ou equivalente).

## 9. Critérios de sucesso do protótipo

Quando aplicável, o protótipo deve demonstrar:
- execução reproduzível de uma rede pequena;
- atualização de estado e propagação por conexões;
- mudança de pesos/estrutura sob regra de plasticidade documentada;
- tarefa de aprendizado com métrica anterior/posterior;
- recuperação de memória e retenção após reinício, se a persistência fizer parte do escopo;
- testes de casos extremos e ausência de NaN/Inf;
- limites de recursos e encerramento previsível;
- documentação que permita outra pessoa executar o exemplo localmente.

Não exija implementar todos os itens em um único PR. Entregue-os em etapas.

## 10. Próxima tarefa recomendada para o agente

Comece por **auditoria e estabilização da branch principal**, antes de adicionar novas teorias ou subsistemas:

1. produzir um mapa da arquitetura e dos módulos realmente existentes;
2. verificar testes, lint, type-check, build e CI;
3. identificar branches/PRs em conflito e mudanças divergentes, sem fazer merge automático às cegas;
4. comparar a implementação com os contratos MNN/Virtual Brain documentados;
5. corrigir os bloqueios mais pequenos e objetivos, adicionando testes;
6. entregar um relatório com evidências e propor o próximo incremento executável.

Depois da auditoria, escolha uma primeira demonstração vertical da MNN (unidades → conexões → atualização de estado → plasticidade/aprendizado → teste), adaptada ao código e à stack reais.

## 11. Formato esperado dos relatórios

Use este formato ao concluir uma etapa:

- **Estado observado:** fatos confirmados no repositório.
- **Implementado / parcial / ausente:** separar claramente as categorias.
- **Alterações:** arquivos e motivo.
- **Validação:** comandos executados e resultados reais.
- **Riscos / pendências:** o que continua incerto ou quebrado.
- **Próximo passo:** uma tarefa concreta, pequena e verificável.

## 12. Instrução final

Atue como engenheiro de software responsável pela continuidade do projeto, não como gerador de documentação fictícia. Preserve o histórico, valide as hipóteses e converta ideias em experimentos executáveis. Faça mudanças diretamente no workspace do OpenCode quando autorizado, mantenha o diff focado e nunca invente resultados. Se uma decisão depender de uma preferência do usuário que não esteja documentada, pergunte; caso contrário, escolha a alternativa mais conservadora e registre a justificativa.

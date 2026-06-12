# Estrutura das seções e metas de profundidade

## Metas mínimas de profundidade (default)

Quando o periódico ou o usuário não impuserem limites, use estes **pisos** de
conteúdo científico. São metas mínimas de profundidade, **não** limites
máximos, e **não** devem ser atingidas com preenchimento artificial — a
expansão deve vir de conteúdo científico relevante.

| Seção | Mínimo recomendado |
|---|---|
| Resumo / Abstract | 350 palavras* |
| Introdução | 600 palavras |
| Materiais e Métodos | 700 palavras |
| Resultados | 900 palavras |
| Discussão | 700 palavras |
| Conclusão | 200 palavras |

\* O abstract estrutural costuma ter teto pelo periódico (ex.: 250 palavras na
Acta Tropica). **A restrição do periódico tem precedência sobre o piso acima.**

Diretrizes:
- Não reduza seções importantes a poucos parágrafos quando há informação para
  aprofundar.
- Resultados devem cobrir adequadamente **todas** as análises realizadas.
- Métodos devem permitir **reprodução** integral do estudo.
- A Introdução deve contextualizar o problema científico de forma completa.
- A Discussão deve explorar mecanismos, limitações e implicações.
- **Importante:** a Discussão deve ter profundidade intelectual igual ou
  superior à dos Resultados.

## Estrutura canônica por seção

### Título e cabeçalho
Título informativo e específico (idealmente com o achado central). Subtítulo
opcional indicando versão/idioma/alvo. Autores e afiliações. Para periódicos
modernos: **Highlights** (geralmente 3–5 bullets curtos) e **Keywords**.

### Resumo / Abstract
Síntese autocontida: contexto e lacuna -> objetivo -> abordagem -> principais
resultados quantitativos -> conclusão/implicação. Sem citações nem siglas não
definidas. Respeite o teto de palavras do periódico.

### 1. Introdução
- contextualize o tema e sua relevância;
- apresente o estado da arte;
- identifique a(s) lacuna(s) de conhecimento;
- justifique o estudo;
- enuncie objetivos e hipóteses de forma explícita ao final.

### 2. Materiais e Métodos
- detalhe protocolos, materiais e organismos/amostras;
- descreva softwares, versões e **parâmetros**;
- documente as análises estatísticas (testes, correções, limiares);
- informe bancos de dados e releases utilizados;
- descreva critérios de inclusão/exclusão;
- garanta reprodutibilidade (alguém deveria conseguir repetir o estudo).
Organize em subseções numeradas (2.1, 2.2, ...).

### 3. Resultados
- descreva os achados objetivamente, sem interpretação excessiva;
- organize em torno de figuras e tabelas, na ordem em que aparecem;
- destaque tendências relevantes e apresente métricas quantitativas reais;
- cada figura/tabela citada no texto e vice-versa;
- **título descritivo (o quê), nunca a conclusão.** O subtítulo nomeia o que foi
  estudado/analisado (ex.: "Catálogo de variantes e validação posicional contra o QTLdb"),
  não o achado (NÃO: "A função se concentra na variação regulatória"). A conclusão fica no
  texto; o título serve à navegação. Pôr a conclusão no título é o vício "fast-food de LLM".
- **arco interno de cada subseção:** (i) *motivação* — por que esta abordagem/análise vem
  agora (1 frase que herda a ponte da subseção anterior); (ii) *resultado descrito* amarrado
  explicitamente à figura/tabela ("A Figura 2 decompõe... ", "como mostra a Tabela S3");
  (iii) *fecho* curto do que aquilo estabelece; (iv) *ponte* para a próxima (ver *Signposting*).
- **encadeie as subseções**: termine cada subseção com uma frase-ponte que levanta a pergunta da próxima (ver *Signposting* abaixo).

### 4. Discussão
- interprete criticamente os achados;
- compare com a literatura (explique concordâncias e divergências);
- discuta mecanismos biológicos plausíveis;
- apresente limitações de forma honesta;
- proponha estudos futuros e aplicações potenciais;
- **encadeie os parágrafos**: termine cada parágrafo/virada com uma frase-ponte para o seguinte — a Discussão é o ponto mais propenso a "parágrafos-ilha" (ver *Signposting* abaixo).

### 5. Conclusão
- sintetize os principais avanços;
- mantenha alinhamento estrito com os resultados;
- evite extrapolações; aponte a implicação central.

### Declarações (exigidas por muitos periódicos)
Financiamento; Conflito de interesses; Contribuições dos autores (CRediT);
Disponibilidade de dados e código; Agradecimentos; Aprovação ética quando
aplicável. Mantenha placeholders explícitos até serem preenchidos.

### Referências
No estilo do periódico-alvo (autor-ano/Harvard, numérico/Vancouver, etc.).
Todas verificadas. Ver `periodicos.md`.

## Tempos verbais por seção (requisito padrão — registrado 2026-06-08)

Aplicar, salvo norma do periódico em contrário:
- **Introdução e Revisão de Literatura:** tempo **presente** (fatos estabelecidos e
  estado da arte: "o índice h *funde* produtividade e impacto").
- **Materiais e Métodos:** **pretérito perfeito** (o que foi feito: "os dados *foram
  coletados*", "*calibrei* os pesos por validação cruzada").
- **Resultados:** tempo **passado** (achados do próprio estudo: "a componente de autoria
  *separou* laureados de elites").
- **Discussão e Conclusões:** **passado para resumir** os achados/resultados, **alternando
  para o presente ao interpretá-los** ("o KANON *recreditou* esses autores; isso *sugere*
  que a estrutura de autoria *carrega* informação").

## Pessoa gramatical (registrado 2026-06-08)

Corrigir para o **singular** SOMENTE quando a frase **remete ao(s) autor(es)** — ações
autorais como "*nós* demonstramos / acreditamos / revelamos / calibramos / propomos".
Em manuscrito de **autor único**, converter essas ocorrências para a 1ª pessoa do singular
(EN: we/our -> I/my; PT: "demonstramos" -> "demonstrei", "nosso" -> "meu", "nós" -> "eu").
**Não** alterar "we/nós" que não sejam autorais (citações, títulos de referências, fala
genérica da comunidade), nem confundir com falsos positivos (PT: "homônimos", "extremos",
preposição "nos"; EN: proteger a bibliografia).

## Signposting / coesão narrativa — evitar "parágrafos-ilha" (requisito padrão — registrado 2026-06-12; reconfirmado pelo Luiz como diretriz-alvo)

**Problema a evitar:** seções (sobretudo **Resultados** e **Discussão**) escritas como blocos
de subtópicos justapostos e autossuficientes — o "efeito fast-food de LLM": cada subseção/parágrafo
abre, resolve um ponto e fecha, sem ligação com o seguinte. A leitura vira uma lista, não um argumento.

**Princípio-resumo (o alvo, em uma linha):** título descritivo (o quê) + signposting no FIM do texto —
cada subseção de Resultados termina com a frase que levanta a pergunta que a próxima responde, de modo
que os Resultados virem um argumento contínuo **sem perder a navegabilidade dos títulos**. O **mesmo
princípio vale nas viradas da Discussão**, que têm o mesmo vício de parágrafos-ilha (e, por raramente
ter subtítulos, dependem inteiramente das frases-ponte). Aplicar a TODO paper, EN e PT.

**Regra (aplicar salvo norma do periódico em contrário):**
- Termine **cada subseção de Resultados** e **cada parágrafo/virada da Discussão** com uma
  **frase-ponte** que aponta para frente: levanta a pergunta, tensão ou limitação que a próxima
  unidade resolve. O leitor deve sentir *por que* a próxima seção vem a seguir.
- **Mantenha títulos/subtítulos** (ajudam o revisor a navegar) — o encadeamento se faz pela prosa,
  não removendo cabeçalhos.
- A frase-ponte **não introduz números nem afirmações novas**: apenas prepara o terreno
  (a evidência fica no parágrafo de destino). Não inventar dado para "costurar".
- **Varie a construção** — não inicie todas as pontes com "However/Porém/Moreover". Alterne formas
  (interrogativa indireta, contraste, consequência, escalonamento).
- Aplique o mesmo encadeamento na versão **EN (submissão)** e na **PT (auditoria)**.

**Consolidação (quando os Resultados têm subtópicos demais):** se houver muitas subseções curtas,
considere fundi-las em **~4 blocos temáticos** com arco lógico (p.ex. descoberta → sistematização →
integração → validação). Cada bloco termina com ponte para o seguinte; as transições internas viram
pontes intra-bloco. Ao renumerar, **corrija referências cruzadas** ("Section 3.8" → novo número) e
as legendas/numeração de Suplementar.

**Viradas típicas da Discussão (onde estão os "parágrafos-ilha"):** a Discussão raramente tem
subtítulos, então o leitor depende inteiramente das frases-ponte para sentir o argumento avançar.
As costuras mais propensas a salto abrupto — e que merecem ponte explícita ao fim do parágrafo:
- **achado central → sua dupla leitura** (o que o resultado significa metodológica e biologicamente);
- **interpretação in silico/computacional → respaldo experimental** ("até aqui o argumento veio de
  sequência/estrutura; faltava evidência de fora dos modelos");
- **parceiro/eixo A → parceiro/mecanismo B da mesma triagem** (a pior costura: troca de assunto sem
  aviso — explicitar que B responde a uma *pergunta diferente*);
- **mecanismo → implicação translacional/alvo** ("uma reação definida é o primeiro requisito de um alvo");
- **alvo druggável → relevância onde a doença ocorre** ("um alvo só vale onde a via importa — e isso
  exige perguntar se o nó opera no hospedeiro/estágio relevante");
- **fios dispersos → modelo unificador** (a ponte justifica *por que* tratar as observações como um só sistema);
- **modelo → limitações → hipóteses testáveis** (um modelo "falsificável" já convida ao parágrafo de limitações;
  as limitações viram **agenda**, não becos sem saída — cada lacuna aponta um experimento).
Padrão de redação da ponte: 1 frase, sem dado novo, levantando a tensão/pergunta que o próximo parágrafo
resolve; enxugar abridores retrospectivos redundantes ("Tendo confirmado…", "Passamos agora a…") quando a
ponte anterior já fez o trabalho — o peso vai para o **fim** da unidade, não para o começo da seguinte.

## Tipos de artigo (ajuste a estrutura)
- **Original/Research**: estrutura completa acima (IMRaD).
- **Comunicação curta / Nota técnica**: Métodos e Resultados podem ser
  fundidos; limites de palavras menores.
- **Revisão**: substitua Resultados/Métodos por seções temáticas; foco em
  síntese crítica e lacunas.
- **Resposta a revisores**: documento ponto-a-ponto — citar o comentário,
  responder, indicar a mudança e a localização no manuscrito.

# Feature Specification: Gerador de Batidas Boom Bap por Gramática Probabilística

**Feature Branch**: `001-boombap-grammar-generator`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "Desenvolva um sistema que gere batidas de boom bap em formato simbólico usando apenas uma gramática generativa probabilística. Cada execução produz um arquivo MIDI que pode ser reproduzido e convertido em áudio só para ouvir. Boom bap é a restrição de estilo do trabalho e precisa ser respeitada em tudo o que o sistema gera (andamento 85–95 BPM, 4/4, bumbo no tempo 1 e em pontos sincopados, caixa nos tempos 2 e 4, chimbal em colcheias ou semicolcheias com dinâmica variada, swing obrigatório). A gramática precisa ser definida formalmente (terminais, não-terminais, regras de produção com probabilidades, axioma), expandindo forma → seções → blocos de 4 ou 8 compassos → padrões de compasso, com viradas mais prováveis no último compasso de cada bloco. Terminais são eventos concretos de bateria no mapa General MIDI (canal 10). Linha de baixo simples opcional. Semente exposta e hiperparâmetros na linha de comando (andamento, swing, densidade, frequência de viradas, quantidade de compassos), com diferença audível ao variá-los."

## Contexto

Este sistema é o Trabalho Prático 1 da disciplina DCC831 – IA Generativa para Música (UFMG, 2026/2). O método escolhido é **gramáticas generativas** (uso exclusivo) e a restrição estilística é **boom bap** (hip-hop dos anos 90, estética de MPC/SP). Os resultados alimentam um resumo no formato ISMIR, que precisa documentar a gramática e mostrar como a variação de sementes e hiperparâmetros altera as músicas geradas.

## Clarifications

### Session 2026-10-05

- Q: Dentro de uma seção, os compassos repetem um groove principal ou são sorteados de forma independente? → A: Cada seção escolhe um groove principal; seus compassos repetem esse groove, com eventos opcionais sorteados por compasso e viradas no fim dos blocos; seções de mesmo tipo (os dois versos) podem escolher grooves diferentes.
- Q: Um compasso de virada pode substituir a caixa do tempo 4? → A: Sim. Em compassos de virada, bumbo no tempo 1 e caixa no tempo 2 são obrigatórios e a caixa do tempo 4 pode ser substituída por eventos da virada; nos demais compassos valem as regras completas.
- Q: Sobre quais posições o swing age? → A: A grade de swing segue a grade do chimbal do compasso: chimbal só em colcheias → swing de colcheia (posições 2, 6, 10, 14 atrasadas); chimbal com semicolcheias → swing de semicolcheia (posições ímpares atrasadas).
- Q: Quem decide quantos compassos cada seção recebe? → A: A própria gramática, por meio de não-terminais indexados pelo número de compassos: distribui o total entre as seções (intro/outro curtas, verso/refrão maiores) e depois divide cada seção em blocos de 4/8, tudo com probabilidades; o total exato é garantido por construção, sem rejeição.
- Q: Onde ficam registrados semente, hiperparâmetros e derivação? → A: Nos dois lugares: um arquivo separado legível por máquina (mesmo nome-base do MIDI) com semente, parâmetros e derivação completa; o MIDI leva semente, parâmetros e marcadores de seção como eventos de texto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar uma batida boom bap completa com um comando (Priority: P1)

O usuário (o aluno, autor do trabalho) executa o gerador pela linha de comando sem nenhum parâmetro além do caminho de saída e recebe um arquivo MIDI com uma música de bateria boom bap completa: forma intro → verso → refrão → verso → outro, cada seção composta de blocos de 4 ou 8 compassos, bateria no canal 10 com bumbo, caixa, aro, chimbal fechado/aberto e prato, swing perceptível e andamento entre 85 e 95 BPM. A semente usada é informada ao usuário.

**Why this priority**: É o núcleo do trabalho. Sem isso não há música, nem entregável, nem resumo.

**Independent Test**: Executar o gerador uma vez, abrir o arquivo em qualquer reprodutor/sintetizador MIDI e verificar (de ouvido e por inspeção dos eventos) que todas as regras de estilo são respeitadas.

**Acceptance Scenarios**:

1. **Given** nenhuma configuração além do destino de saída, **When** o usuário executa o gerador, **Then** um arquivo MIDI válido é criado, a semente utilizada é exibida, e o arquivo toca em um sintetizador General MIDI comum soando como bateria.
2. **Given** um arquivo gerado, **When** seus eventos são inspecionados, **Then** o andamento está entre 85 e 95 BPM, o compasso é 4/4, todo compasso tem bumbo no tempo 1 e caixa no tempo 2, todo compasso que não é de virada tem também caixa no tempo 4 (ver FR-011), e chimbal em grade de colcheias ou semicolcheias com intensidades variadas.
3. **Given** um arquivo gerado, **When** as posições das notas nos contratempos da grade de swing de cada compasso (colcheias de contratempo se o chimbal está em colcheias; semicolcheias ímpares se está em semicolcheias) são medidas, **Then** elas estão atrasadas em relação à grade reta de forma consistente com a intensidade de swing configurada.
4. **Given** um arquivo gerado, **When** a estrutura é inspecionada (pelos marcadores de seção no MIDI ou pelo arquivo de derivação), **Then** aparecem, na ordem, as seções intro, verso, refrão, verso e outro, cada uma formada por blocos de 4 ou 8 compassos.

---

### User Story 2 - Reproduzir e variar resultados por semente (Priority: P1)

O usuário gera várias músicas com a mesma configuração e obtém resultados diferentes a cada execução. Quando gosta de um resultado, reexecuta informando a semente exibida e obtém exatamente o mesmo arquivo.

**Why this priority**: Requisito explícito do enunciado (múltiplas músicas da mesma configuração) e necessário para que os resultados citados no resumo sejam reproduzíveis por quem avaliar o repositório.

**Independent Test**: Executar o gerador três vezes sem semente e comparar os arquivos (devem diferir); executar duas vezes com a mesma semente e mesmos parâmetros e comparar (devem ser idênticos).

**Acceptance Scenarios**:

1. **Given** a mesma configuração e nenhuma semente informada, **When** o usuário executa o gerador várias vezes, **Then** cada execução usa uma semente nova e produz uma sequência de eventos diferente.
2. **Given** uma semente e um conjunto de parâmetros, **When** o usuário executa o gerador duas vezes com eles, **Then** os dois arquivos contêm exatamente os mesmos eventos musicais.
3. **Given** uma execução qualquer, **When** ela termina, **Then** a semente e todos os valores de hiperparâmetros efetivamente usados ficam registrados junto ao resultado, permitindo reproduzi-lo depois.

---

### User Story 3 - Controlar hiperparâmetros com efeito audível (Priority: P2)

O usuário ajusta pela linha de comando andamento, intensidade do swing, densidade de notas, frequência das viradas e quantidade de compassos, e consegue ouvir (e medir) a diferença entre as versões, para usar essas comparações na seção de resultados do resumo.

**Why this priority**: Exigido pelo enunciado (variar ao menos um hiperparâmetro) e central para a seção de resultados do relatório; depende do gerador base (US1).

**Independent Test**: Para cada hiperparâmetro, gerar duas músicas com a mesma semente variando apenas esse parâmetro entre um valor baixo e um alto, e verificar que a métrica correspondente muda na direção esperada.

**Acceptance Scenarios**:

1. **Given** a mesma semente, **When** o usuário gera com densidade baixa e depois com densidade alta, **Then** a versão de densidade alta tem mais bumbos fantasmas/sincopados e mais semicolcheias de chimbal por compasso.
2. **Given** a mesma semente, **When** o usuário gera com frequência de viradas baixa e depois alta, **Then** a versão com frequência alta contém mais compassos de virada.
3. **Given** a mesma semente, **When** o usuário gera com swing mínimo e depois máximo, **Then** o deslocamento médio das notas em contratempo é maior na segunda versão.
4. **Given** a mesma semente, **When** o usuário muda o andamento de 85 para 95 BPM, **Then** o arquivo registra o novo andamento e a duração total diminui proporcionalmente.
5. **Given** um número de compassos pedido, **When** o usuário gera a música, **Then** a música tem a quantidade de compassos pedida, respeitando a forma e os blocos de 4/8 (ver FR-019).
6. **Given** um valor de hiperparâmetro fora da faixa permitida (por exemplo, andamento 120), **When** o usuário executa o gerador, **Then** a execução é recusada com uma mensagem clara indicando a faixa válida, sem gerar arquivo.

---

### User Story 4 - Inspecionar a gramática e a derivação (Priority: P2)

O usuário consegue consultar a definição formal da gramática (terminais, não-terminais, regras com probabilidades, axioma) e, para cada música gerada, a árvore/sequência de derivação que a produziu, para documentá-las no resumo.

**Why this priority**: O enunciado exige documentar formalmente a gramática no resumo; a derivação permite explicar e ilustrar como uma música específica surgiu.

**Independent Test**: Pedir ao sistema a listagem da gramática e conferir que cada não-terminal tem regras cujas probabilidades somam 1; gerar uma música e conferir que a derivação registrada corresponde aos eventos no arquivo.

**Acceptance Scenarios**:

1. **Given** o sistema instalado, **When** o usuário pede a descrição da gramática, **Then** ela é exibida com axioma, conjunto de não-terminais, conjunto de terminais e todas as regras de produção com suas probabilidades (já ajustadas pelos hiperparâmetros informados).
2. **Given** uma música gerada, **When** o usuário consulta a derivação registrada, **Then** ela mostra a escolha feita em cada nível (forma, seções, blocos, compassos, eventos).

---

### User Story 5 - Linha de baixo opcional (Priority: P3)

O usuário pode ativar uma linha de baixo simples que acompanha o bumbo e permanece dentro de uma tonalidade escolhida.

**Why this priority**: Enriquece a audição, mas o enunciado declara explicitamente que não é o foco.

**Independent Test**: Gerar com o baixo ativado e verificar que existe uma trilha de baixo cujas notas coincidem com ataques do bumbo e pertencem à tonalidade escolhida.

**Acceptance Scenarios**:

1. **Given** o baixo ativado e uma tonalidade escolhida, **When** a música é gerada, **Then** existe uma trilha de baixo em canal distinto do 10, com notas apenas da escala da tonalidade, cujos ataques coincidem com ataques do bumbo.
2. **Given** o baixo não ativado, **When** a música é gerada, **Then** o arquivo contém apenas a bateria.

---

### User Story 6 - Ouvir o resultado como áudio (Priority: P3)

O usuário converte o arquivo MIDI gerado em um arquivo de áudio para ouvir e para incluir no repositório como entregável (mínimo de 3 músicas).

**Why this priority**: Necessário para os entregáveis, mas é um passo de pós-processamento sobre o MIDI, que é o artefato principal.

**Independent Test**: Converter um MIDI gerado em áudio e ouvir o resultado de ponta a ponta.

**Acceptance Scenarios**:

1. **Given** um arquivo MIDI gerado e um banco de sons General MIDI disponível, **When** o usuário pede a conversão, **Then** é produzido um arquivo de áudio reproduzível com a mesma duração da música.

---

### Edge Cases

- Quantidade de compassos pedida menor que o mínimo da forma (5 seções × 4 compassos = 20) → a execução é recusada informando o mínimo.
- Quantidade de compassos que não é múltiplo de 4 → a execução é recusada informando que o valor deve ser múltiplo de 4 (ver FR-019).
- Densidade ou frequência de viradas nos extremos (0 e 1) → a música continua respeitando as regras obrigatórias (bumbo no 1, caixa no 2, caixa no 4 fora das viradas, chimbal regular); só os elementos opcionais desaparecem ou saturam.
- Swing no valor mínimo permitido → o swing ainda é perceptível (o swing é obrigatório; não existe valor "reto").
- Humanização que empurraria uma nota para antes do início da música ou para depois do fim do compasso → o deslocamento é limitado para manter a nota dentro do seu compasso e em tempo não negativo.
- Humanização de intensidade que ultrapassaria os limites válidos → a intensidade é limitada à faixa válida.
- Dois eventos da mesma peça na mesma posição da grade → são unificados em um só evento (o de maior intensidade).
- Caminho de saída inválido ou sem permissão de escrita → mensagem de erro clara, sem arquivo parcial (nem MIDI nem arquivo de derivação).
- Semente informada em formato inválido → mensagem de erro clara.

## Requirements *(mandatory)*

### Functional Requirements

**Gramática**

- **FR-001**: O sistema MUST gerar toda a música exclusivamente pela expansão de uma gramática generativa probabilística; nenhum outro método de geração (cadeias de Markov, algoritmos genéticos, aprendizado de máquina) pode ser usado em qualquer decisão musical.
- **FR-002**: A gramática MUST ser definida formalmente com: um axioma, um conjunto explícito de não-terminais, um conjunto explícito de terminais e um conjunto de regras de produção, cada regra com probabilidade associada; para cada não-terminal, as probabilidades de suas regras MUST somar 1.
- **FR-003**: A gramática MUST ser não determinística: ao menos os níveis de seção/bloco, de padrão de compasso e de eventos opcionais MUST ter mais de uma alternativa com probabilidade positiva.
- **FR-004**: O axioma MUST expandir-se na forma da música na ordem intro → verso → refrão → verso → outro.
- **FR-005**: Cada seção MUST expandir-se em um ou mais blocos de 4 ou 8 compassos.
- **FR-006**: Cada seção MUST escolher um groove principal entre ao menos três variações de groove (ex.: via não-terminais indexados pelo groove, mantendo a gramática livre de contexto); cada compasso de seus blocos MUST expandir-se nesse groove principal (com eventos opcionais sorteados por compasso) ou em uma virada. Seções do mesmo tipo (os dois versos) escolhem seu groove de forma independente e podem diferir.
- **FR-007**: A probabilidade de virada MUST ser maior no último compasso de cada bloco do que nos demais compassos do bloco.
- **FR-008**: Cada terminal MUST representar um evento concreto contendo: peça da bateria, posição no compasso em uma grade de 16 subdivisões (0–15), intensidade e, opcionalmente, uma pequena variação de intensidade e/ou de tempo (humanização).
- **FR-009**: O sistema MUST permitir exibir a gramática formal completa (com as probabilidades efetivas após aplicar os hiperparâmetros) em formato legível, adequado para ser transcrito no resumo.
- **FR-010**: O sistema MUST registrar, para cada música gerada, a derivação completa que a produziu (escolha feita em cada nível de expansão) em um arquivo separado legível por máquina, salvo ao lado do MIDI com o mesmo nome-base. O MIDI MUST conter marcadores de seção (eventos de texto/marcador no início de cada seção).

**Restrições de estilo boom bap**

- **FR-011**: Todo compasso MUST ter bumbo no tempo 1 (subdivisão 0) e caixa no tempo 2 (subdivisão 4). Todo compasso que não é de virada MUST ter também caixa no tempo 4 (subdivisão 12). Em compassos de virada, a caixa do tempo 4 MAY ser substituída por eventos da virada; viradas nunca removem o bumbo do tempo 1 nem a caixa do tempo 2.
- **FR-012**: Além do tempo 1, o bumbo MUST cair em posições sincopadas típicas do estilo (por exemplo o "e" do 2 — subdivisão 6 —, a antecipação do 3 — subdivisão 7 —, a antecipação do 1 seguinte — subdivisão 15 —, entre outras definidas na gramática).
- **FR-013**: O chimbal MUST tocar em grade de colcheias ou semicolcheias, com intensidades variadas (acentos nos tempos e contratempos mais fracos), podendo usar chimbal aberto em posições pontuais.
- **FR-014**: O andamento MUST ficar entre 85 e 95 BPM, inclusive, e o compasso MUST ser 4/4.
- **FR-015**: O swing MUST estar sempre presente, com intensidade configurada que nunca é zero. A grade de swing de cada compasso MUST seguir a grade do chimbal desse compasso: se o chimbal toca só em colcheias, as colcheias de contratempo (subdivisões 2, 6, 10, 14) MUST ser atrasadas; se o chimbal toca em semicolcheias, as semicolcheias fracas (subdivisões ímpares) MUST ser atrasadas. O atraso é proporcional à intensidade de swing e se aplica a todas as peças nessas posições.
- **FR-016**: As peças MUST seguir o mapa General MIDI no canal 10: bumbo 36, caixa 38, aro 37, chimbal fechado 42, chimbal aberto 46, prato 49.
- **FR-017**: O prato (49) MUST ser usado com parcimônia, preferencialmente no primeiro tempo de início de seção ou após uma virada.

**Execução, saída e reprodutibilidade**

- **FR-018**: Cada execução MUST produzir um arquivo MIDI padrão que toque em qualquer sintetizador General MIDI.
- **FR-019**: O usuário MUST poder configurar pela linha de comando: semente, andamento (85–95), intensidade do swing (faixa limitada com mínimo acima de zero), densidade de notas (0 a 1), frequência das viradas (0 a 1) e quantidade total de compassos (múltiplo de 4, mínimo 20). Cada parâmetro MUST ter um valor padrão.
- **FR-020**: A densidade MUST atuar alterando as probabilidades das regras que acrescentam bumbos fantasmas/sincopados e semicolcheias no chimbal; a frequência das viradas MUST atuar alterando as probabilidades das regras de virada.
- **FR-021**: Valores fora das faixas permitidas MUST ser recusados com mensagem clara indicando a faixa válida, sem geração de arquivo.
- **FR-022**: Sem semente informada, o sistema MUST sortear uma nova semente a cada execução; a semente usada MUST ser exibida ao usuário.
- **FR-023**: A mesma semente com os mesmos parâmetros MUST produzir exatamente os mesmos eventos musicais.
- **FR-024**: O sistema MUST registrar a semente e todos os hiperparâmetros efetivamente usados tanto no arquivo separado de FR-010 quanto dentro do próprio MIDI (como eventos de texto), de modo que cada um baste sozinho para reproduzir a música.
- **FR-025**: A gramática MUST distribuir a quantidade de compassos pedida entre as cinco seções da forma por meio de não-terminais indexados pelo número de compassos (ex.: `Forma_40 → Intro_4 Verso_12 Refrão_8 Verso_8 Outro_8`), com regras probabilísticas que favorecem intro/outro curtas e verso/refrão maiores; cada seção indexada MUST, por sua vez, dividir-se probabilisticamente em blocos de 4 ou 8 compassos. O total MUST ser exatamente o pedido por construção (só são geradas regras cujas partes somam o índice), sem amostragem por rejeição nem divisão fixa fora da gramática.

**Opcionais**

- **FR-026**: O sistema SHOULD oferecer uma linha de baixo opcional, desativada por padrão, em canal distinto do 10, cujos ataques coincidam com ataques do bumbo e cujas notas pertençam à escala de uma tonalidade escolhida pelo usuário.
- **FR-027**: O sistema SHOULD oferecer uma forma de converter o arquivo MIDI gerado em áudio para audição, usando um banco de sons General MIDI.

### Key Entities

- **Gramática**: axioma, não-terminais, terminais e regras de produção probabilísticas; parametrizada pelos hiperparâmetros (densidade e frequência de viradas alteram probabilidades).
- **Regra de produção**: não-terminal do lado esquerdo, sequência de símbolos do lado direito, probabilidade.
- **Música (Song)**: forma com cinco seções em ordem fixa; tem andamento, semente e hiperparâmetros.
- **Seção**: intro, verso, refrão ou outro; tem um comprimento em compassos (múltiplo de 4, decidido pela gramática) e um groove principal escolhido pela gramática; composta de blocos.
- **Bloco**: 4 ou 8 compassos; o último compasso é candidato preferencial a virada.
- **Compasso**: 16 subdivisões; é um groove ou uma virada; contém eventos.
- **Evento de bateria (terminal)**: peça (nota GM), posição 0–15, intensidade, variação de intensidade e de tempo opcionais.
- **Configuração de execução**: semente, andamento, swing, densidade, frequência de viradas, quantidade de compassos, baixo ligado/desligado, tonalidade.
- **Derivação**: registro das regras escolhidas em cada nível para produzir uma música; salva em arquivo separado legível por máquina junto com semente e hiperparâmetros.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das músicas geradas (verificado em ao menos 100 execuções com sementes distintas e parâmetros variados) respeitam: andamento 85–95, 4/4, bumbo no tempo 1 e caixa no tempo 2 em todos os compassos, caixa no tempo 4 em todos os compassos que não são de virada, chimbal presente em todos os compassos, swing presente, peças apenas do mapa GM listado no canal 10.
- **SC-002**: Em 10 execuções com a mesma configuração e sementes diferentes, ao menos 9 pares de músicas são diferentes entre si (sequências de eventos distintas).
- **SC-003**: Reexecutar com a mesma semente e parâmetros reproduz a música de forma idêntica em 100% das tentativas.
- **SC-004**: Para cada um dos cinco hiperparâmetros, comparar seu valor mínimo com o máximo (mesma semente, demais parâmetros fixos) produz mudança mensurável na direção esperada da métrica correspondente: densidade → notas de bumbo e chimbal por compasso ao menos 30% maiores; viradas → número de compassos de virada maior; swing → atraso médio dos contratempos maior; andamento → duração total menor; compassos → número de compassos igual ao pedido.
- **SC-005**: Uma música padrão (cerca de 40 compassos) é gerada em menos de 5 segundos em um computador pessoal comum.
- **SC-006**: Todo arquivo gerado abre e toca sem erros em ao menos dois reprodutores/sintetizadores MIDI distintos.
- **SC-007**: A definição da gramática exibida pelo sistema pode ser transcrita diretamente para o resumo, e em todos os não-terminais as probabilidades somam 1 (verificado automaticamente).
- **SC-008**: Um ouvinte familiarizado com hip-hop reconhece as músicas geradas como boom bap em uma audição informal das 3 músicas entregues.

## Assumptions

- Usuário principal: o próprio aluno, confortável com linha de comando; não há interface gráfica.
- A forma é fixa (intro, verso, refrão, verso, outro); a variação estrutural vem do comprimento de cada seção e do número e tamanho dos blocos, ambos sorteados pela gramática, não da ordem das seções.
- A quantidade de compassos padrão é 40; mínimo 20 (uma unidade de 4 compassos por seção) e máximo 256. O valor deve ser múltiplo de 4 para caber em blocos de 4/8.
- Andamento padrão: 90 BPM (valor fixo, para que a variação entre execuções venha da gramática e a comparação de parâmetros seja limpa); o usuário pode escolher qualquer valor de 85 a 95.
- Swing é expresso como porcentagem no estilo MPC (proporção entre a primeira e a segunda semicolcheia de cada par), com faixa de 52% a 75% e padrão em torno de 58%; a mesma porcentagem é aplicada ao par de colcheias ou ao par de semicolcheias, conforme a grade de swing do compasso (FR-015).
- Densidade e frequência de viradas são números de 0 a 1, com padrão 0,5; 0 desativa só os elementos opcionais (fantasmas, semicolcheias extras, viradas fora do último compasso), nunca os obrigatórios.
- Viradas atuam principalmente na segunda metade do compasso, preservando o bumbo do tempo 1 e a caixa do tempo 2.
- Humanização: variação de intensidade de poucas unidades e variação de tempo de no máximo alguns milissegundos (pequena frente à duração de uma semicolcheia), sorteadas pela gramática junto com o terminal.
- Tonalidade padrão do baixo: Lá menor (ou outra tonalidade menor), coerente com a estética do estilo; o baixo não é avaliado como foco.
- A conversão para áudio depende de um sintetizador externo e de um banco de sons General MIDI livre instalado na máquina do usuário.
- Os entregáveis acadêmicos (repositório público, README, arquivo de dependências, resumo ISMIR, 3 áudios) são produzidos usando o sistema, mas o resumo em si está fora do escopo do software.

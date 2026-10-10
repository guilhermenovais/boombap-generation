# Research: Gerador de Batidas Boom Bap por Gramática Probabilística

**Feature**: `001-boombap-grammar-generator` | **Data**: 2026-10-05

Cada item resolve uma incógnita do Technical Context do [plan.md](./plan.md) ou uma decisão de projeto que o spec deixou em aberto.

---

## R1. Linguagem e ambiente

- **Decision**: Python ≥ 3.11 (testado no 3.14 da máquina do autor), pacote instalável `boombap` com layout `src/`, dependências em `requirements.txt` (exigido pelo enunciado) espelhadas em `pyproject.toml`.
- **Rationale**: Python é a linguagem das bibliotecas sugeridas pelo enunciado (music21, pretty_midi, mido), o desempenho exigido é trivial (SC-005: < 5 s para ~40 compassos — a expansão produz poucos milhares de símbolos) e o avaliador reproduz com `pip install -r requirements.txt`.
- **Alternatives considered**: nenhuma alternativa séria; Rust/TS adicionariam atrito para o avaliador sem ganho.

## R2. Biblioteca MIDI

- **Decision**: `mido` (única dependência de execução).
- **Rationale**: Controle direto, em ticks, de cada mensagem — necessário para o swing (atraso em ticks), a humanização (±poucos ticks), os meta-eventos de texto/marcador (FR-010, FR-024) e o canal 10 (índice 9). É puro Python e não arrasta numpy.
- **Alternatives considered**:
  - `pretty_midi`: trabalha em segundos e esconde meta-eventos de marcador/texto; depende de numpy. Rejeitado.
  - `music21`: pesado, voltado a notação, baterias GM pouco ergonômicas. Rejeitado.
  - Escrever SMF à mão: possível, mas reinventa VLQ/running status sem benefício acadêmico.

## R3. Representação da gramática (formal e não só "código que sorteia")

- **Decision**: A gramática é um **objeto de dados** (`Grammar` = axioma + não-terminais + terminais + regras `Rule(lhs, rhs, prob)`), montado a partir da tabela de regras do autor (R15) mais as famílias estruturais indexadas geradas pelo código (R4/R5), avaliadas para os hiperparâmetros. Um motor genérico de derivação (`derive`) expande o axioma escolhendo regras pelas probabilidades. Nenhuma decisão musical existe fora das regras (FR-001).
- **Rationale**: Permite (a) listar a gramática formal com probabilidades efetivas (FR-009, US4), (b) validar automaticamente que as probabilidades de cada não-terminal somam 1 (FR-002, SC-007), (c) registrar a derivação como sequência de IDs de regras (FR-010) e (d) separar claramente "o método" (as regras) do "motor", o que facilita escrever o resumo.
- **Alternatives considered**: funções Python aninhadas que chamam `random` diretamente — mais curto, mas a gramática deixa de ser inspecionável e a derivação vira log ad hoc. Rejeitado.

## R4. Não-terminais indexados e enumeração preguiçosa

- **Decision**: Famílias de não-terminais indexados (`Forma_N`, `Corpo_M`, `Verso_k`, `Seção_{k,g,s}` …) cujas regras são produzidas **sob demanda** por geradores de regra (`rules_for(nt)`), com cache. Somente são geradas regras cujas partes somam o índice (FR-025), então o total de compassos sai exato por construção.
- **Decomposição da forma** (mantém o número de regras polinomial pequeno):
  - `Forma_N → Intro_i Corpo_{N−i−o} Outro_o`, com `i, o ∈ {4, 8}` (pesos de `@intro_bars`/`@outro_bars` na tabela).
  - `Corpo_M → Verso_a Refrão_b Verso_c`, com `a + b + c = M`, cada parte múltipla de 4 e ≥ 4. Para N = 256 isso dá no máximo C(59,2) = 1 711 regras — enumerável para exibição.
  - Pesos de `Corpo_M` vêm de uma preferência suave pelas proporções-alvo `@body_share` da tabela, `w = exp(−Σ (parte/M − share)² / (2σ²))` com `σ = @body_sigma` (fração do corpo), normalizados para somar 1. A função de peso é documentada no resumo.
- **Exibição**: `boombap grammar --bars N` lista apenas os não-terminais alcançáveis a partir de `Forma_N` (fechamento transitivo), o que mantém a listagem finita e transcritível; `--max-rules` trunca famílias muito longas com contagem explícita.
- **Alternatives considered**: enumerar todas as composições de N em 5 partes (até ~595 mil regras para N = 256) — explode a listagem; dividir compassos fora da gramática — proibido por FR-025.

## R5. Groove por seção e estado "após virada" sem sair de CFG

- **Decision**: Anotação de estado finito nos índices dos não-terminais:
  - `Verso_k → SeçãoV_{k,g,início}` para g ∈ {G1, G2, G3, …} (escolha do groove; FR-006). Seções de mesmo tipo expandem independentemente.
  - `Seção_{k,g,s} → Bloco4_{g,s,f} Seção_{k−4,g,f} | Bloco8_{g,s,f} Seção_{k−8,g,f}` com `s, f ∈ {início, normal, pós-virada}`; o caso base é `Seção_{0,g,·} → ε`.
  - O índice `f` codifica se o bloco **termina** em virada; isso propaga ao primeiro compasso do bloco seguinte e permite o prato "após uma virada" (FR-017) sem sensibilidade a contexto.
- **Rationale**: Mantém a gramática livre de contexto (como pede o spec, FR-006) e ainda expressa dependências entre compassos vizinhos. É a técnica clássica de "refinamento de símbolos" (gramáticas com atributos finitos compiladas em CFG).
- **Alternatives considered**: gramática sensível a contexto ou pós-processamento que insere pratos — rejeitados (complexidade formal / violaria FR-001).

## R6. Probabilidades em função dos hiperparâmetros

- **Decision**: As probabilidades são **expressões em `density` e `fills`** escritas pelo autor na tabela de regras (R15, [contracts/rule-table.md](./contracts/rule-table.md)). O código não fixa nenhum valor musical. Ele apenas avalia as expressões e verifica as exigências do spec:
  - `@fill_end > @fill_mid` em toda a grade de parâmetros (FR-007);
  - com `fills = 0`, só as viradas fora do último compasso podem desaparecer (Assumptions). Isso é um aviso do `--check`, não um erro;
  - para SC-004 as expressões devem ser **monotônicas não decrescentes** no parâmetro, e com a alternativa "presente"/"virada" listada primeiro. O `--check` testa as duas coisas e avisa se falharem.
- **Rationale**: Mantém FR-020 (os parâmetros agem pelas regras) e deixa as escolhas de estilo inteiramente com o autor.

## R7. Aleatoriedade reprodutível e "números aleatórios comuns"

- **Decision**: Cada decisão de derivação usa um uniforme `u ∈ [0,1)` derivado de `sha256(seed ‖ caminho_do_nó)` (caminho = sequência de índices filhos desde o axioma, mais o nome do não-terminal), e escolhe a regra por CDF inversa com as alternativas em ordem fixa ("opcional presente" primeiro, "virada" primeiro etc.).
- **Rationale**:
  1. **Reprodutibilidade** (FR-023, SC-003): não depende do `hash()` de Python (salgado por processo) nem da ordem de consumo de um stream global.
  2. **Comparação limpa de hiperparâmetros** (SC-004): com a mesma semente, a mesma decisão recebe o mesmo `u` qualquer que seja o parâmetro; como `P(opcional)` cresce monotonicamente com δ, cada evento opcional presente em δ baixo continua presente em δ alto — a métrica cresce de forma garantida, não só "em média". Idem para viradas com φ. Swing e andamento não afetam a derivação.
- **Alternatives considered**: um único `random.Random(seed)` — reprodutível, mas qualquer mudança de probabilidade desalinha todo o resto do stream e a comparação "mesma semente" vira duas músicas sem relação. Rejeitado.
- **Semente**: inteiro não negativo < 2⁶³; sem semente, `secrets.randbits(32)` (FR-022). Entrada não inteira → erro claro.

## R8. Swing (MPC) e humanização

- **Decision**:
  - PPQ = 480 (semicolcheia = 120 ticks).
  - Swing `S` ∈ [52, 75] % (padrão 58). Atraso das posições fracas: `d = (S/100 − 0,5) · 2 · L`, com `L = 120` (grade de semicolcheia, posições ímpares) ou `L = 240` (grade de colcheia, posições 2, 6, 10, 14). A grade de cada compasso é determinada pelo terminal `grid8`/`grid16` que a regra de chimbal emite e registrada na derivação (FR-015).
  - Em S = 52 %: 4,8 ticks em semicolcheia / 9,6 ticks em colcheia (~7–13 ms a 90 BPM), ainda perceptível; não há valor "reto".
  - Humanização: produzida pela gramática por meio dos não-terminais `HumV → dv±N` e `HumT → dt±N`, que o autor define na tabela. O motor os expande após cada terminal de bateria e só impõe |dt| ≤ 10 ticks. A realização limita velocidade a 1–127 e o tempo ao intervalo do próprio compasso e ≥ 0.
- **Rationale**: É a definição usual de swing de MPC/SP-1200 (razão entre as duas notas do par). O mapeamento terminal → tempo é determinístico (realização dos terminais), não uma decisão musical, e por isso não fere FR-001.

## R9. Estrutura do MIDI

- **Decision**: SMF tipo 1, PPQ 480.
  - Trilha 0 (condutor): `set_tempo`, `time_signature 4/4`, `text` com semente e hiperparâmetros (`boombap seed=… bpm=… swing=… …`), `marker` no início de cada seção.
  - Trilha 1: bateria, canal 10 (índice 9), notas de 60 ticks; deduplicação por (peça, posição) mantendo a maior velocidade antes de aplicar swing/humanização.
  - Trilha 2 (só com `--bass`): baixo no canal 1 (índice 0), programa GM 34 (Electric Bass pick) ou 33.
- **Rationale**: Atende FR-010, FR-016, FR-018, FR-024 e toca em qualquer sintetizador GM (SC-006).

## R10. Linha de baixo (opcional)

- **Decision**: Quando ativada, cada terminal de bumbo ganha um nó de baixo. O bumbo do tempo 1 expande `BassFirst` e os demais expandem `BassDeg`. Os dois não-terminais são definidos na tabela pelo autor, com terminais `deg1 deg3 deg4 deg5 deg7`. As notas são mapeadas para a escala menor natural da tonalidade (`--key`, padrão `Am`), oitava 2. Duração até o próximo ataque de bumbo, limitada a uma semínima.
- **Rationale**: Mantém o baixo dentro da gramática (FR-001), ataques coincidem com bumbo por construção (FR-026) e não perturba a derivação da bateria (os `u` dos nós de bateria não mudam, R7).

## R11. Conversão para áudio

- **Decision**: Subcomando `boombap render` que chama o binário `fluidsynth` via `subprocess` (`fluidsynth -ni -F out.wav -r 44100 <sf2> <mid>`); o soundfont é passado por `--soundfont` ou pela variável `BOOMBAP_SOUNDFONT`. README recomenda um SF2 GM livre (FluidR3_GM, pacote `soundfont-fluid` no Arch/Manjaro, ou GeneralUser GS).
- **Rationale**: FluidSynth 2.6 já está instalado na máquina do autor; evita `pyfluidsynth` (binding frágil). Áudio é só pós-processamento (FR-027).
- **Observação**: nenhum soundfont está instalado hoje (`/usr/share/soundfonts` ausente) — é pré-requisito no quickstart.

## R12. Escrita atômica e erros

- **Decision**: Validar todos os parâmetros antes de qualquer geração (FR-021). Gerar MIDI e JSON em memória; gravar em arquivos temporários no diretório de destino e publicar com `os.replace`; em qualquer erro, remover temporários. Código de saída 2 para erro de uso (argparse), 1 para erro de E/S.
- **Rationale**: Edge case "sem arquivo parcial (nem MIDI nem arquivo de derivação)".

## R13. Testes

- **Decision**: `pytest`. Unidade (gramática, soma de probabilidades, swing, clamps, dedup, validação), contrato (CLI e esquema JSON da derivação), integração/propriedade (100 sementes × parâmetros aleatórios verificando SC-001; mesma semente → bytes iguais, SC-003; min vs. max por hiperparâmetro, SC-004; tempo < 5 s, SC-005). Um subcomando `boombap analyze` calcula as métricas a partir do MIDI e é reutilizado pelos testes e pela seção de resultados do resumo.
- **Alternatives considered**: `hypothesis` — útil, mas um laço sobre sementes já cobre SC-001 sem dependência extra.

## R14. Restrição de uso de IA (enunciado)

- **Finding**: O enunciado permite IA como apoio, exige declarar o uso no README com links para as conversas, e **proíbe gerar por IA, na íntegra, a implementação do método** (a gramática) e o resumo.
- **Decision**: O conteúdo musical da gramática fica num arquivo de texto, a **tabela de regras** (`src/boombap/data/boombap.rules`, R15). Ela tem grooves, chimbal, opcionais, viradas, prato, humanização, baixo e todas as probabilidades, e **é escrita pelo aluno**. Ele pode usar uma IA que o entreviste e só formate as respostas, mas as escolhas musicais são dele. A IA implementa a infraestrutura: o carregador e validador da tabela, as famílias estruturais indexadas, o motor de derivação, MIDI, CLI, análise, render, testes e README. O README terá uma seção "Uso de IA" que separa as duas autorias e traz os links das conversas. `/speckit-tasks` e `/speckit-implement` **não devem gerar o conteúdo de `boombap.rules`**. A tarefa correspondente fica marcada como manual, do aluno.

## R15. Tabela de regras e o que o código gera

- **Decision**: Formato textual `LHS -> RHS [prob] | …` com parâmetros `@nome = expr`, especificado em [contracts/rule-table.md](./contracts/rule-table.md). O carregador (`grammar/table.py`) faz o parse, avalia as expressões para a `RunConfig` e devolve `Rule`s comuns. As famílias indexadas de R4 e R5 (`Música_N`, `Forma_N`, `Corpo_M`, `Seção_{k,g,s}`, `Bloco4/8`, `Compasso_{g,pos,s}`) são geradas pelo código. Seus pesos vêm dos parâmetros `@intro_bars`, `@outro_bars`, `@body_share`, `@body_sigma`, `@block_size`, `@fill_end`, `@fill_mid`, `@crash_*` e `@groove_weights` da tabela. `Compasso_{…}` expande para os ganchos `Groove_X`/`Fill_X` da tabela.
- **Validação estática**: análise de ponto fixo "terminais garantidos em toda expansão", em que `must(A)` é a interseção, sobre as regras de A, da união dos `must` do lado direito. Ela prova FR-011/012/013 para *qualquer* derivação, não só para as amostradas. Somas = 1 e monotonicidade são checadas numa grade 5 × 5 de (`density`, `fills`).
- **Testes**: usam uma tabela-fixture **sintética e mínima** (`tests/fixtures/minimal.rules`), que só exercita o formato e os invariantes, sem pretensão musical. Os testes de estilo (SC-001, SC-004) rodam também contra a tabela real quando ela existir.
- **Alternatives considered**: regras em código Python (descartado: mistura autoria e infraestrutura) e YAML/JSON (mais verboso e menos parecido com a notação formal que vai para o resumo).

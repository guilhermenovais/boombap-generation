---

description: "Lista de tarefas para implementar o gerador boom bap por gramática probabilística"
---

# Tasks: Gerador de Batidas Boom Bap por Gramática Probabilística

**Input**: Documentos de design em `/specs/001-boombap-grammar-generator/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md, rule-table.md, midi-output.md, derivation.schema.json), quickstart.md

**Tests**: INCLUÍDOS. O plano (research R13) e os critérios de sucesso (SC-001, SC-003, SC-004, SC-005, SC-007) pedem verificação automática com `pytest`. Em cada história, os testes vêm antes da implementação e devem falhar até ela ser feita.

**Organization**: As tarefas estão agrupadas por história de usuário, para que cada uma possa ser implementada e testada de forma independente.

## ⚠️ Regra de autoria (research R14, enunciado)

`src/boombap/data/boombap.rules` é **de autoria do aluno** e já existe (grooves `Classic`, `Lazy`, `Bounce`). Nenhuma tarefa deste arquivo pode criar, reescrever ou "corrigir" o conteúdo musical dessa tabela (eventos, velocidades, probabilidades). Se a validação apontar erro nela, a tarefa termina **reportando o erro ao aluno**. Tarefas marcadas **[MANUAL — aluno]** são feitas pelo aluno, não pelo implementador. A tabela sintética `tests/fixtures/minimal.rules` é só para testes de formato e pode ser escrita pelo implementador.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: história de usuário a que a tarefa pertence (US1…US6)
- Caminhos relativos à raiz do repositório (`/home/guilherme/Documents/ia-na-musica/tp1`)

## Path Conventions

Projeto único, layout `src/`: pacote em `src/boombap/`, testes em `tests/` (ver plan.md, "Project Structure").

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialização do projeto e estrutura básica

- [X] T001 Criar `pyproject.toml` na raiz: build-backend setuptools, `name = "boombap"`, `requires-python = ">=3.11"`, `dependencies = ["mido>=1.3"]`, `[project.optional-dependencies] test = ["pytest>=8", "jsonschema>=4"]`, `[project.scripts] boombap = "boombap.cli:main"`, layout `src/` (`[tool.setuptools.packages.find] where = ["src"]`), `package-data` incluindo `boombap/data/*.rules`, versão dinâmica lida de `boombap.__version__`, e `[tool.pytest.ini_options] testpaths = ["tests"]`
- [X] T002 [P] Criar `requirements.txt` na raiz contendo apenas `mido>=1.3` (exigido pelo enunciado; dependências de teste ficam no extra `test` do pyproject)
- [X] T003 [P] Criar o esqueleto do pacote: `src/boombap/__init__.py` (`__version__ = "0.1.0"`), `src/boombap/__main__.py` (chama `boombap.cli.main()` e sai com o código retornado), `src/boombap/grammar/__init__.py` vazio, e módulos vazios com docstring de uma linha: `src/boombap/cli.py`, `config.py`, `derive.py`, `sections.py`, `realize.py`, `midi_io.py`, `output.py`, `analyze.py`, `render.py`, `grammar/core.py`, `grammar/table.py`, `grammar/structure.py`, `grammar/format.py`. **Não tocar** em `src/boombap/data/boombap.rules`
- [X] T004 [P] Criar `.gitignore` na raiz ignorando `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/` e `out/` (não ignorar `samples/`, que é entregável)
- [X] T005 [P] Criar `tests/fixtures/minimal.rules`: tabela sintética mínima, sem pretensão musical, no formato de `contracts/rule-table.md`, que passe em toda a validação do §3. Deve ter `@grooves = A B C`; todos os parâmetros obrigatórios (`@fill_end`, `@fill_mid` com `@fill_end > @fill_mid` em todo `fills ∈ [0,1]`, `@intro_bars`, `@outro_bars`, `@body_share`, `@body_sigma`, `@block_size`, `@crash_section`, `@crash_intro`, `@crash_after_fill`); `Groove_X` e `Fill_X` para cada X; `HumV`, `HumT`, `BassFirst`, `BassDeg`; ao menos uma regra opcional com prob. dependente de `density` (alternativa "presente" primeiro) e uma com `[rest]`, uma com alternativas sem `[ ]`, um comentário de fim de linha `#` e uma continuação de linha iniciada por `|`
- [X] T006 [P] Criar fixtures inválidas em `tests/fixtures/invalid/`, uma violação por arquivo, cada uma derivada de `minimal.rules`: `missing_snare12.rules` (um `Groove_X` sem `snare@12` garantido), `missing_kick0_fill.rules` (`Fill_X` sem `kick@0`), `no_sync_kick.rules` (`Groove_X` sem bumbo em posição ≠ 0), `two_grids.rules` (expansão que emite `grid8` e `grid16`), `no_hats.rules` (`Groove_X` sem `hhc`/`hho` garantido), `sum_over_one.rules` (probabilidades somando > 1), `undefined_nt.rules` (não-terminal referenciado e não definido), `fill_order.rules` (`@fill_end <= @fill_mid` em algum `fills`), `recursion.rules` (ciclo de não-terminais), `two_grooves.rules` (`@grooves` com 2 nomes), `dt_too_big.rules` (`dt+11`), `missing_hook.rules` (sem `HumT`)
- [X] T007 Criar `tests/conftest.py` com fixtures: `minimal_rules` (caminho de `tests/fixtures/minimal.rules`), `real_rules` (caminho de `src/boombap/data/boombap.rules`, com `pytest.skip` se ausente), `out_dir` (`tmp_path / "out"` criado), e helper `run_cli(*args) -> (exit_code, stdout, stderr)` que chama `boombap.cli.main(list(args))` capturando stdout/stderr com `capsys`/`contextlib.redirect_*`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Configuração, núcleo formal da gramática, carregador/validador da tabela, famílias estruturais indexadas e motor de derivação. Tudo o que as histórias usam.

**⚠️ CRITICAL**: Nenhuma história pode começar antes desta fase terminar.

### Tests for Foundational ⚠️

- [X] T008 [P] Testes de `RunConfig` em `tests/unit/test_config.py`: padrões (`bpm=90`, `swing=58.0`, `density=0.5`, `fills=0.5`, `bars=40`, `bass=False`, `key="Am"`); aceita limites (85, 95, 52, 75, 0, 1, 20, 256); recusa `bpm` 84/96/120, `swing` 51.9/75.1, `density`/`fills` < 0 ou > 1, `bars` 16/22/260, `seed` -1/`2**63`/`"abc"`, `key` `"A"`/`"Hm"`/`"am"`; mensagens exatamente no formato de `contracts/cli.md` (ex.: `--bpm must be between 85 and 95 (got 120)`); semente ausente gera inteiro em `[0, 2**32)`
- [X] T009 [P] Testes do núcleo em `tests/unit/test_core.py`: igualdade/hash de `NonTerminal` por `(name, index)`; `str(NonTerminal("Seção", (12, "G2", "início")))` == `"Seção(12,G2,início)"`; `Rule` recusa `prob <= 0` ou `> 1`; `Grammar.validate()` detecta soma ≠ 1 (tolerância 1e-9) e não-terminal alcançável sem regras; `nonterminals()`/`terminals()` retornam só o alcançável a partir do axioma
- [X] T010 [P] Testes do parser em `tests/unit/test_table_parser.py`: carrega `minimal.rules` e `src/boombap/data/boombap.rules` sem erro; `[rest]` = 1 − soma das demais; alternativas sem `[ ]` dividem igualmente o resto; `ε`; comentário de fim de linha; continuação por `|`; terminais `kick@7:88`, `grid16`, `dv+0`, `dt-6`, `deg5`; expressões com `density`, `fills`, `min`, `max`, parênteses; o avaliador **recusa** qualquer outro nome, atributo ou chamada (ex.: `__import__('os')`) com `TableError` contendo arquivo e linha
- [X] T011 [P] Testes da validação estática em `tests/unit/test_table_check.py`: `minimal.rules` e `boombap.rules` passam (sem erros); cada arquivo de `tests/fixtures/invalid/` produz exatamente o erro esperado, com `arquivo:linha` correto; aviso (não erro) quando a prob. da primeira alternativa de uma regra opcional decresce com `density` ou `fills`
- [X] T012 [P] Testes das famílias indexadas em `tests/unit/test_structure.py` (usando `minimal.rules`): para todo `N ∈ {20, 24, …, 256}`, toda regra de `Forma_N`, `Corpo_M` e `Seção_{k,…}` cobre exatamente o índice (FR-025) e cada parte de `Corpo_M` é múltiplo de 4 e ≥ 4; somas = 1 em todos os não-terminais alcançáveis de `Música_N` para `density, fills ∈ {0, 0.5, 1}`; `Corpo_248` (N=256, intro=outro=4) tem ≤ 1 711 regras; `Seção` escolhe entre ≥ 3 grooves; a prob. de virada no fim do bloco é > a do meio para `fills ∈ {0, 0.25, 0.5, 0.75, 1}` (FR-007)
- [X] T013 [P] Testes do motor em `tests/unit/test_derive.py` (usando `minimal.rules`): mesma `(seed, config)` → árvore idêntica; todo `u ∈ [0, 1)`; derivação termina para 20 sementes; `log_prob` = soma de `ln(prob)`; **monotonicidade (R7)**: com mesma semente, o conjunto de terminais opcionais presentes com `density=0` está contido no de `density=1`, e o número de compassos de virada com `fills=0` ≤ com `fills=1`; cada terminal de bateria é seguido por expansões de `HumV` e `HumT`

### Implementation for Foundational

- [X] T014 [P] Implementar `src/boombap/config.py`: `@dataclass(frozen=True) RunConfig(seed: int, bpm: int, swing: float, density: float, fills: float, bars: int, bass: bool, key: str)` e `ConfigError(ValueError)`. `RunConfig.create(seed=None, bpm=90, swing=58.0, density=0.5, fills=0.5, bars=40, bass=False, key="Am")` valida **antes de qualquer geração** (FR-021) e, se `seed is None`, usa `secrets.randbits(32)` (FR-022). Regras (data-model.md): `0 ≤ seed < 2⁶³` (aceita `str` e converte; não inteiro → erro), `bpm` int 85–95, `swing` 52–75, `density` e `fills` 0–1, `bars` múltiplo de 4 entre 20 e 256, `key` casa `^[A-G][#b]?m$`. Mensagens exatas: `--bpm must be between 85 and 95 (got 120)`, `--bars must be a multiple of 4 between 20 and 256 (got 22)`, `--seed must be a non-negative integer below 2^63 (got 'abc')`, e análogas para `--swing`, `--density`, `--fills`, `--key`
- [X] T015 [P] Implementar `src/boombap/grammar/core.py` (genérico, sem nenhum valor musical): `NonTerminal(name: str, index: tuple)` frozen e hashable, `__str__` no formato `Nome(i1,i2,…)` ou `Nome` sem índice; terminais frozen: `DrumHit(piece: str, pos: int, vel: int)` com `piece ∈ {kick, snare, rim, hhc, hho, crash}` → GM 36/38/37/42/46/49 (FR-016), `pos` 0–15, `vel` 1–127, `__str__` = `kick@6:88`; `Grid(n: 8|16)` (`grid8`/`grid16`); `HumDv(n: int)` (`dv+3`); `HumDt(n: int)` com `|n| ≤ 10` (`dt-2`); `Degree(n ∈ {1,3,4,5,7})` (`deg5`); `SectionMark(kind ∈ {intro, verso, refrão, outro})` (`⟨seção:verso⟩`); `EPSILON`. `Rule(id: str, lhs: NonTerminal, rhs: tuple, prob: float)` com `0 < prob ≤ 1`. `Grammar(axiom, rule_provider, source)` com `rules_for(nt)` memorizado (R4), `nonterminals()`/`terminals()` por fechamento transitivo a partir do axioma (ordem determinística: BFS na ordem dos lados direitos), `validate()` → lista de violações (soma por LHS = 1 com tolerância 1e-9; todo NT alcançável tem ≥ 1 regra)
- [X] T016 Implementar o parser em `src/boombap/grammar/table.py` (depende de T015): lê UTF-8; `#` inicia comentário em qualquer ponto da linha; linhas em branco ignoradas; linha iniciada por `|` (após espaços) continua o LHS anterior; `@nome = valor` com as formas de `contracts/rule-table.md` §1 (lista de nomes, expressão, mapa `4:p 8:p`/`X:p`, lista de 3 números); regra `LHS -> alt | alt …`, com `LHS` casando `[A-Za-z_][A-Za-z0-9_]*`, `[expr]` ao fim de cada alternativa, `[rest]`, alternativas sem `[ ]` dividindo igualmente o resto, `ε`. Terminais reconhecidos: `kick|snare|rim|hhc|hho|crash@P:V`, `grid8`, `grid16`, `dv[+-]N`, `dt[+-]N`, `deg1|3|4|5|7`; qualquer outro identificador é não-terminal. Avaliador de expressões **seguro via `ast`** (só números, `density`, `fills`, `+ - * /`, unário, parênteses, `min`, `max`; nunca `eval`). Produz `RuleTable` (parâmetros e alternativas ainda não avaliados, com número de linha) e `RuleTable.evaluate(density, fills) -> dict[NonTerminal, list[Rule]]` com ids estáveis `R.<LHS>.<i>` (i = índice da alternativa) e sem regras de prob. 0. Erros: `TableError(path, line, msg)` com `str` = `<arquivo>:<linha>: <msg>`. Também expõe `sha256` dos bytes do arquivo
- [X] T017 Implementar a validação estática em `src/boombap/grammar/table.py` como `check_table(table, bass: bool) -> (errors: list[TableError], warnings: list[TableError])` (depende de T016), percorrendo `density, fills ∈ {0, 0.25, 0.5, 0.75, 1}` (`contracts/rule-table.md` §3): (1) probs em [0,1] e soma = 1 por LHS; (2) `@fill_end > @fill_mid`; (3) todo NT referenciado definido; ganchos `Groove_X`/`Fill_X` para cada X de `@grooves`, `HumV`, `HumT` e, se `bass`, `BassFirst`/`BassDeg`; ciclo no grafo de referências = erro "recursão infinita"; (4) análise de ponto fixo `must(A) = ⋂_{regras de A} ⋃_{símbolos do RHS} must(símbolo)` (considerando só regras com prob. > 0 no ponto da grade) provando: todo `Groove_X` garante `kick@0`, `snare@4`, `snare@12` e ao menos um `kick` em posição ≠ 0 (garantido = existe em toda expansão; aceitar "algum kick@p≠0 garantido" calculando `must` sobre o predicado), todo `Fill_X` garante `kick@0` e `snare@4`; contagem mín./máx. de terminais `grid*` por expansão de `Groove_X`/`Fill_X` igual a exatamente 1, e ao menos um `hhc`/`hho` garantido; (5) `@grooves` com ≥ 3 nomes e ao menos um NT com ≥ 2 alternativas de prob. > 0 em algum ponto da grade. `dt` com `|N| > 10`, `pos` fora de 0–15 ou `vel` fora de 1–127 = erro. Avisos: prob. da **primeira** alternativa de uma regra decresce em `density` ou `fills` (monotonicidade, R6) e `@fill_end`/`@fill_mid` com `fills=0` deixando viradas fora do fim do bloco > 0. Cada erro com a linha da regra/parâmetro ofensor
- [X] T018 Implementar as famílias indexadas em `src/boombap/grammar/structure.py` (depende de T015, T016), como provedor de regras sob demanda, **sem nenhum valor musical no código**: todos os pesos vêm dos `@parâmetros` avaliados. Famílias (data-model.md, research R4/R5):
  - `Música(N) → Forma(N)` (prob. 1).
  - `Forma(N) → Intro(i) Corpo(N−i−o) Outro(o)` para `i, o ∈ {4, 8}` com `N−i−o ≥ 12`, peso `@intro_bars[i]·@outro_bars[o]`, renormalizado entre as combinações viáveis (para N=20 só `i=o=4`). Id `R.forma.<N>.<i>-<o>`.
  - `Corpo(M) → Verso(a) Refrão(b) Verso(c)` para todo `a+b+c = M`, partes múltiplas de 4 e ≥ 4, peso `exp(−Σ (parte/M − share)² / (2σ²))` com `share = @body_share`, `σ = @body_sigma`, normalizado. Id `R.corpo.<M>.<a>-<b>-<c>`.
  - `Intro(k)|Verso(k)|Refrão(k)|Outro(k) → ⟨seção:tipo⟩ Seção(k, g, início_<tipo>)` para cada groove `g` de `@grooves`, peso `@groove_weights` (uniforme se ausente).
  - Seção com estado `s ∈ {início_intro, início_seção, pós_virada, normal}`: `Seção(k,g,s) → Bloco4(g,s) FimBloco(k−4,g) | Bloco8(g,s) FimBloco(k−8,g)` com pesos `@block_size` entre os tamanhos que cabem (só 4 se `k < 8`); `Bloco4(g,s)` = `Compasso(g,primeiro,s)` + 2× `Compasso(g,meio)`; `Bloco8(g,s)` = `Compasso(g,primeiro,s)` + 6× `Compasso(g,meio)` (o último compasso do bloco fica em `FimBloco`).
  - **A decisão de virada do último compasso fica num nó próprio** para que seu `u` não dependa do tamanho do bloco (R7): `FimBloco(k',g) → Compasso(g,fim,virada) Seção(k',g,pós_virada) [@fill_end] | Compasso(g,fim,groove) Seção(k',g,normal) [rest]`, com a alternativa de virada listada primeiro; `Seção(0,g,·) → ε`.
  - `Compasso(g,primeiro|meio,s) → Prato(ctx) Fill_g [@fill_mid] | Prato(ctx) Groove_g [rest]`; `Compasso(g,fim,virada) → Prato(nenhum) Fill_g`; `Compasso(g,fim,groove) → Prato(nenhum) Groove_g`. **Todo `Compasso` tem RHS com a mesma forma (2 símbolos)** para manter os índices de filhos alinhados entre estados.
  - `Prato(ctx)` com `ctx ∈ {intro, seção, pós_virada, nenhum}` derivado de `s` (`início_intro`→intro, `início_seção`→seção, `pós_virada`→pós_virada, demais→nenhum): `Prato(c) → crash@0:V [@crash_<c>] | ε [rest]`, e `Prato(nenhum) → ε`. A velocidade `V` vem do parâmetro opcional `@crash_velocity` da tabela (padrão 110 se ausente); acrescentar essa linha à tabela do §1 de `specs/001-boombap-grammar-generator/contracts/rule-table.md`.
  - Regras de prob. 0 não são emitidas; ids estáveis e legíveis (ex.: `R.secao.12.Classic.normal.8`, `R.fimbloco.virada`).
- [X] T019 Implementar `build_grammar(config: RunConfig, rules_path: Path | None) -> Grammar` em `src/boombap/grammar/__init__.py` (depende de T016–T018): carrega a tabela (padrão: `importlib.resources.files("boombap") / "data" / "boombap.rules"`), roda `check_table(table, bass=config.bass)` e levanta o primeiro `TableError` se houver erro, avalia as regras da tabela para `(config.density, config.fills)` e junta com o provedor de `structure.py`; axioma `Música(config.bars)`; guarda `rules_sha256`
- [X] T020 Implementar o motor em `src/boombap/derive.py` (depende de T015, T019): `DerivationNode(symbol: str, rule: str, prob: float, u: float, children: list[DerivationNode | TerminalRef])` e `Derivation(seed, config, rules_sha256, grammar_version, log_prob, tree, terminals)`. `derive(grammar, seed) -> Derivation` expande em profundidade, da esquerda para a direita. Para cada NT, `u = int.from_bytes(sha256(f"{seed}|{path}".encode()).digest()[:8], "big") / 2**64`, onde `path` é a sequência de índices de filho desde a raiz unida por `/` (**sem** os índices de estado do NT, para que mudar o estado pós-virada não embaralhe os `u` seguintes); a regra é escolhida por CDF inversa sobre `rules_for(nt)` na ordem da tabela. Após cada `DrumHit` produzido, o motor expande `HumV` e `HumT` com caminhos `"<path do terminal>v"` e `"<path do terminal>t"` (fora da numeração de filhos) e anexa os nós como irmãos logo após o terminal. `log_prob` = Σ `ln(prob)`. Sem recursão Python profunda (usar pilha explícita ou garantir profundidade ≤ ~300 para N=256)
- [ ] T021 [MANUAL — aluno] Rodar `python -c "from boombap.grammar.table import load_table, check_table; t=load_table('src/boombap/data/boombap.rules'); e,w=check_table(t, bass=True); print(*e, *w, sep='\n')"` e, se houver **erros** na tabela do aluno, o aluno corrige `src/boombap/data/boombap.rules`. O implementador apenas executa e reporta; **não edita** o conteúdo da tabela (R14)

**Checkpoint**: `pytest tests/unit` passa; `build_grammar` + `derive` produzem uma árvore completa para `minimal.rules` e para `boombap.rules`.

---

## Phase 3: User Story 1 - Gerar uma batida boom bap completa com um comando (Priority: P1) 🎯 MVP

**Goal**: `boombap generate -o PATH` cria `PATH.mid` e `PATH.json` com uma música boom bap completa (intro → verso → refrão → verso → outro, blocos de 4/8, swing, GM canal 10) e imprime a semente.

**Independent Test**: `boombap generate -o out/demo && boombap analyze out/demo.mid` → `style_violations: []`, 5 seções na ordem, `bars: 40`, bpm 90, 4/4; o arquivo toca em um sintetizador GM.

### Tests for User Story 1 ⚠️

- [X] T022 [P] [US1] Teste de contrato do layout MIDI em `tests/contract/test_midi_layout.py` (para `minimal.rules` e `boombap.rules`, 5 sementes): SMF tipo 1, PPQ 480, 2 trilhas sem `--bass`; trilha 0 com `track_name "boombap"`, exatamente um `set_tempo`, `time_signature` 4/4, um `text` iniciado por `boombap v`, 5 `marker` na ordem `intro, verso, refrão, verso, outro`, um `cue_marker` `grid8`/`grid16` por compasso, `end_of_track` em `bars·1920`; trilha 1 `drums` só canal 9 e notas ∈ {36, 37, 38, 42, 46, 49}; propriedades 1–4 de `contracts/midi-output.md`
- [X] T023 [P] [US1] Teste de integração SC-001 em `tests/integration/test_style_100_seeds.py`: 100 sementes (0–99) com parâmetros sorteados por `random.Random(1234)` dentro das faixas válidas (`bars` múltiplo de 4 em 20–96 para manter o tempo baixo), usando `boombap.rules` (skip se ausente) e também `minimal.rules`; para cada música, `analyze(...)["style_violations"] == []`, seções na ordem certa, cada seção formada por blocos de 4 ou 8 (via `.json`), total de compassos = `bars`
- [X] T024 [P] [US1] Teste de contrato do CLI `generate` em `tests/contract/test_cli_generate.py`: sem opções além de `-o` → exit 0, stdout com as 5 linhas do formato de `contracts/cli.md` (`seed: <int>`, linha de parâmetros, `form: intro(i) verso(a) refrão(b) verso(c) outro(o)`, `wrote: <...>.mid`, `wrote: <...>.json`); sufixo `.mid` acrescentado se ausente e não duplicado se presente; diretório pai inexistente ou sem permissão → exit 1, `error: cannot write to '<path>': <motivo>` em stderr e **nenhum** `.mid`/`.json`/temporário criado; `--rules tests/fixtures/invalid/missing_snare12.rules` → exit 1, mensagem `error: <arquivo>:<linha>: …`, nenhum arquivo

### Implementation for User Story 1

- [X] T025 [P] [US1] Implementar `src/boombap/sections.py`: `extract(derivation) -> list[Section]` percorrendo a árvore. `Section(kind, start_bar, n_bars, groove, blocks)`, `Block(size ∈ {4, 8}, bars)`, `Bar(index global, kind ∈ {"groove", "fill"}, hat_grid ∈ {8, 16}, events: list[DrumEvent], is_block_end)`, `DrumEvent(piece, pos, velocity, dv, dt)`. O tipo do compasso vem de qual gancho (`Groove_*`/`Fill_*`) o `Compasso` expandiu; `hat_grid` vem do único terminal `grid*` do compasso; `dv`/`dt` vêm dos nós `HumV`/`HumT` irmãos de cada terminal; o prato de `Prato(...)` entra nos eventos do compasso
- [X] T026 [P] [US1] Implementar `src/boombap/realize.py` (data-model.md "TimedNote"): constantes `PPQ = 480`, `STEP = 120`, `BAR = 1920`; `swing_delay(pos, hat_grid, swing) = round((swing/100 − 0.5)·2·120)` se `hat_grid == 16` e `pos` ímpar, `round((swing/100 − 0.5)·2·240)` se `hat_grid == 8` e `pos ∈ {2, 6, 10, 14}`, 0 nos demais; `velocity = clamp(vel + dv, 1, 127)`; **dedup** por `(piece, pos)` no compasso mantendo a maior velocity (empate: o primeiro) antes de aplicar tempo; `tick_on = bar·1920 + pos·120 + swing_delay + dt`, limitado a `[bar·1920, bar·1920 + 1919]` e ≥ 0; `tick_off = min(tick_on + 60, (bar+1)·1920)`; saída `TimedNote(tick_on, tick_off, channel=9, note, velocity)` ordenada por `(tick_on, note)`
- [X] T027 [US1] Implementar a escrita em `src/boombap/midi_io.py` (depende de T026), conforme `contracts/midi-output.md`: `build_midi(config, sections, notes, version) -> mido.MidiFile` tipo 1, `ticks_per_beat=480`. Trilha 0: `track_name "boombap"`, `set_tempo(bpm2tempo(bpm))`, `time_signature(4, 4)`, `text` `boombap v<versão> seed=<seed> bpm=<bpm> swing=<swing> density=<δ> fills=<φ> bars=<N> bass=<on|off> key=<key>` (floats com `repr` estável, ex.: `58.0`), `marker` com o nome da seção no início de cada seção, `text "fill"` no início de cada compasso de virada, `cue_marker "grid8"|"grid16"` no início de cada compasso, `end_of_track` em `bars·1920`. Trilha 1: `track_name "drums"`, `note_on`/`note_off` no canal 9. Converter tempos absolutos em delta; eventos simultâneos em ordem determinística (`note_off` antes de `note_on` no mesmo tick). `to_bytes(midi_file) -> bytes` via `BytesIO`
- [X] T028 [US1] Implementar a leitura em `src/boombap/midi_io.py`: `read_song(path) -> ParsedSong` com bpm, assinatura de compasso, texto de configuração, seções (`marker` → `start_bar`), por compasso `hat_grid` (do `cue_marker`) e `is_fill` (do `text "fill"`), e notas por compasso com posição de grade reconstruída: desfazer o swing esperado do `hat_grid` (usando o `swing` do texto de configuração) e arredondar para a semicolcheia mais próxima; guardar também o atraso medido `tick − (bar·1920 + pos·120)`
- [X] T029 [US1] Implementar a serialização da derivação em `src/boombap/derive.py` (`Derivation.to_json(sections) -> str`), conforme `contracts/derivation.schema.json`: chaves `format = "boombap-derivation"`, `version`, `seed`, `rules_sha256`, `config` (`bpm`, `swing`, `density`, `fills`, `bars`, `bass`, `key`), `form` (5 itens com `name`, `start_bar`, `bars`, `groove`, `blocks[{size, bars[{index, kind ∈ {"groove","fill"}, hat_grid}]}]`), `log_prob` (≤ 0), `tree` (nós `{symbol, rule, prob, u, children}` e terminais `{t: "<str do terminal>"}`); `json.dumps(..., ensure_ascii=False, indent=1)` + `\n` final; ordem de chaves fixa
- [X] T030 [US1] Implementar `src/boombap/output.py`: `write_outputs(base: Path, mid_bytes: bytes, json_text: str) -> (Path, Path)`. Acrescenta `.mid` ao caminho se ausente (`base` sem sufixo para o `.json`); verifica que o diretório pai existe e é gravável; grava cada conteúdo em `tempfile.NamedTemporaryFile(dir=pai, delete=False)`, faz `flush`+`fsync` e publica os dois com `os.replace`; em qualquer exceção remove os temporários e, se o primeiro `replace` já ocorreu, remove o arquivo publicado (ou ambos, ou nenhum). Erros viram `OutputError` com mensagem `cannot write to '<path>': <motivo>`
- [X] T031 [US1] Implementar `src/boombap/analyze.py`: `analyze(path) -> dict` usando `read_song`, com `bpm`, `time_signature`, `bars`, `sections [{name, start_bar, bars}]` e `style_violations: list[str]` cobrindo FR-011 (bumbo pos 0 e caixa pos 4 em todo compasso; caixa pos 12 em todo compasso sem `fill`), FR-013 (≥ 1 nota 42 ou 46 por compasso), FR-014 (um só tempo, bpm 85–95, 4/4), FR-015 (atraso médio > 0 nas posições fracas da grade de cada compasso que as tiver), FR-016 (só canal 9 e notas permitidas na trilha de bateria); cada violação como `"bar <i>: <descrição>"` ou `"global: <descrição>"`
- [X] T032 [US1] Implementar `src/boombap/cli.py` (depende de T014, T019, T020, T025–T031): `main(argv=None) -> int` com `argparse` e subcomandos. `generate -o/--output PATH [--seed] [--rules PATH]` (os demais hiperparâmetros entram em US3 e o baixo em US5; até lá usam os padrões de `RunConfig`): cria `RunConfig` (erro → `error: <msg>` em stderr, exit 2), `build_grammar` (`TableError` → `error: <arquivo>:<linha>: <msg>`, exit 1), `derive`, `extract`, `realize`, `build_midi`, `to_json`, `write_outputs` (`OutputError` → exit 1), e imprime em stdout exatamente o formato de `contracts/cli.md`. `analyze PATH.mid [--format text|json]` (padrão `text`: uma chave por linha; `json`: `json.dumps(..., ensure_ascii=False, indent=2)`). Erros de uso do argparse saem com 2. `src/boombap/__main__.py` chama `sys.exit(main())`

**Checkpoint**: US1 funciona sozinha: `boombap generate -o out/demo` + `boombap analyze out/demo.mid` sem violações; `pytest tests/contract/test_cli_generate.py tests/contract/test_midi_layout.py tests/integration/test_style_100_seeds.py` passa.

---

## Phase 4: User Story 2 - Reproduzir e variar resultados por semente (Priority: P1)

**Goal**: Sem semente, cada execução sorteia uma nova e a exibe; com a mesma semente e parâmetros, os arquivos `.mid` e `.json` saem byte a byte idênticos; o MIDI e o JSON, cada um sozinho, bastam para reproduzir a música.

**Independent Test**: Três execuções sem `--seed` → sementes e arquivos diferentes; duas execuções com `--seed 42` → `cmp` idêntico; regenerar a partir do texto do MIDI ou do `config` do JSON → idêntico.

### Tests for User Story 2 ⚠️

- [X] T033 [P] [US2] Teste em `tests/integration/test_reproducibility.py`: para 20 sementes, duas gerações com a mesma semente e parâmetros produzem `.mid` e `.json` **byte a byte** iguais (SC-003), inclusive com `PYTHONHASHSEED` diferente (rodar uma das gerações via `subprocess` com `python -m boombap` e `env={"PYTHONHASHSEED": "1", ...}`); 10 sementes distintas com a mesma configuração → sequências de eventos `(tick, note, velocity)` distintas em ≥ 9 dos pares (SC-002); duas execuções sem `--seed` imprimem sementes diferentes
- [X] T034 [P] [US2] Teste em `tests/contract/test_reproduce_from_records.py`: gerar com parâmetros não padrão; ler o `text` da trilha 0, reconstruir a `RunConfig` com `parse_record` e regenerar → mesmo `.mid`; idem a partir de `seed` + `config` do `.json`

### Implementation for User Story 2

- [X] T035 [US2] Implementar `parse_record(text: str) -> RunConfig` em `src/boombap/config.py`, que lê a linha `boombap v<versão> seed=… bpm=… swing=… density=… fills=… bars=… bass=on|off key=…` e devolve a configuração validada (erro claro se faltar campo), e `RunConfig.record(version) -> str`, usado por `midi_io.build_midi` (substituir a formatação inline de T027 por essa função para que escrita e leitura usem o mesmo formato)
- [X] T036 [US2] Garantir determinismo de bytes em `src/boombap/midi_io.py`, `src/boombap/derive.py` e `src/boombap/output.py`: nenhuma data, hora, caminho absoluto ou ordem de `set`/`hash()` influencia a saída; floats sempre formatados com `repr`; listas de não-terminais/terminais ordenadas de forma estável; revisar que o `u` de cada nó só depende de `seed` e do caminho (R7)
- [X] T037 [US2] Em `src/boombap/cli.py`, garantir que a linha `seed: <int>` seja **a primeira** do stdout tanto com semente sorteada quanto informada, e que `analyze` (formatos text e json) inclua a chave `record` com o texto de configuração lido do MIDI, para que o usuário recupere semente e parâmetros a partir de qualquer arquivo gerado

**Checkpoint**: US1 e US2 funcionam; `pytest tests/integration/test_reproducibility.py tests/contract/test_reproduce_from_records.py` passa.

---

## Phase 5: User Story 3 - Controlar hiperparâmetros com efeito audível (Priority: P2)

**Goal**: `--bpm`, `--swing`, `--density`, `--fills` e `--bars` no CLI, com recusa clara fora da faixa e efeito mensurável e monotônico com a mesma semente; `analyze` mede as métricas de SC-004.

**Independent Test**: Cenário 3 do `quickstart.md`: para cada hiperparâmetro, mín. vs. máx. com `--seed 7` → métrica muda na direção esperada.

### Tests for User Story 3 ⚠️

- [X] T038 [P] [US3] Teste em `tests/contract/test_cli_validation.py`: `--bpm 120`, `--bpm 84`, `--swing 50`, `--swing 80`, `--density 1.5`, `--fills -0.1`, `--bars 22`, `--bars 16`, `--bars 260`, `--seed abc`, `--seed -1`, `--seed 9223372036854775808`, `--key Hm` → exit 2, mensagem com a faixa válida (formato de `contracts/cli.md`) em stderr, nenhum arquivo em `out_dir`
- [X] T039 [P] [US3] Teste SC-004 em `tests/integration/test_hyperparams.py` com `boombap.rules` (skip se ausente), sementes `7` e mais 9 fixas: `density 0` vs `1` → `notes_per_bar.kick + notes_per_bar.hh_closed` em `hi` ≥ 1,3 × `lo`, e o multiconjunto de eventos opcionais de `lo` está contido no de `hi`; `fills 0` vs `1` → `fill_bars` maior em `hi`; `swing 52` vs `75` → `mean_offbeat_delay_ticks` maior em `hi`; `bpm 85` vs `95` → `duration_seconds_hi == duration_seconds_lo · 85/95` (tolerância 0,01); `--bars 64` → `bars == 64` e seções somam 64. Repetir os itens de `fills`, `swing`, `bpm` e `bars` com `minimal.rules`

### Implementation for User Story 3

- [X] T040 [US3] Acrescentar a `src/boombap/analyze.py` as métricas: `duration_seconds = round(bars·4·60/bpm, 2)`; `notes_per_bar` = média por compasso de cada peça (`kick`, `snare`, `rim`, `hh_closed`, `hh_open`, `crash`), arredondada a 2 casas; `fill_bars` = nº de compassos com `text "fill"`; `mean_offbeat_delay_ticks` = média, sobre todas as notas de bateria nas posições fracas da grade de swing do seu compasso (ímpares em `grid16`; 2, 6, 10, 14 em `grid8`), do atraso medido em relação à grade reta, arredondada a 2 casas. Ordem das chaves igual ao exemplo de `contracts/cli.md`
- [X] T041 [US3] Acrescentar ao subcomando `generate` em `src/boombap/cli.py` as opções `--bpm INT`, `--swing FLOAT`, `--density FLOAT`, `--fills FLOAT`, `--bars INT` (padrões 90, 58, 0.5, 0.5, 40), repassadas a `RunConfig.create` sem validação duplicada no argparse (os tipos são lidos como `str` para que a mensagem de faixa venha sempre de `RunConfig`, ex.: `--bars 22` → `error: --bars must be a multiple of 4 between 20 and 256 (got 22)`)

**Checkpoint**: US1–US3 funcionam; cenário 3 e 4 do `quickstart.md` dão o resultado esperado.

---

## Phase 6: User Story 4 - Inspecionar a gramática e a derivação (Priority: P2)

**Goal**: `boombap grammar` lista a gramática formal (axioma, não-terminais, terminais, regras com probabilidades efetivas) em texto ou JSON, com `--check`; o `.json` de cada música segue o esquema e corresponde aos eventos do MIDI.

**Independent Test**: `boombap grammar --bars 40 --max-rules 10` mostra a gramática com somas 1 por LHS; `boombap grammar --check` sai com 0; o `.json` de uma música valida contra o esquema e mostra as escolhas em cada nível.

### Tests for User Story 4 ⚠️

- [X] T042 [P] [US4] Teste de contrato em `tests/contract/test_cli_grammar.py`: formato `text` tem as seções `Axioma`, `Não-terminais`, `Terminais`, `Regras`, linhas de regra `<id>  <LHS> → <RHS…>  [p=0.250]` agrupadas por LHS com a soma do grupo `= 1.000`; `--format json` tem `axiom`, `nonterminals`, `terminals`, `rules[{id, lhs, rhs, prob}]` e a soma por `lhs` é 1 (1e-9); `--max-rules 10` trunca famílias indexadas e mostra `… (+K regras)`; `--density 0` vs `--density 1` mudam a prob. de uma regra opcional; `--check` → exit 0 com `minimal.rules` e `boombap.rules`, exit 1 com cada arquivo de `tests/fixtures/invalid/`, imprimindo `arquivo:linha: violação`; avisos não mudam o exit code
- [X] T043 [P] [US4] Teste em `tests/contract/test_derivation_schema.py`: o `.json` de 10 músicas (com e sem `--bass`) valida com `jsonschema` (Draft 2020-12) contra `specs/001-boombap-grammar-generator/contracts/derivation.schema.json`; a sequência de terminais de bateria da árvore, após dedup, tem o mesmo número de notas e as mesmas `(peça, compasso, posição)` que a trilha de bateria do MIDI; `form` bate com os `marker` do MIDI; toda `rule` da árvore existe na listagem de `boombap grammar --format json` com a mesma configuração

### Implementation for User Story 4

- [X] T044 [US4] Implementar `src/boombap/grammar/format.py`: `to_text(grammar, max_rules: int | None) -> str` e `to_json(grammar) -> str`, sobre os não-terminais **alcançáveis** a partir do axioma `Música(N)` (fechamento transitivo, ordem BFS determinística, R4). Texto: seção `Axioma` (uma linha), `Não-terminais` (lista separada por vírgulas), `Terminais` (ordenados), `Regras` com uma linha por regra `<id>  <LHS> → <RHS…>  [p=<3 casas>]` (`ε` para RHS vazio), agrupadas por LHS e encerradas por `  Σ = 1.000`; com `max_rules`, cada LHS de família indexada (`Forma`, `Corpo`, `Seção`, `FimBloco`) mostra no máximo N regras e uma linha `… (+K regras)`. Incluir no topo um comentário com a tabela usada e seu sha256
- [X] T045 [US4] Implementar o subcomando `grammar` em `src/boombap/cli.py`: opções `--bars`, `--density`, `--fills`, `--bass`, `--key`, `--rules`, `--format text|json`, `--max-rules INT`, `--check` (contrato em `contracts/cli.md`). Sem `--check`: monta a gramática com `RunConfig.create(seed=0, …)` e imprime `to_text`/`to_json`. Com `--check`: roda `check_table` em toda a grade, `Grammar.validate()` para `bars ∈ {20, 40, 256}`, imprime erros como `arquivo:linha: violação` em stdout e avisos como `warning: arquivo:linha: …` em stderr; exit 0 se não há erros, 1 caso contrário

**Checkpoint**: US1–US4 funcionam; cenário 5 do `quickstart.md` dá o resultado esperado.

---

## Phase 7: User Story 5 - Linha de baixo opcional (Priority: P3)

**Goal**: `--bass [--key KEY]` acrescenta uma trilha de baixo (canal 1, programa GM 34) cujos ataques coincidem com bumbos e cujas notas estão na escala menor natural da tonalidade, decididas por `BassFirst`/`BassDeg` da tabela.

**Independent Test**: `boombap generate -o out/bass --seed 7 --bass --key Dm` → trilha `bass`, cada `note_on` no mesmo tick de um bumbo, notas em Ré menor; os eventos de bateria são idênticos aos de `--seed 7` sem `--bass`.

### Tests for User Story 5 ⚠️

- [X] T046 [P] [US5] Teste em `tests/integration/test_bass.py`: com `--bass --key Dm` (e `Am`, `F#m`, `Bbm`), 3 trilhas; trilha 2 `track_name "bass"`, `program_change` 34 no tick 0, só canal 0; todo `note_on` do baixo tem um `note_on` 36 no mesmo tick; toda nota pertence à escala menor natural da tonalidade; durações ≤ 480 ticks; **a trilha de bateria é byte a byte igual** à da mesma semente sem `--bass`; sem `--bass`, só 2 trilhas

### Implementation for User Story 5

- [X] T047 [US5] Em `src/boombap/derive.py`, quando `config.bass`, após cada terminal `kick` expandir `BassFirst` (se `pos == 0`) ou `BassDeg` (demais posições) com caminho `"<path do terminal>b"`, fora da numeração de filhos, para não alterar o `u` de nenhum nó de bateria (R10); em `src/boombap/sections.py`, anexar o grau ao `DrumEvent` do bumbo (`bass_degree: int | None`)
- [X] T048 [US5] Em `src/boombap/realize.py`, implementar `realize_bass(sections, key) -> list[TimedNote]`: tônica de `key` (`A`, `Bb`, `F#`…) na oitava 2 (MIDI `36 + pc`, com `pc` de C=0 a B=11; ex.: A2 = 45); graus da escala menor natural `{1: 0, 3: 3, 4: 5, 5: 7, 7: 10}` semitons; `tick_on` = `tick_on` do bumbo já realizado (mesmo swing e `dt`), dedup herdado do bumbo; `tick_off = min(próximo ataque de bumbo, tick_on + 480)`; canal 0; velocity = velocity do bumbo
- [X] T049 [US5] Em `src/boombap/midi_io.py`, quando houver notas de baixo, acrescentar a trilha 2 com `track_name "bass"`, `program_change(program=33, channel=0)` (GM 34 em base 1) no tick 0 e as notas; `read_song` passa a ler a trilha de baixo, se existir
- [X] T050 [US5] Em `src/boombap/cli.py`, acrescentar `--bass` (flag) e `--key KEY` (padrão `Am`) a `generate` (o stdout passa a mostrar `bass: on`) e garantir que `grammar --bass` inclua `BassFirst`/`BassDeg` na listagem

**Checkpoint**: US1–US5 funcionam; cenário 6 do `quickstart.md` dá o resultado esperado.

---

## Phase 8: User Story 6 - Ouvir o resultado como áudio (Priority: P3)

**Goal**: `boombap render PATH.mid` gera um `.wav` com FluidSynth e um soundfont GM.

**Independent Test**: `boombap render out/demo.mid --soundfont /usr/share/soundfonts/FluidR3_GM.sf2` → `out/demo.wav` tocável, duração ≈ `duration_seconds`.

### Tests for User Story 6 ⚠️

- [X] T051 [P] [US6] Teste em `tests/contract/test_cli_render.py`: sem `--soundfont` e sem `BOOMBAP_SOUNDFONT` → exit 1 com mensagem sugerindo instalar um SF2 GM (ex.: `soundfont-fluid`); soundfont inexistente → exit 1; `fluidsynth` fora do PATH (monkeypatch de `shutil.which` → `None`) → exit 1 com mensagem clara; comando montado é `["fluidsynth", "-ni", "-F", <out>, "-r", "44100", <sf2>, <mid>]` (monkeypatch de `subprocess.run`); saída padrão = mesmo nome-base com `.wav`; teste real (com `pytest.mark.skipif` se não houver `fluidsynth` e soundfont) verifica com o módulo `wave` que a duração ≥ `duration_seconds`

### Implementation for User Story 6

- [X] T052 [US6] Implementar `src/boombap/render.py`: `render(mid: Path, out: Path | None, soundfont: Path | None, sample_rate: int = 44100) -> Path`. Resolve o soundfont por argumento ou `os.environ["BOOMBAP_SOUNDFONT"]`; verifica existência do arquivo, do `.mid` e do binário (`shutil.which("fluidsynth")`); sufixo de saída aceito: `.wav`, `.flac`, `.ogg`; executa `subprocess.run([...], check=True, capture_output=True)`; erros viram `RenderError` com mensagem clara (incluindo o stderr do fluidsynth)
- [X] T053 [US6] Acrescentar o subcomando `render PATH.mid [-o OUT] [--soundfont SF2] [--sample-rate INT]` em `src/boombap/cli.py`; `RenderError` → `error: …` em stderr, exit 1; sucesso imprime `wrote: <out>`

**Checkpoint**: Todas as histórias funcionam de forma independente.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Desempenho, documentação, entregáveis e validação final

- [X] T054 [P] Teste de desempenho SC-005 em `tests/integration/test_performance.py`: `generate` de 40 compassos com `boombap.rules` (ou `minimal.rules` se ausente) em < 5 s medido com `time.perf_counter` (incluindo `build_grammar` e a escrita); 256 compassos também em < 5 s; `grammar --bars 256 --format json` termina em < 5 s
- [X] T055 [P] Escrever `README.md` na raiz: descrição do trabalho (DCC831, gramáticas generativas, boom bap); instalação (`python -m venv`, `pip install -r requirements.txt -e .`, `pip install -e .[test]`); uso de cada subcomando com exemplos do `quickstart.md`; como reproduzir uma música (semente + parâmetros, a partir do `.mid` ou do `.json`); visão geral da gramática (hierarquia de não-terminais do `data-model.md`, divisão entre famílias indexadas geradas pelo código e tabela `boombap.rules`); áudio (FluidSynth + `soundfont-fluid`); lista dos arquivos em `samples/`; seção **"Uso de IA"** separando as autorias: a tabela de regras de estilo `src/boombap/data/boombap.rules` foi escrita pelo aluno; a infraestrutura (carregador e validador da tabela, famílias indexadas, motor de derivação, MIDI, CLI, análise, render, testes, README) foi implementada com apoio de IA; com um marcador `<!-- TODO(aluno): links das conversas -->` onde entram os links
- [ ] T056 [MANUAL — aluno] Preencher em `README.md` os links das conversas com IA exigidos pelo enunciado e revisar a seção "Uso de IA"
- [X] T057 [P] Criar `samples/make_samples.sh` (executável, `set -euo pipefail`) que gera ≥ 3 músicas em `samples/` com sementes e parâmetros documentados no próprio script, mostrando variação de semente e de ao menos um hiperparâmetro (ex.: `--seed 7`; `--seed 7 --density 1 --fills 1`; `--seed 21 --swing 70 --bass --key Dm`), e as renderiza com `boombap render` quando `BOOMBAP_SOUNDFONT` estiver definido (senão avisa e pula o áudio)
- [ ] T058 [MANUAL — aluno] Instalar um soundfont GM (`sudo pacman -S soundfont-fluid`), rodar `samples/make_samples.sh`, ouvir as músicas (SC-008), abrir os `.mid` em um segundo reprodutor (ex.: `timidity` ou MuseScore, SC-006) e versionar `.mid`, `.json` e `.wav` em `samples/`
- [ ] T059 Rodar os cenários 1–8 de `specs/001-boombap-grammar-generator/quickstart.md` em um venv limpo e corrigir qualquer divergência no código (nunca no conteúdo de `boombap.rules`); rodar `pytest -q` completo e confirmar que tudo passa
- [X] T060 [P] Revisar `src/boombap/grammar/core.py`, `structure.py` e `derive.py` para confirmar que nenhum valor musical (posição, velocidade, probabilidade de estilo) está fixado no código, além das constantes documentadas (PPQ, mapa GM, `@crash_velocity` padrão, fórmula de swing); qualquer achado vira parâmetro da tabela documentado em `contracts/rule-table.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup. **Bloqueia todas as histórias.** T021 (manual) pode correr em paralelo com o resto da fase depois de T017.
- **US1 (Phase 3)**: depende da Foundational. É o MVP.
- **US2 (Phase 4)**: depende de US1 (reaproveita o pipeline `generate` e os escritores).
- **US3 (Phase 5)**: depende de US1 (CLI e `analyze`); independe de US2.
- **US4 (Phase 6)**: depende só da Foundational para `format.py` e `--check`; T043 depende de US1 (gera `.json`). Pode correr em paralelo com US2/US3.
- **US5 (Phase 7)**: depende de US1 (realize, MIDI, CLI).
- **US6 (Phase 8)**: depende de US1 para ter um `.mid` real; `render.py` em si é independente.
- **Polish (Phase 9)**: depois das histórias desejadas.

### Within Phase 2

T015 → T016 → T017 → T018 → T019 → T020. T014 é independente. Os testes T008–T013 podem ser escritos em paralelo antes.

### Within Each User Story

- Testes primeiro (devem falhar), depois implementação.
- US1: T025 e T026 em paralelo → T027 → T028 → T029/T030/T031 → T032.
- Tarefas que mexem em `src/boombap/cli.py` (T032, T037, T041, T045, T050, T053) são sequenciais entre si.

### Parallel Opportunities

- Setup: T002–T006 em paralelo.
- Foundational: T008–T013 (testes) em paralelo; T014 em paralelo com T015.
- US1: T022–T024 em paralelo; T025 ∥ T026.
- Entre histórias, depois de US1: US3, US4 (exceto T045 por causa de `cli.py`) e US6 (`render.py`) podem avançar em paralelo.
- Polish: T054, T055, T057, T060 em paralelo.

---

## Parallel Example: User Story 1

```bash
# Testes da US1 juntos:
Task: "Teste de contrato do layout MIDI em tests/contract/test_midi_layout.py"
Task: "Teste de integração SC-001 em tests/integration/test_style_100_seeds.py"
Task: "Teste de contrato do CLI generate em tests/contract/test_cli_generate.py"

# Módulos independentes da US1 juntos:
Task: "Implementar src/boombap/sections.py"
Task: "Implementar src/boombap/realize.py"
```

## Parallel Example: depois da US1

```bash
Task: "US3 — métricas em src/boombap/analyze.py (T040)"
Task: "US4 — listagem em src/boombap/grammar/format.py (T044)"
Task: "US6 — src/boombap/render.py (T052)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup.
2. Phase 2: Foundational (inclui a checagem da tabela do aluno, T021).
3. Phase 3: US1.
4. **PARAR E VALIDAR**: cenário 1 do `quickstart.md` e `pytest`.

### Incremental Delivery

1. Setup + Foundational → gramática e derivação funcionando.
2. US1 → música completa em MIDI (MVP).
3. US2 → reprodutibilidade comprovada (necessária para o resumo).
4. US3 → hiperparâmetros e métricas para a seção de resultados.
5. US4 → listagem formal da gramática para transcrever no resumo.
6. US5 → baixo opcional.
7. US6 → áudio para os entregáveis.
8. Polish → README, amostras, validação final.

---

## Notes

- [P] = arquivos diferentes, sem dependências pendentes.
- [MANUAL — aluno] = feito pelo aluno; o implementador não executa a parte autoral.
- Nunca editar o conteúdo musical de `src/boombap/data/boombap.rules` (R14). Erros na tabela são reportados ao aluno.
- Fazer commit depois de cada tarefa ou grupo lógico.

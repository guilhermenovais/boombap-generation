# Implementation Plan: Gerador de Batidas Boom Bap por Gramática Probabilística

**Branch**: `001-boombap-grammar-generator` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-boombap-grammar-generator/spec.md`

## Summary

CLI em Python que gera músicas de bateria boom bap em MIDI exclusivamente pela expansão de uma gramática probabilística livre de contexto. A gramática combina duas partes. A primeira é uma **tabela de regras em texto** (`boombap.rules`), escrita pelo aluno, com grooves, viradas, chimbal, humanização, baixo e probabilidades expressas em `density`/`fills`. A segunda são as famílias estruturais indexadas, geradas pelo código. O código valida estaticamente a tabela contra as regras de estilo do spec. Não-terminais indexados distribuem os compassos (`Forma_N → Intro_i Corpo_M Outro_o`, `Corpo_M → Verso Refrão Verso`) e propagam o groove da seção e o estado "após virada" sem sair de CFG. Um motor genérico deriva o axioma usando um uniforme por nó, obtido de `sha256(seed‖caminho)`. Com isso a semente reproduz a música exatamente, e mudar um hiperparâmetro com a mesma semente altera a música de forma monotônica. Os terminais (eventos GM no canal 10, em grade de 16) são realizados com swing MPC e humanização limitada, e gravados com `mido` em um `.mid` e um `.json` de derivação. Subcomandos adicionais: `grammar` (listagem formal e verificação), `analyze` (métricas) e `render` (áudio via FluidSynth).

## Technical Context

**Language/Version**: Python ≥ 3.11 (máquina do autor: 3.14.7)

**Primary Dependencies**: `mido` (escrita/leitura MIDI). Stdlib: `argparse`, `hashlib`, `json`, `secrets`, `subprocess`. Externo e opcional: binário `fluidsynth` (2.6.0 instalado) + soundfont GM livre (ainda não instalado).

**Storage**: Arquivos: `<base>.mid` e `<base>.json` (derivação) gravados atomicamente; `.wav` opcional.

**Testing**: `pytest` (unidade, contrato, integração/propriedade sobre 100 sementes)

**Target Platform**: Linux (Manjaro) e qualquer SO com Python; áudio onde houver `fluidsynth`

**Project Type**: CLI + biblioteca (pacote único `boombap`)

**Performance Goals**: ≤ 5 s para 40 compassos (SC-005). Esperado: bem abaixo de 1 s.

**Constraints**: Só gramática em decisões musicais (FR-001); probabilidades por não-terminal somam 1; reprodutibilidade byte a byte; sem arquivo parcial em caso de erro; `requirements.txt` obrigatório; **uso de IA declarado no README; a tabela de regras de estilo (`boombap.rules`) é de autoria do aluno e não é gerada pela IA** (enunciado, ver research R14/R15)

**Scale/Scope**: 20–256 compassos por música; ~1,7 mil regras no pior caso para `Corpo_M`; ~8 módulos

Todas as incógnitas foram resolvidas em [research.md](./research.md). Nenhum NEEDS CLARIFICATION em aberto.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` ainda é o **template não preenchido**: não há princípios ratificados e, portanto, nenhum gate formal a avaliar. Na falta deles, o plano foi checado contra as restrições obrigatórias do spec e do enunciado:

| Gate (spec/enunciado) | Pré-pesquisa | Pós-design |
|---|---|---|
| Método único: gramática probabilística (FR-001) | ✅ | ✅ baixo e humanização também são regras (R8, R10); swing/clamp são realização determinística dos terminais |
| Gramática formal; probabilidades somam 1 (FR-002, SC-007) | ✅ | ✅ `Grammar.validate()` + `boombap grammar --check` |
| Total de compassos exato por construção (FR-025) | ✅ | ✅ regras indexadas só com partes que somam o índice (R4) |
| Livre de contexto com groove por seção (FR-006) | ✅ | ✅ refinamento de símbolos por índices finitos (R5) |
| Reprodutibilidade (FR-023) | ✅ | ✅ RNG por caminho via sha256 (R7) |
| Entregáveis: `requirements.txt`, README com uso de IA | ✅ | ✅ na estrutura do projeto |
| Método não gerado integralmente por IA (enunciado) | ✅ | ✅ conteúdo musical isolado em `boombap.rules`, autoria do aluno; validado por `--check` (R14/R15) |

Resultado: **PASS** (sem violações; Complexity Tracking vazio). Recomenda-se rodar `/speckit-constitution` se o autor quiser gates formais.

## Project Structure

### Documentation (this feature)

```text
specs/001-boombap-grammar-generator/
├── plan.md              # Este arquivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   ├── cli.md                    # subcomandos generate/grammar/analyze/render
│   ├── rule-table.md             # formato e invariantes da tabela de regras
│   ├── midi-output.md            # layout do SMF gerado
│   └── derivation.schema.json    # esquema do <base>.json
└── tasks.md             # Fase 2 (/speckit-tasks — não criado aqui)
```

### Source Code (repository root)

```text
pyproject.toml            # metadados, script `boombap`, pytest config
requirements.txt          # mido (exigido pelo enunciado)
README.md                 # instalação, reprodução, gramática, seção "Uso de IA"
src/boombap/
├── __init__.py           # __version__
├── __main__.py           # python -m boombap
├── data/
│   └── boombap.rules     # TABELA DE REGRAS DE ESTILO — escrita pelo aluno, não pela IA (R14)
├── cli.py                # argparse: generate | grammar | analyze | render
├── config.py             # RunConfig + validação (FR-019/021/022)
├── grammar/
│   ├── core.py           # Symbol, NonTerminal, Terminal, Rule, Grammar, validate()  (genérico)
│   ├── table.py          # parser/avaliador da tabela de regras + validação estática (R15)
│   ├── structure.py      # famílias indexadas Forma/Corpo/Seção/Bloco/Compasso (R4/R5)
│   └── format.py         # listagem text/json da gramática (FR-009)
├── derive.py             # motor de derivação, RNG por caminho, árvore de derivação (R7)
├── sections.py           # árvore → Section/Block/Bar
├── realize.py            # terminais → TimedNote: swing, humanização, clamp, dedup (R8)
├── midi_io.py            # escrita (mido) + leitura para analyze (R9)
├── output.py             # gravação atômica .mid + .json (R12)
├── analyze.py            # métricas e style_violations (SC-001/004)
└── render.py             # chamada ao fluidsynth (R11)

tests/
├── fixtures/minimal.rules  # tabela sintética mínima só para testes de formato/invariantes
├── unit/                 # core, parser da tabela, validação estática, swing, clamp, dedup, config
├── contract/             # CLI (saídas/exit codes), JSON vs. schema, layout MIDI
└── integration/          # 100 sementes (SC-001), reprodutibilidade, min-vs-max (SC-004), tempo (SC-005)

samples/                  # ≥ 3 músicas entregáveis (.mid, .json, .wav)
```

**Structure Decision**: Projeto único com layout `src/` e um pacote `boombap`. O conteúdo musical do método fica num arquivo de dados, `data/boombap.rules`, escrito pelo aluno e separado de todo o código. O código (carregador, estrutura indexada, motor, MIDI, CLI) é genérico e não contém escolhas de estilo. Isso deixa a fronteira de autoria explícita para a seção "Uso de IA" do README. Também permite transcrever a tabela quase literalmente no resumo e experimentar tabelas alternativas com `--rules`.

## Complexity Tracking

Sem violações a justificar.

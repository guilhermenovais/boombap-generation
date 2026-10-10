# Data Model: Gerador de Batidas Boom Bap

**Feature**: `001-boombap-grammar-generator` | **Data**: 2026-10-05

Entidades em memória (não há banco de dados). Os artefatos persistidos são o `.mid` ([contracts/midi-output.md](./contracts/midi-output.md)) e o `.json` de derivação ([contracts/derivation.schema.json](./contracts/derivation.schema.json)).

---

## RunConfig (Configuração de execução)

| Campo | Tipo | Faixa / regra | Padrão | Origem |
|---|---|---|---|---|
| `seed` | int | 0 ≤ seed < 2⁶³ | sorteada (`secrets.randbits(32)`) | FR-022 |
| `bpm` | int | 85–95 | 90 | FR-014 |
| `swing` | float (%) | 52–75 | 58 | FR-015, Assumptions |
| `density` | float | 0–1 | 0,5 | FR-019/020 |
| `fills` | float | 0–1 | 0,5 | FR-019/020 |
| `bars` | int | múltiplo de 4, 20–256 | 40 | FR-019, FR-025 |
| `bass` | bool | — | false | FR-026 |
| `key` | str | tônica + `m` (ex.: `Am`, `Dm`, `F#m`) | `Am` | FR-026 |

**Validação**: feita antes de qualquer geração; uma violação produz `ConfigError` com mensagem que cita a faixa válida (FR-021). Imutável após validação.

---

## Symbol

- `NonTerminal(name: str, index: tuple)` — ex.: `Forma(40)`, `Seção(12, "G2", "início")`, `Compasso("G2", "fim", "normal")`. Igualdade e hash por (name, index).
- `Terminal` — evento concreto de bateria (ver **DrumEvent**), token de humanização (`Δv`, `Δt`), token de grade de chimbal (`grade8`/`grade16`), marcador de seção (`⟨seção:verso⟩`), ou, com baixo, `Bass(pos, grau)`.
- `ε` — produção vazia (opcionais ausentes, caso base de seção).

## Rule (Regra de produção)

| Campo | Tipo | Regra |
|---|---|---|
| `id` | str | estável e legível, ex.: `R.corpo.40.12-8-12`, `R.kick.G1.p7.on` |
| `lhs` | NonTerminal | — |
| `rhs` | tuple[Symbol, …] | pode ser vazio (ε) |
| `prob` | float | 0 < prob ≤ 1 (regras com prob 0 não são emitidas) |

## Grammar

| Campo | Tipo |
|---|---|
| `axiom` | NonTerminal (`Música(N)`) |
| `source` | caminho da tabela de regras |
| `params` | RunConfig (parte que afeta probabilidades: `density`, `fills`, `bars`, `bass`, `key`) |
| `rules_for(nt)` | → list[Rule], gerada sob demanda e memorizada (R4) |
| `nonterminals()` / `terminals()` | conjuntos alcançáveis a partir do axioma |

**Invariantes** (verificadas por `Grammar.validate()` e testes, SC-007):
1. Para todo não-terminal alcançável, `Σ prob = 1` (tolerância 1e-9).
2. Todo não-terminal alcançável tem ao menos uma regra; toda derivação termina (os índices decrescem estritamente em `Seção_k`).
3. Para todo `Forma_N`/`Corpo_M`/`Seção_k`, cada regra cobre exatamente o índice (soma das partes = índice) (FR-025).
4. Os níveis seção/bloco, compasso e evento opcional têm ≥ 2 alternativas com prob > 0 para algum valor de parâmetro (FR-003); grooves ≥ 3 (FR-006).
5. `p_fim(φ) > p_meio(φ)` para todo φ ∈ [0, 1] (FR-007).

### Hierarquia de não-terminais (resumo)

```text
Música_N        → ⟨seção:intro⟩ … (via Forma_N)
Forma_N         → Intro_i Corpo_{N−i−o} Outro_o            i,o ∈ {4,8}
Corpo_M         → Verso_a Refrão_b Verso_c                 a+b+c = M
Intro_k|Verso_k|Refrão_k|Outro_k → Seção_{k,g,início}      g ∈ grooves (≥3)
Seção_{k,g,s}   → Bloco4_{g,s,f} Seção_{k−4,g,f}
                | Bloco8_{g,s,f} Seção_{k−8,g,f}
                | ε (k = 0)
Bloco4_{g,s,f}  → Compasso_{g,primeiro,s} Compasso_{g,meio} Compasso_{g,meio} Compasso_{g,fim,f}
Bloco8_{g,s,f}  → idem com 6 compassos de meio
Compasso_{g,pos,…} → Prato? Groove_g | Prato? Fill_g     (@fill_mid / @fill_end; prato por @crash_*)
── acima: gerado pelo código (pesos vindos dos @parâmetros da tabela) ──
── abaixo: definido pelo autor em boombap.rules (contracts/rule-table.md) ──
Groove_X        → …  deve garantir kick@0 snare@4 snare@12, um bumbo sincopado, grid8|grid16, chimbal
Fill_X          → …  deve garantir kick@0 snare@4, grid8|grid16, chimbal
HumV → dv±N …   HumT → dt±N …        (expandidos após cada terminal de bateria)
BassFirst, BassDeg → deg1 | deg3 | deg4 | deg5 | deg7   (só com --bass)
```

## Derivation (Derivação)

Árvore de nós `DerivationNode`:

| Campo | Tipo | Descrição |
|---|---|---|
| `symbol` | str | nome do não-terminal com índice, ex. `Verso(12)` |
| `rule` | str | `id` da regra escolhida |
| `prob` | float | probabilidade da regra |
| `u` | float | uniforme usado na escolha (auditoria, R7) |
| `children` | list[DerivationNode \| TerminalRef] | filhos na ordem do lado direito |

Também contém: `seed`, `config`, `rules_sha256` (hash da tabela usada), `grammar_version`, `log_prob` (soma de `ln prob`), e a sequência plana de terminais. Serializada conforme [derivation.schema.json](./contracts/derivation.schema.json).

## Section / Block / Bar (vistas derivadas)

Extraídas da árvore após a derivação, para realização e análise:

- **Section**: `kind ∈ {intro, verso, refrão, outro}`, `start_bar`, `n_bars` (múltiplo de 4), `groove ∈ {G1, G2, G3, …}`, `blocks: list[Block]`.
- **Block**: `size ∈ {4, 8}`, `bars: list[Bar]`.
- **Bar**: `index` (global), `kind ∈ {groove, virada}`, `hat_grid ∈ {8, 16}`, `events: list[DrumEvent]`, `is_block_end: bool`.

## DrumEvent (terminal de bateria)

| Campo | Tipo | Regra |
|---|---|---|
| `piece` | enum | KICK=36, SNARE=38, RIM=37, HH_CLOSED=42, HH_OPEN=46, CRASH=49 (FR-016) |
| `pos` | int | 0–15 (FR-008) |
| `velocity` | int | 1–127 após Δv e clamp |
| `dv` | int | definido em `HumV` |
| `dt` | int | definido em `HumT`, \|dt\| ≤ 10 ticks |

**Deduplicação**: no mesmo compasso, eventos com mesmo (`piece`, `pos`) são unificados mantendo a maior `velocity`.

## TimedNote (realização)

`tick_on`, `tick_off`, `channel` (9 bateria / 0 baixo), `note`, `velocity`.

`tick_on = bar·1920 + pos·120 + swing_delay(pos, hat_grid, swing) + dt`, limitado a `[bar·1920, bar·1920 + 1919]` e ≥ 0.

`swing_delay` = `(S/100 − 0,5)·2·120` nas posições ímpares (grade 16) ou `(S/100 − 0,5)·2·240` em {2, 6, 10, 14} (grade 8); 0 nas demais.

## BassNote (opcional)

`pos` (= posição de um bumbo), `degree ∈ {1, ♭3, 4, 5, ♭7}` (de `BassFirst`/`BassDeg`), `midi_note` (escala menor natural de `key`, oitava 2), `duration` (até o próximo bumbo, ≤ 480 ticks).

## Song (resultado)

`config: RunConfig`, `derivation: Derivation`, `sections: list[Section]`, `notes: list[TimedNote]`, `duration_seconds = bars·4·60/bpm`.

## Fluxo / estados

```text
CLI args ─validate→ RunConfig ─load_table(boombap.rules)+validate→ Grammar ─derive(seed)→ Derivation
   └→ extract → Sections/Blocks/Bars ─realize(swing, clamp, dedup)→ TimedNotes
   └→ write (atomic) → <base>.mid + <base>.json
```

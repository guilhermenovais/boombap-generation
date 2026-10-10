# Contract: CLI `boombap`

Executável instalado pelo pacote (`[project.scripts] boombap = "boombap.cli:main"`); também acessível como `python -m boombap`.

Convenções: saída informativa em **stdout**, erros em **stderr**. Códigos de saída: `0` sucesso, `1` erro de E/S/ambiente (caminho sem permissão, fluidsynth ausente), `2` erro de uso/validação (parâmetro fora da faixa, semente inválida).

---

## `boombap generate`

Gera uma música (US1, US2, US3, US5).

```text
boombap generate -o PATH [--seed INT] [--bpm INT] [--swing FLOAT]
                 [--density FLOAT] [--fills FLOAT] [--bars INT]
                 [--bass] [--key KEY] [--rules PATH]
```

| Opção | Tipo | Faixa | Padrão | Requisito |
|---|---|---|---|---|
| `-o, --output` | caminho | diretório pai existente e gravável; sufixo `.mid` acrescentado se ausente | obrigatório | FR-018 |
| `--seed` | int | 0 ≤ s < 2⁶³ | sorteada | FR-022/023 |
| `--bpm` | int | 85–95 | 90 | FR-014 |
| `--swing` | float (%) | 52–75 | 58 | FR-015 |
| `--density` | float | 0–1 | 0.5 | FR-020 |
| `--fills` | float | 0–1 | 0.5 | FR-020 |
| `--bars` | int | múltiplo de 4, 20–256 | 40 | FR-019/025 |
| `--bass` | flag | — | desligado | FR-026 |
| `--key` | str | `<A-G>[#b]?m` | `Am` | FR-026 |
| `--rules` | caminho | tabela válida ([rule-table.md](./rule-table.md)) | `boombap/data/boombap.rules` | R15 |

**Efeitos**: cria `PATH.mid` e `PATH.json` (mesmo nome-base), de forma atômica — ou ambos, ou nenhum.

**stdout (sucesso)** — formato estável, uma chave por linha:

```text
seed: 1234567
bpm: 90  swing: 58.0  density: 0.5  fills: 0.5  bars: 40  bass: off
form: intro(4) verso(12) refrão(8) verso(12) outro(4)
wrote: out/song.mid
wrote: out/song.json
```

**Erros (exit 2, nenhum arquivo criado)** — exemplos de mensagem:

```text
error: --bpm must be between 85 and 95 (got 120)
error: --bars must be a multiple of 4 between 20 and 256 (got 22)
error: --seed must be a non-negative integer below 2^63 (got 'abc')
```

**Tabela inválida (exit 1, nenhum arquivo)**: `error: boombap.rules:42: Groove_B does not guarantee snare@12`.

**Erro de E/S (exit 1)**: `error: cannot write to 'out/x.mid': <motivo>`.

---

## `boombap grammar`

Exibe a gramática formal com probabilidades efetivas (US4, FR-009, SC-007).

```text
boombap grammar [--bars INT] [--density FLOAT] [--fills FLOAT] [--bass] [--key KEY] [--rules PATH]
                [--format text|json] [--max-rules INT] [--check]
```

- **text** (padrão): seções `Axioma`, `Não-terminais`, `Terminais`, `Regras`; cada regra numa linha
  `<id>  <LHS> → <RHS…>  [p=0.250]`, agrupadas por LHS, com a soma por LHS ao final do grupo.
- **json**: `{ "axiom": str, "nonterminals": [str], "terminals": [str], "rules": [{ "id", "lhs", "rhs": [str], "prob" }] }`.
- `--max-rules N`: limita regras exibidas por família indexada, indicando `… (+K regras)`.
- `--check`: valida a tabela em toda a grade de parâmetros (somas = 1, ganchos definidos, eventos garantidos, `@fill_end > @fill_mid`, terminação, cobertura dos índices; ver [rule-table.md](./rule-table.md) §3); exit 0 se ok, 1 caso contrário, imprimindo `arquivo:linha: violação`. Avisos (ex.: probabilidade não monotônica) não falham.

---

## `boombap analyze`

Calcula métricas de um MIDI gerado (US3, SC-001, SC-004; reutilizado pelos testes e pelo resumo).

```text
boombap analyze PATH.mid [--format text|json]
```

Saída JSON:

```json
{
  "bpm": 90.0, "time_signature": "4/4", "bars": 40, "duration_seconds": 106.67,
  "sections": [{"name": "intro", "start_bar": 0, "bars": 4}],
  "notes_per_bar": {"kick": 2.9, "snare": 2.1, "rim": 0.3, "hh_closed": 10.4, "hh_open": 0.2, "crash": 0.1},
  "fill_bars": 6,
  "mean_offbeat_delay_ticks": 19.4,
  "style_violations": []
}
```

`style_violations` lista violações de FR-011/014/015/016 (vazio = música válida). Os compassos de virada são identificados pelos marcadores de texto da trilha condutora (ver [midi-output.md](./midi-output.md)).

---

## `boombap render`

Converte MIDI em áudio (US6, FR-027).

```text
boombap render PATH.mid [-o OUT.wav] [--soundfont SF2] [--sample-rate 44100]
```

- Soundfont: `--soundfont` ou variável `BOOMBAP_SOUNDFONT`; ausência → exit 1 com mensagem sugerindo instalar um SF2 GM.
- Requer o binário `fluidsynth` no PATH; ausência → exit 1.
- Saída padrão: mesmo nome-base com `.wav`. Formatos aceitos pelo sufixo: `.wav`, `.flac`, `.ogg` (o que o fluidsynth suportar).

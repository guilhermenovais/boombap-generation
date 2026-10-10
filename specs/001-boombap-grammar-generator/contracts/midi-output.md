# Contract: Arquivo MIDI gerado

Standard MIDI File **tipo 1**, **PPQ = 480** (semínima = 480 ticks, semicolcheia = 120, compasso 4/4 = 1920).

## Trilha 0 — condutor

| Tick | Evento | Conteúdo |
|---|---|---|
| 0 | `track_name` | `boombap` |
| 0 | `set_tempo` | `bpm2tempo(bpm)`, bpm ∈ [85, 95] — único evento de tempo |
| 0 | `time_signature` | 4/4 |
| 0 | `text` | `boombap v<versão> seed=<seed> bpm=<bpm> swing=<swing> density=<δ> fills=<φ> bars=<N> bass=<on/off> key=<key>` — basta para reproduzir (FR-024) |
| início de cada seção | `marker` | `intro`, `verso`, `refrão`, `verso`, `outro` (FR-010), nesta ordem |
| início de cada compasso de virada | `text` | `fill` |
| início de cada compasso | `cue_marker` | `grid8` ou `grid16` (grade de swing do compasso, permite medir FR-015 sem a derivação) |
| fim | `end_of_track` | em `bars·1920` |

## Trilha 1 — bateria

- `track_name` = `drums`; todas as notas no **canal 10** (índice mido `channel=9`).
- Notas permitidas: 36, 37, 38, 42, 46, 49 (FR-016). Nenhuma outra.
- `note_on` velocity 1–127; `note_off` 60 ticks depois (ou antes do fim do compasso, o que ocorrer primeiro).
- Todo `note_on` de um compasso b está em `[b·1920, b·1920 + 1919]`.
- Não há duas notas da mesma peça com mesmo tick de grade no mesmo compasso (dedup).

## Trilha 2 — baixo (somente com `--bass`)

- `track_name` = `bass`, canal 1 (`channel=0`), `program_change` GM 34 no tick 0.
- Cada `note_on` coincide (mesmo tick) com um `note_on` de bumbo (36) da trilha 1.
- Notas pertencem à escala menor natural da tonalidade de `key`.

## Propriedades verificáveis (SC-001)

1. Exatamente um `set_tempo`, com bpm ∈ [85, 95]; `time_signature` 4/4.
2. Para todo compasso b: existe 36 em pos 0 e 38 em pos 4; se o compasso não tem `text fill`, existe 38 em pos 12. (A posição de grade é obtida desfazendo o swing e arredondando para a semicolcheia mais próxima; |Δt| ≤ 3 ticks ≪ 60.)
3. Todo compasso tem ao menos um 42 ou 46.
4. Nos compassos `grid16`, notas em posições ímpares têm atraso médio > 0; nos `grid8`, notas em {2, 6, 10, 14} têm atraso médio > 0.
5. Mesmos `seed` e parâmetros → arquivos byte a byte idênticos (SC-003).

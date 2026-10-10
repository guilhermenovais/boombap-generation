# Quickstart / Guia de validação

**Feature**: `001-boombap-grammar-generator`

Roteiro executável para provar, de ponta a ponta, que o gerador cumpre o spec. Interfaces em [contracts/cli.md](./contracts/cli.md); formato do MIDI em [contracts/midi-output.md](./contracts/midi-output.md); derivação em [contracts/derivation.schema.json](./contracts/derivation.schema.json).

## Pré-requisitos

- Python ≥ 3.11
- Para áudio: `fluidsynth` (já instalado: 2.6.0) e um soundfont GM livre. No Manjaro/Arch:
  `sudo pacman -S soundfont-fluid` → `/usr/share/soundfonts/FluidR3_GM.sf2`

## Pré-requisito do autor: a tabela de regras

`src/boombap/data/boombap.rules` precisa existir e ser **escrita pelo aluno** (formato em [contracts/rule-table.md](./contracts/rule-table.md)). Valide antes de tudo:

```bash
boombap grammar --check     # deve sair com exit 0
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -e .        # mido + pacote boombap
pip install pytest                          # testes
export BOOMBAP_SOUNDFONT=/usr/share/soundfonts/FluidR3_GM.sf2
```

## Cenários

### 1. Música padrão (US1, SC-001)

```bash
boombap generate -o out/demo
boombap analyze out/demo.mid
```

**Esperado**: imprime `seed: …` e a forma; cria `out/demo.mid` e `out/demo.json`; `analyze` mostra `bpm` 85–95, `4/4`, 5 seções na ordem intro/verso/refrão/verso/outro, `bars: 40`, `style_violations: []`.

### 2. Reprodutibilidade (US2, SC-002, SC-003)

```bash
boombap generate -o out/a --seed 42
boombap generate -o out/b --seed 42
cmp out/a.mid out/b.mid && echo IDENTICOS
boombap generate -o out/c ; boombap generate -o out/d
cmp -s out/c.mid out/d.mid || echo DIFERENTES
```

**Esperado**: `IDENTICOS` e `DIFERENTES`; as sementes de `c` e `d` são impressas e diferem.

### 3. Hiperparâmetros (US3, SC-004)

```bash
for p in "density 0 1" "fills 0 1" "swing 52 75" "bpm 85 95"; do
  set -- $p
  boombap generate -o out/$1-lo --seed 7 --$1 $2
  boombap generate -o out/$1-hi --seed 7 --$1 $3
done
boombap generate -o out/bars64 --seed 7 --bars 64
```

**Esperado** (via `boombap analyze … --format json`):
- `density`: `kick + hh_closed` por compasso em `hi` ≥ 1,3 × `lo`.
- `fills`: `fill_bars` maior em `hi`.
- `swing`: `mean_offbeat_delay_ticks` maior em `hi`.
- `bpm`: `duration_seconds` em `hi` = `lo` × 85/95.
- `bars64`: `bars: 64`.

### 4. Validação de entrada (US3 cen. 6, edge cases)

```bash
boombap generate -o out/x --bpm 120   ; echo "exit=$?"
boombap generate -o out/x --bars 22   ; echo "exit=$?"
boombap generate -o out/x --bars 16   ; echo "exit=$?"
boombap generate -o out/x --seed abc  ; echo "exit=$?"
boombap generate -o /root/x.mid       ; echo "exit=$?"
ls out/x.* 2>/dev/null || echo "nenhum arquivo"
```

**Esperado**: mensagens claras com a faixa válida; exit 2 (uso) ou 1 (E/S); `nenhum arquivo`.

### 5. Gramática e derivação (US4, SC-007)

```bash
boombap grammar --bars 40 --max-rules 10
boombap grammar --bars 40 --density 1 --fills 0 --check && echo OK
python -c "import json;d=json.load(open('out/demo.json'));print([s['name'] for s in d['form']])"
```

**Esperado**: listagem com axioma, não-terminais, terminais e regras com `p=`; `--check` imprime `OK`; a derivação lista as 5 seções na ordem.

### 6. Baixo opcional (US5)

```bash
boombap generate -o out/bass --seed 7 --bass --key Dm
```

**Esperado**: MIDI com trilha `bass` no canal 1; cada nota de baixo coincide com um bumbo; notas na escala de Ré menor. Sem `--bass`, só a trilha de bateria.

### 7. Áudio (US6, SC-006)

```bash
boombap render out/demo.mid            # → out/demo.wav
```

**Esperado**: WAV tocável com duração ≈ `duration_seconds` (+ cauda de release). Abrir o `.mid` também em um segundo reprodutor (ex.: MuseScore ou `timidity`) para SC-006.

### 8. Suíte automática

```bash
pytest -q
```

Cobre SC-001 (100 sementes × parâmetros aleatórios), SC-002, SC-003, SC-004, SC-005 (< 5 s) e SC-007.

## Entregáveis (fora do software, guiados por este roteiro)

Gerar ≥ 3 músicas com variação de semente/parâmetro (cenário 3), renderizar (cenário 7), versionar os `.wav` + `.mid` + `.json` em `samples/` e citar sementes e parâmetros no resumo ISMIR.

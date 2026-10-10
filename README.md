# boombap — batidas boom bap por gramática probabilística

Trabalho prático 1 de DCC831 (IA na Música): geração musical simbólica com **gramáticas generativas**.
O programa gera músicas de bateria no estilo **boom bap** (hip-hop dos anos 90) em MIDI, exclusivamente pela
expansão de uma gramática probabilística livre de contexto. Cada música tem forma
intro → verso → refrão → verso → outro, seções em blocos de 4 ou 8 compassos, swing de MPC, e
pode ter uma linha de baixo opcional.

## Instalação

Requer Python ≥ 3.11.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -e .     # mido + o pacote boombap (comando `boombap`)
pip install -e .[test]                   # pytest e jsonschema, para rodar os testes
```

Para áudio: o binário `fluidsynth` e um soundfont General MIDI livre. No Manjaro/Arch:

```bash
sudo pacman -S fluidsynth soundfont-fluid
export BOOMBAP_SOUNDFONT=/usr/share/soundfonts/FluidR3_GM.sf2
```

## Uso

### Gerar uma música

```bash
boombap generate -o out/demo                       # semente sorteada e impressa
boombap generate -o out/demo --seed 42             # reprodutível
boombap generate -o out/busy --seed 7 --density 1 --fills 1 --swing 66 --bpm 92 --bars 64
boombap generate -o out/bass --seed 7 --bass --key Dm
```

Cria `out/demo.mid` e `out/demo.json` (a derivação completa), de forma atômica: ou os dois, ou nenhum.

| Opção             | Faixa                                                      | Padrão                           |
| ----------------- | ---------------------------------------------------------- | -------------------------------- |
| `--seed`          | inteiro, 0 ≤ s < 2⁶³                                       | sorteada                         |
| `--bpm`           | 85–95                                                      | 90                               |
| `--swing`         | 52–75 (%)                                                  | 58                               |
| `--density`       | 0–1 (bumbos extras, ghost notes, chimbal em semicolcheias) | 0.5                              |
| `--fills`         | 0–1 (frequência de viradas)                                | 0.5                              |
| `--bars`          | múltiplo de 4, 20–256                                      | 40                               |
| `--bass`, `--key` | baixo opcional; tonalidade menor (`Am`, `F#m`, `Bbm`…)     | desligado, `Am`                  |
| `--rules`         | tabela de regras alternativa                               | `src/boombap/data/boombap.rules` |

Valores fora da faixa são recusados (exit 2) com a faixa válida na mensagem.

### Inspecionar a gramática

```bash
boombap grammar --bars 40 --max-rules 10          # axioma, não-terminais, terminais, regras com p=
boombap grammar --bars 40 --format json
boombap grammar --check                           # valida a tabela em toda a grade de parâmetros
```

### Analisar um MIDI gerado

```bash
boombap analyze out/demo.mid                      # bpm, seções, notas/compasso, viradas, swing, violações
boombap analyze out/demo.mid --format json
```

### Converter em áudio

```bash
boombap render out/demo.mid                       # → out/demo.wav (usa BOOMBAP_SOUNDFONT)
boombap render out/demo.mid -o out/demo.flac --soundfont /caminho/GM.sf2
```

## Reprodutibilidade

A mesma semente com os mesmos parâmetros gera arquivos **byte a byte idênticos**. A semente e todos os
hiperparâmetros ficam gravados nos dois arquivos:

- no MIDI, num evento de texto da trilha 0
  (`boombap v0.1.0 seed=7 bpm=90 swing=58.0 density=0.5 fills=0.5 bars=40 bass=off key=Am`),
  que `boombap analyze` mostra na chave `record`;
- no `.json`, nas chaves `seed` e `config`.

Basta repetir o comando com esses valores (`boombap generate -o x --seed 7 --bpm 90 …`).

Cada decisão da derivação usa um número uniforme obtido de `sha256(semente | caminho do nó na árvore)`.
Com isso, mudar só um hiperparâmetro, com a mesma semente, mexe apenas nas decisões que ele afeta.
Como as probabilidades crescem com `density` e `fills`, cada nota opcional presente com o valor baixo
continua presente com o valor alto.

## A gramática

A gramática tem duas partes:

1. **Famílias estruturais indexadas**, geradas pelo código (`src/boombap/grammar/structure.py`).
   Todos os seus pesos vêm dos `@parâmetros` da tabela de regras:

   ```text
   Música(N)    → Forma(N)
   Forma(N)     → Intro(i) Corpo(N−i−o) Outro(o)              i, o ∈ {4, 8}
   Corpo(M)     → Verso(a) Refrão(b) Verso(c)                 a+b+c = M, múltiplos de 4
   Verso(k)     → ⟨seção:verso⟩ Seção(k, g, início_seção)     g ∈ @grooves (≥ 3)
   Seção(k,g,s) → Bloco4(g,s) FimBloco(k−4,g) | Bloco8(g,s) FimBloco(k−8,g) | ε (k = 0)
   Bloco4(g,s)  → Compasso(g,primeiro,s) Compasso(g,meio) Compasso(g,meio)
   FimBloco(k,g)→ Compasso(g,fim,virada) Seção(k,g,pós_virada)  [@fill_end]
                | Compasso(g,fim,groove) Seção(k,g,normal)      [rest]
   Compasso(…)  → Prato(ctx) Fill_g [@fill_mid] | Prato(ctx) Groove_g [rest]
   Prato(ctx)   → crash@0 [@crash_*] | ε [rest]
   ```

   Os índices garantem por construção que a soma dos compassos é exatamente `--bars`. O estado `s`
   (início de intro, início de seção, após virada, normal) mantém a gramática livre de contexto e ainda
   permite o prato depois de uma virada.

2. **Tabela de regras de estilo** (`src/boombap/data/boombap.rules`, formato em
   `specs/001-boombap-grammar-generator/contracts/rule-table.md`). Define grooves (`Groove_X`), viradas
   (`Fill_X`), chimbal, notas opcionais, humanização (`HumV`, `HumT`), baixo (`BassFirst`, `BassDeg`) e
   as probabilidades como expressões em `density` e `fills`.

Antes de cada geração, o programa valida a tabela estaticamente. Probabilidades somam 1 em cada
não-terminal. Todo groove garante bumbo no 0, caixa no 4 e no 12, e um bumbo sincopado. Toda virada
garante bumbo no 0 e caixa no 4. Todo compasso tem chimbal e exatamente uma grade de swing.
Também se exige `@fill_end > @fill_mid` e que não haja recursão infinita.

## Testes

```bash
pytest -q
```

Cobrem 100 sementes com parâmetros aleatórios sem violação de estilo (SC-001), reprodutibilidade byte a
byte (SC-002/003), efeito de cada hiperparâmetro (SC-004), tempo < 5 s (SC-005), somas = 1 e a
listagem da gramática (SC-007), o layout do MIDI, o esquema do `.json`, o baixo e o render.

## Amostras

`samples/make_samples.sh` gera as músicas de exemplo, com sementes e parâmetros documentados no
próprio script:

| Arquivo          | Comando                                                  |
| ---------------- | -------------------------------------------------------- |
| `seed7_default`  | `--seed 7`                                               |
| `seed7_busy`     | `--seed 7 --density 1 --fills 1`                         |
| `seed21_bass_dm` | `--seed 21 --swing 70 --bass --key Dm`                   |
| `seed99_long`    | `--seed 99 --bpm 86 --bars 64 --density 0.2 --fills 0.3` |

Cada uma tem `.mid`, `.json` e, se `BOOMBAP_SOUNDFONT` estiver definido, `.wav`.

## Uso de IA

As autorias estão separadas assim:

- **Escrita pelo aluno**: a tabela de regras de estilo `src/boombap/data/boombap.rules`, isto é, o
  conteúdo musical do método (grooves, viradas, chimbal, notas opcionais, humanização, baixo e todas as
  probabilidades).
- **Implementada com apoio de IA**: a infraestrutura. Inclui o carregador e o validador da tabela, as
  famílias estruturais indexadas, o motor de derivação, a escrita e leitura de MIDI, o CLI, a análise,
  o render, os testes, a tabela sintética de testes `tests/fixtures/minimal.rules` e este README.

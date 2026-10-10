# Contract: Tabela de regras de estilo (`boombap.rules`)

O conteúdo musical da gramática fica num arquivo de texto separado do código. Isso inclui grooves, chimbal, eventos opcionais, viradas, prato, humanização, baixo e as probabilidades de cada um. **O aluno é o autor da tabela** (ver research R14/R15). O programa carrega a tabela, gera as famílias estruturais indexadas a partir dela (forma, corpo, seções, blocos, compassos), valida tudo e deriva.

- Local padrão: `src/boombap/data/boombap.rules` (empacotado). Pode ser trocado com `--rules PATH` em `generate` e `grammar`.
- Codificação UTF-8. `#` inicia comentário. Linhas em branco são ignoradas.

## 1. Parâmetros (`@nome = valor`)

Valores numéricos podem ser expressões aritméticas (`+ - * / ( )`, `min`, `max`) sobre `density` e `fills` (ambos de 0 a 1).

| Parâmetro | Obrigatório | Forma | Significado |
|---|---|---|---|
| `@grooves` | sim | lista de nomes (≥ 3) | grooves disponíveis; cada nome `X` exige uma regra `Groove_X` e uma `Fill_X` |
| `@fill_end` | sim | expressão | prob. de virada no último compasso do bloco |
| `@fill_mid` | sim | expressão | prob. de virada nos demais compassos |
| `@intro_bars`, `@outro_bars` | sim | `4:p 8:p` | tamanho de intro/outro |
| `@body_share` | sim | 3 números | proporções-alvo verso/refrão/verso do corpo |
| `@body_sigma` | sim | número > 0 | tolerância em torno das proporções-alvo, **como fração do corpo** (mesma unidade de `@body_share`) |
| `@block_size` | sim | `4:p 8:p` | preferência de bloco de 4 ou 8 quando os dois cabem |
| `@crash_section`, `@crash_intro`, `@crash_after_fill` | sim | expressão | prob. de prato no 1º tempo (início de seção / início da intro / após virada) |
| `@groove_weights` | não | `X:p …` | prob. de cada groove por seção (padrão: uniforme) |
| `@crash_velocity` | não | número inteiro 1–127 | velocidade do prato emitido por `Prato(…)` (padrão: 110) |

## 2. Regras

```text
LHS -> símbolo símbolo …   [prob]
     | símbolo …           [prob]
```

- `LHS`: identificador (`[A-Za-z_][A-Za-z0-9_]*`). Não-terminais são os identificadores que aparecem como LHS.
- `[prob]`: expressão. `[rest]` = 1 − soma das demais. Alternativas sem `[ ]` dividem igualmente o que sobra.
- `ε` = produção vazia.

### Terminais

| Sintaxe | Significado |
|---|---|
| `kick@P:V`, `snare@P:V`, `rim@P:V`, `hhc@P:V`, `hho@P:V`, `crash@P:V` | peça GM 36/38/37/42/46/49, posição P ∈ 0–15, velocidade V ∈ 1–127 |
| `grid8`, `grid16` | grade de swing do compasso (FR-015) |
| `dv±N` | variação de velocidade (usada em `HumV`) |
| `dt±N` | variação de tempo em ticks, \|N\| ≤ 10 (usada em `HumT`) |
| `deg1 deg3 deg4 deg5 deg7` | grau da escala menor para o baixo |

### Não-terminais que a tabela DEVE definir (ganchos do motor)

| Nome | Função |
|---|---|
| `Groove_X` (para cada X em `@grooves`) | compasso normal do groove X |
| `Fill_X` (para cada X em `@grooves`) | compasso de virada do groove X |
| `HumV`, `HumT` | humanização; o motor expande ambos após cada terminal de bateria |
| `BassFirst`, `BassDeg` | grau do baixo no bumbo do tempo 1 / nos demais bumbos (exigidos só com `--bass`) |

Outros não-terminais auxiliares (ex.: `Hats`, `OptKick_G1`, `FillTail`) são livres.

## 3. Validação (`boombap grammar --check`; também roda antes de todo `generate`)

Os parâmetros são amostrados em uma grade, `density, fills ∈ {0, 0.25, 0.5, 0.75, 1}`. Para cada ponto:

1. As probabilidades de cada não-terminal somam 1 e ficam em [0, 1] (FR-002).
2. `@fill_end > @fill_mid` (FR-007).
3. Todo não-terminal referenciado está definido; não há recursão infinita.
4. **Eventos garantidos**, por análise estática de "presente em toda expansão":
   - todo `Groove_X` garante `kick@0`, `snare@4` e `snare@12`, e ao menos um bumbo em posição ≠ 0 (FR-011/012);
   - todo `Fill_X` garante `kick@0` e `snare@4`;
   - todo `Groove_X`/`Fill_X` emite exatamente um `grid8`/`grid16` e ao menos um `hhc`/`hho` (FR-013/015).
5. `≥ 3` grooves e ao menos 2 alternativas com prob. > 0 em algum nível opcional (FR-003/006).

Um erro aponta o arquivo, a linha e a regra violada. Se a validação falhar, o programa não gera nenhum arquivo.

## 4. Esqueleto mínimo (somente formato; os valores e eventos ficam a cargo do autor)

```text
@grooves = A B C
@fill_end = …
…
Groove_A -> kick@0:… snare@4:… … Hats_A …
Hats_A   -> … [ … ] | … [rest]
Fill_A   -> kick@0:… snare@4:… … FillTail
HumV -> dv-2 | dv0 | dv+2
HumT -> dt-1 | dt0 | dt+1
```

#!/usr/bin/env bash
# Gera as músicas de exemplo entregáveis em samples/ (.mid + .json e, com soundfont, .wav).
# Mostram variação de semente e de hiperparâmetros:
#   seed7_default    --seed 7                              (padrões: 90 bpm, swing 58, density 0.5, fills 0.5, 40 compassos)
#   seed7_busy       --seed 7 --density 1 --fills 1        (mesma semente, mais notas e viradas)
#   seed21_bass_dm   --seed 21 --swing 70 --bass --key Dm  (outra semente, mais swing, com baixo em Ré menor)
#   seed99_long      --seed 99 --bpm 86 --bars 64 --density 0.2 --fills 0.3
# Uso: samples/make_samples.sh   (defina BOOMBAP_SOUNDFONT para renderizar o áudio)
set -euo pipefail

cd "$(dirname "$0")"
BOOMBAP="${BOOMBAP:-boombap}"

"$BOOMBAP" generate -o seed7_default  --seed 7
"$BOOMBAP" generate -o seed7_busy     --seed 7 --density 1 --fills 1
"$BOOMBAP" generate -o seed21_bass_dm --seed 21 --swing 70 --bass --key Dm
"$BOOMBAP" generate -o seed99_long    --seed 99 --bpm 86 --bars 64 --density 0.2 --fills 0.3

if [[ -n "${BOOMBAP_SOUNDFONT:-}" ]]; then
  for mid in seed7_default.mid seed7_busy.mid seed21_bass_dm.mid seed99_long.mid; do
    "$BOOMBAP" render "$mid"
  done
else
  echo "aviso: BOOMBAP_SOUNDFONT não definido; áudio (.wav) não gerado" >&2
fi

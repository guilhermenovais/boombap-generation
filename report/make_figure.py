"""Gera fig_pianoroll.tex: compassos 12-15 da semente 7 com density 0 e density 1.

Uso (na raiz do projeto, com o pacote instalado):
    python report/make_figure.py
"""

import subprocess
import tempfile
from pathlib import Path

from boombap.midi_io import read_song

OUT = Path(__file__).with_name("fig_pianoroll.tex")
SEED, FIRST, NBARS = 7, 12, 4
ROWS = [(49, "prato"), (46, "chimbal ab."), (42, "chimbal"), (37, "aro"), (38, "caixa"), (36, "bumbo")]
STEP_TICKS = 120
XS = 0.092  # cm por semicolcheia
YS = 0.22  # cm por linha


def notes(density: float, tmp: Path):
    out = tmp / f"d{density}"
    subprocess.run(
        ["boombap", "generate", "-o", str(out), "--seed", str(SEED), "--density", str(density)],
        check=True,
        capture_output=True,
    )
    song = read_song(out.with_suffix(".mid"))
    t0 = FIRST * 16 * STEP_TICKS
    return [n for n in song.drum_notes if FIRST <= n.bar < FIRST + NBARS], t0, song.fill_bars


def panel(lines, density, y0, tmp):
    ns, t0, fills = notes(density, tmp)
    row_of = {note: i for i, (note, _) in enumerate(ROWS)}
    width = NBARS * 16 * XS
    height = len(ROWS) * YS
    for b in range(NBARS):
        if FIRST + b in fills:
            lines.append(rf"\fill[black!8] ({b * 16 * XS:.3f},{y0:.3f}) rectangle ({(b + 1) * 16 * XS:.3f},{y0 + height:.3f});")
    for s in range(0, NBARS * 16 + 1, 4):
        style = "black!60" if s % 16 == 0 else "black!15"
        lines.append(rf"\draw[{style}] ({s * XS:.3f},{y0:.3f}) -- ({s * XS:.3f},{y0 + height:.3f});")
    for i, (_, name) in enumerate(ROWS):
        y = y0 + height - (i + 0.5) * YS
        lines.append(rf"\node[anchor=east,font=\tiny] at (-0.05,{y:.3f}) {{{name}}};")
    for n in ns:
        if n.note not in row_of:
            continue
        x = (n.tick - t0) / STEP_TICKS * XS
        y = y0 + height - (row_of[n.note] + 0.5) * YS
        shade = max(25, round(n.velocity / 127 * 100))
        lines.append(rf"\fill[black!{shade}] ({x:.3f},{y - 0.07:.3f}) rectangle ({x + 0.07:.3f},{y + 0.07:.3f});")
    lines.append(rf"\draw[black!60] (0,{y0:.3f}) rectangle ({width:.3f},{y0 + height:.3f});")
    lines.append(rf"\node[anchor=west,font=\scriptsize] at ({width + 0.05:.3f},{y0 + height / 2:.3f}) {{$d={density:g}$}};")


def main():
    lines = [r"\begin{tikzpicture}"]
    with tempfile.TemporaryDirectory() as tmp:
        panel(lines, 1, 0.0, Path(tmp))
        panel(lines, 0, len(ROWS) * YS + 0.15, Path(tmp))
    for b in range(NBARS):
        lines.append(rf"\node[font=\tiny] at ({(b * 16 + 8) * XS:.3f},-0.15) {{{FIRST + b + 1}}};")
    lines.append(r"\end{tikzpicture}")
    OUT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

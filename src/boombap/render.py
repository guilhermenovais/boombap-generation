"""Conversão do MIDI em áudio com o binário `fluidsynth` (R11)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

AUDIO_SUFFIXES = (".wav", ".flac", ".ogg")
SOUNDFONT_HINT = (
    "pass --soundfont PATH or set BOOMBAP_SOUNDFONT to a General MIDI SF2 "
    "(e.g. 'sudo pacman -S soundfont-fluid' installs /usr/share/soundfonts/FluidR3_GM.sf2)"
)


class RenderError(RuntimeError):
    pass


def render_command(mid: Path, out: Path, soundfont: Path, sample_rate: int) -> list[str]:
    return ["fluidsynth", "-ni", "-F", str(out), "-r", str(sample_rate), str(soundfont), str(mid)]


def render(mid: Path | str, out: Path | str | None = None, soundfont: Path | str | None = None, sample_rate: int = 44100) -> Path:
    mid = Path(mid)
    out = Path(out) if out is not None else mid.with_suffix(".wav")
    if out.suffix.lower() not in AUDIO_SUFFIXES:
        raise RenderError(f"output must end in one of {', '.join(AUDIO_SUFFIXES)} (got '{out}')")
    if soundfont is None:
        soundfont = os.environ.get("BOOMBAP_SOUNDFONT") or None
    if soundfont is None:
        raise RenderError(f"no soundfont given: {SOUNDFONT_HINT}")
    soundfont = Path(soundfont)
    if not soundfont.is_file():
        raise RenderError(f"soundfont '{soundfont}' not found: {SOUNDFONT_HINT}")
    if not mid.is_file():
        raise RenderError(f"MIDI file '{mid}' not found")
    if shutil.which("fluidsynth") is None:
        raise RenderError("fluidsynth not found in PATH (install it, e.g. 'sudo pacman -S fluidsynth')")
    try:
        subprocess.run(render_command(mid, out, soundfont, sample_rate), check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or b"").decode(errors="replace").strip()
        raise RenderError(f"fluidsynth failed (exit {e.returncode}): {detail}") from None
    except OSError as e:
        raise RenderError(f"cannot run fluidsynth: {e}") from None
    return out

import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from conftest import generate, run_cli

SF2_CANDIDATES = [Path("/usr/share/soundfonts/FluidR3_GM.sf2"), Path("/usr/share/sounds/sf2/FluidR3_GM.sf2")]


@pytest.fixture
def song(out_dir):
    return generate(out_dir, "song", seed=1, bars=20)[0]


def test_no_soundfont(song, monkeypatch):
    monkeypatch.delenv("BOOMBAP_SOUNDFONT", raising=False)
    code, _, err = run_cli("render", song)
    assert code == 1 and "soundfont" in err and "soundfont-fluid" in err


def test_missing_soundfont(song, tmp_path):
    code, _, err = run_cli("render", song, "--soundfont", tmp_path / "none.sf2")
    assert code == 1 and "not found" in err


def test_no_fluidsynth(song, tmp_path, monkeypatch):
    sf2 = tmp_path / "x.sf2"
    sf2.write_bytes(b"")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    code, _, err = run_cli("render", song, "--soundfont", sf2)
    assert code == 1 and "fluidsynth not found" in err


def test_command(song, tmp_path, monkeypatch):
    sf2 = tmp_path / "x.sf2"
    sf2.write_bytes(b"")
    calls = []
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setenv("BOOMBAP_SOUNDFONT", str(sf2))
    code, out, _ = run_cli("render", song)
    out_wav = song.with_suffix(".wav")
    assert code == 0 and out.strip() == f"wrote: {out_wav}"
    assert calls == [["fluidsynth", "-ni", "-F", str(out_wav), "-r", "44100", str(sf2), str(song)]]


def test_bad_suffix(song, tmp_path):
    sf2 = tmp_path / "x.sf2"
    sf2.write_bytes(b"")
    code, _, err = run_cli("render", song, "-o", tmp_path / "x.mp3", "--soundfont", sf2)
    assert code == 1


SF2 = next((p for p in SF2_CANDIDATES if p.exists()), None)


@pytest.mark.skipif(shutil.which("fluidsynth") is None or SF2 is None, reason="fluidsynth ou soundfont GM ausente")
def test_real_render(song):
    from boombap.analyze import analyze

    code, _, err = run_cli("render", song, "--soundfont", SF2)
    assert code == 0, err
    with wave.open(str(song.with_suffix(".wav"))) as w:
        assert w.getnframes() / w.getframerate() >= analyze(song)["duration_seconds"]

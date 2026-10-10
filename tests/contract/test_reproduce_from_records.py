import json

import mido

from boombap.config import RunConfig, parse_record
from conftest import generate

OPTS = dict(seed=987654321, bpm=87, swing=66.5, density=0.8, fills=0.2, bars=48, bass=True, key="F#m")


def _cli_opts(cfg: RunConfig) -> dict:
    return dict(seed=cfg.seed, bpm=cfg.bpm, swing=cfg.swing, density=cfg.density, fills=cfg.fills,
                bars=cfg.bars, bass=cfg.bass, key=cfg.key)


def test_from_midi_text(out_dir):
    mid, _, _ = generate(out_dir, "orig", **OPTS)
    text = next(m.text for m in mido.MidiFile(str(mid)).tracks[0] if m.type == "text" and m.text.startswith("boombap v"))
    cfg = parse_record(text)
    again, _, _ = generate(out_dir, "again", **_cli_opts(cfg))
    assert again.read_bytes() == mid.read_bytes()


def test_from_json(out_dir):
    mid, js, _ = generate(out_dir, "orig", **OPTS)
    d = json.loads(js.read_text())
    cfg = RunConfig.create(seed=d["seed"], **d["config"])
    again, again_js, _ = generate(out_dir, "again", **_cli_opts(cfg))
    assert again.read_bytes() == mid.read_bytes()
    assert again_js.read_bytes() == js.read_bytes()


def test_analyze_shows_record(out_dir):
    from conftest import run_cli

    mid, _, _ = generate(out_dir, "orig", **OPTS)
    code, out, _ = run_cli("analyze", mid, "--format", "json")
    assert code == 0
    rec = json.loads(out)["record"]
    assert parse_record(rec) == RunConfig.create(**OPTS)
    code, out, _ = run_cli("analyze", mid)
    assert any(line.startswith("record: ") for line in out.splitlines())

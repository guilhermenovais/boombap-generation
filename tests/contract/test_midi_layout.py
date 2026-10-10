import mido
import pytest

from conftest import FIXTURES, REAL_RULES, generate

TABLES = [FIXTURES / "minimal.rules"] + ([REAL_RULES] if REAL_RULES.exists() else [])
FORM = ["intro", "verso", "refrão", "verso", "outro"]


def _abs(track):
    now = 0
    for msg in track:
        now += msg.time
        yield now, msg


@pytest.mark.parametrize("rules", TABLES, ids=lambda p: p.name)
@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_layout(out_dir, rules, seed):
    mid_path, _, _ = generate(out_dir, "s", rules, seed=seed, bars=40)
    mid = mido.MidiFile(str(mid_path))
    assert mid.type == 1 and mid.ticks_per_beat == 480 and len(mid.tracks) == 2

    conductor = list(_abs(mid.tracks[0]))
    assert conductor[0][1].type == "track_name" and conductor[0][1].name == "boombap"
    assert sum(m.type == "set_tempo" for _, m in conductor) == 1
    sigs = [m for _, m in conductor if m.type == "time_signature"]
    assert len(sigs) == 1 and (sigs[0].numerator, sigs[0].denominator) == (4, 4)
    texts = [m.text for _, m in conductor if m.type == "text" and m.text.startswith("boombap v")]
    assert len(texts) == 1 and f"seed={seed}" in texts[0]
    assert [m.text for _, m in conductor if m.type == "marker"] == FORM
    cues = [(t, m.text) for t, m in conductor if m.type == "cue_marker"]
    assert [t for t, _ in cues] == [b * 1920 for b in range(40)]
    assert all(text in ("grid8", "grid16") for _, text in cues)
    assert conductor[-1][1].type == "end_of_track" and conductor[-1][0] == 40 * 1920

    drums = list(_abs(mid.tracks[1]))
    assert drums[0][1].name == "drums"
    notes = [(t, m) for t, m in drums if m.type in ("note_on", "note_off")]
    assert notes and all(m.channel == 9 and m.note in {36, 37, 38, 42, 46, 49} for _, m in notes)
    for t, m in notes:
        if m.type == "note_on":
            assert 1 <= m.velocity <= 127
    assert drums[-1][0] == 40 * 1920

    from boombap.analyze import analyze

    assert analyze(mid_path)["style_violations"] == []

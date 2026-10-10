import mido
import pytest

from conftest import generate

SCALES = {"Dm": 2, "Am": 9, "F#m": 6, "Bbm": 10}
MINOR = {0, 2, 3, 5, 7, 8, 10}


def _abs(track):
    now = 0
    for msg in track:
        now += msg.time
        yield now, msg


@pytest.mark.parametrize("key", sorted(SCALES))
@pytest.mark.parametrize("seed", [7, 8])
def test_bass(out_dir, key, seed):
    with_bass, _, out = generate(out_dir, f"b-{key}-{seed}", seed=seed, bass=True, key=key)
    without, _, _ = generate(out_dir, f"n-{key}-{seed}", seed=seed)
    assert "bass: on" in out
    m, n = mido.MidiFile(str(with_bass)), mido.MidiFile(str(without))
    assert len(m.tracks) == 3 and len(n.tracks) == 2
    assert m.tracks[1] == n.tracks[1]  # bateria idêntica, mensagem a mensagem

    bass = list(_abs(m.tracks[2]))
    assert bass[0][1].type == "track_name" and bass[0][1].name == "bass"
    pcs = [(t, msg) for t, msg in bass if msg.type == "program_change"]
    assert pcs == [(0, pcs[0][1])] and pcs[0][1].program == 33 and pcs[0][1].channel == 0
    kicks = {t for t, msg in _abs(m.tracks[1]) if msg.type == "note_on" and msg.note == 36}
    ons = {}
    for t, msg in bass:
        if msg.type in ("note_on", "note_off"):
            assert msg.channel == 0
        if msg.type == "note_on":
            assert t in kicks
            assert (msg.note - SCALES[key]) % 12 in MINOR
            ons[msg.note, t] = t
        elif msg.type == "note_off":
            starts = [s for (note, s) in ons if note == msg.note and s <= t]
            assert t - max(starts) <= 480
    assert ons

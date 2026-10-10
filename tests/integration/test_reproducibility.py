import os
import subprocess
import sys

import mido

from conftest import FIXTURES, generate, run_cli


def _events(path):
    mid = mido.MidiFile(str(path))
    now, out = 0, []
    for msg in mid.tracks[1]:
        now += msg.time
        if msg.type == "note_on":
            out.append((now, msg.note, msg.velocity))
    return out


def test_same_seed_same_bytes(out_dir):
    for seed in range(20):
        a = generate(out_dir, f"a{seed}", seed=seed, density=0.3, bass=seed % 2 == 0)
        b = generate(out_dir, f"b{seed}", seed=seed, density=0.3, bass=seed % 2 == 0)
        assert a[0].read_bytes() == b[0].read_bytes()
        assert a[1].read_bytes() == b[1].read_bytes()


def test_bytes_independent_of_hash_seed(out_dir):
    mid, js, _ = generate(out_dir, "here", seed=42)
    for hs in ("1", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": hs}
        subprocess.run(
            [sys.executable, "-m", "boombap", "generate", "-o", str(out_dir / f"sub{hs}"), "--seed", "42"],
            check=True, env=env, capture_output=True,
        )
        assert (out_dir / f"sub{hs}.mid").read_bytes() == mid.read_bytes()
        assert (out_dir / f"sub{hs}.json").read_bytes() == js.read_bytes()


def test_different_seeds_differ(out_dir):
    songs = [_events(generate(out_dir, f"d{s}", seed=1000 + s)[0]) for s in range(10)]
    pairs = [(i, j) for i in range(10) for j in range(i + 1, 10)]
    distinct = sum(songs[i] != songs[j] for i, j in pairs)
    assert distinct >= 0.9 * len(pairs)


def test_random_seed_printed_and_differs(out_dir):
    _, o1, _ = run_cli("generate", "-o", out_dir / "r1")
    _, o2, _ = run_cli("generate", "-o", out_dir / "r2")
    s1, s2 = o1.splitlines()[0], o2.splitlines()[0]
    assert s1.startswith("seed: ") and s2.startswith("seed: ") and s1 != s2

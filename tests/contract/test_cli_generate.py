import os
import re

import pytest

from conftest import FIXTURES, run_cli


def test_default_output(out_dir):
    code, out, err = run_cli("generate", "-o", out_dir / "song")
    assert code == 0, err
    lines = out.splitlines()
    assert len(lines) == 5
    assert re.fullmatch(r"seed: \d+", lines[0])
    assert lines[1] == "bpm: 90  swing: 58.0  density: 0.5  fills: 0.5  bars: 40  bass: off"
    assert re.fullmatch(r"form: intro\(\d+\) verso\(\d+\) refrão\(\d+\) verso\(\d+\) outro\(\d+\)", lines[2])
    assert lines[3] == f"wrote: {out_dir / 'song.mid'}"
    assert lines[4] == f"wrote: {out_dir / 'song.json'}"
    assert (out_dir / "song.mid").exists() and (out_dir / "song.json").exists()


def test_mid_suffix_not_duplicated(out_dir):
    code, out, _ = run_cli("generate", "-o", out_dir / "x.mid", "--seed", "1")
    assert code == 0
    assert sorted(os.listdir(out_dir)) == ["x.json", "x.mid"]


def test_missing_parent_dir(out_dir):
    target = out_dir / "nope" / "x"
    code, out, err = run_cli("generate", "-o", target, "--seed", "1")
    assert code == 1
    assert err.startswith(f"error: cannot write to '{target}.mid': ")
    assert os.listdir(out_dir) == []


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissões")
def test_unwritable_dir(out_dir):
    ro = out_dir / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    try:
        code, _, err = run_cli("generate", "-o", ro / "x", "--seed", "1")
        assert code == 1 and "cannot write to" in err
        assert os.listdir(ro) == []
    finally:
        ro.chmod(0o700)


def test_invalid_table(out_dir):
    bad = FIXTURES / "invalid" / "missing_snare12.rules"
    code, out, err = run_cli("generate", "-o", out_dir / "x", "--rules", bad, "--seed", "1")
    assert code == 1
    assert re.match(rf"error: {re.escape(str(bad))}:\d+: Groove_A does not guarantee snare@12", err)
    assert os.listdir(out_dir) == []

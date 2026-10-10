import os

import pytest

from conftest import run_cli


@pytest.mark.parametrize(
    "opt, val, expected",
    [
        ("--bpm", "120", "error: --bpm must be between 85 and 95 (got 120)"),
        ("--bpm", "84", "error: --bpm must be between 85 and 95 (got 84)"),
        ("--swing", "50", "error: --swing must be between 52 and 75 (got 50)"),
        ("--swing", "80", "error: --swing must be between 52 and 75 (got 80)"),
        ("--density", "1.5", "error: --density must be between 0 and 1 (got 1.5)"),
        ("--fills", "-0.1", "error: --fills must be between 0 and 1 (got -0.1)"),
        ("--bars", "22", "error: --bars must be a multiple of 4 between 20 and 256 (got 22)"),
        ("--bars", "16", "error: --bars must be a multiple of 4 between 20 and 256 (got 16)"),
        ("--bars", "260", "error: --bars must be a multiple of 4 between 20 and 256 (got 260)"),
        ("--seed", "abc", "error: --seed must be a non-negative integer below 2^63 (got 'abc')"),
        ("--seed", "-1", "error: --seed must be a non-negative integer below 2^63 (got -1)"),
        ("--seed", "9223372036854775808", "error: --seed must be a non-negative integer below 2^63 (got 9223372036854775808)"),
        ("--key", "Hm", "error: --key must be a minor key like Am, F#m or Bbm (got 'Hm')"),
    ],
)
def test_out_of_range(out_dir, opt, val, expected):
    code, out, err = run_cli("generate", "-o", out_dir / "x", f"{opt}={val}")
    assert code == 2
    assert err.strip() == expected
    assert out == ""
    assert os.listdir(out_dir) == []

import time

import pytest

from conftest import FIXTURES, REAL_RULES, run_cli

RULES = REAL_RULES if REAL_RULES.exists() else FIXTURES / "minimal.rules"


@pytest.mark.parametrize("bars", [40, 256])
def test_generate_under_5s(out_dir, bars):
    t = time.perf_counter()
    code, _, err = run_cli("generate", "-o", out_dir / "p", "--seed", "1", "--bars", bars, "--bass", "--rules", RULES)
    assert code == 0, err
    assert time.perf_counter() - t < 5


def test_grammar_listing_under_5s():
    t = time.perf_counter()
    code, out, _ = run_cli("grammar", "--bars", "256", "--format", "json", "--rules", RULES)
    assert code == 0 and out
    assert time.perf_counter() - t < 5

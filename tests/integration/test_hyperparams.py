from collections import Counter

import pytest

from boombap.analyze import analyze
from boombap.midi_io import read_song
from conftest import FIXTURES, REAL_RULES, generate

SEEDS = [7, 11, 23, 42, 101, 202, 303, 404, 505, 606]


def _rules(which):
    if which == "real":
        if not REAL_RULES.exists():
            pytest.skip("boombap.rules ausente")
        return REAL_RULES
    return FIXTURES / "minimal.rules"


def _pair(out_dir, rules, seed, name, lo, hi, **extra):
    a = generate(out_dir, f"{name}-lo-{seed}", rules, seed=seed, **{name: lo}, **extra)[0]
    b = generate(out_dir, f"{name}-hi-{seed}", rules, seed=seed, **{name: hi}, **extra)[0]
    return a, b


def _non_hat_events(path):
    # Bumbo, caixa, aro e prato vêm de partes fixas, de opcionais monotônicos em density
    # ou de escolhas que não dependem de density; o chimbal troca de padrão (8 ↔ 16).
    return Counter((n.bar, n.note, n.pos) for n in read_song(path).drum_notes if n.note not in (42, 46))


@pytest.mark.parametrize("seed", SEEDS)
def test_density_is_monotonic(out_dir, seed):
    """Garantido pelo motor (R7): todo evento presente com density=0 continua com density=1."""
    lo, hi = _pair(out_dir, _rules("real"), seed, "density", 0, 1)
    a, b = analyze(lo)["notes_per_bar"], analyze(hi)["notes_per_bar"]
    assert b["kick"] + b["hh_closed"] > a["kick"] + a["hh_closed"]
    assert not (_non_hat_events(lo) - _non_hat_events(hi))


@pytest.mark.parametrize("seed", SEEDS)
def test_density_ratio_sc004(out_dir, seed):
    """SC-004: kick + hh_closed por compasso cresce ≥ 1,3×. Depende dos valores da tabela do aluno."""
    lo, hi = _pair(out_dir, _rules("real"), seed, "density", 0, 1)
    a, b = analyze(lo)["notes_per_bar"], analyze(hi)["notes_per_bar"]
    lo_v, hi_v = a["kick"] + a["hh_closed"], b["kick"] + b["hh_closed"]
    assert hi_v >= 1.3 * lo_v, f"density 0 → 1 só multiplica kick+hh_closed por {hi_v / lo_v:.3f} (seed {seed})"


@pytest.mark.parametrize("which", ["real", "minimal"])
@pytest.mark.parametrize("seed", SEEDS)
def test_fills_swing_bpm_bars(out_dir, which, seed):
    rules = _rules(which)
    lo, hi = _pair(out_dir, rules, seed, "fills", 0, 1)
    assert analyze(hi)["fill_bars"] > analyze(lo)["fill_bars"]

    lo, hi = _pair(out_dir, rules, seed, "swing", 52, 75)
    assert analyze(hi)["mean_offbeat_delay_ticks"] > analyze(lo)["mean_offbeat_delay_ticks"]

    lo, hi = _pair(out_dir, rules, seed, "bpm", 85, 95)
    d_lo, d_hi = analyze(lo)["duration_seconds"], analyze(hi)["duration_seconds"]
    assert d_hi == pytest.approx(d_lo * 85 / 95, abs=0.01)

    mid = generate(out_dir, f"b64-{seed}", rules, seed=seed, bars=64)[0]
    a = analyze(mid)
    assert a["bars"] == 64 and sum(s["bars"] for s in a["sections"]) == 64

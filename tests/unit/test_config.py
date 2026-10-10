import pytest

from boombap.config import ConfigError, RunConfig


def test_defaults():
    c = RunConfig.create(seed=1)
    assert (c.bpm, c.swing, c.density, c.fills, c.bars, c.bass, c.key) == (90, 58.0, 0.5, 0.5, 40, False, "Am")


@pytest.mark.parametrize(
    "kw",
    [
        {"bpm": 85}, {"bpm": 95}, {"swing": 52}, {"swing": 75}, {"density": 0}, {"density": 1},
        {"fills": 0}, {"fills": 1}, {"bars": 20}, {"bars": 256}, {"seed": 0}, {"seed": 2**63 - 1},
        {"key": "F#m"}, {"key": "Bbm"}, {"bpm": "90"}, {"seed": "42"},
    ],
)
def test_accepts_limits(kw):
    RunConfig.create(**{"seed": 1, **kw})


@pytest.mark.parametrize(
    "kw, msg",
    [
        ({"bpm": 84}, "--bpm must be between 85 and 95 (got 84)"),
        ({"bpm": 96}, "--bpm must be between 85 and 95 (got 96)"),
        ({"bpm": 120}, "--bpm must be between 85 and 95 (got 120)"),
        ({"bpm": "120"}, "--bpm must be between 85 and 95 (got 120)"),
        ({"swing": 51.9}, "--swing must be between 52 and 75 (got 51.9)"),
        ({"swing": 75.1}, "--swing must be between 52 and 75 (got 75.1)"),
        ({"density": -0.1}, "--density must be between 0 and 1 (got -0.1)"),
        ({"density": 1.5}, "--density must be between 0 and 1 (got 1.5)"),
        ({"fills": -0.1}, "--fills must be between 0 and 1 (got -0.1)"),
        ({"fills": 1.1}, "--fills must be between 0 and 1 (got 1.1)"),
        ({"bars": 16}, "--bars must be a multiple of 4 between 20 and 256 (got 16)"),
        ({"bars": 22}, "--bars must be a multiple of 4 between 20 and 256 (got 22)"),
        ({"bars": 260}, "--bars must be a multiple of 4 between 20 and 256 (got 260)"),
        ({"seed": -1}, "--seed must be a non-negative integer below 2^63 (got -1)"),
        ({"seed": 2**63}, "--seed must be a non-negative integer below 2^63 (got 9223372036854775808)"),
        ({"seed": "abc"}, "--seed must be a non-negative integer below 2^63 (got 'abc')"),
        ({"key": "A"}, "--key must be a minor key like Am, F#m or Bbm (got 'A')"),
        ({"key": "Hm"}, "--key must be a minor key like Am, F#m or Bbm (got 'Hm')"),
        ({"key": "am"}, "--key must be a minor key like Am, F#m or Bbm (got 'am')"),
    ],
)
def test_rejects(kw, msg):
    with pytest.raises(ConfigError) as e:
        RunConfig.create(**{"seed": 1, **kw})
    assert str(e.value) == msg


def test_random_seed_range():
    seeds = {RunConfig.create().seed for _ in range(20)}
    assert all(0 <= s < 2**32 for s in seeds)
    assert len(seeds) > 1

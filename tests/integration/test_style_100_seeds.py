import json
import random

import pytest

from boombap.analyze import analyze
from conftest import FIXTURES, REAL_RULES, generate

FORM = ["intro", "verso", "refrão", "verso", "outro"]


def _params(n=100):
    rng = random.Random(1234)
    for seed in range(n):
        yield seed, {
            "bpm": rng.randint(85, 95),
            "swing": round(rng.uniform(52, 75), 1),
            "density": round(rng.random(), 2),
            "fills": round(rng.random(), 2),
            "bars": rng.randrange(20, 97, 4),
            "bass": rng.random() < 0.3,
        }


@pytest.mark.parametrize("which", ["minimal", "real"])
def test_100_seeds(out_dir, which):
    rules = FIXTURES / "minimal.rules" if which == "minimal" else REAL_RULES
    if not rules.exists():
        pytest.skip("boombap.rules ausente")
    for seed, p in _params():
        mid, js, _ = generate(out_dir, f"s{seed}", rules, seed=seed, **p)
        a = analyze(mid)
        assert a["style_violations"] == [], (seed, p, a["style_violations"][:5])
        assert [s["name"] for s in a["sections"]] == FORM
        assert a["bars"] == p["bars"]
        d = json.loads(js.read_text())
        assert [s["name"] for s in d["form"]] == FORM
        assert sum(s["bars"] for s in d["form"]) == p["bars"]
        for s in d["form"]:
            assert all(b["size"] in (4, 8) and len(b["bars"]) == b["size"] for b in s["blocks"])
            assert sum(b["size"] for b in s["blocks"]) == s["bars"]

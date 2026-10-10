import json
import re
from collections import defaultdict
from pathlib import Path

import pytest

from conftest import FIXTURES, REAL_RULES, run_cli

INVALID = sorted((FIXTURES / "invalid").glob("*.rules"))


def test_text_format(minimal_rules):
    code, out, _ = run_cli("grammar", "--rules", minimal_rules, "--bars", "40")
    assert code == 0
    for header in ("Axioma", "Não-terminais", "Terminais", "Regras"):
        assert re.search(rf"^{header}$", out, re.M)
    rule_lines = re.findall(r"^  (R\.\S+)  (.+?) → (.+)  \[p=(\d\.\d{3})\]$", out, re.M)
    assert rule_lines
    sums = re.findall(r"^  Σ = (\d\.\d{3})$", out, re.M)
    assert sums and set(sums) == {"1.000"}


def test_json_format_and_sums(minimal_rules):
    code, out, _ = run_cli("grammar", "--rules", minimal_rules, "--format", "json")
    assert code == 0
    d = json.loads(out)
    assert d["axiom"] == "Música(40)"
    assert d["nonterminals"] and d["terminals"]
    sums = defaultdict(float)
    for r in d["rules"]:
        assert set(r) == {"id", "lhs", "rhs", "prob"}
        sums[r["lhs"]] += r["prob"]
    assert all(abs(s - 1) < 1e-9 for s in sums.values())


def test_max_rules(minimal_rules):
    code, out, _ = run_cli("grammar", "--rules", minimal_rules, "--bars", "100", "--max-rules", "10")
    assert code == 0
    assert re.search(r"^  … \(\+\d+ regras\)$", out, re.M)
    corpo = defaultdict(list)
    for line in out.splitlines():
        m = re.match(r"^  R\.corpo\.(\d+)\.", line)
        if m:
            corpo[m.group(1)].append(line)
    assert corpo and all(len(lines) == 10 for lines in corpo.values())


def test_density_changes_probabilities(minimal_rules):
    def opt_prob(d):
        _, out, _ = run_cli("grammar", "--rules", minimal_rules, "--density", d, "--format", "json")
        return next(r["prob"] for r in json.loads(out)["rules"] if r["id"] == "R.Opt_A.0")

    assert opt_prob("0") < opt_prob("1")


def test_bass_hooks_listed(minimal_rules):
    _, out, _ = run_cli("grammar", "--rules", minimal_rules, "--bass", "--format", "json")
    assert {"BassFirst", "BassDeg"} <= set(json.loads(out)["nonterminals"])
    _, out, _ = run_cli("grammar", "--rules", minimal_rules, "--format", "json")
    assert "BassFirst" not in json.loads(out)["nonterminals"]


def test_check_valid(minimal_rules):
    tables = [minimal_rules] + ([REAL_RULES] if REAL_RULES.exists() else [])
    for t in tables:
        code, out, err = run_cli("grammar", "--check", "--rules", t)
        assert code == 0, out
        assert out == ""


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.stem)
def test_check_invalid(path: Path):
    code, out, _ = run_cli("grammar", "--check", "--bass", "--rules", path)
    assert code == 1
    assert re.match(rf"^{re.escape(str(path))}:\d+: ", out)


def test_check_warnings_do_not_fail(minimal_rules, tmp_path):
    p = tmp_path / "w.rules"
    p.write_text(minimal_rules.read_text().replace("[0.2 + 0.6*density]", "[0.8 - 0.6*density]"))
    code, out, err = run_cli("grammar", "--check", "--rules", p)
    assert code == 0
    assert "warning: " in err and "decreases with density" in err

from pathlib import Path

import pytest

from boombap.grammar.table import check_table, load_table, parse_table

INVALID = Path(__file__).resolve().parent.parent / "fixtures" / "invalid"

EXPECTED = {
    "missing_snare12": "Groove_A does not guarantee snare@12",
    "missing_kick0_fill": "Fill_A does not guarantee kick@0",
    "no_sync_kick": "Groove_C does not guarantee a kick at a position other than 0",
    "two_grids": "Groove_A must emit exactly one grid8/grid16",
    "no_hats": "Groove_B does not guarantee a hi-hat",
    "sum_over_one": "probabilities of Tail sum to 1.2",
    "undefined_nt": "undefined nonterminal Foo",
    "fill_order": "@fill_end must be greater than @fill_mid",
    "recursion": "infinite recursion",
    "two_grooves": "@grooves must list at least 3 grooves",
    "dt_too_big": "|dt| must be <= 10",
    "missing_hook": "missing required hook HumT",
}


def expected_line(path: Path) -> int:
    for i, line in enumerate(path.read_text().splitlines(), start=1):
        if "# ERR" in line:
            return i
    return 1


def test_valid_tables(minimal_rules, real_rules):
    for p in (minimal_rules, real_rules):
        for bass in (False, True):
            errors, _ = check_table(load_table(p), bass=bass)
            assert errors == [], [str(e) for e in errors]


def test_every_invalid_fixture_is_covered():
    assert {p.stem for p in INVALID.glob("*.rules")} == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_invalid_fixture(name):
    path = INVALID / f"{name}.rules"
    errors, _ = check_table(load_table(path), bass=True)
    assert len(errors) == 1, [str(e) for e in errors]
    (e,) = errors
    assert EXPECTED[name] in e.msg
    assert e.line == expected_line(path)
    assert str(e).startswith(f"{path}:{e.line}: ")


def test_monotonicity_warning(minimal_rules):
    text = minimal_rules.read_text().replace("Opt_A -> kick@7:80 [0.2 + 0.6*density]", "Opt_A -> kick@7:80 [0.8 - 0.6*density]")
    errors, warnings = check_table(parse_table(text, "w.rules"), bass=False)
    assert errors == []
    assert any("Opt_A decreases with density" in w.msg for w in warnings)
    _, base_warnings = check_table(load_table(minimal_rules), bass=False)
    assert not any("decreases" in w.msg for w in base_warnings)

import pytest

from boombap.grammar.core import DrumHit, Grammar, Grid, HumDt, HumDv, NonTerminal, Rule, SectionMark


def test_nonterminal_identity_and_str():
    a = NonTerminal("Seção", (12, "G2", "início"))
    assert a == NonTerminal("Seção", (12, "G2", "início"))
    assert hash(a) == hash(NonTerminal("Seção", (12, "G2", "início")))
    assert a != NonTerminal("Seção", (8, "G2", "início"))
    assert str(a) == "Seção(12,G2,início)"
    assert str(NonTerminal("HumV")) == "HumV"


def test_terminal_str():
    assert str(DrumHit("kick", 6, 88)) == "kick@6:88"
    assert DrumHit("snare", 4, 100).note == 38
    assert str(Grid(16)) == "grid16"
    assert str(HumDv(3)) == "dv+3"
    assert str(HumDt(-2)) == "dt-2"
    assert str(SectionMark("verso")) == "⟨seção:verso⟩"


@pytest.mark.parametrize("p", [0, -0.1, 1.5])
def test_rule_prob_range(p):
    with pytest.raises(ValueError):
        Rule("r", NonTerminal("A"), (), p)


def _grammar(rules):
    table = {}
    for r in rules:
        table.setdefault(r.lhs, []).append(r)
    return Grammar(NonTerminal("S"), lambda nt: table.get(nt, []))


def test_validate_and_reachability():
    S, A, B, X = (NonTerminal(n) for n in "SABX")
    k = DrumHit("kick", 0, 100)
    ok = _grammar([
        Rule("1", S, (A, k), 1.0),
        Rule("2", A, (B,), 0.5), Rule("3", A, (), 0.5),
        Rule("4", B, (Grid(8),), 1.0),
        Rule("5", X, (Grid(16),), 1.0),  # inalcançável
    ])
    assert ok.validate() == []
    assert ok.nonterminals() == [S, A, B]
    assert ok.terminals() == [k, Grid(8)]

    bad_sum = _grammar([Rule("1", S, (A,), 1.0), Rule("2", A, (), 0.5), Rule("3", A, (k,), 0.4)])
    assert any("sum" in p for p in bad_sum.validate())
    missing = _grammar([Rule("1", S, (A,), 1.0)])
    assert any("no rules" in p for p in missing.validate())

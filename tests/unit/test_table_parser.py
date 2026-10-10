import pytest

from boombap.grammar.core import Degree, DrumHit, Grid, HumDt, HumDv, NonTerminal
from boombap.grammar.table import TableError, load_table, parse_table

HEAD = "@grooves = A B C\n"


def rules(text, d=0.5, f=0.5):
    return parse_table(HEAD + text, "t.rules").evaluate(d, f)


def test_loads_tables(minimal_rules, real_rules):
    for p in (minimal_rules, real_rules):
        t = load_table(p)
        assert t.rules and len(t.sha256) == 64


def test_rest_and_equal_split():
    r = rules("X -> kick@0:100 [0.3] | ε [rest]\nY -> grid8 | grid16 [0.5] | ε\n")
    assert [x.prob for x in r[NonTerminal("X")]] == pytest.approx([0.3, 0.7])
    assert [x.prob for x in r[NonTerminal("Y")]] == pytest.approx([0.25, 0.5, 0.25])
    assert r[NonTerminal("X")][1].rhs == ()
    assert [x.id for x in r[NonTerminal("Y")]] == ["R.Y.0", "R.Y.1", "R.Y.2"]


def test_comments_and_continuation():
    r = rules("X -> dv+0 [0.5]   # comentário\n   | dv-3 [rest] # outro\n# linha inteira\n\n")
    assert [str(x.rhs[0]) for x in r[NonTerminal("X")]] == ["dv+0", "dv-3"]


def test_terminals():
    r = rules("X -> kick@7:88 grid16 dv+0 dt-6 deg5 Other\nOther -> ε\n")
    rhs = r[NonTerminal("X")][0].rhs
    assert rhs == (DrumHit("kick", 7, 88), Grid(16), HumDv(0), HumDt(-6), Degree(5), NonTerminal("Other"))


def test_expressions():
    t = parse_table(HEAD + "X -> grid8 [min(1, max(0, (density + fills) / 2 - 0.1*2))] | ε [rest]\n")
    r = t.evaluate(1.0, 0.6)
    assert r[NonTerminal("X")][0].prob == pytest.approx(0.6)
    # Probabilidade 0 não é emitida.
    r0 = t.evaluate(0.0, 0.0)
    assert [x.id for x in r0[NonTerminal("X")]] == ["R.X.1"]


@pytest.mark.parametrize(
    "expr", ["__import__('os')", "density.real", "open('x')", "x", "1 ** 2", "[1][0]", "lambda: 1", "'a'"]
)
def test_unsafe_expressions_rejected(expr):
    with pytest.raises(TableError) as e:
        parse_table(HEAD + "\n\nX -> grid8 [" + expr + "] | ε [rest]\n", "bad.rules")
    assert str(e.value).startswith("bad.rules:4: ")


def test_syntax_errors_have_line():
    with pytest.raises(TableError) as e:
        parse_table("@grooves = A B C\nthis is not a rule\n", "x.rules")
    assert str(e.value).startswith("x.rules:2: ")
    with pytest.raises(TableError) as e:
        parse_table("| grid8\n", "x.rules")
    assert e.value.line == 1

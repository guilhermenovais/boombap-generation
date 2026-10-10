from math import comb

import pytest

from boombap.grammar import grammar_from_table
from boombap.grammar.core import NonTerminal
from boombap.grammar.structure import Structure
from boombap.grammar.table import load_table

INDEXED = {"Forma", "Corpo", "Seção"}


@pytest.fixture(scope="module")
def table():
    from conftest import FIXTURES

    return load_table(FIXTURES / "minimal.rules")


def _parts(rule):
    """Tamanho em compassos de cada símbolo do lado direito de uma regra indexada."""
    sizes = []
    for s in rule.rhs:
        if s.name in ("Intro", "Corpo", "Outro", "Verso", "Refrão", "FimBloco"):
            sizes.append(s.index[0])
        elif s.name == "Bloco4":
            sizes.append(4)
        elif s.name == "Bloco8":
            sizes.append(8)
    return sizes


@pytest.mark.parametrize("n", range(20, 257, 4))
def test_index_coverage(table, n):
    g = grammar_from_table(table, n, 0.5, 0.5, False)
    for nt in g.nonterminals():
        if nt.name not in INDEXED:
            continue
        k = nt.index[0]
        for r in g.rules_for(nt):
            assert sum(_parts(r)) == k, r
            if nt.name == "Corpo":
                assert all(p % 4 == 0 and p >= 4 for p in _parts(r))
    assert g.validate() == []


@pytest.mark.parametrize("d", [0, 0.5, 1])
@pytest.mark.parametrize("f", [0, 0.5, 1])
@pytest.mark.parametrize("n", [20, 40, 100, 256])
def test_sums(table, n, d, f):
    assert grammar_from_table(table, n, d, f, True).validate() == []


def test_corpo_rule_count(table):
    s = Structure(table, 0.5, 0.5)
    # a + b + c = 248 em múltiplos de 4 (≥ 4): composições de 62 em 3 partes.
    assert len(s.rules_for(NonTerminal("Corpo", (248,)))) == comb(61, 2)
    assert len(s.rules_for(NonTerminal("Corpo", (240,)))) == comb(59, 2) == 1711


def test_section_grooves(table):
    s = Structure(table, 0.5, 0.5)
    rules = s.rules_for(NonTerminal("Verso", (12,)))
    assert len({r.rhs[1].index[1] for r in rules}) >= 3


@pytest.mark.parametrize("f", [0, 0.25, 0.5, 0.75, 1])
def test_fill_end_beats_fill_mid(table, f):
    s = Structure(table, 0.5, f)
    end = s.rules_for(NonTerminal("FimBloco", (4, "A")))
    mid = s.rules_for(NonTerminal("Compasso", ("A", "meio", "normal")))
    p_end = sum(r.prob for r in end if r.id.endswith(".virada"))
    p_mid = sum(r.prob for r in mid if r.id.endswith(".virada"))
    assert p_end > p_mid

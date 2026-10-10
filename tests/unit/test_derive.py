import math

import pytest

from boombap.config import RunConfig
from boombap.derive import DerivationNode, TerminalRef, derive
from boombap.grammar import build_grammar
from boombap.grammar.core import DrumHit


def _derive(rules, **kw):
    cfg = RunConfig.create(**{"seed": 3, **kw})
    return derive(build_grammar(cfg, rules), cfg.seed, cfg)


def _nodes(node):
    yield node
    for ch in node.children:
        if isinstance(ch, DerivationNode):
            yield from _nodes(ch)


def _sig(node):
    return (node.symbol, node.rule.id, node.u, [
        _sig(c) if isinstance(c, DerivationNode) else str(c.terminal) for c in node.children
    ])


def test_deterministic(minimal_rules):
    assert _sig(_derive(minimal_rules).tree) == _sig(_derive(minimal_rules).tree)
    assert _sig(_derive(minimal_rules).tree) != _sig(_derive(minimal_rules, seed=4).tree)


@pytest.mark.parametrize("seed", range(20))
def test_terminates_and_u_range(minimal_rules, seed):
    d = _derive(minimal_rules, seed=seed)
    nodes = list(_nodes(d.tree))
    assert all(0 <= n.u < 1 for n in nodes)
    assert d.log_prob == pytest.approx(sum(math.log(n.prob) for n in nodes))


def test_hum_after_every_drum_hit(minimal_rules):
    for node in _nodes(_derive(minimal_rules).tree):
        ch = node.children
        for i, c in enumerate(ch):
            if isinstance(c, TerminalRef) and isinstance(c.terminal, DrumHit):
                assert ch[i + 1].symbol == "HumV" and ch[i + 2].symbol == "HumT"


def _drum_terminals(d):
    return {(t.path, str(t.terminal)) for t in d.terminals if isinstance(t.terminal, DrumHit)}


def _fill_bars(d):
    return sum(1 for n in _nodes(d.tree) if n.symbol.startswith("Compasso(") and n.children[1].symbol.startswith("Fill_"))


@pytest.mark.parametrize("seed", range(10))
def test_monotonic_density_and_fills(minimal_rules, seed):
    lo = _derive(minimal_rules, seed=seed, density=0)
    hi = _derive(minimal_rules, seed=seed, density=1)
    assert _drum_terminals(lo) <= _drum_terminals(hi)
    assert _fill_bars(_derive(minimal_rules, seed=seed, fills=0)) <= _fill_bars(_derive(minimal_rules, seed=seed, fills=1))

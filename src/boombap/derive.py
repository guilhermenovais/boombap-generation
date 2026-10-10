"""Motor de derivação com um uniforme por nó, obtido de sha256(semente | caminho) (R7)."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field

from boombap import __version__
from boombap.grammar.core import DrumHit, Grammar, NonTerminal, Rule, Terminal

HUM_V, HUM_T = NonTerminal("HumV"), NonTerminal("HumT")
BASS_FIRST, BASS_DEG = NonTerminal("BassFirst"), NonTerminal("BassDeg")


class DerivationError(RuntimeError):
    pass


@dataclass
class TerminalRef:
    terminal: Terminal
    path: str
    # Ganchos expandidos pelo motor logo após um terminal de bateria.
    hum_v: "DerivationNode | None" = None
    hum_t: "DerivationNode | None" = None
    bass: "DerivationNode | None" = None


@dataclass
class DerivationNode:
    nt: NonTerminal
    rule: Rule
    u: float
    children: list = field(default_factory=list)

    @property
    def symbol(self) -> str:
        return str(self.nt)

    @property
    def prob(self) -> float:
        return self.rule.prob

    def hook_terminal(self) -> Terminal:
        """Terminal único produzido por um gancho (HumV, HumT, BassFirst, BassDeg)."""
        return self.children[0].terminal


@dataclass
class Derivation:
    seed: int
    config: object
    rules_sha256: str
    grammar_version: str
    log_prob: float
    tree: DerivationNode
    terminals: list[TerminalRef]

    def to_json(self, sections) -> str:
        c = self.config
        data = {
            "format": "boombap-derivation",
            "version": self.grammar_version,
            "seed": self.seed,
            "rules_sha256": self.rules_sha256,
            "config": {
                "bpm": c.bpm,
                "swing": c.swing,
                "density": c.density,
                "fills": c.fills,
                "bars": c.bars,
                "bass": c.bass,
                "key": c.key,
            },
            "form": [
                {
                    "name": s.kind,
                    "start_bar": s.start_bar,
                    "bars": s.n_bars,
                    "groove": s.groove,
                    "blocks": [
                        {
                            "size": b.size,
                            "bars": [{"index": bar.index, "kind": bar.kind, "hat_grid": bar.hat_grid} for bar in b.bars],
                        }
                        for b in s.blocks
                    ],
                }
                for s in sections
            ],
            "log_prob": self.log_prob,
            "tree": _node_json(self.tree),
        }
        return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def _node_json(node: DerivationNode) -> dict:
    return {
        "symbol": node.symbol,
        "rule": node.rule.id,
        "prob": node.prob,
        "u": node.u,
        "children": [_node_json(ch) if isinstance(ch, DerivationNode) else {"t": str(ch.terminal)} for ch in node.children],
    }


def uniform(seed: int, path: str) -> float:
    digest = hashlib.sha256(f"{seed}|{path}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def choose(rules: list[Rule], u: float) -> Rule:
    """CDF inversa sobre as regras, na ordem da tabela."""
    acc = 0.0
    for rule in rules:
        acc += rule.prob
        if u < acc:
            return rule
    return rules[-1]


def derive(grammar: Grammar, seed: int, config=None, bass: bool | None = None) -> Derivation:
    """Expande o axioma em profundidade, da esquerda para a direita.

    O caminho de um nó é a sequência de índices de filho (posição no lado
    direito da regra) desde a raiz; os ganchos ficam fora dessa numeração
    (sufixos `v`, `t`, `b`), assim o `u` de nenhum nó de bateria muda quando
    o baixo é ligado ou quando um estado de índice muda (R7, R10).
    """
    if bass is None:
        bass = bool(getattr(config, "bass", False))
    terminals: list[TerminalRef] = []
    log_prob = 0.0

    def expand(nt: NonTerminal, path: str) -> DerivationNode:
        nonlocal log_prob
        rules = grammar.rules_for(nt)
        if not rules:
            raise DerivationError(f"no rules for {nt}")
        u = uniform(seed, path)
        rule = choose(rules, u)
        log_prob += math.log(rule.prob)
        node = DerivationNode(nt, rule, u)
        for i, sym in enumerate(rule.rhs):
            child_path = f"{path}/{i}"
            if isinstance(sym, NonTerminal):
                node.children.append(expand(sym, child_path))
                continue
            ref = TerminalRef(sym, child_path)
            node.children.append(ref)
            terminals.append(ref)
            if isinstance(sym, DrumHit):
                ref.hum_v = expand(HUM_V, child_path + "v")
                ref.hum_t = expand(HUM_T, child_path + "t")
                node.children += [ref.hum_v, ref.hum_t]
                if bass and sym.piece == "kick":
                    ref.bass = expand(BASS_FIRST if sym.pos == 0 else BASS_DEG, child_path + "b")
                    node.children.append(ref.bass)
        return node

    tree = expand(grammar.axiom, "")
    return Derivation(
        seed=seed,
        config=config,
        rules_sha256=grammar.rules_sha256,
        grammar_version=__version__,
        log_prob=log_prob,
        tree=tree,
        terminals=terminals,
    )

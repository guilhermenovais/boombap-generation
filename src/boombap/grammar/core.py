"""Núcleo formal genérico da gramática: símbolos, regras e gramática (sem valores musicais)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Iterable

EPSILON = "ε"
PROB_TOL = 1e-9

# Mapa General MIDI de percussão (FR-016).
GM_NOTES = {"kick": 36, "rim": 37, "snare": 38, "hhc": 42, "hho": 46, "crash": 49}
DEGREES = (1, 3, 4, 5, 7)
SECTION_KINDS = ("intro", "verso", "refrão", "outro")
MAX_DT = 10


@dataclass(frozen=True)
class NonTerminal:
    name: str
    index: tuple = ()

    def __str__(self) -> str:
        if not self.index:
            return self.name
        return f"{self.name}({','.join(str(i) for i in self.index)})"


class Terminal:
    """Base dos terminais; cada subclasse define `__str__`."""


@dataclass(frozen=True)
class DrumHit(Terminal):
    piece: str
    pos: int
    vel: int

    @property
    def note(self) -> int:
        return GM_NOTES[self.piece]

    def __str__(self) -> str:
        return f"{self.piece}@{self.pos}:{self.vel}"


@dataclass(frozen=True)
class Grid(Terminal):
    n: int

    def __str__(self) -> str:
        return f"grid{self.n}"


@dataclass(frozen=True)
class HumDv(Terminal):
    n: int

    def __str__(self) -> str:
        return f"dv{self.n:+d}"


@dataclass(frozen=True)
class HumDt(Terminal):
    n: int

    def __str__(self) -> str:
        return f"dt{self.n:+d}"


@dataclass(frozen=True)
class Degree(Terminal):
    n: int

    def __str__(self) -> str:
        return f"deg{self.n}"


@dataclass(frozen=True)
class SectionMark(Terminal):
    kind: str

    def __str__(self) -> str:
        return f"⟨seção:{self.kind}⟩"


def terminal_problem(t: Terminal) -> str | None:
    """Descrição do problema de faixa de um terminal, ou None se estiver ok."""
    if isinstance(t, DrumHit):
        if t.piece not in GM_NOTES:
            return f"unknown drum piece {t.piece!r}"
        if not 0 <= t.pos <= 15:
            return f"{t}: position must be between 0 and 15"
        if not 1 <= t.vel <= 127:
            return f"{t}: velocity must be between 1 and 127"
    elif isinstance(t, Grid):
        if t.n not in (8, 16):
            return f"{t}: grid must be grid8 or grid16"
    elif isinstance(t, HumDt):
        if abs(t.n) > MAX_DT:
            return f"{t}: |dt| must be <= {MAX_DT} ticks"
    elif isinstance(t, Degree):
        if t.n not in DEGREES:
            return f"{t}: degree must be one of {DEGREES}"
    elif isinstance(t, SectionMark):
        if t.kind not in SECTION_KINDS:
            return f"{t}: unknown section kind"
    return None


Symbol = NonTerminal | Terminal


def rhs_str(rhs: Iterable[Symbol]) -> str:
    parts = [str(s) for s in rhs]
    return " ".join(parts) if parts else EPSILON


@dataclass(frozen=True)
class Rule:
    id: str
    lhs: NonTerminal
    rhs: tuple
    prob: float

    def __post_init__(self):
        if not (0 < self.prob <= 1 + PROB_TOL):
            raise ValueError(f"rule {self.id}: probability must be in (0, 1] (got {self.prob})")

    def __str__(self) -> str:
        return f"{self.lhs} → {rhs_str(self.rhs)}  [p={self.prob:.3f}]"


class Grammar:
    """Gramática com regras geradas sob demanda e memorizadas (R4).

    `extra_roots` são os ganchos que o motor expande fora do lado direito das
    regras (humanização e baixo); entram no fechamento como se fossem alcançáveis.
    """

    def __init__(
        self,
        axiom: NonTerminal,
        rule_provider: Callable[[NonTerminal], list[Rule]],
        source: str = "",
        extra_roots: tuple = (),
        rules_sha256: str = "",
    ):
        self.axiom = axiom
        self._provider = rule_provider
        self.source = source
        self.extra_roots = tuple(extra_roots)
        self.rules_sha256 = rules_sha256
        self._cache: dict[NonTerminal, list[Rule]] = {}
        self._reach: tuple[list[NonTerminal], list[Terminal]] | None = None

    def rules_for(self, nt: NonTerminal) -> list[Rule]:
        rules = self._cache.get(nt)
        if rules is None:
            rules = list(self._provider(nt))
            self._cache[nt] = rules
        return rules

    def _closure(self) -> tuple[list[NonTerminal], list[Terminal]]:
        if self._reach is None:
            seen_nt: dict[NonTerminal, None] = {}
            seen_t: dict[Terminal, None] = {}
            queue = deque([self.axiom, *self.extra_roots])
            for nt in queue:
                seen_nt.setdefault(nt)
            while queue:
                nt = queue.popleft()
                for rule in self.rules_for(nt):
                    for sym in rule.rhs:
                        if isinstance(sym, NonTerminal):
                            if sym not in seen_nt:
                                seen_nt[sym] = None
                                queue.append(sym)
                        else:
                            seen_t.setdefault(sym)
            self._reach = (list(seen_nt), list(seen_t))
        return self._reach

    def nonterminals(self) -> list[NonTerminal]:
        """Não-terminais alcançáveis a partir do axioma, em ordem BFS determinística."""
        return list(self._closure()[0])

    def terminals(self) -> list[Terminal]:
        """Terminais alcançáveis, na ordem em que aparecem na BFS."""
        return list(self._closure()[1])

    def rules(self) -> list[Rule]:
        return [r for nt in self.nonterminals() for r in self.rules_for(nt)]

    def validate(self) -> list[str]:
        """Violações das invariantes 1 e 2 (soma = 1, todo NT alcançável tem regra)."""
        problems = []
        for nt in self.nonterminals():
            rules = self.rules_for(nt)
            if not rules:
                problems.append(f"{nt}: no rules")
                continue
            total = sum(r.prob for r in rules)
            if abs(total - 1) > PROB_TOL:
                problems.append(f"{nt}: probabilities sum to {total!r}")
        return problems

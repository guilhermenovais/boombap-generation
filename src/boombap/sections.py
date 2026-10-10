"""Vistas derivadas da árvore: seções, blocos, compassos e eventos de bateria."""

from __future__ import annotations

from dataclasses import dataclass, field

from boombap.derive import Derivation, DerivationNode, TerminalRef
from boombap.grammar.core import DrumHit, Grid, SectionMark
from boombap.grammar.structure import BLOCO4, BLOCO8, COMPASSO, FIMBLOCO, SECAO, SECTION_KIND


@dataclass
class DrumEvent:
    piece: str
    pos: int
    velocity: int
    dv: int
    dt: int
    bass_degree: int | None = None


@dataclass
class Bar:
    index: int
    kind: str  # "groove" | "fill"
    hat_grid: int
    events: list[DrumEvent]
    is_block_end: bool


@dataclass
class Block:
    size: int
    bars: list[Bar] = field(default_factory=list)


@dataclass
class Section:
    kind: str
    start_bar: int
    n_bars: int
    groove: str
    blocks: list[Block] = field(default_factory=list)

    @property
    def bars(self) -> list[Bar]:
        return [bar for b in self.blocks for bar in b.bars]


def _bar(node: DerivationNode, index: int, is_block_end: bool) -> Bar:
    hook = node.children[1]
    kind = "fill" if hook.nt.name.startswith("Fill_") else "groove"
    events: list[DrumEvent] = []
    grids: list[int] = []

    def walk(n: DerivationNode):
        for ch in n.children:
            if isinstance(ch, DerivationNode):
                walk(ch)
                continue
            t = ch.terminal
            if isinstance(t, Grid):
                grids.append(t.n)
            elif isinstance(t, DrumHit):
                events.append(_event(ch, t))

    walk(node)
    if len(grids) != 1:
        raise ValueError(f"bar {index}: expected exactly one grid terminal, got {len(grids)}")
    return Bar(index, kind, grids[0], events, is_block_end)


def _event(ref: TerminalRef, t: DrumHit) -> DrumEvent:
    return DrumEvent(
        piece=t.piece,
        pos=t.pos,
        velocity=t.vel,
        dv=ref.hum_v.hook_terminal().n,
        dt=ref.hum_t.hook_terminal().n,
        bass_degree=ref.bass.hook_terminal().n if ref.bass else None,
    )


def _section(node: DerivationNode, start_bar: int) -> Section:
    mark, secao = node.children
    assert isinstance(mark, TerminalRef) and isinstance(mark.terminal, SectionMark)
    k, groove, _ = secao.nt.index
    sec = Section(mark.terminal.kind, start_bar, k, groove)
    bar_index = start_bar
    current = secao
    while current.children:  # Seção(0, …) → ε
        bloco, fim = current.children
        assert bloco.nt.name in (BLOCO4, BLOCO8) and fim.nt.name == FIMBLOCO
        block = Block(4 if bloco.nt.name == BLOCO4 else 8)
        for comp in bloco.children:
            block.bars.append(_bar(comp, bar_index, False))
            bar_index += 1
        last, current = fim.children
        assert last.nt.name == COMPASSO and current.nt.name == SECAO
        block.bars.append(_bar(last, bar_index, True))
        bar_index += 1
        sec.blocks.append(block)
    return sec


def extract(derivation: Derivation) -> list[Section]:
    """Percorre a árvore em ordem e devolve as seções com blocos e compassos."""
    sections: list[Section] = []
    start = 0

    def walk(node: DerivationNode):
        nonlocal start
        if node.nt.name in SECTION_KIND:
            sec = _section(node, start)
            sections.append(sec)
            start += sec.n_bars
            return
        for ch in node.children:
            if isinstance(ch, DerivationNode):
                walk(ch)

    walk(derivation.tree)
    return sections

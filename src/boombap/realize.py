"""Realização dos terminais em notas no tempo: swing MPC, humanização, clamp e dedup (R8)."""

from __future__ import annotations

from dataclasses import dataclass

from boombap.grammar.core import GM_NOTES

PPQ = 480
STEP = 120
BAR = 1920
NOTE_LEN = 60
BASS_MAX_LEN = 480
DRUM_CHANNEL = 9
BASS_CHANNEL = 0

PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MINOR_DEGREES = {1: 0, 3: 3, 4: 5, 5: 7, 7: 10}


@dataclass(frozen=True)
class TimedNote:
    tick_on: int
    tick_off: int
    channel: int
    note: int
    velocity: int


def swing_delay(pos: int, hat_grid: int, swing: float) -> int:
    """Atraso das posições fracas da grade do chimbal do compasso."""
    if hat_grid == 16 and pos % 2 == 1:
        return round((swing / 100 - 0.5) * 2 * STEP)
    if hat_grid == 8 and pos in (2, 6, 10, 14):
        return round((swing / 100 - 0.5) * 2 * 2 * STEP)
    return 0


def _clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def _dedup(events):
    """Um evento por (peça, posição) no compasso, mantendo a maior velocity (empate: o primeiro)."""
    kept: dict[tuple[str, int], tuple[int, object]] = {}
    for ev in events:
        vel = _clamp(ev.velocity + ev.dv, 1, 127)
        key = (ev.piece, ev.pos)
        if key not in kept or vel > kept[key][0]:
            kept[key] = (vel, ev)
    return list(kept.values())


def _tick(bar_index: int, pos: int, hat_grid: int, swing: float, dt: int) -> int:
    start = bar_index * BAR
    return max(0, _clamp(start + pos * STEP + swing_delay(pos, hat_grid, swing) + dt, start, start + BAR - 1))


def _realized(sections, swing: float):
    """(tick_on, velocity, evento) de cada evento após dedup, compasso a compasso."""
    for sec in sections:
        for bar in sec.bars:
            for vel, ev in _dedup(bar.events):
                yield bar, _tick(bar.index, ev.pos, bar.hat_grid, swing, ev.dt), vel, ev


def realize(sections, swing: float) -> list[TimedNote]:
    notes = []
    for bar, on, vel, ev in _realized(sections, swing):
        off = min(on + NOTE_LEN, (bar.index + 1) * BAR)
        notes.append(TimedNote(on, off, DRUM_CHANNEL, GM_NOTES[ev.piece], vel))
    return sorted(notes, key=lambda n: (n.tick_on, n.note))


def key_root(key: str) -> int:
    """Nota MIDI da tônica na oitava 2 (A2 = 45)."""
    name = key[:-1]
    pc = PITCH_CLASS[name[0]] + (1 if name[1:] == "#" else -1 if name[1:] == "b" else 0)
    return 36 + pc % 12


def realize_bass(sections, key: str, swing: float, total_bars: int) -> list[TimedNote]:
    """Uma nota por ataque de bumbo, no grau decidido por BassFirst/BassDeg (R10)."""
    root = key_root(key)
    kicks = sorted(
        (on, vel, ev.bass_degree)
        for _, on, vel, ev in _realized(sections, swing)
        if ev.piece == "kick" and ev.bass_degree is not None
    )
    attacks = []
    for on, vel, deg in kicks:
        if attacks and attacks[-1][0] == on:
            continue  # dois bumbos no mesmo tick: uma nota de baixo só
        attacks.append((on, vel, deg))
    end = total_bars * BAR
    notes = []
    for i, (on, vel, deg) in enumerate(attacks):
        nxt = attacks[i + 1][0] if i + 1 < len(attacks) else end
        off = min(nxt, on + BASS_MAX_LEN, end)
        notes.append(TimedNote(on, off, BASS_CHANNEL, root + MINOR_DEGREES[deg], vel))
    return notes

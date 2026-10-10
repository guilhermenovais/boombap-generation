"""Métricas e violações de estilo de um MIDI gerado (SC-001, SC-004)."""

from __future__ import annotations

from collections import defaultdict

from boombap.grammar.core import GM_NOTES
from boombap.midi_io import read_song

FORM = ["intro", "verso", "refrão", "verso", "outro"]
ALLOWED_NOTES = set(GM_NOTES.values())
METRIC_NAMES = {36: "kick", 38: "snare", 37: "rim", 42: "hh_closed", 46: "hh_open", 49: "crash"}
WEAK_8 = (2, 6, 10, 14)


def is_weak(pos: int, hat_grid: int) -> bool:
    return pos % 2 == 1 if hat_grid == 16 else pos in WEAK_8


def analyze(path) -> dict:
    song = read_song(path)
    bars = song.bars
    bpm = song.bpm
    violations: list[str] = []

    # FR-014
    if len(song.tempos) != 1:
        violations.append(f"global: expected exactly one tempo event (found {len(song.tempos)})")
    if bpm is not None and not 85 <= round(bpm) <= 95:
        violations.append(f"global: tempo {bpm:g} bpm outside 85-95")
    if song.time_signatures != ["4/4"]:
        violations.append(f"global: time signature must be a single 4/4 (found {song.time_signatures})")
    # FR-004
    names = [name for name, _ in song.sections]
    if names != FORM:
        violations.append(f"global: sections {names} are not {FORM}")
    # FR-016
    bad_channel = sorted({n.channel for n in song.drum_notes if n.channel != 9})
    if bad_channel:
        violations.append(f"global: drum notes on channel(s) {[c + 1 for c in bad_channel]}, expected 10")
    bad_notes = sorted({n.note for n in song.drum_notes if n.note not in ALLOWED_NOTES})
    if bad_notes:
        violations.append(f"global: drum notes {bad_notes} outside the General MIDI kit map")

    by_bar: dict[int, list] = defaultdict(list)
    for n in song.drum_notes:
        by_bar[n.bar].append(n)
    weak_delays: list[int] = []
    for b in range(bars):
        notes = by_bar.get(b, [])
        hits = {(n.note, n.pos) for n in notes}
        grid = song.hat_grid.get(b)
        # FR-011
        if (36, 0) not in hits:
            violations.append(f"bar {b}: missing kick on position 0")
        if (38, 4) not in hits:
            violations.append(f"bar {b}: missing snare on position 4")
        if b not in song.fill_bars and (38, 12) not in hits:
            violations.append(f"bar {b}: missing snare on position 12")
        # FR-013
        if not any(n.note in (42, 46) for n in notes):
            violations.append(f"bar {b}: no hi-hat")
        # FR-015
        if grid is None:
            violations.append(f"bar {b}: no grid8/grid16 cue marker")
            continue
        delays = [n.delay for n in notes if is_weak(n.pos, grid)]
        weak_delays += delays
        if delays and sum(delays) / len(delays) <= 0:
            violations.append(f"bar {b}: weak positions of grid{grid} are not delayed (no swing)")

    counts = {name: 0 for name in METRIC_NAMES.values()}
    for n in song.drum_notes:
        if n.note in METRIC_NAMES:
            counts[METRIC_NAMES[n.note]] += 1
    starts = [(name, start) for name, start in song.sections]
    sections = [
        {"name": name, "start_bar": start, "bars": (starts[i + 1][1] if i + 1 < len(starts) else bars) - start}
        for i, (name, start) in enumerate(starts)
    ]
    return {
        "bpm": bpm,
        "time_signature": song.time_signatures[0] if song.time_signatures else None,
        "bars": bars,
        "duration_seconds": round(bars * 4 * 60 / bpm, 2) if bpm else None,
        "sections": sections,
        "notes_per_bar": {k: round(v / bars, 2) if bars else 0.0 for k, v in counts.items()},
        "fill_bars": len(song.fill_bars),
        "mean_offbeat_delay_ticks": round(sum(weak_delays) / len(weak_delays), 2) if weak_delays else 0.0,
        "style_violations": violations,
        "record": song.record,
    }

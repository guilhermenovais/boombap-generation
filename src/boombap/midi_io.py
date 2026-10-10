"""Escrita e leitura do MIDI gerado (contracts/midi-output.md)."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import mido

from boombap.config import ConfigError, RunConfig, parse_record
from boombap.realize import BAR, BASS_CHANNEL, PPQ, STEP, TimedNote, swing_delay

BASS_PROGRAM = 33  # GM 34 (Electric Bass, pick) em base 0


def _to_track(name: str, events: list[tuple[int, mido.Message | mido.MetaMessage]], end: int) -> mido.MidiTrack:
    """Converte (tick absoluto, mensagem) — já em ordem — em trilha com tempos delta."""
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("track_name", name=name, time=0))
    now = 0
    for tick, msg in events:
        track.append(msg.copy(time=tick - now))
        now = tick
    track.append(mido.MetaMessage("end_of_track", time=max(0, end - now)))
    return track


def _note_events(notes: list[TimedNote]) -> list[tuple[int, mido.Message]]:
    raw = []
    for n in notes:
        raw.append((n.tick_on, 1, n.note, mido.Message("note_on", channel=n.channel, note=n.note, velocity=n.velocity)))
        raw.append((n.tick_off, 0, n.note, mido.Message("note_off", channel=n.channel, note=n.note, velocity=0)))
    # note_off antes de note_on no mesmo tick; depois por nota (ordem determinística).
    raw.sort(key=lambda e: (e[0], e[1], e[2]))
    return [(tick, msg) for tick, _, _, msg in raw]


def build_midi(config: RunConfig, sections, notes: list[TimedNote], version: str, bass_notes=None) -> mido.MidiFile:
    end = config.bars * BAR
    conductor: list[tuple[int, mido.MetaMessage]] = [
        (0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(config.bpm))),
        (0, mido.MetaMessage("time_signature", numerator=4, denominator=4)),
        (0, mido.MetaMessage("text", text=config.record(version))),
    ]
    for sec in sections:
        conductor.append((sec.start_bar * BAR, mido.MetaMessage("marker", text=sec.kind)))
        for bar in sec.bars:
            tick = bar.index * BAR
            if bar.kind == "fill":
                conductor.append((tick, mido.MetaMessage("text", text="fill")))
            conductor.append((tick, mido.MetaMessage("cue_marker", text=f"grid{bar.hat_grid}")))

    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    mid.tracks.append(_to_track("boombap", conductor, end))
    mid.tracks.append(_to_track("drums", _note_events(notes), end))
    if bass_notes:
        events = [(0, mido.Message("program_change", channel=BASS_CHANNEL, program=BASS_PROGRAM))]
        events += _note_events(bass_notes)
        mid.tracks.append(_to_track("bass", events, end))
    return mid


def to_bytes(mid: mido.MidiFile) -> bytes:
    buf = io.BytesIO()
    mid.save(file=buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Leitura (usada por analyze e pelos testes)
# ---------------------------------------------------------------------------


@dataclass
class ParsedNote:
    tick: int
    channel: int
    note: int
    velocity: int
    bar: int
    pos: int
    delay: int  # tick − (bar·1920 + pos·120)


@dataclass
class ParsedSong:
    tempos: list[float]
    time_signatures: list[str]
    record: str | None
    config: RunConfig | None
    sections: list[tuple[str, int]]
    bars: int
    hat_grid: dict[int, int]
    fill_bars: set[int]
    drum_notes: list[ParsedNote] = field(default_factory=list)
    bass_notes: list[ParsedNote] = field(default_factory=list)
    track_names: list[str] = field(default_factory=list)

    @property
    def bpm(self) -> float | None:
        return self.tempos[0] if self.tempos else None


def _abs_events(track):
    now = 0
    for msg in track:
        now += msg.time
        yield now, msg


def grid_position(offset: int, hat_grid: int, swing: float) -> int:
    """Posição de grade mais próxima, desfazendo o swing esperado (empate: a menor)."""
    best, best_err = 0, None
    for p in range(16):
        err = abs(offset - (p * STEP + swing_delay(p, hat_grid, swing)))
        if best_err is None or err < best_err:
            best, best_err = p, err
    return best


def read_song(path) -> ParsedSong:
    mid = mido.MidiFile(str(path))
    tempos, sigs, sections = [], [], []
    record = None
    hat_grid: dict[int, int] = {}
    fills: set[int] = set()
    end = 0
    names = [next((m.name for m in track if m.type == "track_name"), None) for track in mid.tracks]
    for track in mid.tracks:
        for tick, _ in _abs_events(track):
            end = max(end, tick)
    conductor = mid.tracks[0] if mid.tracks else []
    for tick, msg in _abs_events(conductor):
        if msg.type == "set_tempo":
            tempos.append(round(mido.tempo2bpm(msg.tempo), 2))
        elif msg.type == "time_signature":
            sigs.append(f"{msg.numerator}/{msg.denominator}")
        elif msg.type == "text" and msg.text.startswith("boombap v"):
            record = msg.text
        elif msg.type == "text" and msg.text == "fill":
            fills.add(tick // BAR)
        elif msg.type == "marker":
            sections.append((msg.text, tick // BAR))
        elif msg.type == "cue_marker" and msg.text in ("grid8", "grid16"):
            hat_grid[tick // BAR] = int(msg.text[4:])
    config = None
    if record:
        try:
            config = parse_record(record)
        except ConfigError:
            config = None
    swing = config.swing if config else 50.0
    bars = -(-end // BAR)

    def notes_of(track) -> list[ParsedNote]:
        out = []
        for tick, msg in _abs_events(track):
            if msg.type == "note_on" and msg.velocity > 0:
                bar = tick // BAR
                offset = tick - bar * BAR
                pos = grid_position(offset, hat_grid.get(bar, 16), swing)
                out.append(ParsedNote(tick, msg.channel, msg.note, msg.velocity, bar, pos, offset - pos * STEP))
        return out

    song = ParsedSong(tempos, sigs, record, config, sections, bars, hat_grid, fills, track_names=names)
    for track, name in zip(mid.tracks, names):
        if name == "drums":
            song.drum_notes = notes_of(track)
        elif name == "bass":
            song.bass_notes = notes_of(track)
    return song

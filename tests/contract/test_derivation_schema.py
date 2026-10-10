import json

import jsonschema
import pytest

from boombap.midi_io import read_song
from conftest import SCHEMA, generate, run_cli

GM = {"kick": 36, "rim": 37, "snare": 38, "hhc": 42, "hho": 46, "crash": 49}


def _bars_of_tree(tree):
    """Eventos de bateria (peça, compasso, posição) da árvore, em ordem, após dedup."""
    bars = []

    def walk(node):
        if node["symbol"].startswith("Compasso("):
            bars.append(set())
            current = bars[-1]

            def collect(n):
                for ch in n["children"]:
                    if "t" in ch:
                        name, _, rest = ch["t"].partition("@")
                        if name in GM:
                            current.add((GM[name], int(rest.split(":")[0])))
                    else:
                        collect(ch)

            collect(node)
            return
        for ch in node["children"]:
            if "t" not in ch:
                walk(ch)

    walk(tree)
    return {(note, b, pos) for b, events in enumerate(bars) for note, pos in events}


@pytest.mark.parametrize("seed", range(10))
def test_schema_and_consistency(out_dir, seed):
    schema = json.loads(SCHEMA.read_text())
    bass = seed % 2 == 1
    mid, js, _ = generate(out_dir, f"s{seed}", seed=seed, bass=bass)
    d = json.loads(js.read_text())
    jsonschema.Draft202012Validator(schema).validate(d)

    song = read_song(mid)
    midi_events = {(n.note, n.bar, n.pos) for n in song.drum_notes}
    tree_events = _bars_of_tree(d["tree"])
    assert len(song.drum_notes) == len(tree_events)
    assert midi_events == tree_events

    assert [(s["name"], s["start_bar"]) for s in d["form"]] == song.sections

    _, out, _ = run_cli("grammar", "--format", "json", "--bars", "40", "--density", d["config"]["density"],
                        "--fills", d["config"]["fills"], *(["--bass"] if bass else []))
    ids = {r["id"] for r in json.loads(out)["rules"]}

    def rules(n):
        yield n["rule"]
        for ch in n["children"]:
            if "t" not in ch:
                yield from rules(ch)

    assert set(rules(d["tree"])) <= ids

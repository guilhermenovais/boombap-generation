"""Linha de comando `boombap`: generate | grammar | analyze | render (contracts/cli.md)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from boombap import __version__
from boombap.config import ConfigError, RunConfig

EXIT_OK, EXIT_IO, EXIT_USAGE = 0, 1, 2


def _error(msg: str, code: int) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return code


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="boombap", description="Gerador de batidas boom bap por gramática probabilística.")
    p.add_argument("--version", action="version", version=f"boombap {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    # Os hiperparâmetros são lidos como texto: a mensagem de faixa vem sempre de RunConfig.
    g = sub.add_parser("generate", help="gera uma música (.mid + .json)")
    g.add_argument("-o", "--output", required=True, metavar="PATH")
    g.add_argument("--seed")
    g.add_argument("--bpm", default="90")
    g.add_argument("--swing", default="58")
    g.add_argument("--density", default="0.5")
    g.add_argument("--fills", default="0.5")
    g.add_argument("--bars", default="40")
    g.add_argument("--bass", action="store_true")
    g.add_argument("--key", default="Am")
    g.add_argument("--rules", metavar="PATH")

    gr = sub.add_parser("grammar", help="lista ou verifica a gramática formal")
    gr.add_argument("--bars", default="40")
    gr.add_argument("--density", default="0.5")
    gr.add_argument("--fills", default="0.5")
    gr.add_argument("--bass", action="store_true")
    gr.add_argument("--key", default="Am")
    gr.add_argument("--rules", metavar="PATH")
    gr.add_argument("--format", choices=("text", "json"), default="text")
    gr.add_argument("--max-rules", type=int, metavar="INT")
    gr.add_argument("--check", action="store_true")

    a = sub.add_parser("analyze", help="métricas e violações de estilo de um MIDI gerado")
    a.add_argument("path", metavar="PATH.mid")
    a.add_argument("--format", choices=("text", "json"), default="text")

    r = sub.add_parser("render", help="converte o MIDI em áudio com fluidsynth")
    r.add_argument("path", metavar="PATH.mid")
    r.add_argument("-o", "--output", metavar="OUT")
    r.add_argument("--soundfont", metavar="SF2")
    r.add_argument("--sample-rate", type=int, default=44100)
    return p


def _generate(args) -> int:
    from boombap.derive import derive
    from boombap.grammar import TableError, build_grammar
    from boombap.midi_io import build_midi, to_bytes
    from boombap.output import OutputError, output_paths, write_outputs
    from boombap.realize import realize, realize_bass
    from boombap.sections import extract

    try:
        cfg = RunConfig.create(
            seed=args.seed,
            bpm=args.bpm,
            swing=args.swing,
            density=args.density,
            fills=args.fills,
            bars=args.bars,
            bass=args.bass,
            key=args.key,
        )
    except ConfigError as e:
        return _error(str(e), EXIT_USAGE)
    try:
        grammar = build_grammar(cfg, args.rules)
    except TableError as e:
        return _error(str(e), EXIT_IO)

    derivation = derive(grammar, cfg.seed, cfg)
    sections = extract(derivation)
    notes = realize(sections, cfg.swing)
    bass = realize_bass(sections, cfg.key, cfg.swing, cfg.bars) if cfg.bass else None
    mid_bytes = to_bytes(build_midi(cfg, sections, notes, __version__, bass))
    json_text = derivation.to_json(sections)
    try:
        mid_path, json_path = write_outputs(args.output, mid_bytes, json_text)
    except OutputError as e:
        return _error(str(e), EXIT_IO)

    bass_txt = f"on  key: {cfg.key}" if cfg.bass else "off"
    print(f"seed: {cfg.seed}")
    print(
        f"bpm: {cfg.bpm}  swing: {cfg.swing!r}  density: {cfg.density!r}  fills: {cfg.fills!r}  "
        f"bars: {cfg.bars}  bass: {bass_txt}"
    )
    print("form: " + " ".join(f"{s.kind}({s.n_bars})" for s in sections))
    print(f"wrote: {mid_path}")
    print(f"wrote: {json_path}")
    return EXIT_OK


def _grammar(args) -> int:
    from boombap.grammar import TableError, build_grammar, default_rules_path, grammar_from_table
    from boombap.grammar.format import to_json, to_text
    from boombap.grammar.table import check_table, load_table

    try:
        cfg = RunConfig.create(seed=0, bars=args.bars, density=args.density, fills=args.fills, bass=args.bass, key=args.key)
    except ConfigError as e:
        return _error(str(e), EXIT_USAGE)

    if args.check:
        path = Path(args.rules) if args.rules else default_rules_path()
        try:
            table = load_table(path)
        except TableError as e:
            print(e)
            return EXIT_IO
        except OSError as e:
            return _error(f"cannot read '{path}': {e.strerror or e}", EXIT_IO)
        errors, warnings = check_table(table, bass=cfg.bass)
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        for e in errors:
            print(e)
        if not errors:
            for bars in (20, 40, 256):
                g = grammar_from_table(table, bars, cfg.density, cfg.fills, cfg.bass)
                for problem in g.validate():
                    errors.append(problem)
                    print(f"{path}:0: Música({bars}): {problem}")
        return EXIT_IO if errors else EXIT_OK

    try:
        grammar = build_grammar(cfg, args.rules)
    except TableError as e:
        return _error(str(e), EXIT_IO)
    if args.format == "json":
        sys.stdout.write(to_json(grammar))
    else:
        sys.stdout.write(to_text(grammar, args.max_rules))
    return EXIT_OK


def _analyze(args) -> int:
    from boombap.analyze import analyze

    try:
        result = analyze(args.path)
    except (OSError, EOFError, ValueError) as e:
        return _error(f"cannot read '{args.path}': {e}", EXIT_IO)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for k, v in result.items():
            print(f"{k}: {json.dumps(v, ensure_ascii=False)}")
    return EXIT_OK


def _render(args) -> int:
    from boombap.render import RenderError, render

    try:
        out = render(args.path, args.output, args.soundfont, args.sample_rate)
    except RenderError as e:
        return _error(str(e), EXIT_IO)
    print(f"wrote: {out}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else EXIT_USAGE
    handler = {"generate": _generate, "grammar": _grammar, "analyze": _analyze, "render": _render}[args.command]
    return handler(args)

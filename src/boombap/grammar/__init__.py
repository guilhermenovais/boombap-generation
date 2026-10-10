"""Montagem da gramática: tabela de regras do autor + famílias estruturais indexadas."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from boombap.grammar.core import Grammar, NonTerminal
from boombap.grammar.structure import MUSICA, NAMES, Structure
from boombap.grammar.table import RuleTable, TableError, check_table, load_table

__all__ = ["build_grammar", "default_rules_path", "TableError"]


def default_rules_path() -> Path:
    return Path(str(resources.files("boombap") / "data" / "boombap.rules"))


def grammar_from_table(table: RuleTable, bars: int, density: float, fills: float, bass: bool) -> Grammar:
    table_rules = table.evaluate(density, fills)
    structure = Structure(table, density, fills)

    def provider(nt: NonTerminal):
        if nt.name in NAMES:
            return structure.rules_for(nt)
        return table_rules.get(nt, [])

    hooks = ["HumV", "HumT"] + (["BassFirst", "BassDeg"] if bass else [])
    return Grammar(
        NonTerminal(MUSICA, (bars,)),
        provider,
        source=str(table.path),
        extra_roots=tuple(NonTerminal(h) for h in hooks),
        rules_sha256=table.sha256,
    )


def build_grammar(config, rules_path: Path | str | None = None) -> Grammar:
    """Carrega e valida a tabela; levanta o primeiro `TableError` se houver erro."""
    path = Path(rules_path) if rules_path is not None else default_rules_path()
    try:
        table = load_table(path)
    except OSError as e:
        raise TableError(path, 0, f"cannot read rule table: {e.strerror or e}") from None
    errors, _ = check_table(table, bass=config.bass)
    if errors:
        raise errors[0]
    return grammar_from_table(table, config.bars, config.density, config.fills, config.bass)

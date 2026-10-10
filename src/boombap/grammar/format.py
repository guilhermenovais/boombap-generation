"""Listagem da gramática formal em texto ou JSON (FR-009)."""

from __future__ import annotations

import json

from boombap.grammar.core import Grammar, rhs_str

TRUNCATED = {"Forma", "Corpo", "Seção", "FimBloco"}


def _groups(grammar: Grammar):
    for nt in grammar.nonterminals():
        yield nt, grammar.rules_for(nt)


def to_text(grammar: Grammar, max_rules: int | None = None) -> str:
    lines = [f"# tabela: {grammar.source}  sha256: {grammar.rules_sha256}", ""]
    lines += ["Axioma", f"  {grammar.axiom}", ""]
    lines += ["Não-terminais", "  " + ", ".join(str(nt) for nt in grammar.nonterminals()), ""]
    lines += ["Terminais", "  " + ", ".join(sorted(str(t) for t in grammar.terminals())), ""]
    lines.append("Regras")
    for nt, rules in _groups(grammar):
        shown = rules
        if max_rules is not None and nt.name in TRUNCATED and len(rules) > max_rules:
            # Mostra as N regras mais prováveis, na ordem original.
            top = sorted(range(len(rules)), key=lambda i: -rules[i].prob)[:max_rules]
            shown = [rules[i] for i in sorted(top)]
        for r in shown:
            lines.append(f"  {r.id}  {r.lhs} → {rhs_str(r.rhs)}  [p={r.prob:.3f}]")
        if len(shown) < len(rules):
            lines.append(f"  … (+{len(rules) - len(shown)} regras)")
        lines.append(f"  Σ = {sum(r.prob for r in rules):.3f}")
        lines.append("")
    return "\n".join(lines)


def to_json(grammar: Grammar) -> str:
    data = {
        "axiom": str(grammar.axiom),
        "nonterminals": [str(nt) for nt in grammar.nonterminals()],
        "terminals": sorted(str(t) for t in grammar.terminals()),
        "rules": [
            {"id": r.id, "lhs": str(r.lhs), "rhs": [str(s) for s in r.rhs], "prob": r.prob}
            for _, rules in _groups(grammar)
            for r in rules
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


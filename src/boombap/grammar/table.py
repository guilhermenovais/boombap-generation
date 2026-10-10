"""Parser, avaliador e validação estática da tabela de regras (contracts/rule-table.md)."""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from boombap.grammar.core import (
    PROB_TOL,
    Degree,
    DrumHit,
    Grid,
    HumDt,
    HumDv,
    NonTerminal,
    Rule,
    Terminal,
    terminal_problem,
)

GRID_POINTS = (0.0, 0.25, 0.5, 0.75, 1.0)
REQUIRED_PARAMS = (
    "grooves",
    "fill_end",
    "fill_mid",
    "intro_bars",
    "outro_bars",
    "body_share",
    "body_sigma",
    "block_size",
    "crash_section",
    "crash_intro",
    "crash_after_fill",
)
# Nomes das famílias geradas por structure.py; a tabela não pode redefini-los.
RESERVED = {"Forma", "Corpo", "Intro", "Verso", "Outro", "Bloco4", "Bloco8", "FimBloco", "Compasso", "Prato"}

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RULE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*->(.*)$")
PARAM_RE = re.compile(r"^@([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")
ALT_PROB_RE = re.compile(r"^(.*?)\s*\[([^\[\]]*)\]\s*$")
DRUM_RE = re.compile(r"^(kick|snare|rim|hhc|hho|crash)@(\d+):(\d+)$")
GRID_RE = re.compile(r"^grid(\d+)$")
DV_RE = re.compile(r"^dv([+-]?\d+)$")
DT_RE = re.compile(r"^dt([+-]?\d+)$")
DEG_RE = re.compile(r"^deg(\d+)$")

KICK_SYNC = "<kick@p≠0>"
HAT = "<hhc|hho>"


class TableError(Exception):
    def __init__(self, path, line: int, msg: str):
        self.path = str(path)
        self.line = line
        self.msg = msg
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.msg}"

    def __eq__(self, other):
        return isinstance(other, TableError) and (self.path, self.line, self.msg) == (
            other.path,
            other.line,
            other.msg,
        )

    def __hash__(self):
        return hash((self.path, self.line, self.msg))


# ---------------------------------------------------------------------------
# Expressões seguras
# ---------------------------------------------------------------------------

_BINOPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}
_UNOPS = {ast.UAdd: lambda a: +a, ast.USub: lambda a: -a}
_FUNCS = {"min": min, "max": max}
_VARS = ("density", "fills")


class ExprError(ValueError):
    pass


def _check_node(node: ast.AST) -> None:
    if isinstance(node, ast.Expression):
        _check_node(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ExprError(f"only numbers are allowed (got {node.value!r})")
    elif isinstance(node, ast.Name):
        if node.id not in _VARS:
            raise ExprError(f"unknown name {node.id!r} (only density and fills are allowed)")
    elif isinstance(node, ast.BinOp):
        if type(node.op) not in _BINOPS:
            raise ExprError("only + - * / are allowed")
        _check_node(node.left)
        _check_node(node.right)
    elif isinstance(node, ast.UnaryOp):
        if type(node.op) not in _UNOPS:
            raise ExprError("only unary + and - are allowed")
        _check_node(node.operand)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ExprError("only min() and max() calls are allowed")
        if node.keywords or not node.args:
            raise ExprError(f"{node.func.id}() takes positional arguments only")
        for a in node.args:
            _check_node(a)
    else:
        raise ExprError(f"construct not allowed in expression: {type(node).__name__}")


def _eval_node(node: ast.AST, env: dict) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return float(env[node.id])
    if isinstance(node, ast.BinOp):
        return _BINOPS[type(node.op)](_eval_node(node.left, env), _eval_node(node.right, env))
    if isinstance(node, ast.UnaryOp):
        return _UNOPS[type(node.op)](_eval_node(node.operand, env))
    if isinstance(node, ast.Call):
        return float(_FUNCS[node.func.id](*(_eval_node(a, env) for a in node.args)))
    raise ExprError(type(node).__name__)  # pragma: no cover


@dataclass(frozen=True)
class Expr:
    text: str
    tree: ast.Expression = field(compare=False, repr=False)

    @classmethod
    def parse(cls, text: str) -> "Expr":
        text = text.strip()
        if not text:
            raise ExprError("empty expression")
        try:
            tree = ast.parse(text, mode="eval")
        except SyntaxError:
            raise ExprError(f"invalid expression {text!r}") from None
        _check_node(tree)
        return cls(text, tree)

    def eval(self, density: float, fills: float) -> float:
        try:
            return _eval_node(self.tree, {"density": density, "fills": fills})
        except ZeroDivisionError:
            raise ExprError(f"division by zero in {self.text!r}") from None


# ---------------------------------------------------------------------------
# Estrutura da tabela
# ---------------------------------------------------------------------------


@dataclass
class Param:
    name: str
    line: int
    raw: str


@dataclass
class Alt:
    line: int
    symbols: tuple  # Terminal | str (nome de não-terminal)
    prob: Expr | str | None  # Expr, "rest" ou None (divide o resto)

    @property
    def nonterminals(self) -> list[str]:
        return [s for s in self.symbols if isinstance(s, str)]


@dataclass
class RuleDef:
    lhs: str
    line: int
    alts: list[Alt]


class RuleTable:
    def __init__(self, path: Path, sha256: str):
        self.path = path
        self.sha256 = sha256
        self.params: dict[str, Param] = {}
        self.rules: dict[str, RuleDef] = {}
        self.range_errors: list[TableError] = []

    # -- erros -----------------------------------------------------------
    def error(self, line: int, msg: str) -> TableError:
        return TableError(self.path, line, msg)

    # -- parâmetros -------------------------------------------------------
    def _param(self, name: str) -> Param:
        p = self.params.get(name)
        if p is None:
            raise self.error(1, f"missing required parameter @{name}")
        return p

    def has_param(self, name: str) -> bool:
        return name in self.params

    def param_line(self, name: str) -> int:
        p = self.params.get(name)
        return p.line if p else 1

    def param_names(self, name: str) -> list[str]:
        p = self._param(name)
        names = p.raw.split()
        for n in names:
            if not IDENT_RE.match(n):
                raise self.error(p.line, f"@{name}: invalid name {n!r}")
        return names

    def param_expr(self, name: str, density: float, fills: float) -> float:
        p = self._param(name)
        try:
            return Expr.parse(p.raw).eval(density, fills)
        except ExprError as e:
            raise self.error(p.line, f"@{name}: {e}") from None

    def param_numbers(self, name: str, density: float, fills: float) -> list[float]:
        p = self._param(name)
        try:
            return [Expr.parse(tok).eval(density, fills) for tok in p.raw.split()]
        except ExprError as e:
            raise self.error(p.line, f"@{name}: {e}") from None

    def param_map(self, name: str, density: float, fills: float) -> dict[str, float]:
        p = self._param(name)
        out: dict[str, float] = {}
        for tok in p.raw.split():
            key, sep, val = tok.partition(":")
            if not sep or not key:
                raise self.error(p.line, f"@{name}: expected key:value pairs (got {tok!r})")
            if key in out:
                raise self.error(p.line, f"@{name}: duplicate key {key!r}")
            try:
                out[key] = Expr.parse(val).eval(density, fills)
            except ExprError as e:
                raise self.error(p.line, f"@{name}: {e}") from None
        if not out:
            raise self.error(p.line, f"@{name}: empty map")
        return out

    def size_map(self, name: str, density: float, fills: float) -> dict[int, float]:
        """Mapa `4:p 8:p`."""
        raw = self.param_map(name, density, fills)
        out = {}
        for k, v in raw.items():
            if k not in ("4", "8"):
                raise self.error(self.param_line(name), f"@{name}: keys must be 4 or 8 (got {k!r})")
            out[int(k)] = v
        return out

    # -- regras -----------------------------------------------------------
    def alt_probs(self, rd: RuleDef, density: float, fills: float) -> list[float]:
        """Probabilidade de cada alternativa (`[rest]` e alternativas sem `[ ]` dividem o resto)."""
        probs: list[float | None] = []
        explicit = 0.0
        for alt in rd.alts:
            if isinstance(alt.prob, Expr):
                try:
                    v = alt.prob.eval(density, fills)
                except ExprError as e:
                    raise self.error(alt.line, str(e)) from None
                probs.append(v)
                explicit += v
            else:
                probs.append(None)
        slots = probs.count(None)
        share = (1.0 - explicit) / slots if slots else 0.0
        return [share if p is None else p for p in probs]

    def evaluate(self, density: float, fills: float) -> dict[NonTerminal, list[Rule]]:
        """Regras da tabela avaliadas para `(density, fills)`; regras de prob. 0 não são emitidas."""
        out: dict[NonTerminal, list[Rule]] = {}
        for lhs, rd in self.rules.items():
            nt = NonTerminal(lhs)
            rules = []
            for i, (alt, p) in enumerate(zip(rd.alts, self.alt_probs(rd, density, fills))):
                if p <= PROB_TOL:
                    continue
                rhs = tuple(NonTerminal(s) if isinstance(s, str) else s for s in alt.symbols)
                rules.append(Rule(f"R.{lhs}.{i}", nt, rhs, min(p, 1.0)))
            out[nt] = rules
        return out


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _parse_symbol(tok: str, table: RuleTable, line: int):
    if tok == "ε":
        return None
    m = DRUM_RE.match(tok)
    if m:
        t: Terminal = DrumHit(m.group(1), int(m.group(2)), int(m.group(3)))
    elif m := GRID_RE.match(tok):
        t = Grid(int(m.group(1)))
    elif m := DV_RE.match(tok):
        t = HumDv(int(m.group(1)))
    elif m := DT_RE.match(tok):
        t = HumDt(int(m.group(1)))
    elif m := DEG_RE.match(tok):
        t = Degree(int(m.group(1)))
    elif IDENT_RE.match(tok):
        return tok
    else:
        raise table.error(line, f"invalid symbol {tok!r}")
    problem = terminal_problem(t)
    if problem:
        table.range_errors.append(table.error(line, problem))
    return t


def _parse_alt(text: str, table: RuleTable, line: int) -> Alt:
    text = text.strip()
    prob: Expr | str | None = None
    m = ALT_PROB_RE.match(text)
    if m:
        text, ptext = m.group(1), m.group(2).strip()
        if ptext == "rest":
            prob = "rest"
        else:
            try:
                prob = Expr.parse(ptext)
            except ExprError as e:
                raise table.error(line, str(e)) from None
    elif "[" in text or "]" in text:
        raise table.error(line, "probability must be written as [expr] at the end of the alternative")
    if not text:
        raise table.error(line, "empty alternative (use ε for the empty production)")
    symbols = []
    for tok in text.split():
        s = _parse_symbol(tok, table, line)
        if s is not None:
            symbols.append(s)
    return Alt(line, tuple(symbols), prob)


def parse_table(text: str, path: Path | str = "<rules>", sha256: str = "") -> RuleTable:
    path = Path(path)
    table = RuleTable(path, sha256 or hashlib.sha256(text.encode("utf-8")).hexdigest())
    current: RuleDef | None = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("|"):
            if current is None:
                raise table.error(lineno, "continuation line '|' without a rule above")
            for part in line[1:].split("|"):
                current.alts.append(_parse_alt(part, table, lineno))
            continue
        m = PARAM_RE.match(line)
        if m:
            current = None
            name, value = m.group(1), m.group(2).strip()
            if name in table.params:
                raise table.error(lineno, f"parameter @{name} defined twice")
            if not value:
                raise table.error(lineno, f"parameter @{name} has no value")
            table.params[name] = Param(name, lineno, value)
            continue
        m = RULE_RE.match(line)
        if m:
            lhs, body = m.group(1), m.group(2)
            if lhs in table.rules:
                raise table.error(lineno, f"{lhs} defined twice (use '|' for more alternatives)")
            current = RuleDef(lhs, lineno, [])
            table.rules[lhs] = current
            if body.strip():
                for part in body.split("|"):
                    current.alts.append(_parse_alt(part, table, lineno))
            continue
        raise table.error(lineno, f"cannot parse line: {line!r}")
    for rd in table.rules.values():
        if not rd.alts:
            raise table.error(rd.line, f"{rd.lhs} has no alternatives")
    return table


def load_table(path: Path | str) -> RuleTable:
    path = Path(path)
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise TableError(path, 1, f"file is not valid UTF-8: {e}") from None
    return parse_table(text, path, hashlib.sha256(data).hexdigest())


# ---------------------------------------------------------------------------
# Validação estática (contracts/rule-table.md §3)
# ---------------------------------------------------------------------------


def _fmt_point(d: float, f: float) -> str:
    return f"density={d:g}, fills={f:g}"


def _find_cycle(table: RuleTable) -> list[str] | None:
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in table.rules}
    stack: list[str] = []

    def visit(n: str) -> list[str] | None:
        color[n] = GREY
        stack.append(n)
        for alt in table.rules[n].alts:
            for m in alt.nonterminals:
                if m not in color:
                    continue
                if color[m] == GREY:
                    return stack[stack.index(m):] + [m]
                if color[m] == WHITE:
                    cyc = visit(m)
                    if cyc:
                        return cyc
        stack.pop()
        color[n] = BLACK
        return None

    for n in table.rules:
        if color[n] == WHITE:
            cyc = visit(n)
            if cyc:
                return cyc
    return None


def _sym_must(sym, must: dict[str, frozenset]) -> frozenset:
    if isinstance(sym, str):
        return must[sym]
    if isinstance(sym, DrumHit):
        extra = set()
        if sym.piece == "kick" and sym.pos != 0:
            extra.add(KICK_SYNC)
        if sym.piece in ("hhc", "hho"):
            extra.add(HAT)
        return frozenset({f"{sym.piece}@{sym.pos}", *extra})
    return frozenset()


def _analyse(table: RuleTable, probs: dict[str, list[float]], order: list[str]):
    """Ponto fixo (aqui, ordem topológica) de `must` e da contagem mín./máx. de grids."""
    must: dict[str, frozenset] = {}
    grids: dict[str, tuple[int, int]] = {}
    for n in order:
        rd = table.rules[n]
        acc: frozenset | None = None
        lo, hi = None, None
        for alt, p in zip(rd.alts, probs[n]):
            if p <= PROB_TOL:
                continue
            s = frozenset().union(*(_sym_must(x, must) for x in alt.symbols)) if alt.symbols else frozenset()
            acc = s if acc is None else acc & s
            a_lo = a_hi = 0
            for x in alt.symbols:
                if isinstance(x, str):
                    a_lo += grids[x][0]
                    a_hi += grids[x][1]
                elif isinstance(x, Grid):
                    a_lo += 1
                    a_hi += 1
            lo = a_lo if lo is None else min(lo, a_lo)
            hi = a_hi if hi is None else max(hi, a_hi)
        must[n] = acc or frozenset()
        grids[n] = (lo or 0, hi or 0)
    return must, grids


def _topo_order(table: RuleTable) -> list[str]:
    order: list[str] = []
    done: set[str] = set()

    def visit(n: str):
        if n in done:
            return
        done.add(n)
        for alt in table.rules[n].alts:
            for m in alt.nonterminals:
                visit(m)
        order.append(n)

    for n in table.rules:
        visit(n)
    return order


def check_table(table: RuleTable, bass: bool) -> tuple[list[TableError], list[TableError]]:
    """Valida a tabela em toda a grade `density, fills ∈ {0, .25, .5, .75, 1}`."""
    errors: dict[TableError, None] = {}
    warnings: dict[TableError, None] = {}
    seen: set[tuple[int, str]] = set()

    def err(line: int, msg: str, point: str = ""):
        # Uma violação é reportada uma só vez, no primeiro ponto da grade em que ocorre.
        if (line, msg) in seen:
            return
        seen.add((line, msg))
        errors.setdefault(table.error(line, f"{msg} ({point})" if point else msg))

    def warn(line: int, msg: str):
        warnings.setdefault(table.error(line, msg))

    for e in table.range_errors:
        errors.setdefault(e)

    # (0) parâmetros obrigatórios e nomes reservados
    for name in REQUIRED_PARAMS:
        if not table.has_param(name):
            err(1, f"missing required parameter @{name}")
    for lhs, rd in table.rules.items():
        if lhs in RESERVED:
            err(rd.line, f"{lhs} is a reserved name (generated by the program)")

    grooves: list[str] = []
    if table.has_param("grooves"):
        try:
            grooves = table.param_names("grooves")
        except TableError as e:
            errors.setdefault(e)
        if len(grooves) < 3:
            err(table.param_line("grooves"), f"@grooves must list at least 3 grooves (got {len(grooves)})")
        if len(set(grooves)) != len(grooves):
            err(table.param_line("grooves"), "@grooves has repeated names")

    # (3) ganchos e não-terminais definidos
    for g in grooves:
        for hook in (f"Groove_{g}", f"Fill_{g}"):
            if hook not in table.rules:
                err(table.param_line("grooves"), f"missing required hook {hook}")
    hooks = ["HumV", "HumT"] + (["BassFirst", "BassDeg"] if bass else [])
    for hook in hooks:
        if hook not in table.rules:
            err(1, f"missing required hook {hook}")
    undefined = False
    for rd in table.rules.values():
        for alt in rd.alts:
            for n in alt.nonterminals:
                if n not in table.rules:
                    undefined = True
                    err(alt.line, f"undefined nonterminal {n}")
    cycle = _find_cycle(table)
    if cycle:
        err(table.rules[cycle[0]].line, "infinite recursion: " + " -> ".join(cycle))

    # Ganchos de humanização e baixo só devem emitir os terminais certos.
    hook_kinds = {"HumV": HumDv, "HumT": HumDt, "BassFirst": Degree, "BassDeg": Degree}
    if not undefined and not cycle:
        for hook, kind in hook_kinds.items():
            rd = table.rules.get(hook)
            if rd is None:
                continue
            for alt in rd.alts:
                if len(alt.symbols) != 1 or not isinstance(alt.symbols[0], kind):
                    err(alt.line, f"each alternative of {hook} must be a single {kind.__name__} terminal")

    nondeterministic = False
    order = _topo_order(table) if not undefined and not cycle else []
    first_probs: dict[str, dict[tuple[float, float], float]] = {}

    for d in GRID_POINTS:
        for f in GRID_POINTS:
            point = _fmt_point(d, f)
            probs: dict[str, list[float]] = {}
            for lhs, rd in table.rules.items():
                try:
                    ps = table.alt_probs(rd, d, f)
                except TableError as e:
                    errors.setdefault(e)
                    ps = [0.0] * len(rd.alts)
                probs[lhs] = ps
                for alt, p in zip(rd.alts, ps):
                    if p < -PROB_TOL or p > 1 + PROB_TOL:
                        err(alt.line, f"probability of {lhs} alternative out of [0, 1]: {p:g}", point)
                total = sum(ps)
                if abs(total - 1) > PROB_TOL:
                    err(rd.line, f"probabilities of {lhs} sum to {total:g}, not 1", point)
                if sum(1 for p in ps if p > PROB_TOL) >= 2:
                    nondeterministic = True
                first_probs.setdefault(lhs, {})[(d, f)] = ps[0]

            # (2) parâmetros
            def pexpr(name):
                try:
                    return table.param_expr(name, d, f)
                except TableError as e:
                    errors.setdefault(e)
                    return None

            fe = pexpr("fill_end") if table.has_param("fill_end") else None
            fm = pexpr("fill_mid") if table.has_param("fill_mid") else None
            if fe is not None and fm is not None:
                if not fe > fm:
                    err(table.param_line("fill_mid"), f"@fill_end must be greater than @fill_mid", point)
                first_probs.setdefault("@fill_end", {})[(d, f)] = fe
                first_probs.setdefault("@fill_mid", {})[(d, f)] = fm
                if f == 0 and fm > PROB_TOL:
                    warn(table.param_line("fill_mid"), f"@fill_mid is {fm:g} with fills=0: fills can still appear inside blocks")
            for name in ("fill_end", "fill_mid", "crash_section", "crash_intro", "crash_after_fill"):
                if table.has_param(name):
                    v = pexpr(name)
                    if v is not None and not 0 <= v <= 1:
                        err(table.param_line(name), f"@{name} must be in [0, 1] (got {v:g})", point)
            for name in ("intro_bars", "outro_bars", "block_size"):
                if table.has_param(name):
                    try:
                        m = table.size_map(name, d, f)
                        if any(v < 0 for v in m.values()) or sum(m.values()) <= 0:
                            err(table.param_line(name), f"@{name} weights must be >= 0 with a positive sum", point)
                        if name != "block_size" and m.get(4, 0) <= 0:
                            err(table.param_line(name), f"@{name} must give 4 bars a positive weight", point)
                    except TableError as e:
                        errors.setdefault(e)
            if table.has_param("body_share"):
                try:
                    share = table.param_numbers("body_share", d, f)
                    if len(share) != 3 or any(s < 0 for s in share):
                        err(table.param_line("body_share"), "@body_share must be 3 non-negative numbers")
                except TableError as e:
                    errors.setdefault(e)
            if table.has_param("body_sigma"):
                v = pexpr("body_sigma")
                if v is not None and not v > 0:
                    err(table.param_line("body_sigma"), f"@body_sigma must be > 0 (got {v:g})")
            if table.has_param("groove_weights"):
                try:
                    gw = table.param_map("groove_weights", d, f)
                    for k in gw:
                        if k not in grooves:
                            err(table.param_line("groove_weights"), f"@groove_weights: {k} is not in @grooves")
                    if any(v < 0 for v in gw.values()) or sum(gw.values()) <= 0:
                        err(table.param_line("groove_weights"), "@groove_weights must be >= 0 with a positive sum")
                except TableError as e:
                    errors.setdefault(e)
            if table.has_param("crash_velocity"):
                v = pexpr("crash_velocity")
                if v is not None and not (v == int(v) and 1 <= v <= 127):
                    err(table.param_line("crash_velocity"), "@crash_velocity must be an integer between 1 and 127")

            # (4) eventos garantidos e contagem de grids
            if not order:
                continue
            must, grids = _analyse(table, probs, order)
            for g in grooves:
                for hook, required in (
                    (f"Groove_{g}", ("kick@0", "snare@4", "snare@12")),
                    (f"Fill_{g}", ("kick@0", "snare@4")),
                ):
                    if hook not in table.rules:
                        continue
                    line = table.rules[hook].line
                    for ev in required:
                        if ev not in must[hook]:
                            err(line, f"{hook} does not guarantee {ev}", point)
                    if hook.startswith("Groove_") and KICK_SYNC not in must[hook]:
                        err(line, f"{hook} does not guarantee a kick at a position other than 0", point)
                    if HAT not in must[hook]:
                        err(line, f"{hook} does not guarantee a hi-hat (hhc/hho)", point)
                    lo, hi = grids[hook]
                    if (lo, hi) != (1, 1):
                        span = f"{lo}" if lo == hi else f"{lo} to {hi}"
                        err(line, f"{hook} must emit exactly one grid8/grid16 (emits {span})", point)

    # (5) não determinismo
    if table.rules and not nondeterministic:
        err(1, "grammar is deterministic: no nonterminal has 2 alternatives with probability > 0")

    # Avisos de monotonicidade (R6): prob. da primeira alternativa não deve decrescer.
    for name, values in first_probs.items():
        if name.startswith("@"):
            line = table.param_line(name[1:])
            label = name
        else:
            rd = table.rules[name]
            if len(rd.alts) < 2:
                continue
            line, label = rd.line, f"the first alternative of {name}"
        for var in ("density", "fills"):
            decreasing = False
            for other in GRID_POINTS:
                seq = [values[(x, other)] if var == "density" else values[(other, x)] for x in GRID_POINTS]
                if any(b < a - PROB_TOL for a, b in zip(seq, seq[1:])):
                    decreasing = True
            if decreasing:
                warn(line, f"probability of {label} decreases with {var}")

    return list(errors), list(warnings)

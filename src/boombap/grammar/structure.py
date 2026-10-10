"""Famílias estruturais indexadas (R4/R5), geradas sob demanda.

Nenhum valor musical é fixado aqui: todos os pesos vêm dos `@parâmetros` da tabela.
"""

from __future__ import annotations

import math

from boombap.grammar.core import PROB_TOL, DrumHit, NonTerminal, Rule, SectionMark
from boombap.grammar.table import RuleTable

DEFAULT_CRASH_VELOCITY = 110

MUSICA, FORMA, CORPO = "Música", "Forma", "Corpo"
INTRO, VERSO, REFRAO, OUTRO = "Intro", "Verso", "Refrão", "Outro"
SECAO, BLOCO4, BLOCO8, FIMBLOCO, COMPASSO, PRATO = "Seção", "Bloco4", "Bloco8", "FimBloco", "Compasso", "Prato"
NAMES = {MUSICA, FORMA, CORPO, INTRO, VERSO, REFRAO, OUTRO, SECAO, BLOCO4, BLOCO8, FIMBLOCO, COMPASSO, PRATO}

# Estados do índice `s` de Seção/Compasso.
INICIO_INTRO, INICIO_SECAO, POS_VIRADA, NORMAL = "início_intro", "início_seção", "pós_virada", "normal"
# Contexto do prato derivado do estado.
PRATO_CTX = {INICIO_INTRO: "intro", INICIO_SECAO: "seção", POS_VIRADA: "pós_virada", NORMAL: "nenhum"}
SECTION_KIND = {INTRO: "intro", VERSO: "verso", REFRAO: "refrão", OUTRO: "outro"}
SECTION_ID = {INTRO: "intro", VERSO: "verso", REFRAO: "refrao", OUTRO: "outro"}

STATE_ID = {INICIO_INTRO: "inicio_intro", INICIO_SECAO: "inicio_secao", POS_VIRADA: "pos_virada", NORMAL: "normal"}
CTX_ID = {"intro": "intro", "seção": "secao", "pós_virada": "pos_virada", "nenhum": "nenhum"}


def _normalize(weighted: list[tuple[float, object]]) -> list[tuple[float, object]]:
    kept = [(w, x) for w, x in weighted if w > 0]
    total = sum(w for w, _ in kept)
    if total <= 0:
        return []
    return [(w / total, x) for w, x in kept]


class Structure:
    """Provedor de regras das famílias indexadas, para um ponto `(density, fills)`."""

    def __init__(self, table: RuleTable, density: float, fills: float):
        d, f = density, fills
        self.grooves = table.param_names("grooves")
        self.fill_end = table.param_expr("fill_end", d, f)
        self.fill_mid = table.param_expr("fill_mid", d, f)
        self.intro_bars = table.size_map("intro_bars", d, f)
        self.outro_bars = table.size_map("outro_bars", d, f)
        self.body_share = table.param_numbers("body_share", d, f)
        self.body_sigma = table.param_expr("body_sigma", d, f)
        self.block_size = table.size_map("block_size", d, f)
        self.crash = {
            "intro": table.param_expr("crash_intro", d, f),
            "seção": table.param_expr("crash_section", d, f),
            "pós_virada": table.param_expr("crash_after_fill", d, f),
        }
        self.crash_velocity = (
            int(table.param_expr("crash_velocity", d, f)) if table.has_param("crash_velocity") else DEFAULT_CRASH_VELOCITY
        )
        if table.has_param("groove_weights"):
            gw = table.param_map("groove_weights", d, f)
            self.groove_weights = [gw.get(g, 0.0) for g in self.grooves]
        else:
            self.groove_weights = [1.0] * len(self.grooves)

    # -- famílias -------------------------------------------------------------
    def rules_for(self, nt: NonTerminal) -> list[Rule]:
        name, idx = nt.name, nt.index
        if name == MUSICA:
            (n,) = idx
            return [Rule(f"R.musica.{n}", nt, (NonTerminal(FORMA, (n,)),), 1.0)]
        if name == FORMA:
            return self._forma(nt)
        if name == CORPO:
            return self._corpo(nt)
        if name in SECTION_KIND:
            return self._section(nt)
        if name == SECAO:
            return self._secao(nt)
        if name in (BLOCO4, BLOCO8):
            g, s = idx
            n_meio = 2 if name == BLOCO4 else 6
            rhs = (NonTerminal(COMPASSO, (g, "primeiro", s)),) + (NonTerminal(COMPASSO, (g, "meio", NORMAL)),) * n_meio
            return [Rule(f"R.{name.lower()}.{g}.{STATE_ID[s]}", nt, rhs, 1.0)]
        if name == FIMBLOCO:
            return self._fimbloco(nt)
        if name == COMPASSO:
            return self._compasso(nt)
        if name == PRATO:
            return self._prato(nt)
        raise KeyError(nt)  # pragma: no cover

    def _forma(self, nt: NonTerminal) -> list[Rule]:
        (n,) = nt.index
        options = []
        for i in (4, 8):
            for o in (4, 8):
                if n - i - o >= 12:
                    options.append((self.intro_bars.get(i, 0.0) * self.outro_bars.get(o, 0.0), (i, o)))
        return [
            Rule(
                f"R.forma.{n}.{i}-{o}",
                nt,
                (NonTerminal(INTRO, (i,)), NonTerminal(CORPO, (n - i - o,)), NonTerminal(OUTRO, (o,))),
                p,
            )
            for p, (i, o) in _normalize(options)
        ]

    def _corpo(self, nt: NonTerminal) -> list[Rule]:
        (m,) = nt.index
        sigma2 = 2 * self.body_sigma**2
        options = []
        for a in range(4, m - 7, 4):
            for b in range(4, m - a - 3, 4):
                c = m - a - b
                dev = sum((part / m - share) ** 2 for part, share in zip((a, b, c), self.body_share))
                options.append((math.exp(-dev / sigma2), (a, b, c)))
        return [
            Rule(
                f"R.corpo.{m}.{a}-{b}-{c}",
                nt,
                (NonTerminal(VERSO, (a,)), NonTerminal(REFRAO, (b,)), NonTerminal(VERSO, (c,))),
                p,
            )
            for p, (a, b, c) in _normalize(options)
        ]

    def _section(self, nt: NonTerminal) -> list[Rule]:
        (k,) = nt.index
        state = INICIO_INTRO if nt.name == INTRO else INICIO_SECAO
        mark = SectionMark(SECTION_KIND[nt.name])
        return [
            Rule(f"R.{SECTION_ID[nt.name]}.{k}.{g}", nt, (mark, NonTerminal(SECAO, (k, g, state))), p)
            for p, g in _normalize(list(zip(self.groove_weights, self.grooves)))
        ]

    def _secao(self, nt: NonTerminal) -> list[Rule]:
        k, g, s = nt.index
        if k == 0:
            return [Rule(f"R.secao.0.{g}.{STATE_ID[s]}", nt, (), 1.0)]
        sizes = [size for size in (4, 8) if size <= k]
        if len(sizes) == 1:
            options = [(1.0, sizes[0])]
        else:
            options = _normalize([(self.block_size.get(size, 0.0), size) for size in sizes])
        return [
            Rule(
                f"R.secao.{k}.{g}.{STATE_ID[s]}.{size}",
                nt,
                (NonTerminal(BLOCO4 if size == 4 else BLOCO8, (g, s)), NonTerminal(FIMBLOCO, (k - size, g))),
                p,
            )
            for p, size in options
        ]

    def _fimbloco(self, nt: NonTerminal) -> list[Rule]:
        # A decisão de virada do último compasso tem nó próprio: seu `u` não depende do tamanho do bloco (R7).
        k, g = nt.index
        options = [
            (self.fill_end, ("virada", POS_VIRADA)),
            (1.0 - self.fill_end, ("groove", NORMAL)),
        ]
        return [
            Rule(
                f"R.fimbloco.{k}.{g}.{kind}",
                nt,
                (NonTerminal(COMPASSO, (g, "fim", kind)), NonTerminal(SECAO, (k, g, nxt))),
                p,
            )
            for p, (kind, nxt) in options
            if p > PROB_TOL
        ]

    def _compasso(self, nt: NonTerminal) -> list[Rule]:
        # Todo Compasso tem RHS de 2 símbolos (Prato, gancho) para manter os índices de filhos alinhados.
        g, where, s = nt.index
        fill, groove = NonTerminal(f"Fill_{g}"), NonTerminal(f"Groove_{g}")
        base = f"R.compasso.{g}.{where}.{STATE_ID.get(s, s)}"
        if where == "fim":
            prato = NonTerminal(PRATO, ("nenhum",))
            return [Rule(base, nt, (prato, fill if s == "virada" else groove), 1.0)]
        ctx = PRATO_CTX[s] if where == "primeiro" else "nenhum"
        prato = NonTerminal(PRATO, (ctx,))
        options = [(self.fill_mid, ("virada", fill)), (1.0 - self.fill_mid, ("groove", groove))]
        return [Rule(f"{base}.{kind}", nt, (prato, hook), p) for p, (kind, hook) in options if p > PROB_TOL]

    def _prato(self, nt: NonTerminal) -> list[Rule]:
        (ctx,) = nt.index
        cid = CTX_ID[ctx]
        if ctx == "nenhum":
            return [Rule(f"R.prato.{cid}", nt, (), 1.0)]
        p = self.crash[ctx]
        crash = DrumHit("crash", 0, self.crash_velocity)
        options = [(p, ("crash", (crash,))), (1.0 - p, ("nada", ()))]
        return [Rule(f"R.prato.{cid}.{kind}", nt, rhs, q) for q, (kind, rhs) in options if q > PROB_TOL]

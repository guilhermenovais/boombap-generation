"""Configuração de execução (RunConfig) e sua validação (FR-019, FR-021, FR-022)."""

from __future__ import annotations

import math
import re
import secrets
from dataclasses import dataclass

SEED_LIMIT = 2**63
KEY_RE = re.compile(r"^[A-G][#b]?m$")
RECORD_FIELDS = ("seed", "bpm", "swing", "density", "fills", "bars", "bass", "key")


class ConfigError(ValueError):
    """Parâmetro fora da faixa ou mal formado."""


def _got(value) -> str:
    """Valor como aparece na mensagem: números crus, textos não numéricos entre aspas."""
    if isinstance(value, str):
        try:
            float(value)
        except ValueError:
            return repr(value)
        return value.strip()
    return str(value)


def _as_int(value, msg: str) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{msg} (got {_got(value)})")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ConfigError(f"{msg} (got {_got(value)})")
    try:
        return int(str(value).strip())
    except ValueError:
        raise ConfigError(f"{msg} (got {_got(value)})") from None


def _as_float(value, msg: str) -> float:
    if isinstance(value, bool):
        raise ConfigError(f"{msg} (got {_got(value)})")
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise ConfigError(f"{msg} (got {_got(value)})") from None
    if not math.isfinite(x):
        raise ConfigError(f"{msg} (got {_got(value)})")
    return x


@dataclass(frozen=True)
class RunConfig:
    seed: int
    bpm: int
    swing: float
    density: float
    fills: float
    bars: int
    bass: bool
    key: str

    @classmethod
    def create(
        cls,
        seed=None,
        bpm=90,
        swing=58.0,
        density=0.5,
        fills=0.5,
        bars=40,
        bass=False,
        key="Am",
    ) -> "RunConfig":
        """Valida todos os parâmetros antes de qualquer geração (FR-021)."""
        if seed is None:
            seed = secrets.randbits(32)
        msg = "--seed must be a non-negative integer below 2^63"
        seed_i = _as_int(seed, msg)
        if not 0 <= seed_i < SEED_LIMIT:
            raise ConfigError(f"{msg} (got {_got(seed)})")

        msg = "--bpm must be between 85 and 95"
        bpm_i = _as_int(bpm, msg)
        if not 85 <= bpm_i <= 95:
            raise ConfigError(f"{msg} (got {_got(bpm)})")

        msg = "--swing must be between 52 and 75"
        swing_f = _as_float(swing, msg)
        if not 52 <= swing_f <= 75:
            raise ConfigError(f"{msg} (got {_got(swing)})")

        msg = "--density must be between 0 and 1"
        density_f = _as_float(density, msg)
        if not 0 <= density_f <= 1:
            raise ConfigError(f"{msg} (got {_got(density)})")

        msg = "--fills must be between 0 and 1"
        fills_f = _as_float(fills, msg)
        if not 0 <= fills_f <= 1:
            raise ConfigError(f"{msg} (got {_got(fills)})")

        msg = "--bars must be a multiple of 4 between 20 and 256"
        bars_i = _as_int(bars, msg)
        if not (20 <= bars_i <= 256 and bars_i % 4 == 0):
            raise ConfigError(f"{msg} (got {_got(bars)})")

        if not isinstance(key, str) or not KEY_RE.match(key):
            raise ConfigError(f"--key must be a minor key like Am, F#m or Bbm (got {key!r})")

        return cls(
            seed=seed_i,
            bpm=bpm_i,
            swing=swing_f + 0.0,
            density=density_f + 0.0,
            fills=fills_f + 0.0,
            bars=bars_i,
            bass=bool(bass),
            key=key,
        )

    def record(self, version: str) -> str:
        """Texto gravado no MIDI; basta para reproduzir a música (FR-024)."""
        return (
            f"boombap v{version} seed={self.seed} bpm={self.bpm} swing={self.swing!r} "
            f"density={self.density!r} fills={self.fills!r} bars={self.bars} "
            f"bass={'on' if self.bass else 'off'} key={self.key}"
        )


def parse_record(text: str) -> RunConfig:
    """Lê o texto de `RunConfig.record` e devolve a configuração validada."""
    parts = text.split()
    if not parts or parts[0] != "boombap" or len(parts) < 2 or not parts[1].startswith("v"):
        raise ConfigError(f"not a boombap record: {text!r}")
    fields = {}
    for tok in parts[2:]:
        k, sep, v = tok.partition("=")
        if not sep:
            raise ConfigError(f"malformed field {tok!r} in record")
        fields[k] = v
    missing = [f for f in RECORD_FIELDS if f not in fields]
    if missing:
        raise ConfigError(f"record is missing field(s): {', '.join(missing)}")
    if fields["bass"] not in ("on", "off"):
        raise ConfigError(f"bass must be on or off in record (got {fields['bass']!r})")
    return RunConfig.create(
        seed=fields["seed"],
        bpm=fields["bpm"],
        swing=fields["swing"],
        density=fields["density"],
        fills=fields["fills"],
        bars=fields["bars"],
        bass=fields["bass"] == "on",
        key=fields["key"],
    )

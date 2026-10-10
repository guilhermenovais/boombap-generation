import contextlib
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
REAL_RULES = ROOT / "src" / "boombap" / "data" / "boombap.rules"
SCHEMA = ROOT / "specs" / "001-boombap-grammar-generator" / "contracts" / "derivation.schema.json"


@pytest.fixture
def minimal_rules() -> Path:
    return FIXTURES / "minimal.rules"


@pytest.fixture
def real_rules() -> Path:
    if not REAL_RULES.exists():
        pytest.skip("src/boombap/data/boombap.rules ausente")
    return REAL_RULES


@pytest.fixture
def out_dir(tmp_path) -> Path:
    d = tmp_path / "out"
    d.mkdir()
    return d


def run_cli(*args) -> tuple[int, str, str]:
    """Roda `boombap.cli.main` capturando stdout/stderr."""
    from boombap.cli import main

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main([str(a) for a in args])
        except SystemExit as e:  # argparse
            code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


def generate(out_dir: Path, name: str, rules: Path | None = None, **opts) -> tuple[Path, Path, str]:
    """Gera uma música pelo CLI e devolve (mid, json, stdout)."""
    args = ["generate", "-o", out_dir / name]
    if rules is not None:
        args += ["--rules", rules]
    for k, v in opts.items():
        flag = "--" + k.replace("_", "-")
        if v is True:
            args.append(flag)
        elif v is not False and v is not None:
            args += [flag, v]
    code, out, err = run_cli(*args)
    assert code == 0, err
    return out_dir / f"{name}.mid", out_dir / f"{name}.json", out

"""Gravação atômica de `<base>.mid` + `<base>.json`: ou ambos, ou nenhum (R12)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class OutputError(OSError):
    pass


def output_paths(base: Path | str) -> tuple[Path, Path]:
    base = Path(base)
    if base.suffix.lower() == ".mid":
        base = base.with_suffix("")
    return base.with_name(base.name + ".mid"), base.with_name(base.name + ".json")


def write_outputs(base: Path | str, mid_bytes: bytes, json_text: str) -> tuple[Path, Path]:
    mid_path, json_path = output_paths(base)
    parent = mid_path.parent
    if not parent.is_dir():
        raise OutputError(f"cannot write to '{mid_path}': directory '{parent}' does not exist")
    if not os.access(parent, os.W_OK | os.X_OK):
        raise OutputError(f"cannot write to '{mid_path}': permission denied")

    temps: list[str] = []
    published: list[Path] = []
    try:
        staged = []
        for target, data in ((mid_path, mid_bytes), (json_path, json_text.encode("utf-8"))):
            with tempfile.NamedTemporaryFile(dir=parent, prefix=f".{target.name}.", suffix=".tmp", delete=False) as f:
                temps.append(f.name)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            staged.append((f.name, target))
        for tmp, target in staged:
            os.replace(tmp, target)
            temps.remove(tmp)
            published.append(target)
    except OSError as e:
        for tmp in temps:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        for target in published:
            try:
                os.unlink(target)
            except OSError:
                pass
        raise OutputError(f"cannot write to '{mid_path}': {e.strerror or e}") from None
    return mid_path, json_path

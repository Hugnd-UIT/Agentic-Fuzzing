"""Agentic fuzzing introspector analysis package.

Run via:  python3 -m introspector

Each sub-module exposes an ``analyze(config) -> dict | None`` function.
The package entry-point iterates over all analysis steps with per-step
error isolation so that one failure does not block the others.
"""
import importlib.util
from pathlib import Path

_rc_path = Path(__file__).parent / "reply-coverage.py"
_spec = importlib.util.spec_from_file_location("reply_coverage", _rc_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Reply = getattr(_mod, "Reply", None)

__all__ = ["Reply"]
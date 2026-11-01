import importlib.util
from pathlib import Path

_memory_dir = Path(__file__).parent

from .history import History
from .summary import Summary

# Load short-term-memory.py
_stm_path = _memory_dir / "short-term-memory.py"
_stm_spec = importlib.util.spec_from_file_location("short_term_memory", _stm_path)
_stm_mod = importlib.util.module_from_spec(_stm_spec)
_stm_spec.loader.exec_module(_stm_mod)
ShortTermMessage = getattr(_stm_mod, "ShortTermMessage")

# Load long-term-memory.py
_ltm_path = _memory_dir / "long-term-memory.py"
_ltm_spec = importlib.util.spec_from_file_location("long_term_memory", _ltm_path)
_ltm_mod = importlib.util.module_from_spec(_ltm_spec)
_ltm_spec.loader.exec_module(_ltm_mod)
LongTermMessage = getattr(_ltm_mod, "LongTermMessage")

__all__ = [
    "History",
    "Summary",
    "ShortTermMessage",
    "LongTermMessage",
]
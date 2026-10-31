import importlib.util
from pathlib import Path
import sys

_memory_dir = Path(__file__).parent

# Load history-processor.py
_hp_path = _memory_dir / "history-processor.py"
_hp_spec = importlib.util.spec_from_file_location("src.memory.history_processor", _hp_path)
_hp_mod = importlib.util.module_from_spec(_hp_spec)
sys.modules["src.memory.history_processor"] = _hp_mod
_hp_spec.loader.exec_module(_hp_mod)
HistoryProcessor = getattr(_hp_mod, "HistoryProcessor")

# Load short-term-memory.py
_stm_path = _memory_dir / "short-term-memory.py"
_stm_spec = importlib.util.spec_from_file_location("src.memory.short_term_memory", _stm_path)
_stm_mod = importlib.util.module_from_spec(_stm_spec)
sys.modules["src.memory.short_term_memory"] = _stm_mod
_stm_spec.loader.exec_module(_stm_mod)
ShortTermMessage = getattr(_stm_mod, "ShortTermMessage")

# Load long-term-memory.py
_ltm_path = _memory_dir / "long-term-memory.py"
_ltm_spec = importlib.util.spec_from_file_location("src.memory.long_term_memory", _ltm_path)
_ltm_mod = importlib.util.module_from_spec(_ltm_spec)
sys.modules["src.memory.long_term_memory"] = _ltm_mod
_ltm_spec.loader.exec_module(_ltm_mod)
LongTermMessage = getattr(_ltm_mod, "LongTermMessage")

from .summarizer import AgentSummarizer

__all__ = ["HistoryProcessor", "ShortTermMessage", "LongTermMessage", "AgentSummarizer"]

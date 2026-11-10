import importlib.util
from pathlib import Path
import sys

_server_dir = Path(__file__).parent

_tm_path = _server_dir / "task-manager.py"
_spec = importlib.util.spec_from_file_location(__name__ + ".task_manager", _tm_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[__name__ + ".task_manager"] = _mod
_spec.loader.exec_module(_mod)

TaskManager = getattr(_mod, "TaskManager")
InMemoryTaskManager = getattr(_mod, "InMemoryTaskManager")

from .server import A2AServer

__all__ = ["A2AServer", "TaskManager", "InMemoryTaskManager"]
import importlib.util
import sys
from pathlib import Path

_target = Path(__file__).parent / "reply-coverage.py"
_spec = importlib.util.spec_from_file_location("full_coverage_reply", _target)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[__name__] = _mod
_spec.loader.exec_module(_mod)

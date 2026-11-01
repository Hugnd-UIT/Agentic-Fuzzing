import sys
import importlib

for _sub in ["", ".types", ".client", ".server", ".utils"]:
    try:
        _mod = importlib.import_module(f"src.agents-2-agents{_sub}")
        sys.modules[f"src.agents_2_agents{_sub}"] = _mod
    except Exception:
        pass
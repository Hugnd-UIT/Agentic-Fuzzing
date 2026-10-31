import sys
import importlib

# Alias module paths without classes
for _sub in ["", ".types", ".client", ".server"]:
    try:
        _mod = importlib.import_module(f"src.agents-2-agents{_sub}")
        sys.modules[f"src.agents_2_agents{_sub}"] = _mod
        sys.modules[f"src.a2a{_sub}"] = _mod
    except Exception:
        pass

import importlib.util
from pathlib import Path

_collect_tools_path = Path(__file__).parent / "collect_tools.py"
_spec = importlib.util.spec_from_file_location("collect_tools", _collect_tools_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Tool = getattr(_mod, "Tool")
Argument = getattr(_mod, "Argument")
ToolCollection = getattr(_mod, "ToolCollection")
load_tool_collections = getattr(_mod, "load_tool_collections")
TOOLs = getattr(_mod, "TOOLs")
SOURCE_TOOL_LIST = getattr(_mod, "SOURCE_TOOL_LIST")

__all__ = ["Tool", "Argument", "ToolCollection", "load_tool_collections", "TOOLs", "SOURCE_TOOL_LIST"]
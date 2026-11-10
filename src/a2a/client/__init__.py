import importlib.util
from pathlib import Path

from .client import A2AClient

_card_resolver_path = Path(__file__).parent / "card-resolver.py"
_spec = importlib.util.spec_from_file_location(__name__ + ".card_resolver", _card_resolver_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
A2ACardResolver = getattr(_mod, "A2ACardResolver")

__all__ = ["A2AClient", "A2ACardResolver"]
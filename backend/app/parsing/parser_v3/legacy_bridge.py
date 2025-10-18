"""Helpers for bridging to the legacy parser implementation."""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType


@lru_cache(maxsize=1)
def load_legacy_parser() -> ModuleType:
    """Dynamically load the legacy parser module."""

    module_name = "parser_v2_0_clean"
    module_path = Path(__file__).resolve().parent.parent / "parser_v2.0_clean.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load legacy parser from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy_parser = load_legacy_parser()


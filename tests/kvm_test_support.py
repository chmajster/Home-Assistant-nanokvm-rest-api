"""Load pure provider modules without a running Home Assistant instance."""

import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "kvm_protocol_tests"
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components/nanokvm_rest")]
    sys.modules[PACKAGE] = package


def provider(name):
    return importlib.import_module(f"{PACKAGE}.providers.{name}")

"""Guard: core/engine must stay importable without PyQt6.

The engine is shared by the PyQt app and the FastAPI service; the service runs
in processes with no Qt at all. Importing any engine module here happens with
PyQt6 masked out of sys.modules, so a stray Qt import fails loudly.
"""

import importlib
import pkgutil
import sys

import pytest


class _QtBlocked:
    def find_module(self, fullname, path=None):  # noqa: ANN001
        if fullname == "PyQt6" or fullname.startswith("PyQt6."):
            return self
        return None

    def load_module(self, fullname):  # noqa: ANN001
        raise ImportError(f"PyQt6 is forbidden inside core.engine (tried {fullname})")


def _engine_modules() -> list[str]:
    import core.engine

    names = ["core.engine"]
    for info in pkgutil.iter_modules(core.engine.__path__):
        names.append(f"core.engine.{info.name}")
    return names


def test_engine_imports_without_qt(monkeypatch: pytest.MonkeyPatch) -> None:
    blocker = _QtBlocked()
    monkeypatch.setattr(sys, "meta_path", [blocker, *sys.meta_path])
    for name in list(sys.modules):
        if name == "PyQt6" or name.startswith("PyQt6.") or name.startswith("core.engine"):
            monkeypatch.delitem(sys.modules, name, raising=False)

    for module_name in _engine_modules():
        importlib.import_module(module_name)

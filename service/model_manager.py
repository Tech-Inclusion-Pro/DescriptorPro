"""One-model-at-a-time manager (spec §5.3).

Stages bracket model use with `async with manager.use(role, name):`. The lock
guarantees the speech, vision, and text models are never resident together.
Release evicts Ollama-backed models with keep_alive=0; in-process models are
dropped and garbage-collected.

Phase 0 registers only the `fake` loader (tests). Real loaders arrive with
their phases and must be recorded in docs/MODEL_LICENSES.md first (spec §5.4).
"""

from __future__ import annotations

import asyncio
import gc
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ModelHandle:
    role: str
    name: str
    instance: Any
    unloader: Callable[[Any], None] | None = None


def _fake_loader(name: str) -> ModelHandle:
    return ModelHandle(role="fake", name=name, instance=object())


def _ollama_unloader(handle: ModelHandle) -> None:
    from core.engine.llm import unload_model

    unload_model(handle.name)


def ollama_loader(name: str) -> ModelHandle:
    """Ollama models are loaded lazily by the first generate call; the handle
    only carries the name so release can evict with keep_alive=0."""
    handle = ModelHandle(role="ollama", name=name, instance=None)
    handle.unloader = _ollama_unloader
    return handle


class ModelManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current: ModelHandle | None = None
        self._loaders: dict[str, Callable[[str], ModelHandle]] = {
            "fake": _fake_loader,
            "ollama": ollama_loader,
        }

    def register_loader(self, role: str, loader: Callable[[str], ModelHandle]) -> None:
        self._loaders[role] = loader

    @property
    def current(self) -> ModelHandle | None:
        return self._current

    @asynccontextmanager
    async def use(self, role: str, name: str):
        if role not in self._loaders:
            raise ValueError(f"No loader registered for model role: {role}")
        async with self._lock:
            handle = await asyncio.to_thread(self._loaders[role], name)
            handle.role = role
            self._current = handle
            try:
                yield handle
            finally:
                await asyncio.to_thread(self._release, handle)
                self._current = None

    def _release(self, handle: ModelHandle) -> None:
        if handle.unloader is not None:
            try:
                handle.unloader(handle)
            except Exception:
                pass  # eviction is best-effort; dropping the reference still frees us
        handle.instance = None
        gc.collect()

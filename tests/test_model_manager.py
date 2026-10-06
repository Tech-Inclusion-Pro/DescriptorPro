"""Model manager: one at a time, release evicts (spec §5.3)."""

from __future__ import annotations

import asyncio

import pytest

from service.model_manager import ModelHandle, ModelManager


async def test_one_model_at_a_time():
    manager = ModelManager()
    order: list[str] = []

    async def use_model(name: str, hold: float):
        async with manager.use("fake", name):
            order.append(f"start-{name}")
            await asyncio.sleep(hold)
            order.append(f"end-{name}")

    await asyncio.gather(use_model("a", 0.05), use_model("b", 0.05))
    # No interleaving: each model fully ends before the next starts.
    assert order in (
        ["start-a", "end-a", "start-b", "end-b"],
        ["start-b", "end-b", "start-a", "end-a"],
    )


async def test_release_calls_unloader():
    manager = ModelManager()
    unloaded: list[str] = []

    def loader(name: str) -> ModelHandle:
        handle = ModelHandle(role="test", name=name, instance=object())
        handle.unloader = lambda h: unloaded.append(h.name)
        return handle

    manager.register_loader("test", loader)
    async with manager.use("test", "demo-model") as handle:
        assert handle.instance is not None
        assert manager.current is handle
    assert unloaded == ["demo-model"]
    assert manager.current is None


async def test_ollama_release_sends_keep_alive_zero(monkeypatch):
    calls: list[str] = []

    import core.engine.llm as llm

    monkeypatch.setattr(llm, "unload_model", lambda model: calls.append(model))

    manager = ModelManager()
    async with manager.use("ollama", "qwen3:8b"):
        pass
    assert calls == ["qwen3:8b"]


async def test_unknown_role_rejected():
    manager = ModelManager()
    with pytest.raises(ValueError):
        async with manager.use("nope", "x"):
            pass

"""Shared fixtures: isolated data dir + a test app/client."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Every test gets its own app-support dir so nothing touches real data."""
    monkeypatch.setenv("DESCRIBE_STUDIO_DATA_DIR", str(tmp_path / "data"))
    return tmp_path


@pytest.fixture
def token() -> str:
    return "test-token-123"


@pytest.fixture
def app(token):
    from service.main import create_app

    return create_app(token)


@pytest.fixture
def client(app, token):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client


@pytest.fixture
def anon_client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client

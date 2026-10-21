import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def temp_database(tmp_path, monkeypatch):
    """Tests never touch the real database or the real API key."""
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")

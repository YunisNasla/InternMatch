import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def temp_database(tmp_path, monkeypatch):
    """Tests never touch the real database."""
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))

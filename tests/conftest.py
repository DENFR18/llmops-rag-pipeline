import os

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("VOYAGE_API_KEY", "test-key")
os.environ.setdefault("NEON_DATABASE_URL", "postgresql://test:test@localhost:5432/test")


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    from src.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

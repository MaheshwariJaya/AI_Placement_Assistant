import os
import pytest

# Ensure automated test suites use mock provider offline by default
os.environ["AI_PROVIDER"] = "mock"
os.environ["PYTEST_CURRENT_TEST"] = "1"

from app.config import get_settings

@pytest.fixture(autouse=True)
def default_mock_ai_provider(monkeypatch):
    """
    Ensure automated tests use MockAIProvider by default unless a test
    explicitly mocks or patches AI_PROVIDER.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")


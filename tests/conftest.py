"""Shared pytest fixtures for the mock_interview test suite."""
import pytest
from app.session_store import clear_all_sessions


@pytest.fixture(autouse=True)
def reset_session_store():
    """Clear session store before each test to ensure isolation."""
    clear_all_sessions()
    yield
    clear_all_sessions()

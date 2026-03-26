"""Tests for the in-memory session store."""
import pytest
from app.session_store import create_session, get_session, delete_session, clear_all_sessions


def test_create_session_returns_uuid_string():
    """create_session stores data and returns a UUID string key."""
    session_id = create_session({"stage": "intro"})
    assert isinstance(session_id, str)
    assert len(session_id) == 36  # UUID4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx


def test_create_session_stores_data():
    """Data passed to create_session is retrievable via get_session."""
    session_id = create_session({"stage": "intro", "role": "engineer"})
    session = get_session(session_id)
    assert session["stage"] == "intro"
    assert session["role"] == "engineer"


def test_create_session_each_call_returns_unique_id():
    """Each call to create_session produces a distinct session ID."""
    id1 = create_session({"stage": "intro"})
    id2 = create_session({"stage": "intro"})
    assert id1 != id2


def test_get_session_raises_key_error_for_missing_id():
    """get_session raises KeyError when the session ID does not exist."""
    with pytest.raises(KeyError):
        get_session("nonexistent-id")


def test_delete_session_removes_session():
    """delete_session removes the session so subsequent get raises KeyError."""
    session_id = create_session({"stage": "intro"})
    delete_session(session_id)
    with pytest.raises(KeyError):
        get_session(session_id)


def test_delete_session_raises_key_error_for_missing_id():
    """delete_session raises KeyError when the session ID does not exist."""
    with pytest.raises(KeyError):
        delete_session("nonexistent-id")


def test_session_data_is_mutable_in_place():
    """Modifying the returned session dict is reflected in subsequent gets."""
    session_id = create_session({"stage": "intro", "count": 0})
    session = get_session(session_id)
    session["count"] = 5
    assert get_session(session_id)["count"] == 5


def test_clear_all_sessions_removes_all():
    """clear_all_sessions removes every stored session."""
    id1 = create_session({"stage": "intro"})
    id2 = create_session({"stage": "questions"})
    clear_all_sessions()
    with pytest.raises(KeyError):
        get_session(id1)
    with pytest.raises(KeyError):
        get_session(id2)

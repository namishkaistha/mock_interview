"""In-memory session store for the mock interview backend.

Sessions are stored in a module-level dict keyed by UUID string.
All data is discarded when the process exits — there is no persistence layer.
"""
import uuid
from typing import Any

_sessions: dict[str, dict[str, Any]] = {}


def create_session(data: dict[str, Any]) -> str:
    """Store session data and return a new UUID session ID."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = data
    return session_id


def get_session(session_id: str) -> dict[str, Any]:
    """Return the session dict for the given ID.

    Raises KeyError if the session does not exist.
    """
    return _sessions[session_id]


def update_session(session_id: str, data: dict[str, Any]) -> None:
    """Merge data into the existing session dict.

    Raises KeyError if the session does not exist.
    """
    _sessions[session_id].update(data)


def delete_session(session_id: str) -> None:
    """Remove the session for the given ID.

    Raises KeyError if the session does not exist.
    """
    del _sessions[session_id]


def clear_all_sessions() -> None:
    """Remove all sessions. Used in tests for isolation."""
    _sessions.clear()

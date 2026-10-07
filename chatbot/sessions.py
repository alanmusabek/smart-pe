"""Bounded, user-owned chat sessions. Cache database reads, never authentication."""
from collections import OrderedDict
from contextvars import ContextVar
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from functools import wraps
from threading import RLock
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException

TTL_SECONDS = 3600
MAX_SESSIONS = 256
_sessions = OrderedDict()
_lock = RLock()
_revision = 0
current_session = ContextVar('chat_session', default=None)


@dataclass
class Session:
    owner: int
    student_id: int
    id: str = field(default_factory=lambda: uuid4().hex)
    touched: float = field(default_factory=monotonic)
    revision: int = -1
    cache: dict = field(default_factory=dict)
    history: list = field(default_factory=list)
    language: str = 'en'
    lock: RLock = field(default_factory=RLock)


def invalidate():
    """Called after successful data mutations; next message reloads its snapshot."""
    global _revision
    with _lock:
        _revision += 1


def create(owner, student_id):
    with _lock:
        now = monotonic()
        for key in list(_sessions):
            if now - _sessions[key].touched > TTL_SECONDS:
                del _sessions[key]
        while len(_sessions) >= MAX_SESSIONS:
            _sessions.popitem(last=False)
        session = Session(owner=owner, student_id=student_id)
        _sessions[session.id] = session
        return session


def get(session_id, owner, student_id):
    with _lock:
        session = _sessions.get(session_id)
        if session is None or monotonic() - session.touched > TTL_SECONDS:
            _sessions.pop(session_id, None)
            raise HTTPException(410, 'Chat session expired. Start a new conversation.')
        if session.owner != owner or session.student_id != student_id:
            raise HTTPException(403, 'Access denied')
        session.touched = monotonic()
        _sessions.move_to_end(session_id)
        return session


@contextmanager
def use(session):
    with session.lock:
        with _lock:
            revision = _revision
        if session.revision != revision:
            session.cache.clear()
            session.revision = revision
        token = current_session.set(session)
        try:
            yield session
        finally:
            current_session.reset(token)


def cached_read(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        session = current_session.get()
        if session is None:
            return function(*args, **kwargs)
        key = (function.__name__, args, tuple(sorted(kwargs.items())))
        if key not in session.cache:
            session.cache[key] = function(*args, **kwargs)
        return deepcopy(session.cache[key])
    return wrapped

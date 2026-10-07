import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import auth


def test_public_registration_cannot_create_teacher(monkeypatch):
    monkeypatch.setattr(auth, "get_connection", lambda: pytest.fail("Database should not be accessed"))

    with pytest.raises(HTTPException) as error:
        auth.register(auth.RegisterRequest(email="teacher@example.com", password="test", role="teacher"))

    assert error.value.status_code == 403


def test_student_cannot_register_a_second_account(monkeypatch):
    class Cursor:
        def __init__(self):
            self.fetches = iter((None, (5,), (9,)))

        def execute(self, sql, params):
            pass

        def fetchone(self):
            return next(self.fetches)

        def close(self):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            pass

    monkeypatch.setattr(auth, "get_connection", Connection)

    with pytest.raises(HTTPException) as error:
        auth.register(auth.RegisterRequest(email="another@example.com", password="test", student_id=5))

    assert error.value.status_code == 409


def test_malformed_token_payload_returns_unauthorized(monkeypatch):
    monkeypatch.setattr(auth.jwt, "decode", lambda *args, **kwargs: {"sub": "invalid", "role": "student"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    with pytest.raises(HTTPException) as error:
        auth.get_current_user(credentials)

    assert error.value.status_code == 401

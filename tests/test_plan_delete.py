import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import auth
from routers import plans


class FakeCursor:
    def __init__(self, status):
        self.status = status
        self.queries = []
        self.closed = False

    def execute(self, sql, params):
        self.queries.append((" ".join(sql.split()), params))

    def fetchone(self):
        return (self.status,) if self.status is not None else None

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, status):
        self.cur = FakeCursor(status)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_delete_workout_removes_dependents_before_plan(monkeypatch):
    conn = FakeConnection("SCHEDULED")
    monkeypatch.setattr(plans, "get_connection", lambda: conn)

    assert plans.delete_workout_plan(12, {"role": "teacher"}) == {"deleted": True, "plan_id": 12}

    statements = [sql for sql, _ in conn.cur.queries]
    expected_prefixes = [
        "DELETE FROM muscle_fatigue",
        "DELETE FROM student_assigned_exercise_interaction",
        "DELETE FROM assigned_exercise_muscle_group",
        "DELETE FROM assigned_exercise WHERE",
        "DELETE FROM workout_plan WHERE",
    ]
    assert len(statements) == 6
    assert all(statement.startswith(prefix) for statement, prefix in zip(statements[1:], expected_prefixes))
    assert all(params == (12,) for _, params in conn.cur.queries)
    assert conn.committed and not conn.rolled_back
    assert conn.cur.closed and conn.closed


@pytest.mark.parametrize("status, expected_status", [(None, 404), ("COMPLETED", 409)])
def test_delete_workout_rejects_missing_or_completed_plan(monkeypatch, status, expected_status):
    conn = FakeConnection(status)
    monkeypatch.setattr(plans, "get_connection", lambda: conn)

    with pytest.raises(HTTPException) as error:
        plans.delete_workout_plan(12, {"role": "teacher"})

    assert error.value.status_code == expected_status
    assert len(conn.cur.queries) == 1
    assert not conn.committed and conn.rolled_back
    assert conn.cur.closed and conn.closed


def test_student_cannot_delete_workout():
    app = FastAPI()
    app.include_router(plans.router)
    token = auth.create_access_token({"sub": 1, "role": "student", "student_id": 1})

    response = TestClient(app).delete("/plans/12", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_delete_one_exercise_removes_its_dependent_records(monkeypatch):
    conn = FakeConnection(55)
    monkeypatch.setattr(plans, "get_connection", lambda: conn)

    assert plans.delete_plan_exercise(12, 55, {"role": "teacher"}) == {"deleted": True}

    statements = [sql for sql, _ in conn.cur.queries]
    assert [statement.split(" WHERE")[0] for statement in statements[1:]] == [
        "DELETE FROM muscle_fatigue",
        "DELETE FROM student_assigned_exercise_interaction",
        "DELETE FROM assigned_exercise_muscle_group",
        "DELETE FROM assigned_exercise",
    ]
    assert all(params == (55,) for _, params in conn.cur.queries[1:])
    assert conn.committed and not conn.rolled_back

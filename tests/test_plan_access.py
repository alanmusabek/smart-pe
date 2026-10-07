import pytest
from fastapi import HTTPException

from routers import plans
from schemas import PlanStatusUpdate


def test_student_cannot_read_another_students_plan(monkeypatch):
    class Cursor:
        def __init__(self):
            self.queries = []
            self.closed = False

        def execute(self, sql, params):
            self.queries.append((sql, params))

        def fetchone(self):
            return (7,)

        def close(self):
            self.closed = True

    class Connection:
        def __init__(self):
            self.cur = Cursor()
            self.closed = False

        def cursor(self):
            return self.cur

        def close(self):
            self.closed = True

    conn = Connection()
    monkeypatch.setattr(plans, "get_connection", lambda: conn)

    with pytest.raises(HTTPException) as error:
        plans.get_plan_exercises(3, {"role": "student", "student_id": 8})

    assert error.value.status_code == 403
    assert len(conn.cur.queries) == 1
    assert conn.cur.closed and conn.closed


def test_student_plan_status_update_is_scoped_to_owner(monkeypatch):
    class Cursor:
        def __init__(self):
            self.params = None

        def execute(self, sql, params):
            assert "student_id = %s" in sql
            self.params = params

        def fetchone(self):
            return None

        def close(self):
            pass

    class Connection:
        def __init__(self):
            self.cur = Cursor()

        def cursor(self):
            return self.cur

        def close(self):
            pass

    conn = Connection()
    monkeypatch.setattr(plans, "get_connection", lambda: conn)
    update = PlanStatusUpdate(workout_plan_id=3, workout_status="COMPLETED")

    with pytest.raises(HTTPException) as error:
        plans.update_plan_status(update, {"role": "student", "student_id": 8})

    assert error.value.status_code == 404
    assert conn.cur.params[-2:] == ("student", 8)

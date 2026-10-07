from routers import interactions
from schemas import InteractionUpdate


def test_repeated_feedback_updates_existing_result(monkeypatch):
    class Cursor:
        def __init__(self):
            self.rows = iter([(29, 119), (10,), (10,)])
            self.sql = []
        def execute(self, sql, params):
            self.sql.append(sql)
        def fetchone(self):
            return next(self.rows)
        def close(self):
            pass
    class Connection:
        def __init__(self):
            self.cur = Cursor()
        def cursor(self):
            return self.cur
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            pass
    conn = Connection()
    monkeypatch.setattr(interactions, 'get_connection', lambda: conn)
    result = interactions.record_interaction(InteractionUpdate(assigned_exercise_id=1, completed=True), {'student_id': 29})
    assert result['interaction_id'] == 10
    assert 'FOR UPDATE OF ae' in conn.cur.sql[0]
    assert any('UPDATE student_assigned_exercise_interaction' in sql for sql in conn.cur.sql)
    assert not any('INSERT INTO student_assigned_exercise_interaction' in sql for sql in conn.cur.sql)

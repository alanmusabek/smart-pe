from datetime import date

import plan_assembler


def test_assemble_plan_fills_each_day_without_duplicate_exercises():
    ranked = [
        {"exercise_id": exercise_id, "category_id": category_id}
        for category_id, first, last in (
            (1, 1, 6),
            (2, 6, 11),
            (3, 11, 21),
            (4, 21, 26),
            (5, 26, 31),
        )
        for exercise_id in range(first, last)
    ]

    plan = plan_assembler.assemble_plan(ranked)

    assert [session["day"] for session in plan] == ["MONDAY", "WEDNESDAY", "FRIDAY"]
    for session in plan:
        assert [len(session[slot]) for slot in ("warmup", "main", "cooldown")] == [2, 3, 2]
        ids = [
            exercise["exercise_id"]
            for slot in ("warmup", "main", "cooldown")
            for exercise in session[slot]
        ]
        assert len(ids) == len(set(ids))


def test_filter_exercises_applies_medical_and_injury_rules():
    class Cursor:
        def __init__(self):
            self.queries = []

        def execute(self, sql, params):
            self.queries.append((sql, params))

        def fetchone(self):
            return (3,)

        def fetchall(self):
            return [(2,)]

        def close(self):
            pass

    class Connection:
        def __init__(self):
            self.cur = Cursor()

        def cursor(self):
            return self.cur

    conn = Connection()
    exercises = [
        {"exercise_id": 1, "difficulty": "low"},
        {"exercise_id": 2, "difficulty": "low"},
        {"exercise_id": 3, "difficulty": "high"},
    ]

    assert plan_assembler.filter_exercises(42, exercises, conn) == [exercises[0]]
    assert "exercise_contraindications" in conn.cur.queries[1][0]


def test_saved_plan_dates_match_weekdays(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 29)  # Tuesday

    class Cursor:
        def __init__(self):
            self.plan_dates = []

        def execute(self, sql, params):
            if "INSERT INTO workout_plan" in sql:
                self.plan_dates.append(params[1])

        def fetchone(self):
            return (len(self.plan_dates),)

        def close(self):
            pass

    class Connection:
        def __init__(self):
            self.cur = Cursor()
            self.committed = False

        def cursor(self):
            return self.cur

        def commit(self):
            self.committed = True

    monkeypatch.setattr(plan_assembler, "date", FixedDate)
    conn = Connection()
    weekly = [
        {"day": day, "warmup": [], "main": [], "cooldown": []}
        for day in ("MONDAY", "WEDNESDAY", "FRIDAY")
    ]

    assert plan_assembler.save_plan_to_db(1, weekly, conn) == [1, 2, 3]
    assert conn.cur.plan_dates == [date(2026, 10, 5), date(2026, 10, 7), date(2026, 10, 9)]
    assert conn.committed

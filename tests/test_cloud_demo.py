"""Real PostgreSQL checks, isolated in a randomly named schema when explicitly configured."""
import os
from uuid import uuid4
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote
import psycopg2
from psycopg2 import sql
import pytest
from deployment.bootstrap_demo import bootstrap_demo


@pytest.fixture
def demo_url():
    database_url = os.environ.get('SMARTPE_TEST_DB_URL')
    if not database_url:
        pytest.skip('Set SMARTPE_TEST_DB_URL for isolated PostgreSQL integration checks')
    schema = 'smartpe_test_' + uuid4().hex[:16]
    conn = psycopg2.connect(database_url, connect_timeout=10)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    parts = urlsplit(database_url)
    # Startup options need a direct connection rather than a transaction pooler.
    netloc = parts.netloc
    if parts.hostname and parts.hostname.endswith('.neon.tech'):
        netloc = netloc.replace('-pooler.', '.')
    query = dict(parse_qsl(parts.query))
    query['options'] = '-c search_path=' + schema
    target = urlunsplit((parts.scheme, netloc, parts.path, urlencode(query, quote_via=quote), parts.fragment))
    try:
        yield target
    finally:
        with conn.cursor() as cur:
            cur.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
        conn.close()


def test_demo_seed_restarts_preserve_data_and_workout_generation(demo_url, monkeypatch):
    teacher_password, student_password = 'teacher-test-password-42', 'student-test-password-42'
    bootstrap_demo(demo_url, teacher_password, student_password)
    bootstrap_demo(demo_url, teacher_password, student_password)
    with psycopg2.connect(demo_url) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM students'); assert cur.fetchone()[0] == 6
            cur.execute('SELECT COUNT(*) FROM users'); assert cur.fetchone()[0] == 2
            cur.execute('SELECT COUNT(*) FROM workout_plan'); assert cur.fetchone()[0] == 24
            cur.execute('SELECT COUNT(*) FROM student_assigned_exercise_interaction'); assert cur.fetchone()[0] == 90
    import plan_assembler
    monkeypatch.setattr(plan_assembler, 'get_connection', lambda: psycopg2.connect(demo_url))
    plan = plan_assembler.generate_plan(1, save_to_db=True)
    assert len(plan) == 3
    assert all(day['warmup'] and day['main'] and day['cooldown'] for day in plan)
    from auth import verify_password
    with psycopg2.connect(demo_url) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT ae.assigned_exercise_id, em.muscle_group_id FROM assigned_exercise ae JOIN exercise_muscle_group em USING (exercise_id) WHERE ae.workout_plan_id > 24')
            expected_muscles = set(cur.fetchall())
            cur.execute('SELECT am.assigned_exercise_id, am.muscle_group_id FROM assigned_exercise_muscle_group am JOIN assigned_exercise ae USING (assigned_exercise_id) WHERE ae.workout_plan_id > 24')
            assert set(cur.fetchall()) == expected_muscles
            assert len(expected_muscles) == 21
            cur.execute("SELECT password_hash FROM users WHERE email='teacher2@smartpe.edu'")
            assert verify_password(teacher_password, cur.fetchone()[0])


def test_demo_seed_refuses_existing_non_demo_schema(demo_url):
    with psycopg2.connect(demo_url) as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE TABLE students (name TEXT)')
            cur.execute("INSERT INTO students VALUES ('Keep this record')")
    with pytest.raises(RuntimeError, match='Refusing to change existing tables'):
        bootstrap_demo(demo_url, 'teacher-test-password-42', 'student-test-password-42')
    with psycopg2.connect(demo_url) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT name FROM students')
            assert cur.fetchall() == [('Keep this record',)]


def test_demo_seed_failure_rolls_back_entire_schema(demo_url, monkeypatch):
    from deployment import bootstrap_demo as module
    def fail(*args):
        raise RuntimeError('Simulated seed failure')
    monkeypatch.setattr(module, 'seed_students', fail)
    with pytest.raises(RuntimeError, match='Simulated seed failure'):
        module.bootstrap_demo(demo_url, 'teacher-test-password-42', 'student-test-password-42')
    with psycopg2.connect(demo_url) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM pg_tables WHERE schemaname=current_schema()')
            assert cur.fetchone()[0] == 0


def test_retraining_can_be_disabled_on_small_cloud_instance(monkeypatch):
    from fastapi import BackgroundTasks, HTTPException
    from routers import model
    from schemas import RetrainRequest
    monkeypatch.setattr(model.settings, 'MODEL_RETRAIN_ENABLED', False)
    with pytest.raises(HTTPException) as error:
        model.trigger_retrain(RetrainRequest(force=True), BackgroundTasks(), {'role': 'teacher'})
    assert error.value.status_code == 403

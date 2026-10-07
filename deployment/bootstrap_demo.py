"""Create fictional demo data only in an empty schema; never reset an existing DB."""
from datetime import date, timedelta
from pathlib import Path
import bcrypt
import psycopg2


def bootstrap_demo(database_url, teacher_password, student_password):
    url = database_url.replace('postgresql+asyncpg://', 'postgresql://').replace('postgresql+psycopg2://', 'postgresql://')
    conn = psycopg2.connect(url, connect_timeout=10)
    try:
        with conn:
            with conn.cursor() as cur:
                # Serialize startup if the host briefly overlaps deployments.
                cur.execute('SELECT pg_advisory_xact_lock(73261007)')
                cur.execute('SELECT tablename FROM pg_tables WHERE schemaname = current_schema()')
                tables = {row[0] for row in cur.fetchall()}
                if 'smartpe_demo_meta' in tables:
                    cur.execute('SELECT version FROM smartpe_demo_meta WHERE id = 1')
                    if cur.fetchone() != (1,):
                        raise RuntimeError('Unrecognized demo schema; no changes were made.')
                    print('Existing fictional demonstration database retained.', flush=True)
                    return
                if tables:
                    raise RuntimeError('DEMO_MODE requires an empty database schema. Refusing to change existing tables.')
                if len(teacher_password) < 16 or len(student_password) < 16:
                    raise RuntimeError('Set DEMO_TEACHER_PASSWORD and DEMO_STUDENT_PASSWORD to distinct strong values of at least 16 characters.')
                if teacher_password == student_password:
                    raise RuntimeError('Use distinct teacher and student demonstration passwords.')
                cur.execute((Path(__file__).parent / 'demo_schema.sql').read_text(encoding='utf-8'))
                seed_catalog(cur)
                seed_students(cur, teacher_password, student_password)
                cur.execute('CREATE TABLE smartpe_demo_meta (id INTEGER PRIMARY KEY, version INTEGER NOT NULL)')
                cur.execute('INSERT INTO smartpe_demo_meta VALUES (1, 1)')
        print('Fictional demonstration database initialized. No existing student data was imported.', flush=True)
    finally:
        conn.close()


def seed_catalog(cur):
    cur.executemany('INSERT INTO medical_group (group_name, description) VALUES (%s, %s)', [
        ('Основная', 'Fictional demo: normal training'), ('Подготовительная', 'Fictional demo: moderate load'),
        ('Специальная', 'Fictional demo: reduced load')])
    cur.executemany('INSERT INTO exercise_categories (category_name) VALUES (%s)',
                    [(name,) for name in ['Разминка', 'Кардио', 'Силовые', 'Растяжка', 'Кор']])
    cur.executemany('INSERT INTO muscle_group (muscle_name) VALUES (%s)',
                    [(name,) for name in ['Ноги', 'Спина', 'Грудь', 'Плечи', 'Пресс']])
    cur.executemany('INSERT INTO equipment (equipment_name) VALUES (%s)', [('Коврик',), ('Гантели',), ('Турник',)])
    cur.execute("INSERT INTO injury_types (type_name, category, body_region, severity_class, typical_recovery_weeks) VALUES ('Demo knee strain', 'Demo', 'Knee', 'mild', 2)")
    cur.execute("INSERT INTO assessment_version (version_name, description, effective_date) VALUES ('Demo v1', 'Illustrative rules, not university standards', %s)", (date.today(),))
    cur.execute("INSERT INTO workout_standard (standard_name, description) VALUES ('Demo standard', 'Fictional presentation dataset')")
    # Only illustrative thresholds for the demo; not claimed as official norms.
    for medical in (1, 2, 3):
        for gender in ('Male', 'Female'):
            for test, thresholds in [('PUSHUP', [0, 10, 20, 30, 1000]), ('PULLUP', [0, 2, 5, 10, 1000]),
                                     ('COOPER', [0, 1200, 1800, 2400, 10000]), ('FLEXIBILITY', [0, 10, 20, 30, 1000])]:
                for score in range(1, 5):
                    cur.execute('INSERT INTO assessment_rule (assessment_version_id, medical_group_id, test_type, gender, min_value, max_value, score) VALUES (1,%s,%s,%s,%s,%s,%s)',
                                (medical, test, gender, thresholds[score - 1], thresholds[score] - 0.001, score))
    exercises = [
        ('Arm circles / Круги руками', 1, 'low', 4), ('Marching / Ходьба на месте', 1, 'low', 1),
        ('Shoulder rotations / Вращения плечами', 1, 'low', 4), ('Hip circles / Вращения тазом', 1, 'low', 1),
        ('Brisk walking / Быстрая ходьба', 2, 'low', 1), ('Light jogging / Лёгкий бег', 2, 'medium', 1),
        ('Side steps / Приставные шаги', 2, 'low', 1), ('Step-ups / Подъёмы на ступень', 2, 'medium', 1),
        ('Bodyweight squats / Приседания', 3, 'medium', 1), ('Wall push-ups / Отжимания от стены', 3, 'low', 3),
        ('Glute bridges / Ягодичный мостик', 3, 'low', 1), ('Knee push-ups / Отжимания с колен', 3, 'medium', 3),
        ('Standing calf raises / Подъёмы на носки', 3, 'low', 1), ('Superman / Супермен', 3, 'low', 2),
        ('Chair sit-to-stand / Подъём со стула', 3, 'low', 1), ('Reverse lunges / Выпады назад', 3, 'medium', 1),
        ('Hamstring stretch / Растяжка задней поверхности бедра', 4, 'low', 1),
        ('Shoulder stretch / Растяжка плеч', 4, 'low', 4), ('Chest stretch / Растяжка груди', 4, 'low', 3),
        ('Back stretch / Растяжка спины', 4, 'low', 2), ('Calf stretch / Растяжка икр', 4, 'low', 1),
        ('Dead bug / Мёртвый жук', 5, 'low', 5), ('Bird dog / Птица-собака', 5, 'low', 5),
        ('Plank / Планка', 5, 'medium', 5), ('Seated knee lifts / Подъём колен сидя', 5, 'low', 5),
        ('Heel taps / Касания пяток', 5, 'low', 5),
    ]
    for name, category, difficulty, muscle in exercises:
        sets, reps = (1, 10) if category in (1, 4) else (3, 12)
        cur.execute('INSERT INTO exercises (exercise_name, category_id, difficulty, description, recommended_sets, recommended_reps, rest_between_sets_sec) VALUES (%s,%s,%s,%s,%s,%s,60) RETURNING exercise_id',
                    (name, category, difficulty, 'Illustrative exercise for the Smart PE demonstration.', sets, reps))
        eid = cur.fetchone()[0]
        cur.execute('INSERT INTO exercise_muscle_group (exercise_id, muscle_group_id) VALUES (%s,%s)', (eid, muscle))
        if eid in (8, 9, 16):
            cur.execute('INSERT INTO exercise_contraindications (exercise_id, injury_type_id) VALUES (%s,1)', (eid,))


def seed_students(cur, teacher_password, student_password):
    today = date.today()
    training_date = next(today + timedelta(days=offset) for offset in range(7)
                         if (today + timedelta(days=offset)).weekday() in (0, 2, 4))
    for index in range(1, 7):
        female = index % 2 == 0
        height, weight = (165, 58 + index) if female else (175, 67 + index)
        fitness = 2 + (index % 3) * 0.5
        cur.execute('INSERT INTO students (student_name, age, gender) VALUES (%s,%s,%s) RETURNING student_id',
                    (f'Demo Student {index:02d} / Демо-студент {index:02d}', 18 + index % 4, 'Female' if female else 'Male'))
        sid = cur.fetchone()[0]
        cur.execute('INSERT INTO students_health_profiles (student_id, medical_group_id, height_cm, weight_kg, cooper_meters, jump_forward, flexibility_cm, push_ups, pull_ups, sit_ups, measurement_date) VALUES (%s,%s,%s,%s,%s,200,25,%s,%s,30,%s) RETURNING health_profile_id',
                    (sid, 2 if index == 2 else 1, height, weight, 1800 + index * 100, 15 + index * 2, 3 + index, today))
        hp = cur.fetchone()[0]
        cur.execute('INSERT INTO students_physical_readiness_assessments (health_profile_id, assessment_version_id, "BMI", strength_score, endurance_score, flexibility_score) VALUES (%s,1,%s,%s,%s,%s)',
                    (hp, round(weight / (height / 100) ** 2, 2), fitness, fitness, fitness))
        for days_ago in (21, 14, 7, 0):
            completed = days_ago > 0
            workout_date = training_date - timedelta(days=days_ago)
            cur.execute('INSERT INTO workout_plan (student_id, workout_standard_id, date, workout_status, satisfaction) VALUES (%s,1,%s,%s,%s) RETURNING workout_plan_id',
                        (sid, workout_date, 'COMPLETED' if completed else 'SCHEDULED', 'Liked' if completed else None))
            pid = cur.fetchone()[0]
            for order, (eid, slot, muscle) in enumerate([(1, 'warmup', 4), (5, 'main', 1), (10, 'main', 3), (22, 'main', 5), (17, 'cooldown', 1)], 1):
                cur.execute('INSERT INTO assigned_exercise (workout_plan_id, exercise_id, slot_type, day_of_week, order_in_session, predicted_score, recommended_sets, recommended_reps) VALUES (%s,%s,%s,%s,%s,0.8,3,12) RETURNING assigned_exercise_id',
                            (pid, eid, slot, workout_date.strftime('%A').upper(), order))
                aid = cur.fetchone()[0]
                cur.execute('INSERT INTO assigned_exercise_muscle_group (assigned_exercise_id, muscle_group_id) VALUES (%s,%s)', (aid, muscle))
                if completed:
                    done = not (index == 3 and order == 3)
                    cur.execute('INSERT INTO student_assigned_exercise_interaction (student_id, workout_plan_id, assigned_exercise_id, completed, actually_sets, actually_reps, perceived_difficulty, interaction_date, exercise_status, feedback_notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                                (sid, pid, aid, done, 3 if done else 0, 12 if done else 0, 'Normal', workout_date, 'COMPLETED' if done else 'SKIPPED', 'Fictional demo result'))
    cur.execute("INSERT INTO student_injury_history (student_id, injury_type_id, diagnosis_date, recovery_date, recovery_status, doctor_notes) VALUES (2,1,%s,%s,'active','Fictional example only')", (today, today + timedelta(days=14)))
    for email, password, role, sid in [('teacher2@smartpe.edu', teacher_password, 'teacher', None),
                                        ('student.demo@smartpe.edu', student_password, 'student', 1)]:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute('INSERT INTO users (email, password_hash, role, student_id, is_active) VALUES (%s,%s,%s,%s,TRUE)', (email, hashed, role, sid))

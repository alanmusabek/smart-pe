"""
generate_data.py
Populates PostgreSQL with ALL tables including workout interaction simulation.
"""
import psycopg2
import random
import bcrypt
from datetime import date, timedelta

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "fitness_db",
    "user": "postgres",
    "password": "1234",
}

random.seed(42)
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

def run(sql, params=None):
    cur.execute(sql, params)

def fetchone(sql, params=None):
    cur.execute(sql, params)
    return cur.fetchone()

def fetchall(sql, params=None):
    cur.execute(sql, params)
    return cur.fetchall()

# ── 0. CREATE TABLES ───────────────────────────────────────────────────────
run("""
DROP TABLE IF EXISTS
    muscle_fatigue,
    student_assigned_exercise_interaction,
    assigned_exercise_muscle_group,
    assigned_exercise,
    workout_plan,
    student_injury_history,
    students_physical_readiness_assessments,
    students_health_profiles,
    jt_exercise_contraindications,
    jt_exercise_equipment,
    jt_exercise_muscle_group,
    assessment_rule,
    assessment_version,
    exercises,
    exercise_categories,
    equipment,
    muscle_group,
    injury_types,
    medical_group,
    users,
    students
CASCADE
""")

# Core tables
run("""
CREATE TABLE students (
    student_id   SERIAL PRIMARY KEY,
    student_name VARCHAR(50) NOT NULL,
    age          INT         CHECK (age BETWEEN 16 AND 30),
    gender       VARCHAR(6)  CHECK (gender IN ('Male','Female'))
)
""")

run("""
CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    email         VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    role          VARCHAR(10) CHECK (role IN ('student','teacher')),
    student_id    INT REFERENCES students(student_id),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

run("""
CREATE TABLE medical_group (
    group_id    SERIAL PRIMARY KEY,
    group_name  VARCHAR(50) NOT NULL,
    description TEXT
)
""")

run("""
CREATE TABLE exercise_categories (
    category_id   SERIAL PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL
)
""")

run("""
CREATE TABLE muscle_group (
    muscle_group_id SERIAL PRIMARY KEY,
    muscle_name     VARCHAR(50) NOT NULL
)
""")

run("""
CREATE TABLE equipment (
    equipment_id   SERIAL PRIMARY KEY,
    equipment_name VARCHAR(50) NOT NULL
)
""")

run("""
CREATE TABLE injury_types (
    injury_type_id         SERIAL PRIMARY KEY,
    type_name              VARCHAR(50) NOT NULL,
    body_region            VARCHAR(50),
    severity_class         VARCHAR(20) CHECK (severity_class IN ('mild','moderate','severe')),
    typical_recovery_weeks INT
)
""")

run("""
CREATE TABLE assessment_version (
    assessment_version_id SERIAL PRIMARY KEY,
    version_name          VARCHAR(50) NOT NULL,
    description           TEXT,
    effective_date        DATE
)
""")

run("""
CREATE TABLE assessment_rule (
    rule_id               SERIAL PRIMARY KEY,
    assessment_version_id INT         NOT NULL REFERENCES assessment_version(assessment_version_id),
    medical_group_id      INT         NOT NULL REFERENCES medical_group(group_id),
    test_type             VARCHAR(20) NOT NULL CHECK (test_type IN ('PUSHUP','PULLUP','COOPER','FLEXIBILITY')),
    gender                VARCHAR(6)  NOT NULL CHECK (gender IN ('Male','Female')),
    min_value             FLOAT       NOT NULL,
    max_value             FLOAT       NOT NULL,
    score                 SMALLINT    CHECK (score BETWEEN 1 AND 4)
)
""")

run("""
CREATE TABLE exercises (
    exercise_id           SERIAL PRIMARY KEY,
    exercise_name         VARCHAR(250) NOT NULL,
    category_id           INT          NOT NULL REFERENCES exercise_categories(category_id),
    difficulty            INT          CHECK (difficulty BETWEEN 1 AND 5),
    description           TEXT,
    recommended_sets      INT,
    recommended_reps      INT,
    rest_between_sets_sec INT
)
""")

run("""
CREATE TABLE jt_exercise_muscle_group (
    exercise_muscle_group_id SERIAL PRIMARY KEY,
    exercise_id              INT NOT NULL REFERENCES exercises(exercise_id),
    muscle_group_id          INT NOT NULL REFERENCES muscle_group(muscle_group_id)
)
""")

run("""
CREATE TABLE jt_exercise_equipment (
    exercise_equipment_id SERIAL PRIMARY KEY,
    exercise_id           INT NOT NULL REFERENCES exercises(exercise_id),
    equipment_id          INT NOT NULL REFERENCES equipment(equipment_id)
)
""")

run("""
CREATE TABLE jt_exercise_contraindications (
    exercise_contraindication SERIAL PRIMARY KEY,
    exercise_id               INT NOT NULL REFERENCES exercises(exercise_id),
    injury_type_id            INT NOT NULL REFERENCES injury_types(injury_type_id)
)
""")

run("""
CREATE TABLE students_health_profiles (
    health_profile_id SERIAL PRIMARY KEY,
    student_id        INT   NOT NULL REFERENCES students(student_id),
    medical_group_id  INT   NOT NULL REFERENCES medical_group(group_id),
    height_cm         FLOAT CHECK (height_cm BETWEEN 140 AND 220),
    weight_kg         FLOAT CHECK (weight_kg BETWEEN 30 AND 300),
    cooper_meters     INT   CHECK (cooper_meters BETWEEN 800 AND 3500),
    jump_forward      INT   CHECK (jump_forward BETWEEN 0 AND 400),
    flexibility_cm    FLOAT CHECK (flexibility_cm BETWEEN 0 AND 50),
    push_ups          INT   CHECK (push_ups BETWEEN 0 AND 300),
    pull_ups          INT   CHECK (pull_ups BETWEEN 0 AND 300),
    sit_ups           INT   CHECK (sit_ups BETWEEN 0 AND 100),
    measurement_date  DATE
)
""")

run("""
CREATE TABLE students_physical_readiness_assessments (
    evaluation_id         SERIAL PRIMARY KEY,
    health_profile_id     INT   NOT NULL REFERENCES students_health_profiles(health_profile_id),
    assessment_version_id INT   NOT NULL REFERENCES assessment_version(assessment_version_id),
    bmi                   FLOAT,
    strength_score        FLOAT,
    endurance_score       FLOAT,
    flexibility_score     FLOAT
)
""")

run("""
CREATE TABLE student_injury_history (
    injury_record_id SERIAL PRIMARY KEY,
    student_id       INT         NOT NULL REFERENCES students(student_id),
    injury_type_id   INT         NOT NULL REFERENCES injury_types(injury_type_id),
    diagnosis_date   DATE,
    recovery_date    DATE,
    recovery_status  VARCHAR(20) CHECK (recovery_status IN ('active','recovered'))
)
""")

# Workout tables
run("""
CREATE TABLE workout_plan (
    workout_plan_id     SERIAL PRIMARY KEY,
    student_id          INT         NOT NULL REFERENCES students(student_id),
    workout_standard_id INT         NOT NULL REFERENCES assessment_version(assessment_version_id),
    date                DATE        NOT NULL,
    workout_status      VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED'
        CHECK (workout_status IN ('COMPLETED','IN_PROGRESS','DISCARDED','SKIPPED','SCHEDULED')),
    satisfaction        VARCHAR(10) CHECK (satisfaction IN ('Liked','Disliked'))
)
""")

run("""
CREATE TABLE assigned_exercise (
    assigned_exercise_id SERIAL PRIMARY KEY,
    workout_plan_id      INT         NOT NULL REFERENCES workout_plan(workout_plan_id),
    exercise_id          INT         NOT NULL REFERENCES exercises(exercise_id),
    slot_type            VARCHAR(10) NOT NULL CHECK (slot_type IN ('warmup','main','cooldown')),
    day_of_week          VARCHAR(10) NOT NULL CHECK (day_of_week IN ('MONDAY','WEDNESDAY','FRIDAY')),
    order_in_session     INT         NOT NULL,
    predicted_score      FLOAT,
    recommended_sets     INT,
    recommended_reps     INT
)
""")

run("""
CREATE TABLE assigned_exercise_muscle_group (
    assigned_exercise_muscle_group_id SERIAL PRIMARY KEY,
    assigned_exercise_id              INT NOT NULL REFERENCES assigned_exercise(assigned_exercise_id),
    muscle_group_id                   INT NOT NULL REFERENCES muscle_group(muscle_group_id)
)
""")

run("""
CREATE TABLE student_assigned_exercise_interaction (
    assigned_exercise_interaction_id SERIAL PRIMARY KEY,
    student_id                       INT         NOT NULL REFERENCES students(student_id),
    workout_plan_id                  INT         NOT NULL REFERENCES workout_plan(workout_plan_id),
    assigned_exercise_id             INT         NOT NULL REFERENCES assigned_exercise(assigned_exercise_id),
    completed                        BOOLEAN     NOT NULL DEFAULT FALSE,
    actually_sets                    INT,
    actually_reps                    INT,
    perceived_difficulty             VARCHAR(20) CHECK (perceived_difficulty IN
        ('Very Easy','Easy','Normal','Hard','Very Hard')),
    feedback_notes                   TEXT,
    interaction_date                 DATE,
    exercise_status                  VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED'
        CHECK (exercise_status IN
            ('COMPLETED','IN_PROGRESS','DISCARDED','SKIPPED','SCHEDULED'))
)
""")

run("""
CREATE TABLE muscle_fatigue (
    muscle_fatigue_id                 SERIAL PRIMARY KEY,
    workout_plan_id                   INT         NOT NULL REFERENCES workout_plan(workout_plan_id),
    student_id                        INT         NOT NULL REFERENCES students(student_id),
    assigned_exercise_id              INT         NOT NULL REFERENCES assigned_exercise(assigned_exercise_id),
    assigned_exercise_muscle_group_id INT         NOT NULL REFERENCES assigned_exercise_muscle_group(assigned_exercise_muscle_group_id),
    date                              DATE        NOT NULL,
    recovery_hours                    FLOAT       NOT NULL,
    status                            VARCHAR(12) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','NOT ACTIVE')),
    recovery_left                     FLOAT       NOT NULL
)
""")

conn.commit()
print("✅ All tables created.")

# ── 1. REFERENCE DATA ───────────────────────────────────────────────────────
for c in [(1,"warmup"),(2,"cardio"),(3,"strength"),(4,"stretching"),(5,"core")]:
    run("INSERT INTO exercise_categories (category_id,category_name) VALUES (%s,%s) ON CONFLICT DO NOTHING", c)

for m in [(1,"chest"),(2,"back"),(3,"shoulders"),(4,"biceps"),(5,"triceps"),
          (6,"core"),(7,"quadriceps"),(8,"hamstrings"),(9,"glutes"),(10,"calves")]:
    run("INSERT INTO muscle_group (muscle_group_id,muscle_name) VALUES (%s,%s) ON CONFLICT DO NOTHING", m)

for e in [(1,"Barbell"),(2,"Dumbbell"),(3,"Bench"),(4,"Pull-up Bar"),
          (5,"Resistance Band"),(6,"Kettlebell"),(7,"Mat"),(8,"None")]:
    run("INSERT INTO equipment (equipment_id,equipment_name) VALUES (%s,%s) ON CONFLICT DO NOTHING", e)

for it in [(1,"knee_sprain","knee","moderate",6),(2,"lower_back_pain","spine","severe",12),
           (3,"shoulder_strain","shoulder","mild",4),(4,"ankle_sprain","ankle","mild",3),
           (5,"wrist_strain","wrist","mild",3),(6,"hip_flexor","hip","moderate",5),
           (7,"neck_strain","neck","mild",4)]:
    run("INSERT INTO injury_types (injury_type_id,type_name,body_region,severity_class,typical_recovery_weeks) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", it)

for mg in [(1,"basic","No restrictions, full intensity allowed"),
           (2,"prepared","Moderate intensity, avoid high-impact"),
           (3,"special","Low intensity only, doctor supervision")]:
    run("INSERT INTO medical_group (group_id,group_name,description) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", mg)

run("INSERT INTO assessment_version (assessment_version_id,version_name,description,effective_date) VALUES (1,'Standard 2024','Default physical readiness assessment','2024-01-01') ON CONFLICT DO NOTHING")

for ar in [
    (1,1,1,'PUSHUP','Male',35,300,4),(2,1,1,'PUSHUP','Male',25,34,3),
    (3,1,1,'PUSHUP','Male',15,24,2),(4,1,1,'PUSHUP','Male',0,14,1),
    (5,1,1,'PUSHUP','Female',20,300,4),(6,1,1,'PUSHUP','Female',12,19,3),
    (7,1,1,'PUSHUP','Female',6,11,2),(8,1,1,'PUSHUP','Female',0,5,1),
    (9,1,1,'PULLUP','Male',12,300,4),(10,1,1,'PULLUP','Male',8,11,3),
    (11,1,1,'PULLUP','Male',4,7,2),(12,1,1,'PULLUP','Male',0,3,1),
    (13,1,1,'COOPER','Male',2800,3500,4),(14,1,1,'COOPER','Male',2400,2799,3),
    (15,1,1,'COOPER','Male',2000,2399,2),(16,1,1,'COOPER','Male',800,1999,1),
    (17,1,1,'FLEXIBILITY','Male',30,50,4),(18,1,1,'FLEXIBILITY','Male',20,29,3),
    (19,1,1,'FLEXIBILITY','Male',10,19,2),(20,1,1,'FLEXIBILITY','Male',0,9,1),
    (21,1,1,'FLEXIBILITY','Female',35,50,4),(22,1,1,'FLEXIBILITY','Female',25,34,3),
    (23,1,1,'FLEXIBILITY','Female',15,24,2),(24,1,1,'FLEXIBILITY','Female',0,14,1),
]:
    run("INSERT INTO assessment_rule (rule_id,assessment_version_id,medical_group_id,test_type,gender,min_value,max_value,score) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ar)

# ── 2. EXERCISES ────────────────────────────────────────────────────────────
exercises = [
    (1,"Jumping Jacks",1,1,"Full body warmup",2,20,30),
    (2,"Arm Circles",1,1,"Shoulder warmup",2,15,20),
    (3,"Leg Swings",1,1,"Hip mobility warmup",2,12,20),
    (4,"High Knees",1,2,"Cardio warmup",2,20,30),
    (5,"Hip Rotations",1,1,"Hip joint warmup",2,10,20),
    (6,"Running",2,2,"Steady state cardio",1,1,60),
    (7,"Burpees",2,4,"High intensity cardio",3,10,60),
    (8,"Jump Rope",2,3,"Cardio endurance",3,30,45),
    (9,"Mountain Climbers",2,3,"Core cardio combo",3,20,45),
    (10,"Box Jumps",2,4,"Explosive cardio",3,8,60),
    (11,"Push-ups",3,2,"Chest and triceps",3,12,60),
    (12,"Pull-ups",3,4,"Back and biceps",3,8,90),
    (13,"Squats",3,2,"Quad and glute compound",3,12,60),
    (14,"Deadlift",3,5,"Full posterior chain",3,5,120),
    (15,"Bench Press",3,4,"Chest compound",3,8,90),
    (16,"Overhead Press",3,4,"Shoulder compound",3,8,90),
    (17,"Barbell Row",3,4,"Upper back compound",3,8,90),
    (18,"Lunges",3,2,"Unilateral leg strength",3,10,60),
    (19,"Dumbbell Curl",3,2,"Bicep isolation",3,12,45),
    (20,"Tricep Dips",3,3,"Tricep isolation",3,10,60),
    (21,"Standing Quad Stretch",4,1,"Quad flexibility",2,1,20),
    (22,"Hamstring Stretch",4,1,"Hamstring flexibility",2,1,20),
    (23,"Chest Opener Stretch",4,1,"Chest and shoulder flex",2,1,20),
    (24,"Cat-Cow Stretch",4,1,"Spine mobility",2,10,20),
    (25,"Child's Pose",4,1,"Full back stretch",2,1,30),
    (26,"Plank",5,2,"Core stability",3,1,60),
    (27,"Crunches",5,2,"Abdominal endurance",3,20,45),
    (28,"Russian Twists",5,3,"Oblique strength",3,16,45),
    (29,"Leg Raises",5,3,"Lower ab strength",3,12,45),
    (30,"Dead Bug",5,2,"Core stability anti-rotation",3,10,45),
]
for ex in exercises:
    run("INSERT INTO exercises (exercise_id,exercise_name,category_id,difficulty,description,recommended_sets,recommended_reps,rest_between_sets_sec) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", ex)

EXERCISE_MUSCLES = {
    1:[7,9],2:[3],3:[7,9],4:[7,6],5:[9],6:[7,8],7:[6,7],8:[7,10],9:[6,7],10:[7,9],
    11:[1,5],12:[2,4],13:[7,9],14:[2,8,9],15:[1,5],16:[3,5],17:[2,3],18:[7,9],19:[4],20:[5],
    21:[7],22:[8],23:[1,3],24:[2,6],25:[2],26:[6],27:[6],28:[6],29:[6],30:[6],
}
jt_id = 1
for ex_id, muscles in EXERCISE_MUSCLES.items():
    for mg_id in muscles:
        run("INSERT INTO jt_exercise_muscle_group (exercise_muscle_group_id,exercise_id,muscle_group_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (jt_id,ex_id,mg_id))
        jt_id += 1

jt_id = 1
for ex_id, eq in {
    1:8,2:8,3:8,4:8,5:8,6:8,7:8,8:8,9:8,10:3,
    11:8,12:4,13:8,14:1,15:[1,3],16:1,17:1,18:8,19:2,20:3,
    21:8,22:8,23:8,24:7,25:7,26:7,27:7,28:7,29:7,30:7,
}.items():
    for eq_id in (eq if isinstance(eq,list) else [eq]):
        run("INSERT INTO jt_exercise_equipment (exercise_equipment_id,exercise_id,equipment_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (jt_id,ex_id,eq_id))
        jt_id += 1

jt_id = 1
for ex_id, inj_id in [
    (13,1),(14,1),(10,1),(18,1),(14,2),(17,2),(16,2),(9,2),
    (16,3),(15,3),(12,3),(17,3),(6,4),(10,4),(8,4),
    (15,5),(19,5),(17,5),(13,6),(14,6),(18,6),(16,7),(2,7),
]:
    run("INSERT INTO jt_exercise_contraindications (exercise_contraindication,exercise_id,injury_type_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (jt_id,ex_id,inj_id))
    jt_id += 1

conn.commit()
print("✅ Reference + exercise data inserted.")

# ── 3. SYNTHETIC STUDENTS ───────────────────────────────────────────────────
first_names_m = ["Amir","Danil","Ruslan","Arman","Timur","Alexei","Nursultan","Bekzat","Ilyas","Dias"]
first_names_f = ["Aida","Zarina","Aliya","Dana","Madina","Karina","Ainur","Saltanat","Gulnara","Nazym"]
last_names = ["Seitkali","Akhmetov","Bekova","Nurlanov","Dzhaksybekov",
              "Issayev","Moldabekov","Omarov","Satpayev","Tulegenov"]

today = date.today()

def lookup_score(test_type, value, gender, mg_id):
    row = fetchone("""
        SELECT score FROM assessment_rule
        WHERE assessment_version_id = 1
        AND medical_group_id = %s AND test_type = %s AND gender = %s
        AND %s BETWEEN min_value AND max_value
        LIMIT 1
    """, (mg_id, test_type, gender, value))
    return row[0] if row else 1

for student_id in range(1, 501):
    gender = random.choice(["Male","Female"])
    age = random.randint(16, 30)
    name = f"{random.choice(first_names_m if gender=='Male' else first_names_f)} {random.choice(last_names)}"
    run("INSERT INTO students (student_id,student_name,age,gender) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (student_id, name, age, gender))

    mg_id = random.choices([1,2,3], weights=[0.65,0.25,0.10])[0]
    intensity = {1:1.0, 2:0.7, 3:0.4}[mg_id]

    if gender == "Male":
        height = round(random.uniform(165,195),1)
        weight = round(random.uniform(60,110),1)
        cooper = int(random.gauss(2400*intensity,300))
        push_ups = int(random.gauss(25*intensity,8))
        pull_ups = int(random.gauss(8*intensity,3))
        flex = round(random.gauss(25*intensity,8),1)
        sit_ups = int(random.gauss(30*intensity,8))
        jump = int(random.gauss(180*intensity,30))
    else:
        height = round(random.uniform(155,180),1)
        weight = round(random.uniform(48,85),1)
        cooper = int(random.gauss(2100*intensity,300))
        push_ups = int(random.gauss(15*intensity,5))
        pull_ups = 0
        flex = round(random.gauss(30*intensity,8),1)
        sit_ups = int(random.gauss(25*intensity,8))
        jump = int(random.gauss(160*intensity,25))

    cooper = max(800, min(3500, cooper))
    push_ups = max(0, min(300, push_ups))
    pull_ups = max(0, min(300, pull_ups))
    flex = max(0.0, min(50.0, flex))
    sit_ups = max(0, min(100, sit_ups))
    jump = max(0, min(400, jump))
    height = max(140, min(220, height))
    weight = max(30, min(300, weight))

    mdate = today - timedelta(days=random.randint(1,180))
    run("""INSERT INTO students_health_profiles
        (student_id,medical_group_id,height_cm,weight_kg,cooper_meters,
         jump_forward,flexibility_cm,push_ups,pull_ups,sit_ups,measurement_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (student_id,mg_id,height,weight,cooper,jump,flex,push_ups,pull_ups,sit_ups,mdate))

    hp_id = fetchone("SELECT health_profile_id FROM students_health_profiles WHERE student_id=%s LIMIT 1", (student_id,))[0]

    bmi = round(weight/((height/100)**2), 2)
    strength_score = round((lookup_score('PUSHUP',push_ups,gender,mg_id) + lookup_score('PULLUP',pull_ups,gender,mg_id)) / 2, 2)
    endurance_score = float(lookup_score('COOPER', cooper, gender, mg_id))
    flex_score = float(lookup_score('FLEXIBILITY', flex, gender, mg_id))

    run("""INSERT INTO students_physical_readiness_assessments
        (health_profile_id,assessment_version_id,bmi,strength_score,endurance_score,flexibility_score)
        VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (hp_id,1,bmi,strength_score,endurance_score,flex_score))

    if random.random() < 0.30:
        for inj_id in random.sample(range(1,8), random.randint(1,2)):
            diag_date = today - timedelta(days=random.randint(7,90))
            rec_date = diag_date + timedelta(days=random.randint(14,120))
            status = "active" if rec_date > today else "recovered"
            run("""INSERT INTO student_injury_history
                (student_id,injury_type_id,diagnosis_date,recovery_date,recovery_status)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (student_id,inj_id,diag_date,rec_date,status))

    # Create user account for student (default password: "student123")
    email = f"student{student_id}@smartpe.edu"
    password_hash = bcrypt.hashpw(b"student123", bcrypt.gensalt()).decode()
    run("""INSERT INTO users (email, password_hash, role, student_id)
           VALUES (%s, %s, 'student', %s) ON CONFLICT DO NOTHING""",
        (email, password_hash, student_id))

conn.commit()
print("✅ 500 students inserted.")

# Create teacher accounts
for i in range(1, 4):
    email = f"teacher{i}@smartpe.edu"
    password_hash = bcrypt.hashpw(b"teacher123", bcrypt.gensalt()).decode()
    run("""INSERT INTO users (email, password_hash, role, student_id)
           VALUES (%s, %s, 'teacher', NULL) ON CONFLICT DO NOTHING""",
        (email, password_hash))

conn.commit()
print("✅ Teacher accounts created (teacher1@smartpe.edu / teacher123)")

# ── 4. SYNTHETIC WORKOUT INTERACTION SIMULATION ─────────────────────────────
DAYS = ["MONDAY","WEDNESDAY","FRIDAY"]
MUSCLE_RECOVERY_HOURS = {1:48,2:48,3:48,4:36,5:36,6:24,7:72,8:72,9:72,10:24}
DIFFICULTY_PERCEPTION = ["Very Easy","Easy","Normal","Hard","Very Hard"]

def get_safe_exercises(student_id, mg_id):
    max_diff = {1:5, 2:3, 3:2}[mg_id]
    rows = fetchall("""
        SELECT e.exercise_id, e.category_id, e.difficulty,
               e.recommended_sets, e.recommended_reps
        FROM exercises e
        WHERE e.difficulty <= %s
        AND e.exercise_id NOT IN (
            SELECT DISTINCT jec.exercise_id
            FROM student_injury_history sih
            JOIN jt_exercise_contraindications jec ON jec.injury_type_id = sih.injury_type_id
            WHERE sih.student_id = %s AND sih.recovery_status = 'active'
        )
    """, (max_diff, student_id))
    return rows

def pick_exercises_for_day(safe_exercises, day_index, used_ids):
    by_cat = {}
    for row in safe_exercises:
        ex_id, cat_id, diff, rec_sets, rec_reps = row
        if ex_id in used_ids:
            continue
        by_cat.setdefault(cat_id, []).append(row)
    for cat in by_cat:
        random.shuffle(by_cat[cat])
    main_cats = [3] if day_index < 2 else [2, 5]
    warmup = by_cat.get(1, [])[:2]
    main = []
    for cat in main_cats:
        main += by_cat.get(cat, [])
    main = main[:3]
    cooldown = (by_cat.get(4, []) + by_cat.get(5, []))[:2]
    selected = warmup + main + cooldown
    return warmup, main, cooldown, selected

def simulate_interaction(exercise_id, slot_type, fitness_level, difficulty):
    diff_gap = difficulty - fitness_level * (5/4)
    if slot_type == "warmup":
        complete_prob = 0.95
    elif diff_gap > 1.5:
        complete_prob = 0.45
    elif diff_gap < -1.5:
        complete_prob = 0.85
    else:
        complete_prob = 0.80
    completed = random.random() < complete_prob
    if completed:
        row = fetchone("SELECT recommended_sets, recommended_reps FROM exercises WHERE exercise_id=%s", (exercise_id,))
        rec_sets, rec_reps = row
        reduction = max(0.5, 1.0 - max(0, diff_gap) * 0.15)
        actually_sets = max(1, round(rec_sets * reduction))
        actually_reps = max(1, round(rec_reps * reduction))
        if diff_gap > 1.5:
            perc = random.choices(DIFFICULTY_PERCEPTION, weights=[0,5,20,45,30])[0]
        elif diff_gap > 0.5:
            perc = random.choices(DIFFICULTY_PERCEPTION, weights=[5,15,40,30,10])[0]
        elif diff_gap > -0.5:
            perc = random.choices(DIFFICULTY_PERCEPTION, weights=[10,25,45,15,5])[0]
        else:
            perc = random.choices(DIFFICULTY_PERCEPTION, weights=[30,40,20,8,2])[0]
        ex_status = "COMPLETED"
    else:
        actually_sets = 0
        actually_reps = 0
        perc = random.choices(DIFFICULTY_PERCEPTION, weights=[5,10,20,35,30])[0]
        ex_status = random.choices(["SKIPPED","DISCARDED"], weights=[0.7,0.3])[0]
    return completed, actually_sets, actually_reps, perc, ex_status

print("⏳ Simulating workout interactions for 500 students (3 weeks each)...")
for student_id in range(1, 501):
    row = fetchone("""
        SELECT hp.medical_group_id, a.strength_score, a.endurance_score, a.flexibility_score
        FROM students_health_profiles hp
        JOIN students_physical_readiness_assessments a ON a.health_profile_id = hp.health_profile_id
        WHERE hp.student_id = %s LIMIT 1
    """, (student_id,))
    if not row:
        continue
    mg_id, s_score, e_score, f_score = row
    fitness_level = (float(s_score) + float(e_score) + float(f_score)) / 3
    safe_exercises = get_safe_exercises(student_id, mg_id)
    if len(safe_exercises) < 7:
        continue
    used_ids_week = set()
    for week in range(3):
        week_start = today - timedelta(weeks=(3 - week))
        used_ids_week.clear()
        for day_index, day_name in enumerate(DAYS):
            plan_date = week_start + timedelta(days=[0,2,4][day_index])
            if random.random() > 0.80:
                continue
            warmup, main, cooldown, selected = pick_exercises_for_day(safe_exercises, day_index, used_ids_week)
            if not selected:
                continue
            session_completed = random.random() < 0.75
            workout_status = "COMPLETED" if session_completed else random.choice(["DISCARDED","SKIPPED"])
            satisfaction = random.choices(["Liked","Disliked"], weights=[0.7,0.3])[0] if session_completed else None
            run("""INSERT INTO workout_plan
                (student_id,workout_standard_id,date,workout_status,satisfaction)
                VALUES (%s,%s,%s,%s,%s)""",
                (student_id, 1, plan_date, workout_status, satisfaction))
            plan_id = fetchone("SELECT lastval()")[0]
            slot_map = (
                [("warmup", ex) for ex in warmup] +
                [("main", ex) for ex in main] +
                [("cooldown", ex) for ex in cooldown]
            )
            order = 1
            for slot_type, ex_row in slot_map:
                ex_id, cat_id, difficulty, rec_sets, rec_reps = ex_row
                predicted_score = round(random.uniform(0.4, 0.95), 4)
                run("""INSERT INTO assigned_exercise
                    (workout_plan_id,exercise_id,slot_type,day_of_week,
                     order_in_session,predicted_score,recommended_sets,recommended_reps)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (plan_id,ex_id,slot_type,day_name,order,predicted_score,rec_sets,rec_reps))
                ae_id = fetchone("SELECT lastval()")[0]
                muscle_groups = EXERCISE_MUSCLES.get(ex_id, [])
                aemg_ids = []
                for mg_grp_id in muscle_groups:
                    run("""INSERT INTO assigned_exercise_muscle_group
                        (assigned_exercise_id,muscle_group_id) VALUES (%s,%s)""",
                        (ae_id, mg_grp_id))
                    aemg_id = fetchone("SELECT lastval()")[0]
                    aemg_ids.append((aemg_id, mg_grp_id))
                completed, act_sets, act_reps, perc_diff, ex_status = simulate_interaction(
                    ex_id, slot_type, fitness_level, difficulty)
                if not session_completed:
                    completed = False
                    act_sets = 0
                    act_reps = 0
                    ex_status = workout_status
                run("""INSERT INTO student_assigned_exercise_interaction
                    (student_id,workout_plan_id,assigned_exercise_id,completed,
                     actually_sets,actually_reps,perceived_difficulty,
                     interaction_date,exercise_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (student_id,plan_id,ae_id,completed,
                     act_sets,act_reps,perc_diff,
                     plan_date,ex_status))
                if completed and slot_type == "main":
                    for aemg_id, mg_grp_id in aemg_ids:
                        recovery_h = MUSCLE_RECOVERY_HOURS.get(mg_grp_id, 48)
                        hours_since = (today - plan_date).total_seconds() / 3600
                        recovery_left = max(0.0, recovery_h - hours_since)
                        status = "ACTIVE" if recovery_left > 0 else "NOT ACTIVE"
                        run("""INSERT INTO muscle_fatigue
                            (workout_plan_id,student_id,assigned_exercise_id,
                             assigned_exercise_muscle_group_id,date,
                             recovery_hours,status,recovery_left)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (plan_id,student_id,ae_id,aemg_id,
                             plan_date,recovery_h,status,recovery_left))
                used_ids_week.add(ex_id)
                order += 1
    if student_id % 50 == 0:
        conn.commit()
        print(f"  Simulated {student_id}/500 students...")

conn.commit()
cur.close()
conn.close()
print("✅ Done. All workout interaction data inserted.")
-- Generated from db/models. Contains schema only, no student records.

CREATE TYPE attendance_status_enum AS ENUM ('PRESENT', 'ABSENT', 'LATE');

CREATE TYPE user_role_enum AS ENUM ('student', 'teacher');

CREATE TYPE gender_enum AS ENUM ('Male', 'Female');

CREATE TYPE test_type_enum AS ENUM ('PUSHUP', 'PULLUP', 'COOPER', 'FLEXIBILITY');

CREATE TYPE credit_status_enum AS ENUM ('PASSED', 'NOT_PASSED', 'IN_PROGRESS');

CREATE TYPE workout_status_enum AS ENUM ('COMPLETED', 'IN_PROGRESS', 'DISCARDED', 'SKIPPED', 'SCHEDULED');

CREATE TYPE satisfaction_enum AS ENUM ('Liked', 'Disliked');

CREATE TYPE slot_type_enum AS ENUM ('warmup', 'main', 'cooldown');

CREATE TYPE day_of_week_enum AS ENUM ('MONDAY', 'WEDNESDAY', 'FRIDAY');

CREATE TYPE perceived_difficulty_enum AS ENUM ('Very Easy', 'Easy', 'Normal', 'Hard', 'Very Hard');

CREATE TYPE exercise_status_enum AS ENUM ('COMPLETED', 'IN_PROGRESS', 'DISCARDED', 'SKIPPED', 'SCHEDULED');

CREATE TYPE fatigue_status_enum AS ENUM ('ACTIVE', 'NOT ACTIVE');

CREATE TABLE theoretical_test (
	test_id SERIAL NOT NULL, 
	title VARCHAR NOT NULL, 
	description TEXT, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (test_id)
);

CREATE TABLE exercise_categories (
	category_id SERIAL NOT NULL, 
	category_name VARCHAR NOT NULL, 
	PRIMARY KEY (category_id)
);

CREATE TABLE muscle_group (
	muscle_group_id SERIAL NOT NULL, 
	muscle_name VARCHAR NOT NULL, 
	PRIMARY KEY (muscle_group_id)
);

CREATE TABLE equipment (
	equipment_id SERIAL NOT NULL, 
	equipment_name VARCHAR NOT NULL, 
	PRIMARY KEY (equipment_id)
);

CREATE TABLE injury_types (
	injury_type_id SERIAL NOT NULL, 
	type_name VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	body_region VARCHAR NOT NULL, 
	severity_class VARCHAR NOT NULL, 
	typical_recovery_weeks INTEGER NOT NULL, 
	PRIMARY KEY (injury_type_id)
);

CREATE TABLE achievement (
	achievement_id SERIAL NOT NULL, 
	achievement_name VARCHAR NOT NULL, 
	description TEXT, 
	points INTEGER NOT NULL, 
	PRIMARY KEY (achievement_id)
);

CREATE TABLE students (
	student_id SERIAL NOT NULL, 
	student_name VARCHAR NOT NULL, 
	age INTEGER NOT NULL, 
	gender gender_enum NOT NULL, 
	PRIMARY KEY (student_id), 
	CONSTRAINT ck_students_age CHECK (age BETWEEN 16 AND 30)
);

CREATE TABLE medical_group (
	group_id SERIAL NOT NULL, 
	group_name VARCHAR NOT NULL, 
	description TEXT, 
	PRIMARY KEY (group_id)
);

CREATE TABLE assessment_version (
	assessment_version_id SERIAL NOT NULL, 
	version_name VARCHAR NOT NULL, 
	description TEXT, 
	effective_date DATE NOT NULL, 
	PRIMARY KEY (assessment_version_id)
);

CREATE TABLE workout_standard (
	workout_standard_id SERIAL NOT NULL, 
	standard_name TEXT NOT NULL, 
	description TEXT, 
	PRIMARY KEY (workout_standard_id)
);

CREATE TABLE daily_activity (
	activity_id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	steps INTEGER NOT NULL, 
	calories_kcal FLOAT NOT NULL, 
	active_minutes INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (activity_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE
);

CREATE TABLE semester_norm (
	norm_id SERIAL NOT NULL, 
	assessment_version_id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	description TEXT, 
	semester VARCHAR NOT NULL, 
	academic_year VARCHAR NOT NULL, 
	PRIMARY KEY (norm_id), 
	FOREIGN KEY(assessment_version_id) REFERENCES assessment_version (assessment_version_id) ON DELETE CASCADE
);

CREATE TABLE theoretical_question (
	question_id SERIAL NOT NULL, 
	test_id INTEGER NOT NULL, 
	question_text TEXT NOT NULL, 
	options JSON NOT NULL, 
	correct_answer VARCHAR NOT NULL, 
	score FLOAT NOT NULL, 
	PRIMARY KEY (question_id), 
	FOREIGN KEY(test_id) REFERENCES theoretical_test (test_id) ON DELETE CASCADE
);

CREATE TABLE student_test_attempt (
	attempt_id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	test_id INTEGER NOT NULL, 
	score FLOAT NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (attempt_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE, 
	FOREIGN KEY(test_id) REFERENCES theoretical_test (test_id) ON DELETE CASCADE
);

CREATE TABLE users (
	user_id SERIAL NOT NULL, 
	email VARCHAR NOT NULL, 
	password_hash VARCHAR NOT NULL, 
	role user_role_enum NOT NULL, 
	student_id INTEGER, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE exercises (
	exercise_id SERIAL NOT NULL, 
	exercise_name VARCHAR NOT NULL, 
	category_id INTEGER NOT NULL, 
	difficulty VARCHAR NOT NULL, 
	description TEXT, 
	recommended_sets INTEGER NOT NULL, 
	recommended_reps INTEGER NOT NULL, 
	rest_between_sets_sec INTEGER NOT NULL, 
	PRIMARY KEY (exercise_id), 
	FOREIGN KEY(category_id) REFERENCES exercise_categories (category_id) ON DELETE RESTRICT
);

CREATE TABLE student_injury_history (
	injury_record_id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	injury_type_id INTEGER NOT NULL, 
	diagnosis_date DATE NOT NULL, 
	recovery_date DATE, 
	recovery_status VARCHAR NOT NULL, 
	doctor_notes TEXT, 
	PRIMARY KEY (injury_record_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE, 
	FOREIGN KEY(injury_type_id) REFERENCES injury_types (injury_type_id) ON DELETE RESTRICT
);

CREATE TABLE student_achievement (
	student_achievement_id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	achievement_id INTEGER NOT NULL, 
	earned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (student_achievement_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE, 
	FOREIGN KEY(achievement_id) REFERENCES achievement (achievement_id) ON DELETE CASCADE
);

CREATE TABLE student_rating_snapshot (
	rating_snapshot_id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	points INTEGER NOT NULL, 
	rank INTEGER NOT NULL, 
	calculated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (rating_snapshot_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE
);

CREATE TABLE students_health_profiles (
	health_profile_id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	medical_group_id INTEGER NOT NULL, 
	height_cm FLOAT NOT NULL, 
	weight_kg FLOAT NOT NULL, 
	cooper_meters FLOAT NOT NULL, 
	jump_forward FLOAT NOT NULL, 
	flexibility_cm FLOAT NOT NULL, 
	push_ups INTEGER NOT NULL, 
	pull_ups INTEGER NOT NULL, 
	sit_ups INTEGER NOT NULL, 
	measurement_date DATE NOT NULL, 
	PRIMARY KEY (health_profile_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE, 
	FOREIGN KEY(medical_group_id) REFERENCES medical_group (group_id) ON DELETE RESTRICT
);

CREATE TABLE assessment_rule (
	rule_id SERIAL NOT NULL, 
	assessment_version_id INTEGER NOT NULL, 
	medical_group_id INTEGER NOT NULL, 
	test_type test_type_enum NOT NULL, 
	gender gender_enum NOT NULL, 
	min_value FLOAT NOT NULL, 
	max_value FLOAT NOT NULL, 
	score SMALLINT NOT NULL, 
	PRIMARY KEY (rule_id), 
	CONSTRAINT ck_assessment_rule_score CHECK (score BETWEEN 1 AND 4), 
	CONSTRAINT ck_assessment_rule_min_value_lte_max_value CHECK (min_value <= max_value), 
	FOREIGN KEY(assessment_version_id) REFERENCES assessment_version (assessment_version_id) ON DELETE CASCADE, 
	FOREIGN KEY(medical_group_id) REFERENCES medical_group (group_id) ON DELETE RESTRICT
);

CREATE TABLE student_credit_status (
	credit_status_id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	assessment_version_id INTEGER NOT NULL, 
	status credit_status_enum NOT NULL, 
	updated_at DATE NOT NULL, 
	PRIMARY KEY (credit_status_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE, 
	FOREIGN KEY(assessment_version_id) REFERENCES assessment_version (assessment_version_id) ON DELETE RESTRICT
);

CREATE TABLE workout_plan (
	workout_plan_id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	workout_standard_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	workout_status workout_status_enum NOT NULL, 
	satisfaction satisfaction_enum, 
	PRIMARY KEY (workout_plan_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE, 
	FOREIGN KEY(workout_standard_id) REFERENCES workout_standard (workout_standard_id) ON DELETE RESTRICT
);

CREATE TABLE attendance_session (
	attendance_session_id SERIAL NOT NULL, 
	teacher_user_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	qr_code VARCHAR NOT NULL, 
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	description TEXT, 
	PRIMARY KEY (attendance_session_id), 
	FOREIGN KEY(teacher_user_id) REFERENCES users (user_id) ON DELETE RESTRICT, 
	UNIQUE (qr_code)
);

CREATE TABLE exercise_muscle_group (
	exercise_muscle_group_id SERIAL NOT NULL, 
	exercise_id INTEGER NOT NULL, 
	muscle_group_id INTEGER NOT NULL, 
	PRIMARY KEY (exercise_muscle_group_id), 
	FOREIGN KEY(exercise_id) REFERENCES exercises (exercise_id) ON DELETE CASCADE, 
	FOREIGN KEY(muscle_group_id) REFERENCES muscle_group (muscle_group_id) ON DELETE RESTRICT
);

CREATE TABLE exercise_equipment (
	exercise_equipment_id SERIAL NOT NULL, 
	exercise_id INTEGER NOT NULL, 
	equipment_id INTEGER NOT NULL, 
	PRIMARY KEY (exercise_equipment_id), 
	FOREIGN KEY(exercise_id) REFERENCES exercises (exercise_id) ON DELETE CASCADE, 
	FOREIGN KEY(equipment_id) REFERENCES equipment (equipment_id) ON DELETE RESTRICT
);

CREATE TABLE exercise_contraindications (
	exercise_contraindication_id SERIAL NOT NULL, 
	exercise_id INTEGER NOT NULL, 
	injury_type_id INTEGER NOT NULL, 
	PRIMARY KEY (exercise_contraindication_id), 
	FOREIGN KEY(exercise_id) REFERENCES exercises (exercise_id) ON DELETE CASCADE, 
	FOREIGN KEY(injury_type_id) REFERENCES injury_types (injury_type_id) ON DELETE RESTRICT
);

CREATE TABLE students_physical_readiness_assessments (
	evaluation_id SERIAL NOT NULL, 
	health_profile_id INTEGER NOT NULL, 
	assessment_version_id INTEGER NOT NULL, 
	"BMI" FLOAT NOT NULL, 
	strength_score FLOAT NOT NULL, 
	endurance_score FLOAT NOT NULL, 
	flexibility_score FLOAT NOT NULL, 
	PRIMARY KEY (evaluation_id), 
	FOREIGN KEY(health_profile_id) REFERENCES students_health_profiles (health_profile_id) ON DELETE CASCADE, 
	FOREIGN KEY(assessment_version_id) REFERENCES assessment_version (assessment_version_id) ON DELETE RESTRICT
);

CREATE TABLE assigned_exercise (
	assigned_exercise_id SERIAL NOT NULL, 
	workout_plan_id INTEGER NOT NULL, 
	exercise_id INTEGER NOT NULL, 
	slot_type slot_type_enum NOT NULL, 
	day_of_week day_of_week_enum NOT NULL, 
	order_in_session INTEGER NOT NULL, 
	predicted_score FLOAT, 
	recommended_sets INTEGER NOT NULL, 
	recommended_reps INTEGER NOT NULL, 
	PRIMARY KEY (assigned_exercise_id), 
	FOREIGN KEY(workout_plan_id) REFERENCES workout_plan (workout_plan_id) ON DELETE CASCADE, 
	FOREIGN KEY(exercise_id) REFERENCES exercises (exercise_id) ON DELETE RESTRICT
);

CREATE TABLE attendance_record (
	attendance_record_id SERIAL NOT NULL, 
	attendance_session_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	check_in_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	status attendance_status_enum NOT NULL, 
	PRIMARY KEY (attendance_record_id), 
	FOREIGN KEY(attendance_session_id) REFERENCES attendance_session (attendance_session_id) ON DELETE CASCADE, 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE
);

CREATE TABLE student_assigned_exercise_interaction (
	assigned_exercise_interaction_id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	workout_plan_id INTEGER NOT NULL, 
	assigned_exercise_id INTEGER NOT NULL, 
	completed BOOLEAN NOT NULL, 
	actually_sets INTEGER, 
	actually_reps INTEGER, 
	perceived_difficulty perceived_difficulty_enum, 
	feedback_notes TEXT, 
	interaction_date DATE NOT NULL, 
	exercise_status exercise_status_enum NOT NULL, 
	PRIMARY KEY (assigned_exercise_interaction_id), 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE, 
	FOREIGN KEY(workout_plan_id) REFERENCES workout_plan (workout_plan_id) ON DELETE CASCADE, 
	FOREIGN KEY(assigned_exercise_id) REFERENCES assigned_exercise (assigned_exercise_id) ON DELETE CASCADE
);

CREATE TABLE assigned_exercise_muscle_group (
	assigned_exercise_muscle_group_id SERIAL NOT NULL, 
	assigned_exercise_id INTEGER NOT NULL, 
	muscle_group_id INTEGER NOT NULL, 
	PRIMARY KEY (assigned_exercise_muscle_group_id), 
	FOREIGN KEY(assigned_exercise_id) REFERENCES assigned_exercise (assigned_exercise_id) ON DELETE CASCADE, 
	FOREIGN KEY(muscle_group_id) REFERENCES muscle_group (muscle_group_id) ON DELETE RESTRICT
);

CREATE TABLE muscle_fatigue (
	muscle_fatigue_id SERIAL NOT NULL, 
	workout_plan_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	assigned_exercise_id INTEGER NOT NULL, 
	assigned_exercise_muscle_group_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	recovery_hours INTEGER NOT NULL, 
	status fatigue_status_enum NOT NULL, 
	recovery_left INTEGER NOT NULL, 
	PRIMARY KEY (muscle_fatigue_id), 
	FOREIGN KEY(workout_plan_id) REFERENCES workout_plan (workout_plan_id) ON DELETE CASCADE, 
	FOREIGN KEY(student_id) REFERENCES students (student_id) ON DELETE CASCADE, 
	FOREIGN KEY(assigned_exercise_id) REFERENCES assigned_exercise (assigned_exercise_id) ON DELETE CASCADE, 
	FOREIGN KEY(assigned_exercise_muscle_group_id) REFERENCES assigned_exercise_muscle_group (assigned_exercise_muscle_group_id) ON DELETE CASCADE
);

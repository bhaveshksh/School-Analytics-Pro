-- ============================================================
-- Enterprise School Performance Analytics System
-- PostgreSQL Schema - Normalized Tables
-- Server: localhost | DB: postgres | Port: 5432
-- User: postgres | Password: admin
-- ============================================================
-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS attrition CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS marks CASCADE;
DROP TABLE IF EXISTS subjects CASCADE;
DROP TABLE IF EXISTS teachers CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS users CASCADE;
-- ============================================================
-- 1. users  (authentication)
-- ============================================================
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    -- bcrypt hashed, NEVER plain text
    role VARCHAR(20) NOT NULL DEFAULT 'Teacher' CHECK (role IN ('Admin', 'Teacher')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
-- ============================================================
-- 2. students
-- ============================================================
CREATE TABLE students (
    student_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    class VARCHAR(10) NOT NULL CHECK (class IN ('10th', '11th', '12th')),
    section CHAR(1) NOT NULL CHECK (section IN ('A', 'B', 'C')),
    behavior SMALLINT NOT NULL CHECK (
        behavior BETWEEN 1 AND 10
    ),
    enrolled_at DATE DEFAULT CURRENT_DATE
);
CREATE INDEX idx_students_class ON students(class);
CREATE INDEX idx_students_section ON students(section);
-- ============================================================
-- 3. teachers
-- ============================================================
CREATE TABLE teachers (
    teacher_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    user_id INT REFERENCES users(user_id) ON DELETE
    SET NULL
);
-- ============================================================
-- 4. subjects
-- ============================================================
CREATE TABLE subjects (
    subject_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    class VARCHAR(10) NOT NULL CHECK (class IN ('10th', '11th', '12th')),
    teacher_id INT REFERENCES teachers(teacher_id) ON DELETE
    SET NULL
);
CREATE INDEX idx_subjects_class ON subjects(class);
-- ============================================================
-- 5. marks
-- ============================================================
CREATE TABLE marks (
    mark_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    subject_id INT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    score NUMERIC(5, 2) NOT NULL CHECK (
        score BETWEEN 0 AND 100
    ),
    exam_date DATE DEFAULT CURRENT_DATE
);
CREATE INDEX idx_marks_student ON marks(student_id);
CREATE INDEX idx_marks_subject ON marks(subject_id);
-- ============================================================
-- 6. attendance
-- ============================================================
CREATE TABLE attendance (
    att_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    month DATE NOT NULL,
    -- first day of month
    total_days SMALLINT NOT NULL DEFAULT 20,
    present SMALLINT NOT NULL,
    late SMALLINT NOT NULL DEFAULT 0,
    CONSTRAINT chk_present CHECK (present <= total_days),
    CONSTRAINT chk_late CHECK (late <= present)
);
CREATE INDEX idx_attendance_student ON attendance(student_id);
CREATE INDEX idx_attendance_month ON attendance(month);
-- ============================================================
-- 7. attrition  (dropout tracking)
-- ============================================================
CREATE TABLE attrition (
    atr_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    dropped BOOLEAN DEFAULT FALSE,
    drop_date DATE,
    reason TEXT
);
CREATE INDEX idx_attrition_student ON attrition(student_id);
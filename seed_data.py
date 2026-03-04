# =============================================================
# seed_data.py  –  Enterprise School Performance Analytics
# Populates PostgreSQL with realistic demo data.
# Run AFTER applying schema.sql:
#   python seed_data.py
# =============================================================

import numpy as np
import pandas as pd
import bcrypt
import psycopg2
from psycopg2.extras import execute_values

DB_CONFIG = {
    "host":     "localhost",
    "database": "postgres",
    "port":     5432,
    "user":     "postgres",
    "password": "admin",
}

np.random.seed(42)
N_STUDENTS = 300

FIRST_NAMES = ["Aarav","Shivam","Priya","Neha","Rohit","Sneha","Arjun","Pooja",
               "Vikram","Kavya","Ravi","Meera","Aditya","Sonal","Kiran","Raj",
               "Deepa","Suresh","Anita","Mohit","Anjali","Rahul","Nidhi","Kunal"]
LAST_NAMES  = ["Sharma","Verma","Patil","Singh","Kumar","Joshi","Nair","Mehta",
               "Desai","Gupta","Rao","Shah","Mishra","Chopra","Bose","Iyer"]

CLASS_10_SUBJECTS = {
    "Marathi":        "Prof. Bharti",
    "Hindi":          "Prof. Naina",
    "English":        "Prof. Lawrence",
    "Mathematics":    "Prof. Talfade",
    "Science & Tech": "Prof. Namo",
    "Social Science": "Prof. Emily",
}
CLASS_11_12_SUBJECTS = {
    "English":     "Prof. Winson",
    "Marathi":     "Prof. Narkhede",
    "Mathematics": "Prof. Talfade Jr.",
    "Physics":     "Prof. Vidya",
    "Chemistry":   "Prof. Khatole",
    "Biology":     "Prof. Namo",
}

MONTHS = pd.date_range("2023-01-01", periods=6, freq="MS").tolist()


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def seed(conn):
    cur = conn.cursor()

    print("🗑  Clearing existing data …")
    for tbl in ["attrition","attendance","marks","subjects","teachers","students","users"]:
        cur.execute(f"TRUNCATE TABLE {tbl} RESTART IDENTITY CASCADE;")

    # ── users ─────────────────────────────────────────────────
    print("👤 Seeding users …")
    user_rows = [
        ("admin",        hash_pw("admin@123"), "Admin"),
        ("teacher_bharti",  hash_pw("teach@123"), "Teacher"),
        ("teacher_naina",   hash_pw("teach@123"), "Teacher"),
        ("teacher_lawrence",hash_pw("teach@123"), "Teacher"),
        ("teacher_talfade", hash_pw("teach@123"), "Teacher"),
        ("teacher_namo",    hash_pw("teach@123"), "Teacher"),
        ("teacher_emily",   hash_pw("teach@123"), "Teacher"),
        ("teacher_winson",  hash_pw("teach@123"), "Teacher"),
        ("teacher_narkhede",hash_pw("teach@123"), "Teacher"),
        ("teacher_vidya",   hash_pw("teach@123"), "Teacher"),
        ("teacher_khatole", hash_pw("teach@123"), "Teacher"),
    ]
    execute_values(cur,
        "INSERT INTO users (username, password, role) VALUES %s RETURNING user_id",
        user_rows)
    conn.commit()

    cur.execute("SELECT user_id, username FROM users WHERE role = 'Teacher' ORDER BY user_id")
    teacher_users = cur.fetchall()  # [(user_id, username), ...]

    # Build teacher name ↔ user_id map
    uname_to_uid = {row[1]: row[0] for row in teacher_users}
    teacher_name_uname = {
        "Prof. Bharti":     "teacher_bharti",
        "Prof. Naina":      "teacher_naina",
        "Prof. Lawrence":   "teacher_lawrence",
        "Prof. Talfade":    "teacher_talfade",
        "Prof. Namo":       "teacher_namo",
        "Prof. Emily":      "teacher_emily",
        "Prof. Winson":     "teacher_winson",
        "Prof. Narkhede":   "teacher_narkhede",
        "Prof. Talfade Jr.":"teacher_talfade",   # reuse
        "Prof. Vidya":      "teacher_vidya",
        "Prof. Khatole":    "teacher_khatole",
        "Prof. Namo (11/12)":"teacher_namo",
    }

    # ── teachers ──────────────────────────────────────────────
    print("👩‍🏫 Seeding teachers …")
    all_teacher_names = list(dict.fromkeys(
        list(CLASS_10_SUBJECTS.values()) + list(CLASS_11_12_SUBJECTS.values())
    ))
    teacher_rows = []
    for t_name in all_teacher_names:
        uname = teacher_name_uname.get(t_name)
        uid   = uname_to_uid.get(uname)
        teacher_rows.append((t_name, uid))

    execute_values(cur, "INSERT INTO teachers (name, user_id) VALUES %s RETURNING teacher_id, name", teacher_rows)
    conn.commit()
    cur.execute("SELECT teacher_id, name FROM teachers")
    teacher_id_map = {row[1]: row[0] for row in cur.fetchall()}  # name → teacher_id

    # ── subjects ──────────────────────────────────────────────
    print("📚 Seeding subjects …")
    subject_rows = []
    for cls, mapping in [("10th", CLASS_10_SUBJECTS), ("11th", CLASS_11_12_SUBJECTS), ("12th", CLASS_11_12_SUBJECTS)]:
        for subj_name, teacher_name in mapping.items():
            tid = teacher_id_map.get(teacher_name)
            subject_rows.append((subj_name, cls, tid))

    execute_values(cur, "INSERT INTO subjects (name, class, teacher_id) VALUES %s RETURNING subject_id, name, class", subject_rows)
    conn.commit()
    cur.execute("SELECT subject_id, name, class FROM subjects")
    subjects_db = cur.fetchall()   # [(subject_id, name, class), ...]
    subj_key_map = {(row[1], row[2]): row[0] for row in subjects_db}  # (name, class) → subject_id

    # ── students ──────────────────────────────────────────────
    print("🎓 Seeding students …")
    classes  = np.random.choice(["10th","11th","12th"], N_STUDENTS)
    sections = np.random.choice(["A","B","C"], N_STUDENTS)
    names    = [f"{np.random.choice(FIRST_NAMES)} {np.random.choice(LAST_NAMES)}" for _ in range(N_STUDENTS)]
    behaviors= np.random.randint(1, 11, N_STUDENTS)

    student_rows = [(names[i], classes[i], sections[i], int(behaviors[i])) for i in range(N_STUDENTS)]
    execute_values(cur, "INSERT INTO students (name, class, section, behavior) VALUES %s RETURNING student_id", student_rows)
    conn.commit()
    cur.execute("SELECT student_id, class FROM students ORDER BY student_id")
    students_db = cur.fetchall()   # [(student_id, class), ...]

    # ── marks ─────────────────────────────────────────────────
    print("📝 Seeding marks …")
    marks_rows = []
    for student_id, cls in students_db:
        mapping = CLASS_10_SUBJECTS if cls == "10th" else CLASS_11_12_SUBJECTS
        for subj_name in mapping:
            sid = subj_key_map.get((subj_name, cls))
            if sid is None:
                continue
            score = round(float(np.clip(np.random.normal(65, 15), 0, 100)), 1)
            marks_rows.append((student_id, sid, score))

    execute_values(cur, "INSERT INTO marks (student_id, subject_id, score) VALUES %s", marks_rows)
    conn.commit()

    # ── attendance ────────────────────────────────────────────
    print("📅 Seeding attendance …")
    att_rows = []
    for student_id, _ in students_db:
        for month in MONTHS:
            present = int(np.random.randint(10, 21))
            late    = int(np.random.randint(0, min(6, present + 1)))
            att_rows.append((student_id, month.strftime("%Y-%m-%d"), 20, present, late))

    execute_values(cur, "INSERT INTO attendance (student_id, month, total_days, present, late) VALUES %s", att_rows)
    conn.commit()

    # ── attrition ─────────────────────────────────────────────
    print("⚠️  Seeding attrition …")
    atr_rows = []
    for student_id, _ in students_db:
        dropped = bool(np.random.choice([False, True], p=[0.95, 0.05]))
        atr_rows.append((student_id, dropped, None, None))

    execute_values(cur, "INSERT INTO attrition (student_id, dropped, drop_date, reason) VALUES %s", atr_rows)
    conn.commit()

    cur.close()
    print("\n✅ Database seeded successfully!")
    print("─" * 40)
    print(f"  Users:      {len(user_rows)}")
    print(f"  Teachers:   {len(all_teacher_names)}")
    print(f"  Subjects:   {len(subject_rows)}")
    print(f"  Students:   {N_STUDENTS}")
    print(f"  Mark rows:  {len(marks_rows)}")
    print(f"  Att rows:   {len(att_rows)}")
    print("─" * 40)
    print("\n🔑 Login credentials:")
    print("   Admin   →  username: admin        | password: admin@123")
    print("   Teacher →  username: teacher_bharti | password: teach@123")


if __name__ == "__main__":
    print("🚀 Connecting to PostgreSQL …")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        seed(conn)
        conn.close()
    except psycopg2.OperationalError as e:
        print(f"\n❌ Could not connect to PostgreSQL:\n   {e}")
        print("\n💡 The app works without DB using synthetic data.")
        print("   Run: streamlit run main.py")

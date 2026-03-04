# =============================================================
# util.py  –  Enterprise School Performance Analytics System
# Responsibilities:
#   • DatabaseManager  – connect, create_user, validate_login
#   • SchoolMapping    – get_teachers_by_class
#   • DataProcessor    – clean_data, calculate_attendance,
#                        calculate_risk_score, grade_student
# =============================================================

import re
import bcrypt
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# ─────────────────────────────────────────────────────────────
# DATABASE CONFIGURATION
# ─────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "database": "postgres",
    "port":     5432,
    "user":     "postgres",
    "password": "admin",
}

# SQL to create the users table (run once on first startup)
CREATE_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id      SERIAL PRIMARY KEY,
    username     VARCHAR(50)  UNIQUE NOT NULL,
    email        VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT         NOT NULL,
    role         VARCHAR(20)  DEFAULT 'Teacher',
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
"""


# =============================================================
# CLASS: SchoolMapping
# =============================================================
class SchoolMapping:
    """
    Stores the Class → Teacher mapping as specified.
    Call get_teachers_by_class(class_name) to get the
    dict  {subject: teacher_name}  for that class.
    """

    # ── Static mapping tables ─────────────────────────────────
    _CLASS_10_MAP = {
        "Marathi":              "Prof. Bharti",
        "Hindi":                "Prof. Miss. Naina",
        "English":              "Prof. Mr. Lawrence",
        "Mathematics":          "Prof. Mr. Talfade",
        "Science & Technology": "Prof. Mr. Namo",
        "Social Science":       "Prof. Miss. Emily",
    }

    _CLASS_11_12_MAP = {
        "English":     "Prof. Mr. Winson",
        "Marathi":     "Prof. Miss. Narkhede",
        "Mathematics": "Prof. Mr. Talfades",
        "Physics":     "Prof. Miss. Vidya",
        "Chemistry":   "Prof. Mr. Khatole",
        "Biology":     "Prof. Mr. Namo",
    }

    def get_teachers_by_class(self, class_name: str) -> dict:
        """
        Returns {subject: teacher} for the given class.
        Accepts '10th', '11th', or '12th'.
        Returns an empty dict for unknown class names.
        """
        if class_name == "10th":
            return dict(self._CLASS_10_MAP)
        elif class_name in ("11th", "12th"):
            return dict(self._CLASS_11_12_MAP)
        return {}

    def get_teacher_list(self, class_name: str) -> list:
        """Returns a sorted list of teacher names for the given class."""
        return sorted(self.get_teachers_by_class(class_name).values())

    def get_subject_list(self, class_name: str) -> list:
        """Returns a sorted list of subject names for the given class."""
        return sorted(self.get_teachers_by_class(class_name).keys())

    def get_teacher_for_subject(self, class_name: str, subject: str) -> str:
        """Returns teacher name for a given class + subject combination."""
        return self.get_teachers_by_class(class_name).get(subject, "N/A")

    @property
    def all_classes(self) -> list:
        """List of all available class options."""
        return ["10th", "11th", "12th"]


# =============================================================
# CLASS: DatabaseManager
# =============================================================
class DatabaseManager:
    """
    Handles all PostgreSQL interactions.
    Uses a context-manager pattern for safe connection handling.
    Provides:
      • connect()       – context-manager, yields a connection
      • fetch_data()    – runs SELECT, returns DataFrame
      • execute()       – runs INSERT / UPDATE / DELETE
      • create_user()   – registers a new user with hashed password
      • validate_login()– checks email/username + password
      • load_all_data() – loads all core analytics tables
    """

    def __init__(self, config: dict = DB_CONFIG):
        self.config = config

    # ----------------------------------------------------------
    @contextmanager
    def connect(self):
        """Yield a psycopg2 connection; auto-commit or rollback on exit."""
        conn = None
        try:
            conn = psycopg2.connect(**self.config)
            yield conn
            conn.commit()
        except Exception as exc:
            if conn:
                conn.rollback()
            raise exc
        finally:
            if conn:
                conn.close()

    # ----------------------------------------------------------
    def _ensure_users_table(self):
        """Create the users table if it doesn't exist yet."""
        try:
            self.execute(CREATE_USERS_TABLE_SQL)
        except Exception:
            pass  # DB may not be reachable – ignore silently

    # ----------------------------------------------------------
    def fetch_data(self, query: str, params=None) -> pd.DataFrame:
        """Execute a SELECT query and return results as a DataFrame."""
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or ())
                rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    # ----------------------------------------------------------
    def execute(self, query: str, params=None) -> None:
        """Execute an INSERT / UPDATE / DELETE / DDL statement."""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params or ())

    # ----------------------------------------------------------
    def create_user(self, username: str, email: str,
                    plain_password: str, role: str = "Teacher") -> dict:
        """
        Register a new user.

        Steps:
          1. Hash the plain_password with bcrypt.
          2. Insert into users table (parameterised query → no SQL injection).
          3. Return  {'success': True}  on success.
          4. Return  {'success': False, 'error': '<reason>'}  on failure.

        Validation handled here:
          • Duplicate username → error message
          • Duplicate email    → error message
        """
        # Hash password – never store plain text
        password_hash = bcrypt.hashpw(
            plain_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        try:
            self._ensure_users_table()
            self.execute(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                """,
                (username, email.lower().strip(), password_hash, role),
            )
            return {"success": True}

        except psycopg2.errors.UniqueViolation as e:
            # Determine which unique constraint was violated
            err_str = str(e).lower()
            if "username" in err_str:
                return {"success": False, "error": "Username already taken. Please choose another."}
            elif "email" in err_str:
                return {"success": False, "error": "Email already registered. Please sign in instead."}
            return {"success": False, "error": "Account already exists."}

        except Exception as exc:
            return {"success": False, "error": f"Database error: {exc}"}

    # ----------------------------------------------------------
    def validate_login(self, identifier: str, plain_password: str) -> dict | None:
        """
        Validate user credentials and return user info dict on success.

        Logic:
          • If identifier contains '@' → treat as email.
          • Otherwise → treat as username.

        Returns:
          dict  {'role', 'user_id', 'username', 'email'}  on success.
          None  on failure (wrong credential or user not found).

        Falls back to hardcoded demo accounts if DB is unreachable.
        """
        identifier = identifier.strip()
        is_email   = "@" in identifier

        # ── 1. Try real PostgreSQL ────────────────────────────
        try:
            self._ensure_users_table()
            if is_email:
                query  = "SELECT * FROM users WHERE email = %s"
                lookup = identifier.lower()
            else:
                query  = "SELECT * FROM users WHERE username = %s"
                lookup = identifier

            df = self.fetch_data(query, (lookup,))

            if not df.empty:
                row = df.iloc[0]
                stored_hash = row["password_hash"]
                # bcrypt constant-time comparison
                if bcrypt.checkpw(plain_password.encode("utf-8"),
                                  stored_hash.encode("utf-8")):
                    return {
                        "role":       row["role"],
                        "user_id":    int(row["user_id"]),
                        "username":   row["username"],
                        "email":      row["email"],
                        "teacher_id": None,   # extended later if DB has teachers table
                    }
                return None  # wrong password

        except Exception:
            pass  # DB unavailable – fall through to demo accounts

        # ── 2. Demo / hardcoded fallback ─────────────────────
        # Works even when PostgreSQL is not running.
        DEMO_ACCOUNTS = {
            "admin":   {
                "password": "admin@123", "email": "admin@school.com",
                "role": "Admin", "user_id": 0, "teacher_id": None,
            },
            "teacher": {
                "password": "teach@123", "email": "teacher@school.com",
                "role": "Teacher", "user_id": 1, "teacher_id": 1,
            },
        }

        # Match by email or username
        for uname, acc in DEMO_ACCOUNTS.items():
            matched = (
                (is_email and acc["email"] == identifier.lower()) or
                (not is_email and uname == identifier)
            )
            if matched and plain_password == acc["password"]:
                return {
                    "role":       acc["role"],
                    "user_id":    acc["user_id"],
                    "username":   uname,
                    "email":      acc["email"],
                    "teacher_id": acc["teacher_id"],
                }

        return None  # all checks failed

    # ----------------------------------------------------------
    def load_all_data(self) -> dict:
        """
        Load all core analytics tables; fall back to synthetic data
        if DB is unavailable or has no rows.
        """
        try:
            students = self.fetch_data("""
                SELECT s.student_id, s.name, s.class, s.section, s.behavior,
                       COALESCE(a2.dropped, FALSE) AS dropped
                FROM students s
                LEFT JOIN attrition a2 ON a2.student_id = s.student_id
            """)
            marks = self.fetch_data("""
                SELECT m.student_id, sub.name AS subject, t.name AS teacher,
                       m.score, m.exam_date, sub.class AS class
                FROM marks m
                JOIN subjects sub ON sub.subject_id = m.subject_id
                JOIN teachers t   ON t.teacher_id   = sub.teacher_id
            """)
            attendance = self.fetch_data("""
                SELECT att_id, student_id, month, total_days, present, late
                FROM attendance
            """)
            subjects = self.fetch_data("SELECT * FROM subjects")
            teachers = self.fetch_data("SELECT * FROM teachers")

            if students.empty:
                raise ValueError("No student data – falling back to synthetic data.")

            return dict(
                students=students, marks=marks,
                attendance=attendance, subjects=subjects, teachers=teachers,
            )
        except Exception:
            return _synthetic_data()


# =============================================================
# SYNTHETIC DATA FALLBACK  (used when DB has no records yet)
# =============================================================
def _synthetic_data() -> dict:
    """Generate realistic in-memory demo data using SchoolMapping."""
    np.random.seed(42)
    n = 500

    ids   = np.arange(1, n + 1)
    first = ["Aarav","Shivam","Priya","Neha","Rohit","Sneha","Arjun","Pooja",
             "Vikram","Kavya","Ravi","Meera","Aditya","Sonal","Kiran","Raj",
             "Deepa","Suresh","Anita","Mohit"]
    last  = ["Sharma","Verma","Patil","Singh","Kumar","Joshi","Nair","Mehta",
             "Desai","Gupta","Rao","Shah","Mishra","Chopra","Bose","Iyer",
             "Pillai","Das","Garg","Saxena"]
    names    = [f"{np.random.choice(first)} {np.random.choice(last)}" for _ in range(n)]
    classes  = np.random.choice(["10th","11th","12th"], n)
    sections = np.random.choice(["A","B","C"], n)
    behavior = np.random.randint(1, 11, n)
    dropped  = np.random.choice([False, True], n, p=[0.95, 0.05])

    students = pd.DataFrame({
        "student_id": ids, "name": names, "class": classes,
        "section": sections, "behavior": behavior, "dropped": dropped,
    })

    # Use SchoolMapping for consistent teacher/subject data
    sm = SchoolMapping()
    class_10_map     = sm.get_teachers_by_class("10th")
    class_11_12_map  = sm.get_teachers_by_class("11th")

    marks_rows = []
    for sid, cls in zip(ids, classes):
        mapping = class_10_map if cls == "10th" else class_11_12_map
        for subj, teacher in mapping.items():
            score = round(float(np.clip(np.random.normal(65, 15), 0, 100)), 1)
            marks_rows.append({
                "student_id": sid, "subject": subj,
                "teacher": teacher, "score": score, "class": cls,
            })
    marks = pd.DataFrame(marks_rows)

    att_rows = []
    months   = pd.date_range("2023-01-01", periods=6, freq="MS")
    for sid in ids:
        for m in months:
            present = int(np.random.randint(10, 21))
            late    = int(np.random.randint(0, min(6, present + 1)))
            att_rows.append({
                "student_id": sid, "month": m,
                "total_days": 20, "present": present, "late": late,
            })
    attendance = pd.DataFrame(att_rows)

    subjects = pd.DataFrame({
        "subject_id": range(1, 13),
        "name": list(class_10_map.keys()) + list(class_11_12_map.keys()),
        "class": ["10th"] * 6 + ["11th"] * 6,
    })
    teachers_df = pd.DataFrame({
        "teacher_id": range(1, 13),
        "name": list(class_10_map.values()) + list(class_11_12_map.values()),
    })

    return dict(
        students=students, marks=marks,
        attendance=attendance, subjects=subjects, teachers=teachers_df,
    )


# =============================================================
# CLASS: DataProcessor
# =============================================================
class DataProcessor:
    """
    All feature-engineering, metric calculation, and risk-scoring
    operate on Pandas DataFrames (works with DB-loaded & synthetic data).
    """

    # ----------------------------------------------------------
    def clean_data(self, students: pd.DataFrame, marks: pd.DataFrame,
                   attendance: pd.DataFrame):
        """
        Normalise column types, clip scores, fill NaNs.
        Returns cleaned (students, marks, attendance).
        """
        students = students.copy()
        students["behavior"] = (
            pd.to_numeric(students["behavior"], errors="coerce")
            .fillna(5).clip(1, 10).astype(int)
        )
        students["dropped"] = students.get("dropped", False).fillna(False).astype(bool)

        marks = marks.copy()
        marks["score"]  = pd.to_numeric(marks["score"], errors="coerce").fillna(0).clip(0, 100)
        marks["status"] = np.where(marks["score"] >= 40, "Pass", "Fail")

        attendance = attendance.copy()
        attendance["month"]      = pd.to_datetime(attendance["month"], errors="coerce")
        attendance["total_days"] = (
            pd.to_numeric(attendance["total_days"], errors="coerce")
            .fillna(20).clip(1, 31).astype(int)
        )
        attendance["present"] = pd.to_numeric(attendance["present"], errors="coerce").fillna(0).clip(0)
        attendance["late"]    = pd.to_numeric(attendance["late"],    errors="coerce").fillna(0).clip(0)

        return students, marks, attendance

    # ----------------------------------------------------------
    def calculate_attendance(self, attendance: pd.DataFrame) -> pd.DataFrame:
        """
        Returns per-student attendance summary:
          att_pct, late_pct, chronic_late (late_pct > 20%).
        """
        att = attendance.copy()
        att["att_pct"]  = (att["present"] / att["total_days"].replace(0, 1)) * 100
        att["late_pct"] = (att["late"]    / att["present"].replace(0, 1))    * 100

        summary = att.groupby("student_id").agg(
            att_pct   =("att_pct",  "mean"),
            late_pct  =("late_pct", "mean"),
            total_late=("late",     "sum"),
        ).reset_index()
        summary["chronic_late"] = summary["late_pct"] > 20
        return summary

    # ----------------------------------------------------------
    def calculate_risk_score(self, students: pd.DataFrame,
                             marks: pd.DataFrame,
                             attendance: pd.DataFrame) -> pd.DataFrame:
        """
        Composite risk score (0–100):
          • 40% from low marks
          • 30% from low attendance
          • 20% from high late rate
          • 10% from low behavior
        """
        mark_avg    = marks.groupby("student_id")["score"].mean().reset_index(name="avg_score")
        att_summary = self.calculate_attendance(attendance)

        df = students[["student_id", "behavior"]].merge(mark_avg, on="student_id", how="left")
        df = df.merge(att_summary[["student_id","att_pct","late_pct"]], on="student_id", how="left")
        df.fillna({"avg_score": 0, "att_pct": 0, "late_pct": 0}, inplace=True)

        df["marks_risk"]    = (100 - df["avg_score"]).clip(0, 100) * 0.40
        df["att_risk"]      = (100 - df["att_pct"]).clip(0, 100)   * 0.30
        df["late_risk"]     = df["late_pct"].clip(0, 100)           * 0.20
        df["behavior_risk"] = ((10 - df["behavior"]) / 9 * 100).clip(0, 100) * 0.10

        df["risk_score"] = (
            df["marks_risk"] + df["att_risk"] +
            df["late_risk"]  + df["behavior_risk"]
        ).clip(0, 100).round(1)

        df["risk_level"] = pd.cut(
            df["risk_score"],
            bins=[0, 30, 60, 100],
            labels=["Low 🟢", "Medium 🟡", "High 🔴"],
            right=True,
        )
        return df[["student_id","avg_score","att_pct","late_pct","risk_score","risk_level"]]

    # ----------------------------------------------------------
    def grade_student(self, avg_score: float) -> str:
        """Return letter grade A/B/C/D/F based on average score."""
        if avg_score >= 75: return "A"
        if avg_score >= 60: return "B"
        if avg_score >= 50: return "C"
        if avg_score >= 40: return "D"
        return "F"

    # ----------------------------------------------------------
    def subject_difficulty_index(self, marks: pd.DataFrame) -> pd.DataFrame:
        """Difficulty index = (100 − mean_score) / 100. Higher = harder."""
        df = marks.groupby("subject")["score"].agg(
            mean_score="mean",
            std_score="std",
            pass_rate=lambda x: (x >= 40).mean() * 100,
        ).reset_index()
        df["difficulty_index"] = ((100 - df["mean_score"]) / 100).round(3)
        return df.sort_values("difficulty_index", ascending=False)

    # ----------------------------------------------------------
    def teacher_effectiveness(self, marks: pd.DataFrame) -> pd.DataFrame:
        """Effectiveness = weighted average of pass_rate and mean_score."""
        df = marks.groupby("teacher")["score"].agg(
            mean_score="mean",
            pass_rate=lambda x: (x >= 40).mean() * 100,
            student_count="count",
        ).reset_index()
        df["effectiveness"] = (0.5 * df["pass_rate"] + 0.5 * df["mean_score"]).round(1)
        return df.sort_values("effectiveness", ascending=False)

    # ----------------------------------------------------------
    def student_rank(self, marks: pd.DataFrame, students: pd.DataFrame) -> pd.DataFrame:
        """Return per-student rank within their class."""
        avg = marks.groupby("student_id")["score"].mean().reset_index(name="avg_score")
        avg = avg.merge(students[["student_id","class","name"]], on="student_id", how="left")
        avg["rank"]  = avg.groupby("class")["avg_score"].rank(ascending=False, method="min").astype(int)
        avg["grade"] = avg["avg_score"].apply(self.grade_student)
        return avg.sort_values(["class","rank"])

    # ----------------------------------------------------------
    def attrition_trend(self, students: pd.DataFrame,
                        attendance: pd.DataFrame) -> pd.DataFrame:
        """Identify students absent >= 20 cumulative days (dropout proxy)."""
        att = attendance.groupby("student_id").agg(
            total_absent=("present", lambda x: (attendance.loc[x.index, "total_days"] - x).sum())
        ).reset_index()
        att["at_risk_dropout"] = att["total_absent"] >= 20
        return att

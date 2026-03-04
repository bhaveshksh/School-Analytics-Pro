# =============================================================
# main.py  –  Enterprise School Performance Analytics System
# Responsibilities:
#   • App entry point & page config
#   • Session state initialisation
#   • Routing: Signup → Login → Dashboard
#   • Signup page (username + email + password + role)
#   • Login page (email OR username + password)
#   • Role-based dashboard (Admin / Teacher)
#   • Sidebar with filters + logout
# =============================================================

import re
import streamlit as st
import pandas as pd

from util import DatabaseManager, DataProcessor, _synthetic_data
from implementation import DashboardUI, GLOBAL_CSS

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be the very first Streamlit call)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="School Analytics Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject global CSS once
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SINGLETONS
# ─────────────────────────────────────────────────────────────
_db = DatabaseManager()
_dp = DataProcessor()
_ui = DashboardUI()


# =============================================================
# VALIDATION HELPERS
# =============================================================
def _is_valid_email(email: str) -> bool:
    """Return True if email matches a basic RFC-5322 pattern."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email.strip()))


# =============================================================
# CLASS: AppController
# =============================================================
class AppController:
    """
    Orchestrates the entire Streamlit application.

    Public API:
      run()  → initialises session, routes to correct page.

    Pages:
      show_signup()    – new user registration form
      show_login()     – email/username + password sign-in form
      show_dashboard() – role-based analytics dashboard
    """

    # ── Session helpers ───────────────────────────────────────
    @staticmethod
    def _init_session():
        """Ensure all session state keys exist with default values."""
        defaults = {
            "logged_in":  False,
            "role":       None,
            "username":   "",
            "email":      "",
            "user_id":    None,
            "teacher_id": None,
            "page":       "login",   # login | signup | dashboard
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

    @staticmethod
    def _logout():
        """Clear all session state and redirect to login page."""
        for key in ["logged_in","role","username","email","user_id","teacher_id"]:
            st.session_state[key] = False if key == "logged_in" else None
        st.session_state["username"]   = ""
        st.session_state["email"]      = ""
        st.session_state["page"]       = "login"
        st.rerun()

    # ──────────────────────────────────────────────────────────
    def show_signup(self):
        """
        Signup / Registration page.

        Fields:
          • Username  (unique)
          • Email     (unique, validated)
          • Password  (min 6 chars, hashed before storing)
          • Confirm Password
          • Role      (Admin / Teacher)

        On success: redirects to login page.
        """
        # ── Full-page centered layout with no side gaps ────────
        _, col_m, _ = st.columns([0.5, 3, 0.5])
        with col_m:
            # ── Brand header ────────────────────────────────
            st.markdown("""
            <div style='
                text-align:center;
                padding: 40px 0 28px;
                background: linear-gradient(180deg, rgba(108,99,255,0.08) 0%, transparent 100%);
                border-radius: 20px;
                margin-bottom: 8px;
            '>
                <span style='font-size:56px'>📝</span>
                <h1 style='color:#e2e8f0; margin:10px 0 4px; font-size:32px; font-weight:700;'>
                    Create Account
                </h1>
                <p style='color:#a0aec0; margin:0; font-size:15px;'>
                    Register to access the School Analytics Platform
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Divider label — no broken HTML wrapper
            st.markdown(
                "<p style='color:#6c63ff; font-weight:700; font-size:16px; margin:16px 0 4px;'>"
                "👤 New User Registration</p>",
                unsafe_allow_html=True,
            )

            with st.form("signup_form", clear_on_submit=True):
                new_user = st.text_input(
                    "Username",
                    placeholder="Choose a unique username",
                    help="Must be unique. Example: john_doe",
                )
                new_email = st.text_input(
                    "Email",
                    placeholder="your@email.com",
                    help="Must be a valid email address and unique.",
                )
                c1, c2 = st.columns(2)
                with c1:
                    new_pwd = st.text_input(
                        "Password",
                        type="password",
                        placeholder="Min. 6 characters",
                    )
                with c2:
                    new_pwd2 = st.text_input(
                        "Confirm Password",
                        type="password",
                        placeholder="Re-enter password",
                    )
                role = st.selectbox(
                    "Role",
                    ["Teacher", "Admin"],
                    help="Admin has full access; Teacher sees own subject data.",
                )
                submitted = st.form_submit_button(
                    "✅ Create Account", use_container_width=True
                )

                if submitted:
                    errors = []
                    if not new_user.strip():
                        errors.append("Username is required.")
                    elif len(new_user.strip()) < 3:
                        errors.append("Username must be at least 3 characters.")

                    if not new_email.strip():
                        errors.append("Email is required.")
                    elif not _is_valid_email(new_email):
                        errors.append("Please enter a valid email address.")

                    if not new_pwd:
                        errors.append("Password is required.")
                    elif len(new_pwd) < 6:
                        errors.append("Password must be at least 6 characters.")
                    elif new_pwd != new_pwd2:
                        errors.append("Passwords do not match.")

                    if errors:
                        for err in errors:
                            st.error(f"❌ {err}")
                    else:
                        result = _db.create_user(
                            username=new_user.strip(),
                            email=new_email.strip(),
                            plain_password=new_pwd,
                            role=role,
                        )
                        if result["success"]:
                            st.success(
                                f"🎉 Account created for **{new_user}** as **{role}**! "
                                "Please sign in."
                            )
                            st.session_state["page"] = "login"
                            st.rerun()
                        else:
                            st.error(f"❌ {result['error']}")

            st.markdown("---")
            if st.button("← Back to Sign In", use_container_width=True):
                st.session_state["page"] = "login"
                st.rerun()

    # ──────────────────────────────────────────────────────────
    def show_login(self):
        """
        Login page.

        Accepts either:
          • Email + password      (identifier contains '@')
          • Username + password   (identifier does NOT contain '@')

        Security:
          • bcrypt password verification (constant-time)
          • Parameterised DB queries (no SQL injection)
          • Session state updated on success; redirects to dashboard
        """
        # ── Full-page centered layout — no narrow columns, no black gaps ──
        _, col_m, _ = st.columns([0.5, 3, 0.5])
        with col_m:
            # ── Brand hero banner ───────────────────────────
            st.markdown("""
            <div style='
                text-align: center;
                padding: 50px 20px 30px;
                background: linear-gradient(160deg,
                    rgba(108,99,255,0.15) 0%,
                    rgba(72,202,228,0.08) 50%,
                    transparent 100%);
                border-radius: 24px;
                margin-bottom: 10px;
            '>
                <div style='font-size:64px; line-height:1;'>🎓</div>
                <h1 style='
                    color: #e2e8f0;
                    margin: 14px 0 6px;
                    font-size: 36px;
                    font-weight: 800;
                    letter-spacing: -0.5px;
                '>School Analytics Pro</h1>
                <p style='
                    color: #a0aec0;
                    margin: 0;
                    font-size: 16px;
                    font-weight: 400;
                '>Enterprise Performance Intelligence Platform</p>
            </div>
            """, unsafe_allow_html=True)

            # Section label — plain markdown, no broken HTML wrappers
            st.markdown(
                "<p style='color:#6c63ff; font-weight:700; font-size:17px; margin:20px 0 6px;'>"
                "🔐 Sign In to Your Account</p>",
                unsafe_allow_html=True,
            )

            with st.form("login_form", clear_on_submit=False):
                identifier = st.text_input(
                    "Email or Username",
                    placeholder="Enter your email or username",
                    help="Type your email (e.g. admin@school.com) OR just your username.",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                )
                submitted = st.form_submit_button(
                    "🚀 Sign In", use_container_width=True
                )

                if submitted:
                    if not identifier.strip() or not password:
                        st.error("❌ Please enter both identifier and password.")
                    else:
                        result = _db.validate_login(identifier.strip(), password)
                        if result:
                            st.session_state.update({
                                "logged_in":  True,
                                "role":       result["role"],
                                "username":   result["username"],
                                "email":      result.get("email", ""),
                                "user_id":    result.get("user_id"),
                                "teacher_id": result.get("teacher_id"),
                                "page":       "dashboard",
                            })
                            st.success(f"✅ Welcome back, **{result['username']}**!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid credentials. Please check and try again.")

            st.markdown("---")
            st.markdown(
                "<p style='text-align:center; color:#a0aec0; font-size:14px;'>"
                "Don't have an account?</p>",
                unsafe_allow_html=True,
            )
            if st.button("📝 Create New Account", use_container_width=True):
                st.session_state["page"] = "signup"
                st.rerun()

            with st.expander("ℹ️ Demo Credentials (work without PostgreSQL)"):
                st.info(
                    "**Admin account**\n"
                    "- Username: `admin`  ·  Password: `admin@123`\n"
                    "- Email: `admin@school.com`  ·  Password: `admin@123`\n\n"
                    "**Teacher account**\n"
                    "- Username: `teacher`  ·  Password: `teach@123`\n"
                    "- Email: `teacher@school.com`  ·  Password: `teach@123`\n\n"
                    "💡 These work even when PostgreSQL is not configured.\n"
                    "To use a real DB: run `schema.sql` then `seed_data.py`."
                )

    # ──────────────────────────────────────────────────────────
    def _render_sidebar(self, data: dict):
        """
        Sidebar with filter controls. Returns filtered DataFrames.
        Admin sees all teachers; Teacher sees filtered data.
        """
        students, marks, attendance = (
            data["students"], data["marks"], data["attendance"]
        )

        with st.sidebar:
            # User profile badge
            st.markdown(f"""
            <div style='padding:12px;background:linear-gradient(135deg,#6c63ff,#48cae4);
                 border-radius:10px;margin-bottom:16px;text-align:center'>
                <span style='font-size:24px'>🎓</span>
                <div style='font-size:14px;font-weight:700;color:white'>
                    School Analytics Pro
                </div>
                <div style='font-size:11px;color:rgba(255,255,255,0.8)'>
                    {st.session_state["username"]} · {st.session_state["role"]}
                </div>
            </div>""", unsafe_allow_html=True)

            st.markdown("### 🎛️ Filters")

            # Class filter
            all_classes = sorted(students["class"].dropna().unique().tolist())
            sel_class   = st.multiselect("📚 Class",   all_classes,   default=all_classes, key="f_class")

            # Section filter
            all_sections = sorted(students["section"].dropna().unique().tolist())
            sel_section  = st.multiselect("🏫 Section", all_sections, default=all_sections, key="f_section")

            # Subject filter (only subjects in selected classes)
            filtered_sids = students[
                students["class"].isin(sel_class) & students["section"].isin(sel_section)
            ]["student_id"]
            avail_subjs  = sorted(
                marks[marks["student_id"].isin(filtered_sids)]["subject"].dropna().unique().tolist()
            )
            sel_subject = st.multiselect("📖 Subject", avail_subjs, default=avail_subjs, key="f_subj")

            # Teacher filter (Admin only)
            if st.session_state["role"] == "Admin":
                avail_teachers = sorted(marks["teacher"].dropna().unique().tolist())
                sel_teacher    = st.multiselect("👩‍🏫 Teacher", avail_teachers,
                                                default=avail_teachers, key="f_teacher")
            else:
                sel_teacher = []   # Teacher role uses teacher_tab filtering

            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                self._logout()

        # ── Apply filters ─────────────────────────────────────
        f_students = students[
            students["class"].isin(sel_class) &
            students["section"].isin(sel_section)
        ]
        f_marks = marks[
            marks["student_id"].isin(f_students["student_id"]) &
            marks["subject"].isin(sel_subject)
        ]
        f_attendance = attendance[attendance["student_id"].isin(f_students["student_id"])]

        return f_students, f_marks, f_attendance

    # ──────────────────────────────────────────────────────────
    def show_dashboard(self):
        """
        Main analytics dashboard shown after successful login.
        Admin → 3 tabs (Overall, Teacher View, Risk & Attrition)
        Teacher → 2 tabs (My Subject Data, Risk View)
        """
        # Load data (from DB with synthetic fallback)
        raw = _db.load_all_data()
        students, marks, attendance = _dp.clean_data(
            raw["students"], raw["marks"], raw["attendance"]
        )

        # Sidebar filters
        f_students, f_marks, f_attendance = self._render_sidebar(
            dict(students=students, marks=marks, attendance=attendance)
        )

        # Page header
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:14px;margin-bottom:20px'>
            <span style='font-size:40px'>🎓</span>
            <div>
                <h1 style='color:#e2e8f0;margin:0;font-size:28px'>
                    School Performance Analytics
                </h1>
                <p style='color:#a0aec0;margin:0;font-size:13px'>
                    Real-time insights · Logged in as <b>{st.session_state['username']}</b>
                    · Role: <b>{st.session_state['role']}</b>
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # KPI cards row
        _ui.render_kpis(f_students, f_marks, f_attendance)
        st.markdown("<br>", unsafe_allow_html=True)

        # Role-based tabs
        if st.session_state["role"] == "Admin":
            tab_overall, tab_teacher, tab_risk = st.tabs([
                "🌐 Overall & Analytics",
                "👩‍🏫 Teacher View",
                "⚠️ Risk & Attrition",
            ])
            with tab_overall:
                _ui.render_charts(f_students, f_marks, f_attendance)
            with tab_teacher:
                _ui.render_teacher_tab(f_marks, f_students)
            with tab_risk:
                _ui.render_risk_tab(f_students, f_marks, f_attendance)
        else:
            # Teacher role – limited view
            tab_teacher, tab_risk = st.tabs(["📊 My Subject Data", "⚠️ Risk View"])
            with tab_teacher:
                _ui.render_teacher_tab(f_marks, f_students)
            with tab_risk:
                _ui.render_risk_tab(f_students, f_marks, f_attendance)

    # ── Main router ───────────────────────────────────────────
    def run(self):
        """
        Entry point.
        1. Initialise session state defaults.
        2. Route to: signup / login / dashboard.
        """
        self._init_session()
        page = st.session_state.get("page", "login")

        if not st.session_state["logged_in"] or page in ("login", "signup"):
            if page == "signup":
                self.show_signup()
            else:
                self.show_login()
        else:
            self.show_dashboard()


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    controller = AppController()
    controller.run()

# =============================================================
# implementation.py  –  Enterprise School Performance Analytics
# Responsibilities:
#   • DashboardUI  – render_kpis, render_charts,
#                    render_teacher_tab (with DYNAMIC class→teacher
#                    dropdown using SchoolMapping),
#                    render_risk_tab
#   • All Plotly chart types
#   • KPI cards with trend arrows
#   • Gauge chart with legend
#   • Download helpers
# =============================================================

import io
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from util import DataProcessor, SchoolMapping

_dp = DataProcessor()
_sm = SchoolMapping()   # Class-Teacher mapping helper

# ─────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────
PALETTE = px.colors.qualitative.Bold
C_PASS  = "#2ecc71"
C_FAIL  = "#e74c3c"
C_WARN  = "#f39c12"
C_BLUE  = "#3498db"
C_DARK  = "#1a1a2e"

# ─────────────────────────────────────────────────────────────
# GLOBAL CSS  (injected once by main.py via st.markdown)
# ─────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Remove Streamlit top gap so hero fills the viewport ── */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    max-width: 100% !important;
}
#root > div:first-child { padding-top: 0 !important; }

/* ── Hide default Streamlit header padding ── */
header[data-testid="stHeader"] { height: 0 !important; }

/* ── KPI Card ── */
.kpi-card {
    background: linear-gradient(135deg, #1e1e3f 0%, #16213e 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 18px 20px;
    text-align: center;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
    transition: transform .2s, box-shadow .2s;
}
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 14px 40px rgba(0,0,0,0.5); }
.kpi-label   { font-size: 12px; color: #a0aec0; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px; }
.kpi-value   { font-size: 28px; font-weight: 700; color: #ffffff; }
.kpi-delta   { font-size: 12px; margin-top: 4px; }
.kpi-up      { color: #2ecc71; }
.kpi-down    { color: #e74c3c; }
.kpi-neutral { color: #a0aec0; }

/* ── Teacher mapping card ── */
.teacher-map-card {
    background: rgba(108,99,255,0.08);
    border: 1px solid rgba(108,99,255,0.25);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 12px;
}
.teacher-map-subject { font-size: 13px; color: #a0aec0; font-weight: 600; }
.teacher-map-name    { font-size: 16px; color: #e2e8f0; font-weight: 700; }

/* ── Section header ── */
.section-header {
    font-size: 18px; font-weight: 700; color: #e2e8f0;
    border-left: 4px solid #6c63ff; padding-left: 10px;
    margin: 24px 0 12px;
}

/* ── Sidebar tweaks ── */
section[data-testid="stSidebar"] { background: #0f0f23 !important; }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* ── Tab bar ── */
.stTabs [data-baseweb="tab"] { font-weight: 600; }
.stTabs [aria-selected="true"] { color: #6c63ff !important; border-bottom-color: #6c63ff !important; }

/* ── Data table ── */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* ── Download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #6c63ff, #48cae4);
    color: white; border: none; border-radius: 8px;
    padding: 8px 18px; font-weight: 600; transition: opacity .2s;
}
.stDownloadButton > button:hover { opacity: 0.85; }

/* ── Form inputs (auth pages) ── */
.stTextInput > div > div > input {
    border-radius: 10px !important;
    border: 1px solid rgba(108,99,255,0.4) !important;
    background: rgba(255,255,255,0.05) !important;
    color: #e2e8f0 !important;
    padding: 10px 14px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #6c63ff !important;
    box-shadow: 0 0 0 2px rgba(108,99,255,0.25) !important;
}

/* ── Primary buttons ── */
.stButton > button[kind="primary"],
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #6c63ff, #48cae4) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: opacity .2s, transform .15s !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────
# CHART LAYOUT DEFAULTS
# ─────────────────────────────────────────────────────────────
_BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#e2e8f0", size=12),
    margin=dict(l=40, r=20, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
)

def _apply_base(fig):
    fig.update_layout(**_BASE_LAYOUT)
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)")
    return fig


# =============================================================
# CLASS: DashboardUI
# =============================================================
class DashboardUI:
    """
    All Streamlit UI rendering logic for the analytics dashboard.
    Methods:
      • render_kpis()         – 6 KPI cards at top of dashboard
      • render_charts()       – Overall analytics tab (10 charts)
      • render_teacher_tab()  – Teacher view with DYNAMIC class→teacher dropdown
      • render_risk_tab()     – Risk & attrition tab
    """

    # ── Static helpers ────────────────────────────────────────
    @staticmethod
    def _kpi(label: str, value: str, delta: str = "", up: bool = True) -> str:
        """Generate HTML for a single KPI card."""
        arrow  = "▲" if up else "▼"
        d_cls  = "kpi-up" if up else "kpi-down"
        delta_html = (
            f'<div class="kpi-delta {d_cls}">{arrow} {delta}</div>' if delta else
            '<div class="kpi-delta kpi-neutral">–</div>'
        )
        return f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>"""

    @staticmethod
    def _section(title: str):
        """Render a styled section header."""
        st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

    @staticmethod
    def _csv_bytes(df: pd.DataFrame) -> bytes:
        return df.to_csv(index=False).encode("utf-8")

    # ──────────────────────────────────────────────────────────
    def render_kpis(self, students, marks, attendance):
        """
        Row of 6 KPI metric cards at the top of the dashboard:
        Total Students | Avg Score | Attendance | Late Rate | Dropout | Avg Behaviour
        """
        att_sum = _dp.calculate_attendance(attendance)
        merged  = students.merge(att_sum, on="student_id", how="left")

        total_s   = len(students)
        avg_score = marks["score"].mean()         if not marks.empty else 0
        avg_att   = merged["att_pct"].mean()      if "att_pct"  in merged.columns else 0
        avg_late  = merged["late_pct"].mean()     if "late_pct" in merged.columns else 0
        dropout   = students["dropped"].mean() * 100 if "dropped" in students.columns else 0
        avg_beh   = students["behavior"].mean() if "behavior" in students.columns else 0

        cols = st.columns(6)
        cards_data = [
            ("Total Students", f"{total_s:,}",      "",  True),
            ("Avg Score",      f"{avg_score:.1f}",   "",  avg_score >= 60),
            ("Attendance",     f"{avg_att:.1f}%",    "",  avg_att   >= 75),
            ("Late Rate",      f"{avg_late:.1f}%",   "",  avg_late  < 15),
            ("Dropout Rate",   f"{dropout:.1f}%",    "",  dropout   <  5),
            ("Avg Behaviour",  f"{avg_beh:.1f}/10",  "",  avg_beh   >= 6),
        ]
        for col, (lbl, val, dlt, up) in zip(cols, cards_data):
            col.markdown(self._kpi(lbl, val, dlt, up), unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────
    def render_charts(self, students, marks, attendance):
        """
        Overall tab – 10 analytical charts across 4 rows.
        """
        if marks.empty:
            st.warning("No marks data available for selected filters.")
            return

        att = attendance.copy()
        att["att_pct"]  = att["present"]  / att["total_days"].replace(0, 1) * 100
        att["late_pct"] = att["late"]     / att["present"].replace(0, 1)    * 100

        # ── Row 1 ───────────────────────────────────────────
        self._section("📚 Academic Performance")
        r1c1, r1c2, r1c3 = st.columns(3)

        # 1. Grouped Bar – Avg score by class & subject
        marks_cls = marks.copy()
        if "class" not in marks_cls.columns:
            marks_cls = marks_cls.merge(students[["student_id","class"]], on="student_id", how="left")
        if "class" in marks_cls.columns:
            class_subj = marks_cls.groupby(["class","subject"])["score"].mean().reset_index()
            fig1 = px.bar(class_subj, x="subject", y="score", color="class",
                          barmode="group", title="Avg Score by Class & Subject",
                          color_discrete_sequence=PALETTE,
                          labels={"score":"Avg Score","subject":"Subject"})
        else:
            subj_avg2 = marks_cls.groupby("subject")["score"].mean().reset_index()
            fig1 = px.bar(subj_avg2, x="subject", y="score",
                          title="Avg Score by Subject", color_discrete_sequence=PALETTE)
        _apply_base(fig1)
        r1c1.plotly_chart(fig1, use_container_width=True)

        # 2. Horizontal Bar – Subject-wise average
        subj_avg = marks.groupby("subject")["score"].mean().reset_index().sort_values("score")
        fig2 = px.bar(subj_avg, x="score", y="subject", orientation="h",
                      title="Subject-wise Avg Score",
                      color="score", color_continuous_scale="Viridis",
                      labels={"score":"Avg Score","subject":""})
        _apply_base(fig2)
        r1c2.plotly_chart(fig2, use_container_width=True)

        # 3. Donut – Pass vs Fail
        pf = marks["status"].value_counts().reset_index()
        pf.columns = ["status","count"]
        fig3 = px.pie(pf, values="count", names="status", title="Pass vs Fail",
                      color="status",
                      color_discrete_map={"Pass": C_PASS, "Fail": C_FAIL},
                      hole=0.55)
        _apply_base(fig3)
        r1c3.plotly_chart(fig3, use_container_width=True)

        # ── Row 2 ───────────────────────────────────────────
        self._section("📊 Distributions & Correlations")
        r2c1, r2c2, r2c3 = st.columns(3)

        # 4. Histogram – Average marks per student
        student_avg = marks.groupby("student_id")["score"].mean().reset_index(name="avg_score")
        fig4 = px.histogram(student_avg, x="avg_score", nbins=30,
                            title="Distribution of Avg Marks Per Student",
                            color_discrete_sequence=[C_BLUE],
                            labels={"avg_score":"Average Score"})
        _apply_base(fig4)
        r2c1.plotly_chart(fig4, use_container_width=True)

        # 5. Box Plot – Score distribution by class
        box_df = marks_cls if "class" in marks_cls.columns else marks
        if "class" in box_df.columns:
            fig5 = px.box(box_df, x="class", y="score",
                          title="Score Distribution by Class",
                          color="class", color_discrete_sequence=PALETTE,
                          labels={"score":"Score","class":"Class"})
        else:
            fig5 = px.box(marks, y="score", title="Score Distribution",
                          color_discrete_sequence=PALETTE)
        _apply_base(fig5)
        r2c2.plotly_chart(fig5, use_container_width=True)

        # 6. Scatter – Behaviour vs Avg Score
        beh_df = marks.groupby("student_id")["score"].mean().reset_index(name="avg_score")
        beh_df = beh_df.merge(students[["student_id","behavior"]], on="student_id", how="left")
        fig6 = px.scatter(beh_df, x="behavior", y="avg_score",
                          trendline="ols",
                          title="Behaviour vs Avg Marks",
                          color_discrete_sequence=[C_WARN],
                          labels={"behavior":"Behaviour (1–10)","avg_score":"Avg Score"})
        _apply_base(fig6)
        r2c3.plotly_chart(fig6, use_container_width=True)

        # ── Row 3 ───────────────────────────────────────────
        self._section("📅 Attendance & Trends")
        r3c1, r3c2, r3c3 = st.columns(3)

        # 7. Line – Attendance trend over months
        if not att.empty:
            att_trend = att.groupby("month")["att_pct"].mean().reset_index()
            att_trend["month_str"] = att_trend["month"].dt.strftime("%b %Y")
            fig7 = px.line(att_trend, x="month_str", y="att_pct",
                           title="Monthly Avg Attendance (%)",
                           markers=True, color_discrete_sequence=[C_BLUE],
                           labels={"month_str":"Month","att_pct":"Attendance %"})
            _apply_base(fig7)
            r3c1.plotly_chart(fig7, use_container_width=True)

        # 8. Heatmap – Section × Class performance
        if "section" in students.columns:
            merge_cols = ["student_id","section"]
            if "class" not in marks.columns:
                merge_cols.append("class")
            sec_marks = marks.merge(students[merge_cols], on="student_id", how="left")
            if "class" in sec_marks.columns and "section" in sec_marks.columns:
                heat       = sec_marks.groupby(["class","section"])["score"].mean().reset_index()
                heat_pivot = heat.pivot(index="class", columns="section", values="score")
                fig8 = go.Figure(go.Heatmap(
                    z=heat_pivot.values.tolist(),
                    x=heat_pivot.columns.tolist(),
                    y=heat_pivot.index.tolist(),
                    colorscale="RdYlGn", zmin=0, zmax=100,
                    text=heat_pivot.values.round(1),
                    texttemplate="%{text}",
                    hovertemplate="Class: %{y}<br>Section: %{x}<br>Avg Score: %{z:.1f}<extra></extra>",
                ))
                fig8.update_layout(title="Section × Class Heatmap", **_BASE_LAYOUT)
                r3c2.plotly_chart(fig8, use_container_width=True)

        # 9. Area – Attrition (dropout) trend
        months       = pd.date_range("2023-01-01", periods=6, freq="MS")
        dropout_vals = [2.0, 2.5, 3.1, 2.8, 3.5, 4.2]
        fig9 = px.area(x=months.strftime("%b %Y"), y=dropout_vals,
                       title="Projected Dropout / Attrition Trend",
                       color_discrete_sequence=[C_FAIL],
                       labels={"x":"Month","y":"Dropout Rate (%)"})
        _apply_base(fig9)
        r3c3.plotly_chart(fig9, use_container_width=True)

        # ── Row 4 ───────────────────────────────────────────
        self._section("📈 Teacher & Subject Analytics")
        r4c1, r4c2 = st.columns(2)

        # 10. Clustered Bar – Teacher effectiveness
        eff  = _dp.teacher_effectiveness(marks)
        fig10 = px.bar(eff, x="teacher", y=["mean_score","pass_rate"],
                       barmode="group",
                       title="Teacher Effectiveness (Score vs Pass Rate)",
                       color_discrete_sequence=PALETTE,
                       labels={"value":"Score / Rate","variable":"Metric","teacher":"Teacher"})
        _apply_base(fig10)
        r4c1.plotly_chart(fig10, use_container_width=True)

        # 11. Horizontal Bar – Subject difficulty index
        diff  = _dp.subject_difficulty_index(marks)
        fig11 = px.bar(diff, x="difficulty_index", y="subject", orientation="h",
                       title="Subject Difficulty Index",
                       color="difficulty_index", color_continuous_scale="OrRd",
                       labels={"difficulty_index":"Difficulty","subject":""})
        _apply_base(fig11)
        r4c2.plotly_chart(fig11, use_container_width=True)

        # ── Download buttons ─────────────────────────────────
        st.markdown("---")
        dl1, dl2, _ = st.columns([1, 1, 2])
        dl1.download_button("⬇️ Download Marks Data",
                            data=self._csv_bytes(marks),
                            file_name="filtered_marks.csv", mime="text/csv")
        dl2.download_button("⬇️ Download Student Data",
                            data=self._csv_bytes(students),
                            file_name="filtered_students.csv", mime="text/csv")

    # ──────────────────────────────────────────────────────────
    def render_teacher_tab(self, marks, students):
        """
        Teacher View tab.

        DYNAMIC CLASS → TEACHER DROPDOWN:
        ─────────────────────────────────
        Step 1 – User selects a Class (10th / 11th / 12th).
        Step 2 – Teacher dropdown AUTOMATICALLY UPDATES to show
                 only the teachers for that class (via SchoolMapping).
        Step 3 – Data is filtered to the chosen teacher's marks.

        This is achieved without a page reload using Streamlit's
        reactive session state: when the class selectbox value
        changes, the teacher options are recomputed on the same run.
        """
        self._section("👩‍🏫 Teacher Analytics")

        # ── STEP 1: Class selector ────────────────────────────
        col_class, col_teacher, col_subject = st.columns(3)

        with col_class:
            selected_class = st.selectbox(
                "📚 Select Class",
                options=_sm.all_classes,
                key="teacher_tab_class",
                help="Choose a class to load its teacher list",
            )

        # ── STEP 2: Dynamic teacher list from SchoolMapping ──
        # Teacher options update instantly when class changes.
        class_teacher_map = _sm.get_teachers_by_class(selected_class)
        teacher_options   = sorted(class_teacher_map.values())

        with col_teacher:
            selected_teacher = st.selectbox(
                "👩‍🏫 Select Teacher",
                options=teacher_options,
                key=f"teacher_tab_teacher_{selected_class}",   # key changes → widget resets
                help=f"Teachers for {selected_class}",
            )

        # ── Subject list for chosen class ────────────────────
        subject_options = _sm.get_subject_list(selected_class)

        with col_subject:
            selected_subject = st.selectbox(
                "📖 Select Subject",
                options=["All Subjects"] + subject_options,
                key=f"teacher_tab_subject_{selected_class}",
                help="Filter by subject (optional)",
            )

        st.markdown("---")

        # ── Mapping reference card ───────────────────────────
        with st.expander(f"📋 {selected_class} – Full Subject → Teacher Mapping", expanded=False):
            map_cols = st.columns(3)
            for i, (subj, teacher) in enumerate(class_teacher_map.items()):
                with map_cols[i % 3]:
                    st.markdown(
                        f"""<div class="teacher-map-card">
                            <div class="teacher-map-subject">📖 {subj}</div>
                            <div class="teacher-map-name">👩‍🏫 {teacher}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        # ── Filter marks by class, then teacher ──────────────
        t_df = marks.copy()

        # Filter by class
        if "class" in t_df.columns:
            t_df = t_df[t_df["class"] == selected_class]
        else:
            # Try merging class from students
            if "class" in students.columns:
                t_df = t_df.merge(students[["student_id","class"]],
                                  on="student_id", how="left")
                t_df = t_df[t_df["class"] == selected_class]

        # Filter by selected teacher
        if "teacher" in t_df.columns:
            t_df = t_df[t_df["teacher"] == selected_teacher]

        # Filter by subject if chosen
        if selected_subject != "All Subjects" and "subject" in t_df.columns:
            t_df = t_df[t_df["subject"] == selected_subject]

        if t_df.empty:
            st.info(f"ℹ️ No marks data found for **{selected_teacher}** in **{selected_class}**."
                    " The analytics charts will appear once data is seeded into the database.")
            return

        # ── Metric strip ─────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📊 Avg Score",     f"{t_df['score'].mean():.1f}")
        m2.metric("✅ Pass Rate",     f"{(t_df['score'] >= 40).mean()*100:.1f}%")
        m3.metric("👥 Students",      t_df["student_id"].nunique())
        m4.metric("📉 Std Deviation", f"{t_df['score'].std():.1f}")

        left, right = st.columns([1, 1.4])

        # ── Gauge chart ──────────────────────────────────────
        avg_val = float(t_df["score"].mean())
        gauge   = go.Figure(go.Indicator(
            mode  = "gauge+number+delta",
            value = round(avg_val, 1),
            delta = {"reference": 60, "increasing": {"color": C_PASS}, "decreasing": {"color": C_FAIL}},
            title = {"text": f"Avg Performance – {selected_teacher}", "font": {"size": 14, "color": "#e2e8f0"}},
            gauge = {
                "axis":    {"range": [0, 100], "tickwidth": 1, "tickcolor": "#e2e8f0"},
                "bar":     {"color": C_BLUE},
                "bgcolor":  "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0,  40], "color": "#c0392b"},
                    {"range": [40, 75], "color": "#e67e22"},
                    {"range": [75,100], "color": "#27ae60"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 3},
                    "thickness": 0.75, "value": 60,
                },
            },
        ))
        for lbl, clr in [("Poor (0–40)","#c0392b"),("Average (40–75)","#e67e22"),("Good (75–100)","#27ae60")]:
            gauge.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=12, color=clr, symbol="square"),
                name=lbl, showlegend=True, hoverinfo="none",
            ))
        _gauge_layout = {k: v for k, v in _BASE_LAYOUT.items() if k != "legend"}
        gauge.update_layout(
            **_gauge_layout,
            showlegend=True,
            legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
        )
        left.plotly_chart(gauge, use_container_width=True)

        # ── Top 10 students ──────────────────────────────────
        self._section("🏆 Top 10 Students")
        top10 = t_df.nlargest(10, "score")[["student_id","subject","score","status"]].copy()
        top10 = top10.merge(students[["student_id","name"]], on="student_id", how="left")
        top10 = top10[["name","subject","score","status"]].rename(
            columns={"name":"Student","subject":"Subject","score":"Score","status":"Status"}
        )
        right.dataframe(top10, use_container_width=True, hide_index=True)

        # ── Subject-wise score bar (for this teacher) ────────
        self._section("📊 Subject-wise Performance")
        if "subject" in t_df.columns and t_df["subject"].nunique() > 1:
            subj_bar = t_df.groupby("subject")["score"].mean().reset_index()
            fig_sb = px.bar(subj_bar, x="subject", y="score",
                            title=f"Avg Score per Subject – {selected_teacher}",
                            color="score", color_continuous_scale="Viridis",
                            labels={"subject":"Subject","score":"Avg Score"})
            _apply_base(fig_sb)
            st.plotly_chart(fig_sb, use_container_width=True)

        # ── 12. Score trend (if exam_date exists) ────────────
        self._section("📈 Score Trend")
        if "exam_date" in t_df.columns:
            trend_df = t_df.copy()
            trend_df["exam_date"] = pd.to_datetime(trend_df["exam_date"], errors="coerce")
            trend_df = trend_df.dropna(subset=["exam_date"])
            if not trend_df.empty:
                tr = (trend_df
                      .groupby([trend_df["exam_date"].dt.to_period("M"), "subject"])["score"]
                      .mean().reset_index())
                tr["exam_date"] = tr["exam_date"].astype(str)
                fig_tr = px.line(tr, x="exam_date", y="score", color="subject",
                                 markers=True, title="Monthly Score Trend by Subject",
                                 color_discrete_sequence=PALETTE,
                                 labels={"exam_date":"Month","score":"Avg Score"})
                _apply_base(fig_tr)
                st.plotly_chart(fig_tr, use_container_width=True)

        # ── Download ─────────────────────────────────────────
        st.download_button(
            "⬇️ Download Teacher Data",
            data=self._csv_bytes(t_df),
            file_name=f"{selected_teacher.replace(' ','_')}_{selected_class}_data.csv",
            mime="text/csv",
        )

    # ──────────────────────────────────────────────────────────
    def render_risk_tab(self, students, marks, attendance):
        """
        Risk & Attrition tab:
          • Risk score table with colour coding
          • Monthly Late Trend line chart
          • Overall cohort risk gauge
          • High-risk student list
        """
        self._section("⚠️ Student Risk Scores")
        risk_df  = _dp.calculate_risk_score(students, marks, attendance)
        rank_df  = _dp.student_rank(marks, students)
        combined = risk_df.merge(
            rank_df[["student_id","name","class","grade"]], on="student_id", how="left"
        )
        combined["avg_score"]  = combined["avg_score"].round(1)
        combined["risk_score"] = combined["risk_score"].round(1)
        combined["att_pct"]    = combined["att_pct"].round(1)

        display_cols = ["name","class","grade","avg_score","att_pct","risk_score","risk_level"]
        col_labels   = {
            "name":"Student", "class":"Class", "grade":"Grade",
            "avg_score":"Avg Score", "att_pct":"Attendance %",
            "risk_score":"Risk Score", "risk_level":"Risk Level",
        }
        st.dataframe(
            combined[display_cols].rename(columns=col_labels).sort_values("Risk Score", ascending=False),
            use_container_width=True, hide_index=True,
        )

        lc, rc = st.columns(2)

        # 13. Line Chart with markers – Monthly Late Trend
        att = attendance.copy()
        att["late_pct"] = (att["late"] / att["present"].replace(0, 1)) * 100
        if "month" in att.columns:
            late_trend = att.groupby("month")["late_pct"].mean().reset_index()
            late_trend["month_str"] = pd.to_datetime(late_trend["month"]).dt.strftime("%b %Y")
            fig_late = px.line(late_trend, x="month_str", y="late_pct",
                               title="Monthly Late Arrival Rate (%)",
                               markers=True, color_discrete_sequence=[C_WARN],
                               labels={"month_str":"Month","late_pct":"Late Rate (%)"})
            fig_late.update_traces(line_width=2.5, marker_size=8)
            _apply_base(fig_late)
            lc.plotly_chart(fig_late, use_container_width=True)

        # Gauge – Overall cohort risk
        avg_risk  = float(risk_df["risk_score"].mean()) if not risk_df.empty else 0
        coh_gauge = go.Figure(go.Indicator(
            mode  = "gauge+number",
            value = round(avg_risk, 1),
            title = {"text": "Overall Cohort Risk Score", "font": {"size": 14, "color": "#e2e8f0"}},
            gauge = {
                "axis":  {"range": [0, 100]},
                "bar":   {"color": C_BLUE},
                "steps": [
                    {"range": [0,  30], "color": "#27ae60"},
                    {"range": [30, 60], "color": "#e67e22"},
                    {"range": [60,100], "color": "#c0392b"},
                ],
                "threshold": {"line": {"color": "white","width": 3}, "thickness": 0.75, "value": 50},
            },
        ))
        coh_gauge.update_layout(**_BASE_LAYOUT)
        rc.plotly_chart(coh_gauge, use_container_width=True)

        # High-risk student list
        self._section("🔴 High-Risk Students")
        high_risk = combined[combined["risk_level"].astype(str).str.contains("High")][
            ["name","class","avg_score","att_pct","risk_score"]
        ].rename(columns={
            "name":"Student","class":"Class",
            "avg_score":"Avg Score","att_pct":"Att %","risk_score":"Risk Score",
        })
        st.dataframe(high_risk.sort_values("Risk Score", ascending=False),
                     use_container_width=True, hide_index=True)

        # Download risk report
        st.download_button(
            "⬇️ Download Risk Report",
            data=self._csv_bytes(combined[display_cols]),
            file_name="risk_report.csv", mime="text/csv",
        )

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIG & CSS ---
st.set_page_config(page_title="School Analytics", layout="wide")
st.markdown("""
<style>
.metric-box { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
.metric-title { font-size: 14px; color: #666; font-weight: 600; }
.metric-value { font-size: 24px; color: #111; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Login")
    with st.form("login"):
        user = st.text_input("Username (admin)")
        pwd = st.text_input("Password (admin@23)", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if user == 'admin' and pwd == 'admin@23':
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("Invalid credentials")
    st.stop()

# --- 3. DATA GENERATION ---
@st.cache_data
def load_data():
    np.random.seed(42)
    s_ids = range(1, 501)
    
    # Students Data
    classes = np.random.choice(['10th', '11th', '12th'], 500)
    students = pd.DataFrame({
        'student_id': s_ids, 'class': classes,
        'section': np.random.choice(['A', 'B', 'C'], 500), 'behavior': np.random.randint(1, 11, 500),
        'attrited': np.random.choice([0, 1], 500, p=[0.95, 0.05])
    })
    
    # Marks Data
    class_10_map = {
        'Marathi': 'Prof. Bharti', 'Hindi': 'Prof. Miss. Naina', 'English': 'Prof. Mr. Lawrence',
        'Mathematics': 'Prof. Mr. Talfade', 'Science & Technology': 'Prof. Mr. Namo', 'Social Science': 'Prof. Miss. Emily'
    }
    class_11_12_map = {
        'English': 'Prof. Mr. Winson', 'marathi': 'Prof. Miss.Narkhede', 'mathematics': 'Prof. Mr. Talfades',
        'physics': 'Prof. Miss. Vidya', 'chemistry': 'Prof. Mr. Khatole', 'biology': 'Prof. Mr. Namo'
    }

    marks_data = []
    for sid, cls in zip(s_ids, classes):
        mapping = class_10_map if cls == '10th' else class_11_12_map
        for subj, teacher in mapping.items():
            marks_data.append({'student_id': sid, 'subject': subj, 'teacher': teacher, 'score': np.random.normal(65, 15)})

    marks = pd.DataFrame(marks_data)
    marks['score'] = marks['score'].clip(0, 100).round(1)
    marks['status'] = np.where(marks['score'] >= 40, 'Pass', 'Fail')
    
    # Attendance Data
    att = pd.DataFrame([
        {'student_id': sid, 'month': m, 'total': 20, 'present': p, 'late': np.random.randint(0, 6)}
        for sid in s_ids for m in pd.date_range('2023-01-01', periods=6, freq='ME') 
        if (p := np.random.randint(10, 21)) or True
    ])
    att['att_pct'] = (att['present'] / att['total']) * 100
    att['late_pct'] = (att['late'] / att['present'].replace(0, 1)) * 100
    
    return students, marks, att

df_s, df_m, df_a = load_data()

# --- 4. SIDEBAR FILTERS ---
st.sidebar.title("📊 Filter Panel")
cls = st.sidebar.multiselect("Class", df_s['class'].unique(), df_s['class'].unique())
sec = st.sidebar.multiselect("Section", df_s['section'].unique(), df_s['section'].unique())

valid_students = df_s[df_s['class'].isin(cls)]['student_id']
valid_subs = df_m[df_m['student_id'].isin(valid_students)]['subject'].unique()
if len(valid_subs) == 0: valid_subs = df_m['subject'].unique()

sub = st.sidebar.multiselect("Subject", valid_subs, valid_subs)
if st.sidebar.button("Logout"): st.session_state['logged_in'] = False; st.rerun()

# Apply Filters
f_s = df_s[df_s['class'].isin(cls) & df_s['section'].isin(sec)]
f_m = df_m[df_m['student_id'].isin(f_s['student_id']) & df_m['subject'].isin(sub)]
f_a = df_a[df_a['student_id'].isin(f_s['student_id'])]

# --- 5. DASHBOARD LAYOUT ---
st.title("🎓 School Performance Dashboard")
t1, t2, t3 = st.tabs(["🌎 Overall", "👩‍🏫 Teacher", "⚠️ Risk"])

def kpi_card(title, val):
    return f"<div class='metric-box'><div class='metric-title'>{title}</div><div class='metric-value'>{val}</div></div>"

with t1:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.markdown(kpi_card("Total Students", len(f_s)), unsafe_allow_html=True)
    c2.markdown(kpi_card("Avg Score", f"{f_m['score'].mean():.1f}"), unsafe_allow_html=True)
    c3.markdown(kpi_card("Attendance", f"{f_a['att_pct'].mean():.1f}%"), unsafe_allow_html=True)
    c4.markdown(kpi_card("Late Rate", f"{f_a['late_pct'].mean():.1f}%"), unsafe_allow_html=True)
    c5.markdown(kpi_card("Dropout", f"{(f_s['attrited'].mean()*100):.1f}%"), unsafe_allow_html=True)
    c6.markdown(kpi_card("Avg Behavior", f"{f_s['behavior'].mean():.1f}/10"), unsafe_allow_html=True)
    st.divider()
    
    # Charts Row 1
    r1c1, r1c2, r1c3 = st.columns(3)
    if not f_m.empty: 
        r1c1.plotly_chart(px.bar(f_m.groupby('subject')['score'].mean().reset_index(), x='subject', y='score', title="Avg Score by Subject", color='subject'), width=400)
        r1c3.plotly_chart(px.pie(f_m['status'].value_counts().reset_index(), values='count', names='status', title="Pass/Fail"), width=400)
    if not f_a.empty and not f_s.empty:
        df_merged = pd.merge(f_a, f_s, on='student_id')
        r1c2.plotly_chart(px.bar(df_merged.groupby('section')['att_pct'].mean().reset_index(), x='section', y='att_pct', title="Attendance by Section", color='section'), width=400)

    # Charts Row 2
    r2c1, r2c2 = st.columns(2)
    if not f_m.empty:
        student_avg = f_m.groupby('student_id')['score'].mean().reset_index()
        r2c1.plotly_chart(px.histogram(student_avg, x='score', title="Student Average Marks Distribution"), width=400)
        merged_marks = pd.merge(f_m, f_s, on='student_id')
        r2c2.plotly_chart(px.scatter(merged_marks.groupby(['student_id', 'behavior'])['score'].mean().reset_index(), x='behavior', y='score', trendline="ols", title="Behavior vs Marks"), width=400)

with t2:
    if f_m.empty: st.warning("No data based on filters."); st.stop()
    teacher = st.selectbox("Select Teacher", f_m['teacher'].unique())
    t_df = f_m[f_m['teacher'] == teacher]
    
    tc1, tc2, tc3 = st.columns(3)
    tc1.metric("Avg Marks", f"{t_df['score'].mean():.1f}")
    tc2.metric("Pass %", f"{(len(t_df[t_df['status'] == 'Pass']) / len(t_df) * 100):.1f}%")
    tc3.metric("Students", t_df['student_id'].nunique())
    
    c1, c2 = st.columns([1, 1.5])
    gauge_fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = t_df['score'].mean(),
        title = {'text': "Average Performance"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "#1f77b4"},
            'steps': [
                {'range': [0, 40], 'color': "#ff7f0e"},
                {'range': [40, 75], 'color': "#ffbb78"},
                {'range': [75, 100], 'color': "#2ca02c"}]
        }
    ))
    gauge_fig.update_layout(hovermode="x unified")
    # Dummy traces to create a legend for the gauge chart
    for label, color in [("Poor (0-40)", "#ff7f0e"), ("Average (40-75)", "#ffbb78"), ("Good (75-100)", "#2ca02c")]:
        gauge_fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', marker=dict(size=12, color=color), name=label, showlegend=True, hoverinfo='none'))
    gauge_fig.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    c1.plotly_chart(gauge_fig, width=400)
    c2.markdown("**Top 5 Students**")
    c2.dataframe(t_df.nlargest(5, 'score')[['student_id', 'score', 'status']], width=400, hide_index=True)

with t3:
    rc1, rc2 = st.columns(2)
    if not f_a.empty: 
        fig_late = px.line(f_a.groupby('month')['late_pct'].mean().reset_index(), x='month', y='late_pct', title="Monthly Late Trend", markers=True, labels={'month': 'Timeline (Months)', 'late_pct': 'Late Arrivals (%)'})
        rc1.plotly_chart(fig_late, width=400)
    
    fig_attr = px.area(x=pd.date_range('2023-01-01', periods=6, freq='ME').strftime('%b %Y'), y=[2.0, 3.1, 2.8, 3.5, 3.0, 4.2], title="Projected Dropout Trend", labels={'x': 'Timeline (Months)', 'y': 'Dropout Rate (%)'})
    rc2.plotly_chart(fig_attr, width=400)

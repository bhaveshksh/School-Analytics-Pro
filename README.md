# 🎓 School Analytics Pro

**Enterprise Performance Intelligence Platform**

School Analytics Pro is a comprehensive, modular web application built with Python and Streamlit to analyze, visualize, and manage school performance data. It provides a secure, role-based dashboard for both Administrators and Teachers to track academic performance, attendance, risk factors, and teacher effectiveness.

---

## ✨ Key Features

### 🔐 Secure Authentication System
* **Dual Login Support**: Sign in using either your Username or Email.
* **Robust Security**: Passwords are cryptographically hashed using `bcrypt` to ensure they are never stored in plain text.
* **Registration**: Built-in user registration with real-time validation for unique usernames and emails.
* **Protected Routes**: Session state management automatically redirects unauthenticated users to the login screen.

### 👥 Role-Based Access Control (RBAC)
* **Admin View**: Full access to overall school analytics, global teacher performance, and comprehensive risk analysis.
* **Teacher View**: Focused access showing analytics specific to the subjects and classes assigned to the logged-in teacher.

### 🔄 Dynamic UI & Mappings
* **Intelligent Dropdowns**: When a user selects a Class (10th, 11th, or 12th) on the Teacher tab, the Teacher dropdown instantly and dynamically updates to show only the relevant educators without requiring a page reload.

### 📊 Advanced Data Analytics & Visualizations
Utilizing `Plotly` and `Pandas`, the platform generates 11 distinct interactive charts:
* Grouped Bar Charts for average scores by class & subject.
* Donut Charts for Pass vs. Fail ratios.
* Heatmaps for analyzing Section × Class performance.
* Gauge Charts to visualize overall cohort and teacher-specific performance against benchmarks.
* Trend Lines mapping monthly attendance and late arrival rates.

### ⚠️ Attrition & Risk Tracking
* Calculates a composite **Risk Score** (0-100) for every student based on weighted parameters: low marks, poor attendance, high late rates, and behavioral history.
* Flags high-risk students to help administrators take preemptive action.

### 💾 PostgreSQL Integration with Fallback
* Standardized relational database schema (`users`, `students`, `teachers`, `subjects`, `marks`, `attendance`, `attrition`).
* **Synthetic Data Generation**: If PostgreSQL is not configured or goes offline, the app dynamically falls back to a realistic synthetic dataset (500 students) ensuring zero downtime.

---

## 🛠️ Technology Stack

* **Frontend & Framework**: [Streamlit](https://streamlit.io/)
* **Data Manipulation**: [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
* **Data Visualization**: [Plotly](https://plotly.com/python/)
* **Database**: [PostgreSQL](https://www.postgresql.org/), `psycopg2`
* **Security & Auth**: `bcrypt`
* **Styling**: Injectable Vanilla CSS (Glassmorphism, Google Inter font)

---

## 📁 Project Structure

The project strictly follows a 3-file modular architecture to ensure separation of concerns:

```text
├── main.py              # Application entry point, routing, session stat & UI layout
├── util.py              # PostgreSQL database manager, auth logic, and data processing
├── implementation.py    # UI components, KPI rendering, and Plotly visualization logic
├── schema.sql           # Database schema implementation details
├── requirements.txt     # Python dependency list
└── README.md            # Project documentation
```

---

## 🚀 Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/school-analytics-pro.git
cd school-analytics-pro
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Setup (Optional but Recommended)
Ensure PostgreSQL is installed and running.
```bash
# Apply the schema to create necessary tables
psql -U postgres -d postgres -f schema.sql

# Run seed data script if available
# python seed_data.py
```
*(Note: If the DB is omitted, the app functions perfectly using the auto-generated synthetic fallback data).*

### 4. Run the Application
```bash
streamlit run main.py
```

The app will now be available at `http://localhost:8501`.

---

## 🔑 Demo Credentials

If running locally without creating a new account, you can use the pre-configured demo users:

| Role | Username | Email | Password |
|------|----------|-------|----------|
| **Admin** | `admin` | `admin@school.com` | `admin@123` |
| **Teacher** | `teacher` | `teacher@school.com` | `teach@123` |

---

## 📸 Screenshots

*(Replace these placeholder links with actual screenshots of your running application)*
* **Login & Registration**: Clean, modern auth module with input validation.
* **Overall Dashboard**: KPI rows and high-level charts.
* **Dynamic Teacher Analytics**: Dynamic dropdowns and gauge charts for specific educators.
* **Risk & Attrition Tracker**: Data tables highlighting at-risk students.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!

## 📝 License
This project is licensed under the MIT License.

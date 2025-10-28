import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import plotly.express as px
import os
from PIL import Image

# -----------------------
# Configuration / Helpers
# -----------------------
st.set_page_config(page_title="House Points Tracker", layout="wide")
DEFAULT_WEEKLY_TARGET = 15
EXPECTED_COLS = [
    "Pupil Name", "House", "Form", "Year", "Reward", "Category", "Points",
    "Date", "Reward Description", "Teacher", "Dept", "Subject", "Email"
]

# -----------------------
# Embedded Permanent Staff List
# -----------------------
PERMANENT_STAFF = pd.DataFrame({
    "Teacher": [
        "A. Johnson", "B. Smith", "C. Brown", "D. Wilson", "E. Taylor",
        "F. Lewis", "G. Clark", "H. Adams", "I. Davies", "J. Evans"
    ],
    "Dept": [
        "Maths", "English", "Science", "PE", "Humanities",
        "Art", "Music", "MFL", "Computing", "DT"
    ]
})

# -----------------------
# Display School Logo
# -----------------------
try:
    logo = Image.open("logo.png")  # Ensure logo.png is in repo root
    st.image(logo, width=150)
except:
    st.warning("Logo not found. Make sure logo.png is in the repo root.")

# -----------------------
# Helper functions
# -----------------------
def load_and_clean(uploaded_file, week_label):
    df = pd.read_csv(uploaded_file, header=0, dtype=str)
    if len(df.columns) == len(EXPECTED_COLS):
        df.columns = EXPECTED_COLS
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    df["Category"] = df["Category"].astype(str).str.strip().str.title()
    df["Teacher"] = df["Teacher"].astype(str).str.strip()
    df["Dept"] = df["Dept"].astype(str).str.strip()
    df["Value"] = df["Reward"].astype(str).str.strip()
    df["Pupil Name"] = df["Pupil Name"].astype(str).str.strip()
    df["Email"] = df.get("Email", "")
    df["Week"] = week_label
    return df

def detect_point_types(df):
    house_mask = df["Category"].str.contains("house|reward", case=False, na=False)
    conduct_mask = df["Category"].str.contains("conduct|behaviour", case=False, na=False)
    if not house_mask.any() and not conduct_mask.any():
        house_mask = df["Points"] > 0
        conduct_mask = df["Points"] < 0
    return house_mask, conduct_mask

def aggregate_weekly(df, week_label, target):
    house_mask, conduct_mask = detect_point_types(df)
    house_df = df[house_mask].copy() if house_mask.any() else df.copy()
    conduct_df = df[conduct_mask].copy() if conduct_mask.any() else pd.DataFrame(columns=df.columns)
    staff_house = house_df.groupby("Teacher", as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"})
    staff_conduct = conduct_df.groupby("Teacher", as_index=False)["Points"].sum().rename(columns={"Points":"Conduct Points This Week"})
    dept_house = house_df.groupby("Dept", as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"})
    student_house = house_df.groupby(["Pupil Name","Year","Form"], as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"})
    value_school = house_df.groupby("Value", as_index=False)["Points"].count().rename(columns={"Points":"Count"})
    staff_summary = staff_house.merge(staff_conduct, on="Teacher", how="outer").fillna(0)
    teacher_dept = house_df.groupby("Teacher")["Dept"].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "").reset_index()
    if "Dept" in teacher_dept.columns:
        staff_summary = staff_summary.merge(teacher_dept, on="Teacher", how="left")
    
    # 🔹 Embed permanent staff list (add missing staff with zero points)
    staff_summary = PERMANENT_STAFF.merge(staff_summary, on=["Teacher", "Dept"], how="left").fillna(0)

    staff_summary["UnderTargetThisWeek"] = staff_summary["House Points This Week"] < target
    staff_summary["Week"] = week_label
    student_house = student_house.sort_values("House Points This Week", ascending=False)
    return {
        "staff_summary": staff_summary,
        "dept_house": dept_house,
        "student_house": student_house,
        "value_school": value_school,
        "raw_house_df": house_df,
        "raw_conduct_df": conduct_df
    }

def update_cumulative_tracker(staff_weekly_df, cumulative_path):
    cols = ["Teacher","House Points This Week","Conduct Points This Week","Week"]
    for c in cols:
        if c not in staff_weekly_df.columns:
            staff_weekly_df[c] = 0
    to_append = staff_weekly_df[cols].copy()
    os.makedirs(os.path.dirname(cumulative_path) or ".", exist_ok=True)
    if os.path.exists(cumulative_path):
        cum = pd.read_csv(cumulative_path)
        cum = pd.concat([cum, to_append], ignore_index=True)
    else:
        cum = to_append.copy()
    cum.to_csv(cumulative_path, index=False)
    staff_stats = cum.groupby("Teacher", as_index=False).agg(
        TotalHousePoints=("House Points This Week","sum"),
        WeeksReported=("Week","nunique"),
        AvgHousePerWeek=("House Points This Week","mean")
    )
    staff_stats["AvgHousePerWeek"] = staff_stats["AvgHousePerWeek"].round(2)
    staff_stats["ContributionStatus"] = np.where(staff_stats["AvgHousePerWeek"] >= DEFAULT_WEEKLY_TARGET, "Positive", "Negative")
    return cum, staff_stats

def to_excel_bytes(summaries: dict):
    from openpyxl import Workbook
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        summaries["staff_summary"].to_excel(writer, sheet_name="Staff Summary", index=False)
        summaries["dept_house"].to_excel(writer, sheet_name="Dept Summary", index=False)
        summaries["student_house"].to_excel(writer, sheet_name="Students", index=False)
        summaries["value_school"].to_excel(writer, sheet_name="Values", index=False)
        summaries["raw_house_df"].to_excel(writer, sheet_name="Raw House Rows", index=False)
        summaries["raw_conduct_df"].to_excel(writer, sheet_name="Raw Conduct Rows", index=False)
    out.seek(0)
    return out.read()

# -----------------------
# Streamlit Layout
# -----------------------
st.title("House & Conduct Points — Weekly Tracker")

with st.sidebar:
    st.header("Settings")
    target_input = st.number_input("Weekly house points target per staff", min_value=1, value=DEFAULT_WEEKLY_TARGET, step=1)
    cumulative_path = st.text_input("Cumulative tracker CSV path", value="./cumulative_tracker.csv")
    st.markdown("Upload weekly CSV then press 'Run analysis'.")
    st.markdown("---")
    st.markdown("Columns expected:")
    st.write(EXPECTED_COLS)

st.markdown("## 1) Upload weekly CSV")
uploaded_file = st.file_uploader("Upload CSV (weekly)", type=["csv"])
st.markdown("## 2) Week label (auto or manual)")
week_label = st.text_input("Week label", value=datetime.now().strftime("%Y-%m-%d"))

if uploaded_file is not None:
    try:
        df = load_and_clean(uploaded_file, week_label)
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        st.stop()

    st.success(f"Loaded {len(df):,} rows. Date range: {df['Date'].min()} to {df['Date'].max()}")
    st.dataframe(df.head(10))

    if st.button("Run analysis"):
        with st.spinner("Aggregating weekly data..."):
            aggregates = aggregate_weekly(df, week_label, target_input)

        # Staff Summary
        st.subheader("Staff Summary (Weekly)")
        staff_df = aggregates["staff_summary"].sort_values("House Points This Week", ascending=False)
        def highlight_staff_target(row):
            return ["background-color: #ffcccc" if row["UnderTargetThisWeek"] else "#ccffcc"]*len(row)
        st.dataframe(staff_df.style.apply(highlight_staff_target, axis=1))

        # Sidebar Leaderboard
        st.sidebar.markdown("---")
        st.sidebar.subheader("🏆 Top 5 Staff This Week")
        top_staff = staff_df.head(5)
        for _, row in top_staff.iterrows():
            status = "✅" if not row["UnderTargetThisWeek"] else "⚠️"
            st.sidebar.write(f"{status} {row['Teacher']}: {row['House Points This Week']} pts")

        # Weekly Target Alert
        under_target_staff = staff_df[staff_df["UnderTargetThisWeek"]]
        if not under_target_staff.empty:
            st.warning(f"⚠️ {len(under_target_staff)} staff below weekly target of {target_input} house points!")

        # Key Metrics
        total_house = int(aggregates["raw_house_df"]["Points"].sum()) if not aggregates["raw_house_df"].empty else 0
        total_conduct = int(aggregates["raw_conduct_df"]["Points"].abs().sum()) if not aggregates["raw_conduct_df"].empty else 0
        col1, col2, col3 = st.columns(3)
        col1.metric("Total house points (week)", f"{total_house:,}")
        col2.metric("Total conduct points (week, abs)", f"{total_conduct:,}")
        col3.metric("Staff below target", f"{len(under_target_staff)}")

        # Department Summary
        st.subheader("Department Summary (Weekly)")
        st.dataframe(aggregates["dept_house"].sort_values("House Points This Week", ascending=False))

        # Top Students
        st.subheader("Top Students (Weekly House Points)")
        student_df = aggregates["student_house"].head(30)
        st.dataframe(student_df)
        if not student_df.empty:
            fig_students = px.bar(
                student_df.head(15),
                x="House Points This Week",
                y="Pupil Name",
                orientation='h',
                text="House Points This Week",
                hover_data={"Pupil Name": True, "House Points This Week": True, "Year": True, "Form": True},
                title="Top Students (week)"
            )
            fig_students.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_students, use_container_width=True)

        # Top Staff Chart
        if not staff_df.empty:
            fig_staff = px.bar(
                staff_df.sort_values("House Points This Week", ascending=False).head(15),
                x="House Points This Week",
                y="Teacher",
                orientation='h',
                text="House Points This Week",
                hover_data={"Teacher": True, "House Points This Week": True, "Dept": True},
                title="Top Staff (week)"
            )
            fig_staff.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_staff, use_container_width=True)

        # Values Frequency (Weekly)
        st.subheader("Reward Values Frequency (Weekly)")
        val_df = aggregates["value_school"].sort_values("Count", ascending=False)
        st.dataframe(val_df)
        if not val_df.empty:
            fig_values = px.pie(
                val_df,
                values="Count",
                names="Value",
                title="Values distribution (week)",
                hover_data={"Count": True}
            )
            st.plotly_chart(fig_values, use_container_width=True)

        # Interactive Value Frequency Chart
        st.subheader("Value Frequency — House vs Conduct Points (Interactive)")
        departments = sorted(df["Dept"].dropna().unique())
        selected_dept = st.multiselect("Select Department (leave empty for all):", departments)
        week_labels = sorted(df['Week'].dropna().unique())
        selected_week = st.selectbox("Select Week to filter (leave blank for all)", options=np.append("All", week_labels))

        filtered_df = df.copy()
        if selected_dept:
            filtered_df = filtered_df[filtered_df["Dept"].isin(selected_dept)]
        if selected_week != "All":
            filtered_df = filtered_df[filtered_df["Week"] == selected_week]

        house_df_filtered = filtered_df[filtered_df["Category"].str.contains("house|reward", case=False, na=False)]
        conduct_df_filtered = filtered_df[filtered_df["Category"].str.contains("conduct|behaviour", case=False, na=False)]

        house_freq = house_df_filtered.groupby("Value")["Points"].count().reset_index()
        house_freq.rename(columns={"Points":"Count"}, inplace=True)
        house_freq["Category"] = "House Points"

        conduct_freq = conduct_df_filtered.groupby("Value")["Points"].count().reset_index()
        conduct_freq.rename(columns={"Points":"Count"}, inplace=True)
        conduct_freq["Category"] = "Conduct Points"

        freq_df = pd.concat([house_freq, conduct_freq], ignore_index=True)

        if not freq_df.empty:
            fig_freq = px.bar(
                freq_df,
                x="Value",
                y="Count",
                color="Category",
                barmode="group",
                text="Count",
                hover_data={"Value": True, "Count": True, "Category": True},
                title="Frequency of Each Value (Filtered by Department & Week)"
            )
            fig_freq.update_traces(texttemplate="%{text}", textposition="outside")
            fig_freq.update_layout(xaxis_title="Value", yaxis_title="Count", xaxis_tickangle=-45)
            st.plotly_chart(fig_freq, use_container_width=True)

        # Download Excel Summary
        excel_bytes = to_excel_bytes(aggregates)
        st.download_button(
            "Download weekly Excel summary",
            data=excel_bytes,
            file_name=f"weekly_summary_{week_label}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Cumulative Tracker
        st.subheader("Cumulative Tracker")
        try:
            cum_df, staff_stats = update_cumulative_tracker(aggregates["staff_summary"], cumulative_path)
            st.dataframe(staff_stats.sort_values("TotalHousePoints", ascending=False))
        except Exception as e:
            st.error(f"Error updating cumulative tracker: {e}")

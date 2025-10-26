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

HOUSE_MAPPING = {
    "B": "Brunel",
    "L": "Liddell",
    "D": "Dickens",
    "W": "Wilberforce"
}

# -----------------------
# Display School Logo
# -----------------------
try:
    logo = Image.open("logo.png")
    st.image(logo, width=150)
except Exception:
    st.warning("Logo not found or unreadable. Continuing without logo.")

# -----------------------
# Helper functions
# -----------------------
def load_and_clean(uploaded_file, week_label):
    try:
        df = pd.read_csv(uploaded_file, header=0, dtype=str)
        df.columns = df.columns.str.strip()
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return pd.DataFrame()

    # Dept column handling
    if "Dept" not in df.columns and "Dep" in df.columns:
        df["Dept"] = df["Dep"].astype(str).str.strip()
    elif "Dept" not in df.columns:
        df["Dept"] = ""
    else:
        df["Dept"] = df["Dept"].astype(str).str.strip()

    # Ensure all expected columns exist
    for col in EXPECTED_COLS:
        if col not in df.columns:
            df[col] = ""

    # Data type corrections
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    df["Category"] = df["Category"].astype(str).str.strip().str.title()
    df["Teacher"] = df["Teacher"].astype(str).str.strip()
    df["Value"] = df["Reward"].astype(str).str.strip()
    df["Pupil Name"] = df["Pupil Name"].astype(str).str.strip()
    df["Email"] = df.get("Email", "")
    df["Week"] = week_label
    return df

def safe_plot(df, x, y, title, text=None, orientation='v', margin_l=80):
    if df.empty:
        st.warning(f"No data to plot: {title}")
        return
    try:
        fig = px.bar(df, x=x, y=y, text=text, orientation=orientation, title=title)
        if text:
            fig.update_traces(texttemplate="%{text}", textposition="outside")
        fig.update_layout(margin=dict(l=margin_l))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not generate plot {title}: {e}")

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
    st.markdown("Expected columns:")
    st.write(EXPECTED_COLS)

uploaded_file = st.file_uploader("Upload weekly CSV", type=["csv"])
week_label = st.text_input("Week label", value=datetime.now().strftime("%Y-%m-%d"))

if uploaded_file:
    df = load_and_clean(uploaded_file, week_label)
    if df.empty:
        st.warning("CSV is empty or unreadable.")
    else:
        st.success(f"Loaded {len(df):,} rows. Date range: {df['Date'].min()} to {df['Date'].max()}")
        st.dataframe(df.head(10))

        if st.button("Run analysis"):
            # Split house and conduct points
            house_mask = df["Category"].str.contains("house|reward", case=False, na=False)
            conduct_mask = df["Category"].str.contains("conduct|behaviour", case=False, na=False)
            house_df = df[house_mask] if house_mask.any() else pd.DataFrame()
            conduct_df = df[conduct_mask] if conduct_mask.any() else pd.DataFrame()

            # Staff summary (safe groupby)
            if "Teacher" in house_df.columns and not house_df.empty:
                staff_house = house_df.groupby("Teacher")["Points"].sum().reset_index().rename(columns={"Points":"House Points This Week"})
            else:
                staff_house = pd.DataFrame(columns=["Teacher","House Points This Week"])
            if "Teacher" in conduct_df.columns and not conduct_df.empty:
                staff_conduct = conduct_df.groupby("Teacher")["Points"].sum().reset_index().rename(columns={"Points":"Conduct Points This Week"})
            else:
                staff_conduct = pd.DataFrame(columns=["Teacher","Conduct Points This Week"])

            staff_summary = pd.merge(staff_house, staff_conduct, on="Teacher", how="outer").fillna(0)
            staff_summary["UnderTargetThisWeek"] = staff_summary["House Points This Week"] < target_input
            st.subheader("Staff Summary")
            st.dataframe(staff_summary)

            # -----------------------
            # Top Staff chart (horizontal, readable)
            # -----------------------
            if not staff_summary.empty:
                top_staff = staff_summary.sort_values("House Points This Week", ascending=True).tail(15)
                fig_staff = px.bar(
                    top_staff,
                    x="House Points This Week",
                    y="Teacher",
                    orientation="h",
                    text="House Points This Week",
                    title="Top Staff (Weekly)"
                )
                fig_staff.update_layout(
                    yaxis=dict(tickfont=dict(size=12)),
                    xaxis=dict(title="House Points", tickfont=dict(size=12)),
                    title=dict(font=dict(size=20)),
                    margin=dict(l=120)
                )
                fig_staff.update_traces(texttemplate="%{text}", textposition="outside")
                st.plotly_chart(fig_staff, use_container_width=True)

            # -----------------------
            # Top Students chart (horizontal, readable)
            # -----------------------
            if not house_df.empty:
                student_df = house_df.groupby(["Pupil Name","Year","Form"])["Points"].sum().reset_index().rename(columns={"Points":"House Points This Week"})
                student_df = student_df.sort_values("House Points This Week", ascending=True).tail(15)
                fig_students = px.bar(
                    student_df,
                    x="House Points This Week",
                    y="Pupil Name",
                    orientation="h",
                    text="House Points This Week",
                    title="Top Students (Weekly)"
                )
                fig_students.update_layout(
                    yaxis=dict(tickfont=dict(size=12)),
                    xaxis=dict(title="House Points", tickfont=dict(size=12)),
                    title=dict(font=dict(size=20)),
                    margin=dict(l=150)
                )
                fig_students.update_traces(texttemplate="%{text}", textposition="outside")
                st.plotly_chart(fig_students, use_container_width=True)

            # House points by house
            if not house_df.empty:
                house_points = house_df.copy()
                house_points["House"] = house_points["House"].map(HOUSE_MAPPING).fillna(house_points["House"])
                house_points = house_points.groupby("House")["Points"].sum().reset_index()
                safe_plot(house_points, x="House", y="Points", title="House Points by House", text="Points")

            # Conduct points by house
            if not conduct_df.empty:
                conduct_points = conduct_df.copy()
                conduct_points["House"] = conduct_points["House"].map(HOUSE_MAPPING).fillna(conduct_points["House"])
                conduct_points = conduct_points.groupby("House")["Points"].sum().reset_index()
                safe_plot(conduct_points, x="House", y="Points", title="Conduct Points by House", text="Points")

            # Category frequency
            category_counts = df.groupby("Category")["Points"].count().reset_index().sort_values("Points", ascending=False)
            safe_plot(category_counts, x="Category", y="Points", title="Category Frequency", text="Points")

            # Department summary
            if not house_df.empty:
                dept_house = house_df.groupby("Dept")["Points"].sum().reset_index().rename(columns={"Points":"House Points This Week"})
                st.subheader("Department Summary")
                st.dataframe(dept_house)
            else:
                dept_house = pd.DataFrame()

            # Excel download
            summaries = {
                "staff_summary": staff_summary,
                "dept_house": dept_house,
                "student_house": student_df if not house_df.empty else pd.DataFrame(),
                "value_school": df.groupby("Value")["Points"].count().reset_index().rename(columns={"Points":"Count"}),
                "raw_house_df": house_df,
                "raw_conduct_df": conduct_df
            }
            excel_bytes = to_excel_bytes(summaries)
            st.download_button(
                "Download weekly Excel summary",
                data=excel_bytes,
                file_name=f"weekly_summary_{week_label}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Cumulative tracker
            try:
                cum_df, staff_stats = update_cumulative_tracker(staff_summary, cumulative_path)
                st.subheader("Cumulative Tracker")
                st.dataframe(staff_stats.sort_values("TotalHousePoints", ascending=False))
            except Exception as e:
                st.warning(f"Could not update cumulative tracker: {e}")

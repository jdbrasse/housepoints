import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
from io import BytesIO
import os

# -----------------------
# CONFIGURATION
# -----------------------
st.set_page_config(page_title="House & Conduct Points Tracker", layout="wide")
st.title("House & Conduct Points Tracker")

DEFAULT_WEEKLY_TARGET = 15
DEFAULT_STAFF_FILE = "./staff list - Sheet1 (1).csv"
HOUSE_MAPPING = {"B": "Brunel", "L": "Liddell", "D": "Dickens", "W": "Wilberforce"}
HOUSE_COLORS = {"Brunel": "red", "Liddell": "yellow", "Dickens": "blue", "Wilberforce": "purple"}
EXPECTED_REWARD_COLS = [
    "Pupil Name", "House", "Form", "Year", "Reward", "Category", "Points",
    "Date", "Reward Description", "Teacher", "Dep", "Subject"
]

# -----------------------
# FUNCTIONS
# -----------------------

def read_staff_file(path_or_buffer):
    """Read staff master list: A=First, B=Surname, C=Initials, D=Dept."""
    try:
        df = pd.read_csv(path_or_buffer, dtype=str)
    except Exception as e:
        st.error(f"Error reading staff list: {e}")
        return pd.DataFrame(columns=["Initials", "FullName", "Dep"])

    df.columns = df.columns.str.strip()
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    if len(df.columns) < 4:
        st.warning("Staff file has fewer than 4 columns. Expected First, Surname, Initials, Dept.")
        return pd.DataFrame(columns=["Initials", "FullName", "Dep"])

    df["FirstName"] = df.iloc[:, 0]
    df["Surname"] = df.iloc[:, 1]
    df["Initials"] = df.iloc[:, 2].astype(str).str.upper().str.strip()
    df["Dep"] = df.iloc[:, 3]
    df["FullName"] = df["FirstName"].fillna("") + " " + df["Surname"].fillna("")
    df = df[["Initials", "FullName", "Dep"]].dropna(subset=["Initials"])
    return df

def read_rewards_file(file_or_buffer):
    """Read and clean weekly rewards CSV."""
    df = pd.read_csv(file_or_buffer, dtype=str)
    df.columns = df.columns.str.strip()
    if len(df.columns) >= len(EXPECTED_REWARD_COLS):
        df = df.iloc[:, :len(EXPECTED_REWARD_COLS)]
        df.columns = EXPECTED_REWARD_COLS
    else:
        for col in EXPECTED_REWARD_COLS:
            if col not in df.columns:
                df[col] = ""
        df = df[EXPECTED_REWARD_COLS]

    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df["Teacher"] = df["Teacher"].fillna("").astype(str).str.upper().str.strip()
    df["Dep"] = df["Dep"].fillna("").astype(str).str.strip()
    df["Reward"] = df["Reward"].fillna("").astype(str).str.lower().str.strip()
    df["Category"] = df["Category"].fillna("").astype(str).str.lower().str.strip()
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    df["House"] = df["House"].astype(str).str.strip().str.upper().map(HOUSE_MAPPING).fillna(df["House"])
    return df

def safe_plot(df_plot, x, y, title, text=None, orientation="v", color=None, color_map=None):
    if df_plot.empty:
        st.info(f"No data for {title}")
        return
    try:
        fig = px.bar(df_plot, x=x, y=y, text=text, orientation=orientation, title=title,
                     color=color, color_discrete_map=color_map)
        fig.update_traces(texttemplate="%{text}", textposition="outside")
        fig.update_layout(title=dict(font=dict(size=18)))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Plot error for {title}: {e}")

def to_excel_bytes(data_dict):
    from openpyxl import Workbook
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in data_dict.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    output.seek(0)
    return output.read()

# -----------------------
# STAFF LIST HANDLING (with cache)
# -----------------------
@st.cache_data(show_spinner=False)
def load_staff_data(file_or_path):
    return read_staff_file(file_or_path)

st.sidebar.header("Staff List Configuration")
staff_df = None

# Try default file
if os.path.exists(DEFAULT_STAFF_FILE):
    staff_df = load_staff_data(DEFAULT_STAFF_FILE)
    st.sidebar.success("✅ Loaded default staff list.")
else:
    # Check for cached upload
    if "cached_staff_file" in st.session_state and st.session_state["cached_staff_file"] is not None:
        st.sidebar.success("✅ Using previously uploaded staff list.")
        staff_df = load_staff_data(st.session_state["cached_staff_file"])
    else:
        st.sidebar.warning("⚠️ Default staff file not found.")
        staff_upload = st.sidebar.file_uploader("Upload Staff List CSV", type=["csv"], key="staff_upload")
        if staff_upload is not None:
            st.session_state["cached_staff_file"] = staff_upload
            staff_df = load_staff_data(staff_upload)
            st.sidebar.success("✅ Uploaded staff list loaded and saved for this session.")
        else:
            st.sidebar.error("Please upload a staff list CSV to continue.")
            st.stop()

# -----------------------
# REWARDS FILE HANDLING (with cache)
# -----------------------
@st.cache_data(show_spinner=False)
def load_rewards_data(file_or_buffer):
    return read_rewards_file(file_or_buffer)

uploaded = st.file_uploader("Upload Weekly Rewards CSV", type=["csv"], key="rewards_upload")

if uploaded is not None:
    st.session_state["cached_rewards_file"] = uploaded
    df = load_rewards_data(uploaded)
elif "cached_rewards_file" in st.session_state and st.session_state["cached_rewards_file"] is not None:
    st.info("✅ Using previously uploaded weekly rewards file.")
    df = load_rewards_data(st.session_state["cached_rewards_file"])
else:
    st.info("Please upload a weekly rewards CSV to begin analysis.")
    st.stop()

# -----------------------
# SPLIT HOUSE VS CONDUCT
# -----------------------
house_df = df[df["Reward"].str.contains("house", case=False, na=False)]
conduct_df = df[df["Reward"].str.contains("conduct", case=False, na=False)]

st.write(f"🏠 House Points Rows: {len(house_df)} | ⚠️ Conduct Points Rows: {len(conduct_df)}")

# -----------------------
# STAFF AGGREGATES
# -----------------------
if not house_df.empty:
    staff_house = house_df.groupby("Teacher", as_index=False)["Points"].sum().rename(columns={"Points": "House Points This Week"})
else:
    staff_house = pd.DataFrame(columns=["Teacher", "House Points This Week"])

if not conduct_df.empty:
    staff_conduct = conduct_df.groupby("Teacher", as_index=False)["Points"].count().rename(columns={"Points": "Conduct Points This Week"})
else:
    staff_conduct = pd.DataFrame(columns=["Teacher", "Conduct Points This Week"])

staff_agg = pd.merge(staff_house, staff_conduct, on="Teacher", how="outer").fillna(0)
staff_agg["Teacher"] = staff_agg["Teacher"].astype(str).str.upper().str.strip()

# -----------------------
# MERGE WITH STAFF LIST
# -----------------------
st.subheader("🧩 Merging Staff List with Weekly Data")

if "Initials" in staff_df.columns:
    staff_df = staff_df.rename(columns={"Initials": "Teacher"})
staff_df["Teacher"] = staff_df["Teacher"].astype(str).str.upper().str.strip()

master = staff_df[["Teacher", "FullName", "Dep"]].rename(columns={"Dep": "Dept"}).copy()

staff_full = pd.merge(master, staff_agg, on="Teacher", how="left").fillna(0)
staff_full["House Points This Week"] = pd.to_numeric(staff_full["House Points This Week"], errors="coerce").fillna(0).astype(int)
staff_full["Conduct Points This Week"] = pd.to_numeric(staff_full["Conduct Points This Week"], errors="coerce").fillna(0).astype(int)
staff_full["On Target (≥15)"] = np.where(staff_full["House Points This Week"] >= DEFAULT_WEEKLY_TARGET, "✅ Yes", "⚠️ No")

st.subheader("📅 Weekly Staff Summary (Includes 0-point staff)")
st.dataframe(staff_full.sort_values("House Points This Week", ascending=False).reset_index(drop=True))

# -----------------------
# DEPARTMENT SUMMARY
# -----------------------
dept_summary = staff_full.groupby("Dept", as_index=False)["House Points This Week"].sum().rename(columns={"House Points This Week": "House Points"})
st.subheader("🏢 Department Summary (House Points)")
st.dataframe(dept_summary.sort_values("House Points", ascending=False))

# -----------------------
# CHARTS
# -----------------------
st.subheader("📊 Top Staff (House Points)")
safe_plot(staff_full.sort_values("House Points This Week", ascending=True).tail(15),
          x="House Points This Week", y="Teacher", text="House Points This Week",
          title="Top 15 Staff (House Points)", orientation="h")

if not house_df.empty:
    student_top = house_df.groupby(["Pupil Name"], as_index=False)["Points"].sum().rename(columns={"Points": "House Points"})
    student_top = student_top.sort_values("House Points", ascending=True).tail(15)
    st.subheader("🏅 Top Students (House Points)")
    safe_plot(student_top, x="House Points", y="Pupil Name", text="House Points", title="Top 15 Students", orientation="h")

if not house_df.empty:
    house_points = house_df.groupby("House", as_index=False)["Points"].sum().rename(columns={"Points": "House Points"})
    st.subheader("🏠 House Points by House")
    safe_plot(house_points, x="House", y="House Points", text="House Points", title="House Points by House",
              color="House", color_map=HOUSE_COLORS)

if not conduct_df.empty:
    conduct_points = conduct_df.groupby("House", as_index=False)["Points"].count().rename(columns={"Points": "Conduct Points"})
    st.subheader("⚠️ Conduct Points by House")
    safe_plot(conduct_points, x="House", y="Conduct Points", text="Conduct Points", title="Conduct Points by House",
              color="House", color_map=HOUSE_COLORS)

# -----------------------
# CATEGORY FREQUENCY
# -----------------------
if not house_df.empty:
    cat_freq = house_df.groupby("Category", as_index=False)["Points"].count().rename(columns={"Points": "Frequency"})
    st.subheader("📘 House Points Category Frequency")
    safe_plot(cat_freq.sort_values("Frequency", ascending=False),
              x="Category", y="Frequency", text="Frequency", title="House Category Frequency")

if not conduct_df.empty:
    cat_freq_conduct = conduct_df.groupby("Category", as_index=False)["Points"].count().rename(columns={"Points": "Frequency"})
    st.subheader("📕 Conduct Points Category Frequency")
    safe_plot(cat_freq_conduct.sort_values("Frequency", ascending=False),
              x="Category", y="Frequency", text="Frequency", title="Conduct Category Frequency")

# -----------------------
# EXCEL DOWNLOAD
# -----------------------
summaries = {
    "Staff Summary": staff_full,
    "Department Summary": dept_summary,
    "House Points": house_df,
    "Conduct Points": conduct_df
}
excel_data = to_excel_bytes(summaries)
st.download_button("📥 Download Weekly Summary (Excel)", data=excel_data,
                   file_name=f"weekly_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

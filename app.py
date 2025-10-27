# app.py
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import plotly.express as px
import os

# -----------------------
# Configuration
# -----------------------
st.set_page_config(page_title="House & Conduct Points Tracker", layout="wide")
st.title("House & Conduct Points Tracker")

DEFAULT_WEEKLY_TARGET = 15
DEFAULT_STAFF_FILE = "./staff list - Sheet1 (1).csv"  # default staff list path (you uploaded this)
CUMULATIVE_PATH_DEFAULT = "./cumulative_tracker.csv"

HOUSE_MAPPING = {"B": "Brunel", "L": "Liddell", "D": "Dickens", "W": "Wilberforce"}
HOUSE_COLORS = {
    "Brunel": "red",
    "Liddell": "yellow",
    "Dickens": "blue",
    "Wilberforce": "purple"
}

EXPECTED_REWARDS_COLS = [
    "Pupil Name","House","Form","Year","Reward","Category","Points","Date","Reward Description","Teacher","Dep","Subject"
]

# -----------------------
# Helpers
# -----------------------
def read_staff_file(path_or_buffer):
    """
    Load staff master list. The file you uploaded has:
    Col A = First name, Col B = Surname, Col C = Initials, Col D = Dept
    We'll try to read column names; if not present, assume those positions.
    Returns dataframe with columns: Initials, FirstName, Surname, FullName, Dep
    """
    try:
        staff = pd.read_csv(path_or_buffer, header=0, dtype=str)
    except Exception as e:
        st.warning(f"Could not read staff file: {e}")
        return pd.DataFrame(columns=["Initials","FirstName","Surname","FullName","Dep"])

    # strip whitespace from column names and values
    staff.columns = staff.columns.str.strip()
    staff = staff.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # Heuristics: find columns
    cols = list(staff.columns)
    # If expected headers exist (common names), try to use them
    # We'll create FirstName, Surname, Initials, Dep by checking known names or fallback to positions
    first_col = cols[0] if len(cols) >= 1 else None
    second_col = cols[1] if len(cols) >= 2 else None
    third_col = cols[2] if len(cols) >= 3 else None
    fourth_col = cols[3] if len(cols) >= 4 else None

    # Determine mapping
    # look for likely column names
    def choose_col(name_options, fallback):
        for n in name_options:
            if n in staff.columns:
                return n
        return fallback

    first_name_col = choose_col(["First Name","FirstName","Firstname", first_col], first_col)
    surname_col = choose_col(["Surname","Last Name","LastName","Last", second_col], second_col)
    initials_col = choose_col(["Initials","Initial","Initials.", third_col], third_col)
    dept_col = choose_col(["Dep","Department","Dept","Dept.", fourth_col], fourth_col)

    # Build normalized staff df
    staff_norm = pd.DataFrame()
    staff_norm["FirstName"] = staff[first_name_col].fillna("") if first_name_col in staff.columns else ""
    staff_norm["Surname"] = staff[surname_col].fillna("") if surname_col in staff.columns else ""
    staff_norm["Initials"] = staff[initials_col].fillna("").astype(str).str.strip().str.upper() if initials_col in staff.columns else ""
    staff_norm["Dep"] = staff[dept_col].fillna("") if dept_col in staff.columns else ""
    staff_norm["FullName"] = (staff_norm["FirstName"].fillna("") + " " + staff_norm["Surname"].fillna("")).str.strip()
    staff_norm = staff_norm[["Initials","FirstName","Surname","FullName","Dep"]]
    staff_norm["Initials"] = staff_norm["Initials"].replace("", np.nan)
    staff_norm = staff_norm.dropna(subset=["Initials"]).reset_index(drop=True)
    staff_norm["Initials"] = staff_norm["Initials"].str.upper().str.strip()
    return staff_norm

def read_rewards_csv(uploaded_file):
    """
    Read and normalise the weekly rewards csv. Accepts file buffer (uploaded_file).
    Force expected column names (strip and assign by position if necessary).
    """
    try:
        df = pd.read_csv(uploaded_file, dtype=str)
    except Exception as e:
        raise RuntimeError(f"Could not read rewards CSV: {e}")

    # strip column whitespace
    df.columns = df.columns.str.strip()

    # If headers already match expected we use them, else we try to reassign by position
    if set(EXPECTED_REWARDS_COLS).issubset(set(df.columns)):
        df = df[EXPECTED_REWARDS_COLS].copy()
    else:
        # fallback: assign expected names in order of current columns (if same length or longer)
        cols = list(df.columns)
        if len(cols) >= len(EXPECTED_REWARDS_COLS):
            df = df[cols[:len(EXPECTED_REWARDS_COLS)]].copy()
            df.columns = EXPECTED_REWARDS_COLS
        else:
            # pad missing columns to avoid key errors
            for i, col in enumerate(EXPECTED_REWARDS_COLS):
                if col not in df.columns:
                    df[col] = ""
            df = df[EXPECTED_REWARDS_COLS].copy()

    # Clean / normalise values
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    # Teacher initials uppercase
    df["Teacher"] = df["Teacher"].fillna("").astype(str).str.upper().str.strip()
    df["Dep"] = df["Dep"].fillna("").astype(str).str.strip()
    df["Reward"] = df["Reward"].fillna("").astype(str).str.lower().str.strip()
    df["Category"] = df["Category"].fillna("").astype(str).str.lower().str.strip()
    # Points numeric (will keep positive/negative as provided)
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    # Normalize house codes to uppercase letters and map to full names (if present)
    df["HouseRaw"] = df["House"].fillna("").astype(str).str.strip()
    df["HouseCode"] = df["HouseRaw"].str.upper().str.extract(r'([A-Za-z])', expand=False).fillna("")
    df["House"] = df["HouseCode"].map(HOUSE_MAPPING).fillna(df["HouseRaw"])
    # Form and Year cleanup
    df["Form"] = df["Form"].fillna("").astype(str).str.strip()
    df["Year"] = df["Year"].fillna("").astype(str).str.strip()
    # Pupil Name
    df["Pupil Name"] = df["Pupil Name"].fillna("").astype(str).str.strip()
    return df

def to_excel_bytes(summaries):
    from openpyxl import Workbook
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for sheet_name, df in summaries.items():
            try:
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            except Exception:
                # skip problematic sheets
                pass
    out.seek(0)
    return out.read()

def safe_plot(df_plot, x, y, title, text=None, orientation='v', color=None, color_map=None, margin_l=80):
    if df_plot.empty:
        st.info(f"No data for {title}")
        return
    try:
        if color and color_map:
            fig = px.bar(df_plot, x=x, y=y, color=color, color_discrete_map=color_map, text=text, orientation=orientation, title=title)
        else:
            fig = px.bar(df_plot, x=x, y=y, text=text, orientation=orientation, title=title)
        if text:
            fig.update_traces(texttemplate="%{text}", textposition="outside")
        fig.update_layout(margin=dict(l=margin_l), title=dict(font=dict(size=18)))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Plot error for {title}: {e}")

def update_cumulative_tracker(staff_weekly_df, cumulative_path):
    # Ensure required columns exist
    for c in ["Teacher","House Points This Week","Conduct Points This Week","Week"]:
        if c not in staff_weekly_df.columns:
            staff_weekly_df[c] = 0

    # Force numeric
    staff_weekly_df["House Points This Week"] = pd.to_numeric(staff_weekly_df["House Points This Week"], errors="coerce").fillna(0)
    staff_weekly_df["Conduct Points This Week"] = pd.to_numeric(staff_weekly_df["Conduct Points This Week"], errors="coerce").fillna(0)

    to_append = staff_weekly_df[["Teacher","House Points This Week","Conduct Points This Week","Week"]].copy()
    os.makedirs(os.path.dirname(cumulative_path) or ".", exist_ok=True)

    if os.path.exists(cumulative_path):
        cum = pd.read_csv(cumulative_path)
        # coerce existing columns to numeric
        for col in ["House Points This Week","Conduct Points This Week"]:
            if col in cum.columns:
                cum[col] = pd.to_numeric(cum[col], errors="coerce").fillna(0)
            else:
                cum[col] = 0
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

# -----------------------
# Sidebar / Inputs
# -----------------------
st.sidebar.header("Settings")
staff_file_override = st.sidebar.file_uploader("Optional: upload staff list CSV to override default", type=["csv"])
cumulative_path = st.sidebar.text_input("Cumulative tracker CSV path", value=CUMULATIVE_PATH_DEFAULT)
weekly_target = st.sidebar.number_input("Weekly house points target per staff", min_value=1, value=DEFAULT_WEEKLY_TARGET, step=1)
week_label = st.sidebar.text_input("Week label (for export & cumulative)", value=datetime.now().strftime("%Y-%m-%d"))

st.sidebar.markdown("---")
st.sidebar.caption("Notes: staff master list defaults to the file provided to the app (Option B). You can override by uploading another staff CSV here.")

# -----------------------
# Load staff master
# -----------------------
if staff_file_override is not None:
    staff_df = read_staff_file(staff_file_override)
else:
    # try default path
    if os.path.exists(DEFAULT_STAFF_FILE):
        staff_df = read_staff_file(DEFAULT_STAFF_FILE)
    else:
        st.warning(f"Default staff file not found at {DEFAULT_STAFF_FILE}. Please upload staff file in the sidebar.")
        staff_df = pd.DataFrame(columns=["Initials","FirstName","Surname","FullName","Dep"])

# Ensure initials present and uppercase
if not staff_df.empty:
    staff_df["Initials"] = staff_df["Initials"].astype(str).str.upper().str.strip()
    staff_df = staff_df.drop_duplicates(subset=["Initials"]).reset_index(drop=True)

# -----------------------
# Upload weekly rewards CSV
# -----------------------
uploaded = st.file_uploader("Upload weekly rewards CSV", type=["csv"], key="rewards_uploader")

if uploaded is None:
    st.info("Upload weekly rewards CSV to run analysis.")
    st.stop()

# Read rewards
try:
    rewards = read_rewards_csv(uploaded)
except Exception as e:
    st.error(str(e))
    st.stop()

# Debug info
st.subheader("File structure & quick checks")
st.write("Detected columns:", rewards.columns.tolist())
st.write("Unique Reward values:", rewards["Reward"].unique())
st.write("Unique House values:", rewards["House"].unique()[:20])
st.write(f"Total rows in weekly file: {len(rewards)}")

# Separate house vs conduct using Reward column (flexible contains)
house_df = rewards[rewards["Reward"].str.contains("house", case=False, na=False)].copy()
conduct_df = rewards[rewards["Reward"].str.contains("conduct", case=False, na=False)].copy()

st.write(f"House rows: {len(house_df)} — Conduct rows: {len(conduct_df)}")

# Aggregate calculations
# For house points: sum Points (positive 1)
if not house_df.empty:
    staff_house = house_df.groupby("Teacher", as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"})
else:
    staff_house = pd.DataFrame(columns=["Teacher","House Points This Week"])

# For conduct: count entries and present as positive counts
if not conduct_df.empty:
    staff_conduct = conduct_df.groupby("Teacher", as_index=False)["Points"].count().rename(columns={"Points":"Conduct Points This Week"})
else:
    staff_conduct = pd.DataFrame(columns=["Teacher","Conduct Points This Week"])

# Merge staff aggregates
staff_agg = pd.merge(staff_house, staff_conduct, on="Teacher", how="outer").fillna(0)
# ensure numeric types
if "House Points This Week" in staff_agg.columns:
    staff_agg["House Points This Week"] = pd.to_numeric(staff_agg["House Points This Week"], errors="coerce").fillna(0).astype(int)
else:
    staff_agg["House Points This Week"] = 0
if "Conduct Points This Week" in staff_agg.columns:
    staff_agg["Conduct Points This Week"] = pd.to_numeric(staff_agg["Conduct Points This Week"], errors="coerce").fillna(0).astype(int)
else:
    staff_agg["Conduct Points This Week"] = 0

# Ensure Teacher initials uppercase
staff_agg["Teacher"] = staff_agg["Teacher"].astype(str).str.upper().str.strip()

# -----------------------
# Merge with master staff list so everyone is included
# -----------------------
# staff_df has Initials column; staff_agg has Teacher (initials)
all_staff = staff_df.copy()
if all_staff.empty:
    # no master list — fallback to staff_agg teachers only
    master = pd.DataFrame({"Initials": staff_agg["Teacher"].unique()})
    master["FullName"] = master["Initials"]
    master["Dep"] = ""
else:
    master = all_staff.rename(columns={"Initials":"Teacher", "Dep":"Dept"})
    master = master.rename(columns={"FullName":"FullName"} )
    master = master[["Teacher","FullName","Dep"]].rename(columns={"Dep":"Dept"})

# Merge
staff_full = pd.merge(master, staff_agg, left_on="Teacher", right_on="Teacher", how="left").fillna(0)
# If staff_agg had no Teacher column (empty) create columns
if "House Points This Week" not in staff_full.columns:
    staff_full["House Points This Week"] = 0
if "Conduct Points This Week" not in staff_full.columns:
    staff_full["Conduct Points This Week"] = 0

# Ensure numeric types
staff_full["House Points This Week"] = pd.to_numeric(staff_full["House Points This Week"], errors="coerce").fillna(0).astype(int)
staff_full["Conduct Points This Week"] = pd.to_numeric(staff_full["Conduct Points This Week"], errors="coerce").fillna(0).astype(int)

# On target column
staff_full["On Target"] = np.where(staff_full["House Points This Week"] >= weekly_target, "✅ Yes", "⚠️ No")

# Display staff summary
st.subheader("Weekly Staff Summary (includes staff with 0 points)")
st.dataframe(staff_full.sort_values(["House Points This Week","Teacher"], ascending=[False,True]).reset_index(drop=True))

# -----------------------
# Department summary (use Dept from master if present; otherwise use Dep from rewards)
# -----------------------
# If master provided Dept, prefer master Dept
if "Dept" in staff_full.columns and staff_full["Dept"].notnull().any():
    dept_source = staff_full[["Dept","House Points This Week"]].groupby("Dept", as_index=False).sum().rename(columns={"House Points This Week":"House Points"})
else:
    # fallback to rewards file groupby Dep
    dept_source = house_df.groupby("Dep", as_index=False)["Points"].sum().rename(columns={"Points":"House Points"})

st.subheader("Department House Points (weekly)")
st.dataframe(dept_source.sort_values("House Points", ascending=False).reset_index(drop=True))

# -----------------------
# Top staff & students charts
# -----------------------
st.subheader("Top Staff (House Points) — weekly")
safe_plot(staff_full.sort_values("House Points This Week", ascending=True).tail(15), x="House Points This Week", y="Teacher", text="House Points This Week", title="Top 15 Staff (House Points)", orientation="h")

if not house_df.empty:
    student_house = house_df.groupby(["Pupil Name","Form","Year"], as_index=False)["Points"].sum().rename(columns={"Points":"House Points"})
    student_top = student_house.sort_values("House Points", ascending=True).tail(15)
    st.subheader("Top Students (House Points)")
    safe_plot(student_top, x="House Points", y="Pupil Name", text="House Points", title="Top 15 Students (House Points)", orientation="h")

# -----------------------
# House and Conduct by House (use colors)
# -----------------------
if not house_df.empty:
    house_points = house_df.groupby("House", as_index=False)["Points"].sum().rename(columns={"Points":"House Points"})
    # ensure house names are the full names
    house_points["House"] = house_points["House"].fillna("Unknown")
    st.subheader("House Points by House")
    safe_plot(house_points, x="House", y="House Points", text="House Points", title="House Points by House", color="House", color_map=HOUSE_COLORS)

if not conduct_df.empty:
    conduct_points = conduct_df.groupby("House", as_index=False)["Points"].count().rename(columns={"Points":"Conduct Points"})
    conduct_points["House"] = conduct_points["House"].fillna("Unknown")
    st.subheader("Conduct Points by House")
    safe_plot(conduct_points, x="House", y="Conduct Points", text="Conduct Points", title="Conduct Points by House", color="House", color_map=HOUSE_COLORS)

# -----------------------
# Category frequency
# -----------------------
if not house_df.empty:
    cat_freq = house_df.groupby("Category", as_index=False)["Points"].count().rename(columns={"Points":"Frequency"})
    st.subheader("House - Category Frequency")
    safe_plot(cat_freq.sort_values("Frequency", ascending=False), x="Category", y="Frequency", text="Frequency", title="House Categories Frequency")

if not conduct_df.empty:
    cat_freq_c = conduct_df.groupby("Category", as_index=False)["Points"].count().rename(columns={"Points":"Frequency"})
    st.subheader("Conduct - Category Frequency")
    safe_plot(cat_freq_c.sort_values("Frequency", ascending=False), x="Category", y="Frequency", text="Frequency", title="Conduct Categories Frequency")

# -----------------------
# Excel download of summaries
# -----------------------
summaries = {
    "Staff Summary": staff_full,
    "Dept Summary": dept_source,
    "Top Students (House)": student_house if 'student_house' in locals() else pd.DataFrame(),
    "House Points Raw": house_df,
    "Conduct Points Raw": conduct_df
}
excel_bytes = to_excel_bytes(summaries)
st.download_button("Download weekly Excel summary", data=excel_bytes, file_name=f"weekly_summary_{week_label}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -----------------------
# Update cumulative tracker (safe)
# -----------------------
try:
    cum_df, staff_stats = update_cumulative_tracker(staff_full[["Teacher","House Points This Week","Conduct Points This Week"]].assign(Week=week_label), cumulative_path)
    st.subheader("Cumulative Staff Stats")
    st.dataframe(staff_stats.sort_values("TotalHousePoints", ascending=False).reset_index(drop=True))
except Exception as e:
    st.warning(f"Could not update cumulative tracker: {e}")


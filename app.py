import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import re
import os
from io import BytesIO

# -----------------------
# App configuration & style
# -----------------------
st.set_page_config(page_title="House Points Dashboard", layout="wide")
st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stDownloadButton>button { width: 100%; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# Constants
# -----------------------
DEFAULT_WEEKLY_TARGET = 15
HOUSE_COLOURS = {"B": "red", "L": "yellow", "D": "blue", "W": "purple"}
EXPECTED_COLS = [
    "Pupil Name","House","Form","Year","Reward","Category","Points",
    "Date","Reward Description","Teacher","Dept","Subject","Email"
]
REQUIRED_FOR_CHARTS = ["House","Form","Points","Category","Date","Pupil Name","Teacher","Dept","Reward","Year","Reward Description","Subject","Email"]

# Aliases for fuzzy header matching
ALIASES = {
    "Pupil Name": [r"^student(\s*name)?$", r"^pupil(\s*name)?$", r"^learner(\s*name)?$", r"^name$"],
    "House": [r"^house$", r"^house\s*name$", r"^team$", r"^house\s*group$"],
    "Form": [r"^form$", r"^tutor\s*group$", r"^class$", r"^reg(istration)?\s*group$", r"^form\s*group$"],
    "Year": [r"^year$", r"^yr$", r"^year\s*group$"],
    "Reward": [r"^reward$", r"^value$", r"^type$", r"^merit\s*type$"],
    "Category": [r"^category$", r"^point\s*type$", r"^type\s*category$", r"^behavio(u)?r\s*category$", r"^house\s*point\s*category$"],
    "Points": [r"^points?$", r"^score$", r"^value\s*points?$", r"^merit\s*points?$", r"^behavio(u)?r\s*points?$"],
    "Date": [r"^date$", r"^timestamp$", r"^created(\s*at)?$", r"^issued(\s*at)?$"],
    "Reward Description": [r"^reward\s*description$", r"^description$", r"^comment$", r"^notes?$"],
    "Teacher": [r"^teacher(\s*name)?$", r"^staff(\s*name)?$", r"^awarded\s*by$", r"^given\s*by$", r"^owner$"],
    "Dept": [r"^dept$", r"^department$", r"^faculty$", r"^subject\s*area$"],
    "Subject": [r"^subject$", r"^course$"],
    "Email": [r"^email$", r"^teacher\s*email$", r"^staff\s*email$", r"^awarder\s*email$"]
}

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

def guess_mapping(df: pd.DataFrame) -> dict:
    """Map raw CSV columns to EXPECTED_COLS using aliases and heuristics."""
    raw_norm = {c: norm(c) for c in df.columns}
    mapping = {}
    used = set()

    # alias pass
    for target, patterns in ALIASES.items():
        found = None
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            for pat in patterns:
                if re.match(pat, n):
                    found = raw_col
                    break
            if found:
                break
        if found:
            mapping[target] = found
            used.add(found)

    # heuristic fallbacks
    if "House" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "house" in n or n in {"h"}:
                mapping["House"] = raw_col; used.add(raw_col); break

    if "Form" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if n.startswith("form") or "tutor" in n or "reg" in n or n in {"class"}:
                mapping["Form"] = raw_col; used.add(raw_col); break

    if "Points" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "point" in n or n in {"score","value"}:
                mapping["Points"] = raw_col; used.add(raw_col); break

    if "Category" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "category" in n or "behavio" in n or "housepoint" in n:
                mapping["Category"] = raw_col; used.add(raw_col); break

    if "Date" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if n.startswith("date") or "time" in n or "created" in n:
                mapping["Date"] = raw_col; used.add(raw_col); break

    if "Teacher" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "teacher" in n or "staff" in n or "awardedby" in n or "owner" in n or "givenby" in n:
                mapping["Teacher"] = raw_col; used.add(raw_col); break

    if "Dept" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "dept" in n or "department" in n or "faculty" in n:
                mapping["Dept"] = raw_col; used.add(raw_col); break

    if "Reward" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "reward" in n or n == "value" or "merit" in n:
                mapping["Reward"] = raw_col; used.add(raw_col); break

    if "Pupil Name" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "name" in n or "student" in n or "pupil" in n or "learner" in n:
                mapping["Pupil Name"] = raw_col; used.add(raw_col); break

    if "Year" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if n in {"year","yr","yeargroup"}:
                mapping["Year"] = raw_col; used.add(raw_col); break

    if "Reward Description" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "descr" in n or "comment" in n or n == "notes":
                mapping["Reward Description"] = raw_col; used.add(raw_col); break

    if "Subject" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "subject" in n or "course" in n:
                mapping["Subject"] = raw_col; used.add(raw_col); break

    if "Email" not in mapping:
        for raw_col, n in raw_norm.items():
            if raw_col in used: 
                continue
            if "email" in n:
                mapping["Email"] = raw_col; used.add(raw_col); break

    return mapping

def normalize_house_code(s: str) -> str:
    s = str(s or "").strip().upper()
    if not s:
        return ""
    # Allow full names or initials
    if s.startswith("BRU"): return "B"
    if s.startswith("DIC"): return "D"
    if s.startswith("LID"): return "L"
    if s.startswith("WIL"): return "W"
    if s in {"B","D","L","W"}: return s
    return s[:1]  # best-effort fallback

def apply_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    # Build a renamed dataframe with expected headers only (keep originals for safety)
    out = pd.DataFrame()
    for col in EXPECTED_COLS:
        if col in mapping and mapping[col] in df.columns:
            out[col] = df[mapping[col]].copy()
        else:
            out[col] = ""  # create empty if missing
    return out

def clean_types(df: pd.DataFrame, week_label: str) -> pd.DataFrame:
    # Coerce types safely
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    # Normalise text columns
    for col in ["Reward","Category","Teacher","Dept","Pupil Name","Subject","Email","Reward Description","Year","Form"]:
        df[col] = df[col].astype(str).str.strip()
    # House + Form
    df["House"] = df["House"].apply(normalize_house_code)
    df["Form"] = df["Form"].astype(str).str.strip().str.upper()
    df["Week"] = week_label
    return df

def detect_point_types(df):
    house_mask = df["Category"].str.contains("house|reward", case=False, na=False)
    conduct_mask = df["Category"].str.contains("conduct|behavio", case=False, na=False)
    if not house_mask.any() and not conduct_mask.any():
        house_mask = df["Points"] > 0
        conduct_mask = df["Points"] < 0
    return house_mask, conduct_mask

def aggregate_weekly(df: pd.DataFrame, week_label: str, target: int):
    house_mask, conduct_mask = detect_point_types(df)
    house_df = df[house_mask].copy()
    conduct_df = df[conduct_mask].copy()
    conduct_df["Points"] = conduct_df["Points"].abs()

    # Staff
    staff_house = house_df.groupby("Teacher", as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"}) if not house_df.empty else pd.DataFrame(columns=["Teacher","House Points This Week"])
    staff_conduct = conduct_df.groupby("Teacher", as_index=False)["Points"].sum().rename(columns={"Points":"Conduct Points This Week"}) if not conduct_df.empty else pd.DataFrame(columns=["Teacher","Conduct Points This Week"])
    staff_summary = staff_house.merge(staff_conduct, on="Teacher", how="outer").fillna(0)

    if not house_df.empty and "Dept" in house_df.columns:
        dept_mode = house_df.groupby("Teacher")["Dept"].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "").reset_index()
        staff_summary = staff_summary.merge(dept_mode, on="Teacher", how="left")
    else:
        staff_summary["Dept"] = ""

    staff_summary["UnderTargetThisWeek"] = staff_summary["House Points This Week"] < target
    staff_summary["Week"] = week_label

    # Dept
    dept_house = house_df.groupby("Dept", as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"}) if not house_df.empty else pd.DataFrame(columns=["Dept","House Points This Week"])

    # Students
    student_house = house_df.groupby(["Pupil Name","Year","Form","House"], as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"}) if not house_df.empty else pd.DataFrame(columns=["Pupil Name","Year","Form","House","House Points This Week"])

    # Reward counts
    value_school = house_df.groupby("Reward", as_index=False)["Points"].count().rename(columns={"Points":"Count"}) if not house_df.empty else pd.DataFrame(columns=["Reward","Count"])

    return {
        "staff_summary": staff_summary,
        "dept_house": dept_house,
        "student_house": student_house,
        "value_school": value_school,
        "raw_house_df": house_df,
        "raw_conduct_df": conduct_df
    }

def to_excel_bytes(summaries: dict):
    from openpyxl import Workbook  # ensure engine
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, df in summaries.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    out.seek(0)
    return out.read()

# -----------------------
# UI — Upload + Mapping
# -----------------------
st.title("🏫 Weekly House & Conduct Points Dashboard")

st.markdown("### 📤 Upload your weekly CSV file")
uploaded_file = st.file_uploader("Browse for your CSV file", type=["csv"], label_visibility="collapsed")

week_label = st.sidebar.text_input("Week label", value=datetime.now().strftime("%Y-%m-%d"))
target_input = st.sidebar.number_input("Weekly house points target per staff", min_value=1, value=DEFAULT_WEEKLY_TARGET)

if uploaded_file is None:
    st.info("👆 Please upload your weekly CSV file to begin.")
    st.stop()

# Read raw
raw_df = pd.read_csv(uploaded_file, dtype=str)
st.success(f"✅ Loaded {len(raw_df):,} rows.")
st.caption(f"Headers detected: {list(raw_df.columns)}")
st.dataframe(raw_df.head(10))

# Auto guess mapping, then let user adjust
auto_map = guess_mapping(raw_df)

with st.expander("🔧 Column Mapping — adjust if needed"):
    cols = list(raw_df.columns)
    mapping = {}
    for target in EXPECTED_COLS:
        default = auto_map.get(target, None)
        mapping[target] = st.selectbox(
            f"{target}",
            options=["(none)"] + cols,
            index=(cols.index(default) + 1) if default in cols else 0,
            key=f"map_{target}"
        )
    st.caption("Tip: only mapped columns will be used; unmapped will remain blank.")

# Build unified dataframe with expected headers
final_map = {t: c for t, c in mapping.items() if c and c != "(none)"}
df = apply_mapping(raw_df, final_map)
df = clean_types(df, week_label)

# Quality checks
missing_critical = [c for c in ["House","Form","Points","Category"] if df[c].eq("").all()]
if missing_critical:
    st.error(f"Missing required data for: {', '.join(missing_critical)}. Please set the correct columns in the mapping above.")
    st.stop()

# House filter (after cleaning)
houses_available = sorted([h for h in df["House"].dropna().unique() if h])
selected_house = st.multiselect("🏠 Filter by House (leave empty for all)", houses_available)
if selected_house:
    df = df[df["House"].isin(selected_house)]

# Aggregate & build dashboard
aggs = aggregate_weekly(df, week_label, target_input)
staff_df = aggs["staff_summary"].sort_values("House Points This Week", ascending=False)

# Staff summary table
st.subheader("👩‍🏫 Staff Summary (Weekly)")
def highlight_staff_target(row):
    return ["background-color: #ffcccc" if row["UnderTargetThisWeek"] else "#ccffcc"]*len(row)
st.dataframe(staff_df.style.apply(highlight_staff_target, axis=1))

# Metrics
total_house = int(aggs["raw_house_df"]["Points"].sum()) if not aggs["raw_house_df"].empty else 0
total_conduct = int(aggs["raw_conduct_df"]["Points"].sum()) if not aggs["raw_conduct_df"].empty else 0
under_target = staff_df[staff_df["UnderTargetThisWeek"]]
m1, m2, m3 = st.columns(3)
m1.metric("Total House Points", f"{total_house:,}")
m2.metric("Total Conduct Points (abs)", f"{total_conduct:,}")
m3.metric("Staff Below Target", f"{len(under_target)}")

# Department summary
st.subheader("🏢 Department Summary (Weekly)")
if not aggs["dept_house"].empty:
    st.dataframe(aggs["dept_house"].sort_values("House Points This Week", ascending=False))
else:
    st.info("No department data in current selection.")

# Student top table & chart
st.subheader("🎓 Top Students (Weekly House Points)")
student_df = aggs["student_house"].sort_values("House Points This Week", ascending=False).head(30)
st.dataframe(student_df)
if not student_df.empty:
    fig_students = px.bar(
        student_df.head(15),
        x="House Points This Week", y="Pupil Name",
        color="House", color_discrete_map=HOUSE_COLOURS,
        orientation='h', text="House Points This Week",
        title="Top 15 Students (Week)"
    )
    fig_students.update_traces(texttemplate="%{text}", textposition="outside")
    st.plotly_chart(fig_students, use_container_width=True)

# Top staff chart
st.subheader("👨‍🏫 Top Staff (House Points)")
if not staff_df.empty:
    fig_staff = px.bar(
        staff_df.head(15),
        x="House Points This Week", y="Teacher",
        color="Dept", orientation='h',
        text="House Points This Week",
        title="Top 15 Staff by House Points"
    )
    fig_staff.update_traces(texttemplate="%{text}", textposition="outside")
    st.plotly_chart(fig_staff, use_container_width=True)

# House / Conduct / Net
st.subheader("🏠 House & Conduct Points by House")
house_totals = aggs["raw_house_df"].groupby("House", as_index=False)["Points"].sum() if not aggs["raw_house_df"].empty else pd.DataFrame(columns=["House","Points"])
conduct_totals = aggs["raw_conduct_df"].groupby("House", as_index=False)["Points"].sum() if not aggs["raw_conduct_df"].empty else pd.DataFrame(columns=["House","Points"])
if not conduct_totals.empty:
    conduct_totals["Points"] = conduct_totals["Points"].abs()
combined = pd.merge(house_totals, conduct_totals, on="House", how="outer", suffixes=("_House","_Conduct")).fillna(0)
combined["Net"] = combined["Points_House"] - combined["Points_Conduct"]

c1, c2 = st.columns(2)
with c1:
    if not combined.empty:
        fig_house = px.bar(combined, x="House", y="Points_House", color="House",
                           color_discrete_map=HOUSE_COLOURS, text="Points_House", title="Total House Points")
        fig_house.update_traces(texttemplate="%{text}", textposition="outside")
        st.plotly_chart(fig_house, use_container_width=True)
with c2:
    if not combined.empty:
        fig_conduct = px.bar(combined, x="Points_Conduct", y="House", color="House",
                             color_discrete_map=HOUSE_COLOURS, orientation="h",
                             text="Points_Conduct", title="Total Conduct Points (Lower = Better)")
        fig_conduct.update_traces(texttemplate="%{text}", textposition="outside")
        fig_conduct.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_conduct, use_container_width=True)

st.subheader("🏆 Net Points (House − Conduct)")
if not combined.empty:
    fig_net = px.bar(
        combined, x="Net", y="House",
        color="House", color_discrete_map=HOUSE_COLOURS,
        orientation="h", text="Net", title="Net Points by House"
    )
    fig_net.update_traces(texttemplate="%{text}", textposition="outside")
    st.plotly_chart(fig_net, use_container_width=True)

# Top forms per house
st.subheader("🏫 Top Performing Forms per House")
if not aggs["raw_house_df"].empty:
    form_points = aggs["raw_house_df"].groupby(["House","Form"], as_index=False)["Points"].sum()
    top_forms = form_points.sort_values(["House","Points"], ascending=[True, False]).groupby("House").head(3)
    if not top_forms.empty:
        fig_forms = px.bar(
            top_forms, x="Points", y="Form",
            color="House", color_discrete_map=HOUSE_COLOURS,
            orientation="h", text="Points",
            title="Top 3 Forms in Each House"
        )
        fig_forms.update_traces(texttemplate="%{text}", textposition="outside")
        st.plotly_chart(fig_forms, use_container_width=True)

# Reward values frequency
st.subheader("🎖️ Reward Values Frequency (Weekly)")
val_df = aggs["value_school"].sort_values("Count", ascending=False)
st.dataframe(val_df)
if not val_df.empty:
    fig_values = px.pie(val_df, values="Count", names="Reward", title="Reward Distribution (House Points)")
    st.plotly_chart(fig_values, use_container_width=True)

# Excel export
def to_excel_bytes(summaries: dict):
    from openpyxl import Workbook
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, df in summaries.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    out.seek(0)
    return out.read()

excel_bytes = to_excel_bytes(aggs)
st.download_button(
    "📥 Download Weekly Excel Summary",
    data=excel_bytes,
    file_name=f"weekly_summary_{week_label}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

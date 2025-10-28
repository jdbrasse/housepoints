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
# Permanent Staff List
# -----------------------
PERMANENT_STAFF = [
    {"Teacher": "Alice Smith", "Dept": "English"},
    {"Teacher": "Bob Jones", "Dept": "Maths"},
    {"Teacher": "Carla Patel", "Dept": "Science"},
    {"Teacher": "David Lee", "Dept": "Art"},
    {"Teacher": "Ella Brown", "Dept": "PE"},
    {"Teacher": "Fiona Green", "Dept": "History"},
    {"Teacher": "George White", "Dept": "Geography"},
    {"Teacher": "Hannah Black", "Dept": "Computing"},
]

# -----------------------
# House Colour Map
# -----------------------
HOUSE_COLOURS = {
    "B": "red",          # Brunel
    "D": "blue",         # Dickens
    "L": "gold",         # Liddell
    "W": "purple"        # Wilberforce
}

# -----------------------
# Display School Logo
# -----------------------
try:
    logo = Image.open("logo.png")
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
    df["House"] = df["House"].astype(str).str.strip().str.upper()
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
    student_house = house_df.groupby(["Pupil Name","Year","Form","House"], as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"})
    value_school = house_df.groupby("Value", as_index=False)["Points"].count().rename(columns={"Points":"Count"})

    staff_summary = staff_house.merge(staff_conduct, on="Teacher", how="outer").fillna(0)
    teacher_dept = house_df.groupby("Teacher")["Dept"].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "").reset_index()
    if "Dept" in teacher_dept.columns:
        staff_summary = staff_summary.merge(teacher_dept, on="Teacher", how="left")

    # Merge with permanent staff list
    permanent_df = pd.DataFrame(PERMANENT_STAFF)
    staff_summary = permanent_df.merge(staff_summary, on=["Teacher", "Dept"], how="left")
    staff_summary["House Points This Week"] = staff_summary["House Points This Week"].fillna(0).astype(int)
    staff_summary["Conduct Points This Week"] = staff_summary["Conduct Points This Week"].fillna(0).astype(int)
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
    cols = ["Teacher","Dept","House Points This Week","Conduct Points This Week","Week"]
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
    staff_stats = cum.groupby(["Teacher","Dept"], as_index=False).agg(
        TotalHousePoints=("House Points This Week","sum"),
        WeeksReported=("Week","nunique"),
        AvgHousePerWeek=("House Points This Week","mean")
    )
    staff_stats["AvgHousePerWeek"] = staff_stats["AvgHousePerWeek"].round(2)
    staff_stats["ContributionStatus"] = np.where(
        staff_stats["AvgHousePerWeek"] >= DEFAULT_WEEKLY_TARGET, "Positive", "Negative"
    )
    permanent_df = pd.DataFrame(PERMANENT_STAFF)
    staff_stats = permanent_df.merge(staff_stats, on=["Teacher", "Dept"], how="left").fillna({
        "TotalHousePoints": 0,
        "WeeksReported": 0,
        "AvgHousePerWeek": 0,
        "ContributionStatus": "No Data"
    })
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

        staff_df = aggregates["staff_summary"].sort_values("House Points This Week", ascending=False)
        st.subheader("Staff Summary (Weekly)")
        def highlight_staff_target(row):
            return ["background-color: #ffcccc" if row["UnderTargetThisWeek"] else "#ccffcc"]*len(row)
        st.dataframe(staff_df.style.apply(highlight_staff_target, axis=1))

        # --- House Points ---
        st.subheader("🏠 House Leaderboard (House Points)")
        house_totals = aggregates["raw_house_df"].groupby("House", as_index=False)["Points"].sum()
        if not house_totals.empty:
            fig_house = px.bar(
                house_totals, x="House", y="Points",
                color="House", color_discrete_map=HOUSE_COLOURS,
                text="Points", title="Total House Points by House"
            )
            fig_house.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_house, use_container_width=True)

        st.subheader("🏫 Best Forms per House (House Points)")
        form_totals = aggregates["raw_house_df"].groupby(["House","Form"], as_index=False)["Points"].sum()
        top_forms = form_totals.sort_values(["House","Points"], ascending=[True,False]).groupby("House").head(3)
        if not top_forms.empty:
            fig_forms = px.bar(
                top_forms, x="Points", y="Form",
                color="House", color_discrete_map=HOUSE_COLOURS,
                orientation="h", text="Points",
                title="Top Forms within Each House (House Points)"
            )
            fig_forms.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_forms, use_container_width=True)

        # --- Conduct Points (Inverted) ---
        st.subheader("⚠️ House Leaderboard (Conduct Points — lower is better)")
        conduct_df = aggregates["raw_conduct_df"]
        if not conduct_df.empty:
            conduct_totals = conduct_df.groupby("House", as_index=False)["Points"].sum()
            conduct_totals["Points"] = conduct_totals["Points"].abs()
            conduct_totals = conduct_totals.sort_values("Points")
            fig_conduct_house = px.bar(
                conduct_totals, x="Points", y="House",
                color="House", color_discrete_map=HOUSE_COLOURS,
                orientation="h", text="Points",
                title="Conduct Points by House (lower = better)"
            )
            fig_conduct_house.update_traces(texttemplate="%{text}", textposition="outside")
            fig_conduct_house.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_conduct_house, use_container_width=True)

            st.subheader("🚨 Forms with Most Conduct Points (Top 3 per House)")
            form_conduct = conduct_df.groupby(["House","Form"], as_index=False)["Points"].sum()
            form_conduct["Points"] = form_conduct["Points"].abs()
            top_bad_forms = form_conduct.sort_values(["House","Points"], ascending=[True,False]).groupby("House").head(3)
            if not top_bad_forms.empty:
                fig_conduct_forms = px.bar(
                    top_bad_forms, x="Points", y="Form",
                    color="House", color_discrete_map=HOUSE_COLOURS,
                    orientation="h", text="Points",
                    title="Top Forms per House (Conduct Points — lower = better)"
                )
                fig_conduct_forms.update_traces(texttemplate="%{text}", textposition="outside")
                fig_conduct_forms.update_yaxes(categoryorder="total ascending")
                st.plotly_chart(fig_conduct_forms, use_container_width=True)

        # --- Net Points ---
        st.subheader("🏆 Net Points Leaderboard (House − Conduct)")
        if not house_totals.empty:
            conduct_totals = conduct_df.groupby("House", as_index=False)["Points"].sum() if not conduct_df.empty else pd.DataFrame(columns=["House","Points"])
            conduct_totals["Points"] = conduct_totals["Points"].abs() if "Points" in conduct_totals else 0
            net_df = house_totals.merge(conduct_totals, on="House", suffixes=("_House", "_Conduct"), how="outer").fillna(0)
            net_df["NetPoints"] = net_df["Points_House"] - net_df["Points_Conduct"]
            net_df = net_df.sort_values("NetPoints", ascending=False)
            fig_net = px.bar(
                net_df, x="NetPoints", y="House",
                color="House", color_discrete_map=HOUSE_COLOURS,
                orientation="h", text="NetPoints",
                title="Overall Net Points by House (House − Conduct)"
            )
            fig_net.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_net, use_container_width=True)

        # --- Cumulative Tracker ---
        st.subheader("📈 Cumulative Staff Tracker")
        cum_df, staff_stats = update_cumulative_tracker(aggregates["staff_summary"], cumulative_path)
        st.dataframe(staff_stats.sort_values("TotalHousePoints", ascending=False))

        # --- Download Excel ---
        excel_bytes = to_excel_bytes(aggregates)
        st.download_button(
            "Download weekly Excel summary",
            data=excel_bytes,
            file_name=f"weekly_summary_{week_label}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

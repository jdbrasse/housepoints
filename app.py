import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import os
from PIL import Image
from io import BytesIO

# -----------------------
# App Configuration & Style
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

# -----------------------
# Optional logo (no warnings shown if missing)
# -----------------------
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

# -----------------------
# Helper functions
# -----------------------
def load_and_clean(uploaded_file, week_label):
    df = pd.read_csv(uploaded_file, header=0, dtype=str)
    # If file already has expected headers length, align names
    if len(df.columns) == len(EXPECTED_COLS):
        df.columns = EXPECTED_COLS
    # Coerce/standardise
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    # Tidy key text columns
    for col in ["Reward","Category","Teacher","Dept","Pupil Name","Subject","Email"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
    if "Form" in df.columns:
        df["Form"] = df["Form"].astype(str).str.strip().str.upper()
    if "House" in df.columns:
        df["House"] = df["House"].astype(str).str.strip().str.upper()
    df["Week"] = week_label
    return df

def detect_point_types(df):
    # Try to infer: "House/Reward" vs "Conduct/Behaviour"
    house_mask = df["Category"].str.contains("house|reward", case=False, na=False)
    conduct_mask = df["Category"].str.contains("conduct|behaviour|behavior", case=False, na=False)
    # Fallback: positives are house, negatives are conduct
    if not house_mask.any() and not conduct_mask.any():
        house_mask = df["Points"] > 0
        conduct_mask = df["Points"] < 0
    return house_mask, conduct_mask

def aggregate_weekly(df, week_label, target):
    house_mask, conduct_mask = detect_point_types(df)
    house_df = df[house_mask].copy()
    conduct_df = df[conduct_mask].copy()
    conduct_df["Points"] = conduct_df["Points"].abs()

    # Staff
    staff_house = house_df.groupby("Teacher", as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"})
    staff_conduct = conduct_df.groupby("Teacher", as_index=False)["Points"].sum().rename(columns={"Points":"Conduct Points This Week"})
    staff_summary = staff_house.merge(staff_conduct, on="Teacher", how="outer").fillna(0)

    # Department for staff (mode of dept)
    if not house_df.empty:
        teacher_dept = house_df.groupby("Teacher")["Dept"].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "").reset_index()
        staff_summary = staff_summary.merge(teacher_dept, on="Teacher", how="left")

    staff_summary["UnderTargetThisWeek"] = staff_summary["House Points This Week"] < target
    staff_summary["Week"] = week_label

    # Dept Summary
    dept_house = house_df.groupby("Dept", as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"}) if not house_df.empty else pd.DataFrame(columns=["Dept","House Points This Week"])

    # Students
    student_house = house_df.groupby(["Pupil Name","Year","Form","House"], as_index=False)["Points"].sum().rename(columns={"Points":"House Points This Week"}) if not house_df.empty else pd.DataFrame(columns=["Pupil Name","Year","Form","House","House Points This Week"])

    # Values (by Reward)
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
    # Export all frames to sheets
    from openpyxl import Workbook  # noqa: F401  (ensures engine available)
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, df in summaries.items():
            # Sheet names limited to 31 chars
            sheet = str(name)[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)
    out.seek(0)
    return out.read()

# -----------------------
# Sidebar & Upload
# -----------------------
st.sidebar.header("⚙️ Settings")
target_input = st.sidebar.number_input("Weekly house points target per staff", min_value=1, value=DEFAULT_WEEKLY_TARGET)
week_label = st.sidebar.text_input("Week label", value=datetime.now().strftime("%Y-%m-%d"))
st.sidebar.markdown("---")
st.sidebar.caption("Upload weekly CSV:")
uploaded_file = st.sidebar.file_uploader("📂 Browse CSV", type=["csv"])
st.sidebar.markdown("---")
st.sidebar.caption("Expected columns:")
st.sidebar.write(EXPECTED_COLS)

# -----------------------
# Main Layout
# -----------------------
st.title("🏫 Weekly House & Conduct Points Tracker")

if uploaded_file is not None:
    df = load_and_clean(uploaded_file, week_label)
    st.success(f"✅ Loaded {len(df):,} rows. Date range: {df['Date'].min().date() if pd.notna(df['Date'].min()) else '—'} to {df['Date'].max().date() if pd.notna(df['Date'].max()) else '—'}")
    st.dataframe(df.head(10))

    # House filter
    houses = [h for h in ["B","D","L","W"] if h in set(df["House"].dropna().unique())]
    selected_house = st.multiselect("🏠 Filter by House (leave empty for all)", houses)
    df_filtered = df[df["House"].isin(selected_house)] if selected_house else df

    # Aggregate
    aggregates = aggregate_weekly(df_filtered, week_label, target_input)
    staff_df = aggregates["staff_summary"].sort_values("House Points This Week", ascending=False)

    # -----------------------
    # Staff Summary
    # -----------------------
    st.subheader("👩‍🏫 Staff Summary (Weekly)")
    def highlight_staff_target(row):
        return ["background-color: #ffcccc" if row["UnderTargetThisWeek"] else "#ccffcc"]*len(row)
    if not staff_df.empty:
        st.dataframe(staff_df.style.apply(highlight_staff_target, axis=1))
    else:
        st.info("No staff data for current selection.")

    # Top Staff Sidebar
    st.sidebar.subheader("🏆 Top 5 Staff This Week")
    for _, row in staff_df.head(5).iterrows():
        badge = "✅" if not row["UnderTargetThisWeek"] else "⚠️"
        st.sidebar.write(f"{badge} {row['Teacher']}: {int(row['House Points This Week'])} pts")

    under_target = staff_df[staff_df["UnderTargetThisWeek"]] if not staff_df.empty else pd.DataFrame()
    if not under_target.empty:
        st.warning(f"⚠️ {len(under_target)} staff below weekly target of {target_input} house points!")

    # -----------------------
    # Key Metrics
    # -----------------------
    total_house = int(aggregates["raw_house_df"]["Points"].sum()) if not aggregates["raw_house_df"].empty else 0
    total_conduct = int(aggregates["raw_conduct_df"]["Points"].sum()) if not aggregates["raw_conduct_df"].empty else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Total House Points", f"{total_house:,}")
    col2.metric("Total Conduct Points (abs)", f"{total_conduct:,}")
    col3.metric("Staff Below Target", f"{len(under_target)}")

    # -----------------------
    # Department Summary
    # -----------------------
    st.subheader("🏢 Department Summary (Weekly)")
    if not aggregates["dept_house"].empty:
        st.dataframe(aggregates["dept_house"].sort_values("House Points This Week", ascending=False))
    else:
        st.info("No department data for current selection.")

    # -----------------------
    # Student Summary & Chart
    # -----------------------
    st.subheader("🎓 Top Students (Weekly House Points)")
    student_df = aggregates["student_house"].sort_values("House Points This Week", ascending=False).head(30)
    if not student_df.empty:
        st.dataframe(student_df)
        fig_students = px.bar(
            student_df.head(15),
            x="House Points This Week",
            y="Pupil Name",
            color="House",
            color_discrete_map=HOUSE_COLOURS,
            orientation='h',
            text="House Points This Week",
            title="Top 15 Students (Week)"
        )
        fig_students.update_traces(texttemplate="%{text}", textposition="outside")
        st.plotly_chart(fig_students, use_container_width=True)
    else:
        st.info("No student data for current selection.")

    # -----------------------
    # Top Staff Chart
    # -----------------------
    st.subheader("👨‍🏫 Top Staff (House Points)")
    if not staff_df.empty:
        fig_staff = px.bar(
            staff_df.head(15),
            x="House Points This Week",
            y="Teacher",
            color="Dept",
            orientation='h',
            text="House Points This Week",
            title="Top 15 Staff by House Points"
        )
        fig_staff.update_traces(texttemplate="%{text}", textposition="outside")
        st.plotly_chart(fig_staff, use_container_width=True)
    else:
        st.info("No staff chart to display.")

    # -----------------------
    # House & Conduct by House (side-by-side)
    # -----------------------
    st.subheader("🏠 House & Conduct Points by House")
    house_totals = aggregates["raw_house_df"].groupby("House", as_index=False)["Points"].sum() if not aggregates["raw_house_df"].empty else pd.DataFrame(columns=["House","Points"])
    conduct_totals = aggregates["raw_conduct_df"].groupby("House", as_index=False)["Points"].sum() if not aggregates["raw_conduct_df"].empty else pd.DataFrame(columns=["House","Points"])
    if not conduct_totals.empty:
        conduct_totals["Points"] = conduct_totals["Points"].abs()

    combined = pd.merge(house_totals, conduct_totals, on="House", how="outer", suffixes=("_House","_Conduct")).fillna(0)
    combined["Net"] = combined["Points_House"] - combined["Points_Conduct"]

    colA, colB = st.columns(2)
    with colA:
        if not combined.empty:
            fig_house = px.bar(
                combined,
                x="House", y="Points_House",
                color="House", color_discrete_map=HOUSE_COLOURS,
                text="Points_House", title="Total House Points"
            )
            fig_house.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_house, use_container_width=True)
        else:
            st.info("No house totals to display.")

    with colB:
        if not combined.empty:
            fig_conduct = px.bar(
                combined,
                x="Points_Conduct", y="House",
                color="House", color_discrete_map=HOUSE_COLOURS,
                orientation="h", text="Points_Conduct",
                title="Total Conduct Points (Lower = Better)"
            )
            fig_conduct.update_traces(texttemplate="%{text}", textposition="outside")
            fig_conduct.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_conduct, use_container_width=True)
        else:
            st.info("No conduct totals to display.")

    # Net points
    st.subheader("🏆 Net Points (House − Conduct)")
    if not combined.empty:
        fig_net = px.bar(
            combined,
            x="Net", y="House",
            color="House", color_discrete_map=HOUSE_COLOURS,
            orientation="h", text="Net",
            title="Net Points by House"
        )
        fig_net.update_traces(texttemplate="%{text}", textposition="outside")
        st.plotly_chart(fig_net, use_container_width=True)
    else:
        st.info("No net points to display.")

    # -----------------------
    # Top Performing Forms per House
    # -----------------------
    st.subheader("🏫 Top Performing Forms per House (House Points)")
    if not aggregates["raw_house_df"].empty:
        form_points = aggregates["raw_house_df"].groupby(["House","Form"], as_index=False)["Points"].sum()
        top_forms = form_points.sort_values(["House","Points"], ascending=[True, False]).groupby("House").head(3)
        if not top_forms.empty:
            fig_forms = px.bar(
                top_forms,
                x="Points", y="Form",
                color="House", color_discrete_map=HOUSE_COLOURS,
                orientation="h", text="Points",
                title="Top 3 Forms in Each House"
            )
            fig_forms.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_forms, use_container_width=True)
        else:
            st.info("No forms data to display.")
    else:
        st.info("No house points available to build forms chart.")

    # -----------------------
    # Reward Values Frequency
    # -----------------------
    st.subheader("🎖️ Reward Values Frequency (Weekly)")
    val_df = aggregates["value_school"].sort_values("Count", ascending=False)
    if not val_df.empty:
        st.dataframe(val_df)
        fig_values = px.pie(val_df, values="Count", names="Reward", title="Reward Distribution (House Points)")
        st.plotly_chart(fig_values, use_container_width=True)
    else:
        st.info("No reward distribution to display.")

    # -----------------------
    # House vs Conduct — Reward Frequency Comparison
    # -----------------------
    st.subheader("📊 Frequency of Reward Types — House vs Conduct")
    if not aggregates["raw_house_df"].empty or not aggregates["raw_conduct_df"].empty:
        house_values = aggregates["raw_house_df"].groupby("Reward", as_index=False)["Points"].count().rename(columns={"Points":"Count"}) if not aggregates["raw_house_df"].empty else pd.DataFrame(columns=["Reward","Count"])
        house_values["Type"] = "House"
        conduct_values = aggregates["raw_conduct_df"].groupby("Reward", as_index=False)["Points"].count().rename(columns={"Points":"Count"}) if not aggregates["raw_conduct_df"].empty else pd.DataFrame(columns=["Reward","Count"])
        conduct_values["Type"] = "Conduct"
        combined_freq = pd.concat([house_values, conduct_values], ignore_index=True)
        if not combined_freq.empty:
            fig_combined = px.bar(
                combined_freq,
                x="Reward", y="Count",
                color="Type", barmode="group",
                text="Count", title="Reward Type Frequency (House vs Conduct)"
            )
            fig_combined.update_traces(texttemplate="%{text}", textposition="outside")
            fig_combined.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig_combined, use_container_width=True)
        else:
            st.info("No reward frequency data to compare.")
    else:
        st.info("No data available for reward frequency comparison.")

    # -----------------------
    # Download Excel Summary
    # -----------------------
    excel_bytes = to_excel_bytes(aggregates)
    st.download_button(
        "📥 Download Weekly Excel Summary",
        data=excel_bytes,
        file_name=f"weekly_summary_{week_label}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("👈 Please upload your weekly CSV file using the sidebar to begin.")

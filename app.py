import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- CONFIG ---
st.set_page_config(page_title="House & Conduct Points Analysis", layout="wide")
st.title("🏫 House & Conduct Points Analysis Dashboard")
st.write("Upload your weekly CSV file below to generate the full analysis.")

DEFAULT_WEEKLY_TARGET = 15
HOUSE_MAPPING = {"B": "Brunel", "L": "Liddell", "D": "Dickens", "W": "Wilberforce"}
HOUSE_COLORS = {"Brunel": "#FF0000", "Dickens": "#0000FF", "Liddell": "#FFD700", "Wilberforce": "#800080"}

# --- EMBEDDED STAFF INITIALS (from your Excel, Column A) ---
PERMANENT_STAFF = pd.DataFrame({
    "Teacher": [
        "LJO","POT","LTA","JSI","MPU","NIQ","LGS","LTH","VSB","FA","JMA","RC","VT",
        "EPO","TNE","IMO","NPE","MO","CL","ACA","LHO","SBR","DBE","CLT","JHO","BW",
        "DOL","DE","VM","DBR","EMC","MRO","HME","DWI","NHE","CTU","JRO","JWA","EWE",
        "GSM","MSA","HST","EBA","CDO","EFO","SSP","TDU","KFE","WRO","SCO","ECA",
        "SMA","RPO","MRA","JPO","SMI","LMI","LPE","EBO","JBO","MFI","LST","SSA",
        "RFI","MAW","JHA","SWA","DGU","JWI","RWI","ACO","MMI","GDO","RLI","HWA",
        "LHU","HRO","EPO2","JSO","JFO","TSM","RBA","RRA","PRA","ELO","CWA","NMI",
        "AFA","SSA2","TLE","EBO2","MMO","VLO","MPO","JMU","KST","DTA","RGA"
    ]
})

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload weekly CSV file", type=["csv"])

# --- DATA CLEANING ---
def load_and_clean(file):
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()
    expected_columns = [
        "Pupil Name","House","Form","Year","Reward","Category",
        "Points","Date","Reward Description","Teacher","Dep","Subject"
    ]
    if len(df.columns) >= len(expected_columns):
        df.columns = expected_columns
    else:
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""

    df["Teacher"] = df["Teacher"].astype(str).str.strip().replace("", "Unknown")
    df["Dep"] = df["Dep"].astype(str).str.strip()
    df["Reward"] = df["Reward"].astype(str).str.strip().str.lower()
    df["Category"] = df["Category"].astype(str).str.strip().str.lower()
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    df["House"] = df["House"].astype(str).str.strip().str.upper().map(HOUSE_MAPPING)
    df["Form"] = df["Form"].astype(str).str.strip().str.upper()
    df["Year"] = df["Year"].astype(str).str.strip()
    return df

# --- SAFE PLOT FUNCTION ---
def safe_plot(data, x, y, title, text=None, orientation="v", color=None, color_map=None):
    if data.empty:
        st.info(f"No data available for {title}")
        return
    fig = px.bar(
        data, x=x, y=y, text=text, orientation=orientation, title=title,
        color=color, color_discrete_map=color_map
    )
    fig.update_traces(texttemplate="%{text}", textposition="outside")
    fig.update_layout(title=dict(font=dict(size=20)), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

# --- MAIN APP ---
if uploaded_file is not None:
    try:
        df = load_and_clean(uploaded_file)

        # --- Split into house vs conduct ---
        house_df = df[df["Reward"].str.contains("house", case=False, na=False)]
        conduct_df = df[df["Reward"].str.contains("conduct", case=False, na=False)]

        # --- HOUSE POINTS ANALYSIS ---
        if not house_df.empty:
            st.subheader("🏠 House Points Summary")

            # Staff totals
            staff_house = (
                house_df.groupby("Teacher")["Points"].sum().reset_index()
                .rename(columns={"Points": "House Points This Week"})
            )
            staff_house = PERMANENT_STAFF.merge(staff_house, on="Teacher", how="left").fillna(0)
            staff_house = staff_house.sort_values("House Points This Week", ascending=False)

            # Department totals
            dept_house = (
                house_df.groupby("Dep")["Points"].sum().reset_index()
                .rename(columns={"Points": "House Points"})
            )

            # Top students
            student_house = (
                house_df.groupby(["Pupil Name","Form","Year"])["Points"]
                .sum().reset_index().rename(columns={"Points":"House Points"})
            )

            # House totals
            house_points = house_df.groupby("House")["Points"].sum().reset_index()

            # Form totals (NEW)
            form_house = (
                house_df.groupby(["Form","House"])["Points"].sum().reset_index()
                .rename(columns={"Points":"House Points"})
                .sort_values("House Points", ascending=False)
            )

            # Category frequency
            cat_freq = (
                house_df.groupby("Category")["Points"].count().reset_index()
                .rename(columns={"Points":"Frequency"})
                .sort_values("Frequency", ascending=False)
            )

            # --- CHARTS ---
            col1, col2 = st.columns(2)
            with col1:
                safe_plot(staff_house.head(15), x="Teacher", y="House Points This Week",
                          text="House Points This Week", title="Top 15 Staff (House Points)")
            with col2:
                safe_plot(dept_house, x="Dep", y="House Points", text="House Points",
                          title="House Points by Department")

            col3, col4 = st.columns(2)
            with col3:
                safe_plot(student_house.sort_values("House Points", ascending=False).head(15),
                          x="Pupil Name", y="House Points", text="House Points",
                          title="Top 15 Students (House Points)")
            with col4:
                safe_plot(house_points, x="House", y="Points", text="Points",
                          color="House", color_map=HOUSE_COLORS,
                          title="House Points by House")

            # NEW: House Points by Form
            st.subheader("🏫 House Points by Form")
            safe_plot(form_house, x="Form", y="House Points", text="House Points",
                      color="House", color_map=HOUSE_COLORS, title="House Points by Form")

            st.subheader("📘 House Points Category Frequency")
            safe_plot(cat_freq, x="Category", y="Frequency", text="Frequency",
                      title="House Point Categories Frequency")

        # --- CONDUCT POINTS ANALYSIS ---
        if not conduct_df.empty:
            st.subheader("⚠️ Conduct Points Summary")

            staff_conduct = (
                conduct_df.groupby("Teacher")["Points"].count().reset_index()
                .rename(columns={"Points": "Conduct Points This Week"})
            )
            staff_conduct = PERMANENT_STAFF.merge(staff_conduct, on="Teacher", how="left").fillna(0)
            staff_conduct = staff_conduct.sort_values("Conduct Points This Week", ascending=False)

            dept_conduct = (
                conduct_df.groupby("Dep")["Points"].count().reset_index()
                .rename(columns={"Points": "Conduct Points"})
            )

            house_conduct = (
                conduct_df.groupby("House")["Points"].count().reset_index()
                .rename(columns={"Points": "Conduct Points"})
            )

            # Form totals (NEW)
            form_conduct = (
                conduct_df.groupby(["Form","House"])["Points"].count().reset_index()
                .rename(columns={"Points":"Conduct Points"})
                .sort_values("Conduct Points", ascending=False)
            )

            cat_freq_conduct = (
                conduct_df.groupby("Category")["Points"].count().reset_index()
                .rename(columns={"Points": "Frequency"})
                .sort_values("Frequency", ascending=False)
            )

            col5, col6 = st.columns(2)
            with col5:
                safe_plot(staff_conduct.head(15), x="Teacher", y="Conduct Points This Week",
                          text="Conduct Points This Week", title="Top 15 Staff (Conduct Points)")
            with col6:
                safe_plot(dept_conduct, x="Dep", y="Conduct Points", text="Conduct Points",
                          title="Conduct Points by Department")

            col7, col8 = st.columns(2)
            with col7:
                safe_plot(house_conduct, x="House", y="Conduct Points", text="Conduct Points",
                          color="House", color_map=HOUSE_COLORS,
                          title="Conduct Points by House")
            with col8:
                safe_plot(cat_freq_conduct, x="Category", y="Frequency", text="Frequency",
                          title="Conduct Categories Frequency")

            # NEW: Conduct Points by Form
            st.subheader("🏫 Conduct Points by Form")
            safe_plot(form_conduct, x="Form", y="Conduct Points", text="Conduct Points",
                      color="House", color_map=HOUSE_COLORS, title="Conduct Points by Form")

        # --- WEEKLY STAFF SUMMARY ---
        st.subheader("📅 Weekly Staff Summary (House Points)")
        full_summary = PERMANENT_STAFF.merge(
            staff_house[["Teacher","House Points This Week"]], on="Teacher", how="left"
        ).fillna(0)
        full_summary["On Target (≥15)"] = np.where(
            full_summary["House Points This Week"] >= DEFAULT_WEEKLY_TARGET, "✅ Yes", "⚠️ No"
        )
        st.dataframe(full_summary.sort_values("House Points This Week", ascending=False))

    except Exception as e:
        st.error(f"Error loading CSV: {e}")
else:
    st.info("Please upload your CSV file to begin analysis.")

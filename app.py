import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- CONFIG ---
st.set_page_config(page_title="House & Conduct Points Analysis", layout="wide")
st.title("🏫 House & Conduct Points Analysis Dashboard")
st.write("Upload your weekly CSV file to generate the analysis below.")

# --- SETTINGS ---
DEFAULT_WEEKLY_TARGET = 15
HOUSE_MAPPING = {"B": "Brunel", "L": "Liddell", "D": "Dickens", "W": "Wilberforce"}
HOUSE_COLORS = {"Brunel": "red", "Liddell": "yellow", "Dickens": "blue", "Wilberforce": "purple"}

# --- EMBEDDED STAFF LIST (from Excel Columns A=Initials, B=Dept) ---
STAFF_MASTER = [
    {"Initials": "ABI", "Dep": "English"},
    {"Initials": "ACU", "Dep": "Maths"},
    {"Initials": "ADU", "Dep": "Science"},
    {"Initials": "AGR", "Dep": ""},
    {"Initials": "AJO", "Dep": "PE"},
    {"Initials": "AOR", "Dep": "History"},
    {"Initials": "BBR", "Dep": "Geography"},
    {"Initials": "BKI", "Dep": "Science"},
    {"Initials": "CAR", "Dep": "Art"},
    {"Initials": "CJO", "Dep": "Music"},
    {"Initials": "DWA", "Dep": "History"},
    {"Initials": "EJO", "Dep": "MFL"},
    {"Initials": "EMO", "Dep": "RE"},
    {"Initials": "FMI", "Dep": "Science"},
    {"Initials": "GBA", "Dep": "Maths"},
    {"Initials": "HSA", "Dep": "Pastoral"},
    {"Initials": "JBR", "Dep": "Art"},
    {"Initials": "KSM", "Dep": "Science"},
    {"Initials": "LJO", "Dep": "Pastoral"},
    {"Initials": "MCO", "Dep": "Business"},
    {"Initials": "NPA", "Dep": "Computing"},
    {"Initials": "PFA", "Dep": "English"},
    {"Initials": "RDA", "Dep": "Drama"},
    {"Initials": "RHA", "Dep": "Science"},
    {"Initials": "SBA", "Dep": "PE"},
    {"Initials": "SMI", "Dep": "Geography"},
    {"Initials": "THA", "Dep": "English"},
    {"Initials": "WPO", "Dep": "DT"},
]
staff_df = pd.DataFrame(STAFF_MASTER)
staff_df["Teacher"] = staff_df["Initials"].astype(str).str.upper().str.strip()
staff_df["Dep"] = staff_df["Dep"].astype(str).str.strip()
staff_df = staff_df[["Teacher", "Dep"]].drop_duplicates().reset_index(drop=True)

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

# --- DATA CLEANING ---
def load_and_clean(file):
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()
    expected_columns = [
        "Pupil Name","House","Form","Year","Reward","Category",
        "Points","Date","Reward Description","Teacher","Dep","Subject"
    ]
    df = df.iloc[:, :len(expected_columns)]
    df.columns = expected_columns
    df["Teacher"] = df["Teacher"].astype(str).str.upper().str.strip().replace("", "UNKNOWN")
    df["Dep"] = df["Dep"].astype(str).str.strip()
    df["Reward"] = df["Reward"].astype(str).str.strip().str.lower()
    df["Category"] = df["Category"].astype(str).str.strip().str.lower()
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    df["House"] = df["House"].astype(str).str.strip().str.upper().map(HOUSE_MAPPING).fillna(df["House"])
    return df

# --- SAFE PLOT ---
def safe_plot(data, x, y, title, text=None, orientation="v", color=None, color_map=None):
    if data.empty:
        st.info(f"No data for {title}")
        return
    fig = px.bar(data, x=x, y=y, text=text, orientation=orientation, title=title,
                 color=color, color_discrete_map=color_map)
    fig.update_traces(texttemplate="%{text}", textposition="outside")
    fig.update_layout(title=dict(font=dict(size=20)), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

# --- MAIN APP ---
if uploaded_file is not None:
    try:
        df = load_and_clean(uploaded_file)

        st.subheader("🔍 Data Check")
        st.write("Columns:", df.columns.tolist())
        st.write("Reward values:", df["Reward"].unique())
        st.write("Houses:", df["House"].unique())

        # --- SPLIT HOUSE & CONDUCT ---
        house_df = df[df["Reward"].str.contains("house", case=False, na=False)]
        conduct_df = df[df["Reward"].str.contains("conduct", case=False, na=False)]

        st.write(f"🏠 House rows: {len(house_df)} | ⚠️ Conduct rows: {len(conduct_df)}")

        # --- STAFF AGGREGATES ---
        staff_house = (house_df.groupby("Teacher", as_index=False)["Points"].sum()
                       .rename(columns={"Points": "House Points This Week"})
                       if not house_df.empty else pd.DataFrame(columns=["Teacher", "House Points This Week"]))
        staff_conduct = (conduct_df.groupby("Teacher", as_index=False)["Points"].count()
                         .rename(columns={"Points": "Conduct Points This Week"})
                         if not conduct_df.empty else pd.DataFrame(columns=["Teacher", "Conduct Points This Week"]))
        staff_agg = pd.merge(staff_house, staff_conduct, on="Teacher", how="outer").fillna(0)
        staff_agg["Teacher"] = staff_agg["Teacher"].astype(str).str.upper().str.strip()

        # --- MERGE WITH STAFF MASTER ---
        staff_full = pd.merge(staff_df, staff_agg, on="Teacher", how="left").fillna(0)
        staff_full["House Points This Week"] = pd.to_numeric(staff_full["House Points This Week"], errors="coerce").fillna(0).astype(int)
        staff_full["Conduct Points This Week"] = pd.to_numeric(staff_full["Conduct Points This Week"], errors="coerce").fillna(0).astype(int)
        staff_full["On Target (≥15)"] = np.where(staff_full["House Points This Week"] >= DEFAULT_WEEKLY_TARGET, "✅ Yes", "⚠️ No")

        # --- HOUSE POINTS ---
        if not house_df.empty:
            st.subheader("🏠 House Points Summary")

            staff_house_chart = staff_full.sort_values("House Points This Week", ascending=False)
            dept_house = (staff_full.groupby("Dep", as_index=False)["House Points This Week"].sum()
                          .rename(columns={"House Points This Week": "House Points"}))
            student_house = (house_df.groupby("Pupil Name", as_index=False)["Points"].sum()
                             .rename(columns={"Points": "House Points"}))
            house_points = house_df.groupby("House", as_index=False)["Points"].sum().rename(columns={"Points": "House Points"})
            cat_freq = (house_df.groupby("Category", as_index=False)["Points"].count()
                        .rename(columns={"Points": "Frequency"}).sort_values("Frequency", ascending=False))

            col1, col2 = st.columns(2)
            with col1:
                safe_plot(staff_house_chart.head(15), x="Teacher", y="House Points This Week",
                          text="House Points This Week", title="Top 15 Staff (House Points)")
            with col2:
                safe_plot(dept_house, x="Dep", y="House Points", text="House Points",
                          title="House Points by Department")

            col3, col4 = st.columns(2)
            with col3:
                safe_plot(student_house.head(15), x="Pupil Name", y="House Points",
                          text="House Points", title="Top 15 Students (House Points)")
            with col4:
                safe_plot(house_points, x="House", y="House Points", text="House Points",
                          title="House Points by House", color="House", color_map=HOUSE_COLORS)

            st.subheader("📘 House Points Category Frequency")
            safe_plot(cat_freq, x="Category", y="Frequency", text="Frequency",
                      title="House Point Categories Frequency")

        # --- CONDUCT POINTS ---
        if not conduct_df.empty:
            st.subheader("⚠️ Conduct Points Summary")

            staff_conduct_chart = staff_full.sort_values("Conduct Points This Week", ascending=False)
            dept_conduct = (conduct_df.groupby("Dep", as_index=False)["Points"].count()
                            .rename(columns={"Points": "Conduct Points"}))
            house_conduct = (conduct_df.groupby("House", as_index=False)["Points"].count()
                             .rename(columns={"Points": "Conduct Points"}))
            cat_freq_conduct = (conduct_df.groupby("Category", as_index=False)["Points"].count()
                                .rename(columns={"Points": "Frequency"})
                                .sort_values("Frequency", ascending=False))

            col5, col6 = st.columns(2)
            with col5:
                safe_plot(staff_conduct_chart.head(15), x="Teacher", y="Conduct Points This Week",
                          text="Conduct Points This Week", title="Top 15 Staff (Conduct Points)")
            with col6:
                safe_plot(dept_conduct, x="Dep", y="Conduct Points", text="Conduct Points",
                          title="Conduct Points by Department")

            col7, col8 = st.columns(2)
            with col7:
                safe_plot(house_conduct, x="House", y="Conduct Points", text="Conduct Points",
                          title="Conduct Points by House", color="House", color_map=HOUSE_COLORS)
            with col8:
                safe_plot(cat_freq_conduct, x="Category", y="Frequency", text="Frequency",
                          title="Conduct Categories Frequency")

        # --- STAFF SUMMARY ---
        st.subheader("📅 Weekly Staff Summary (House Points)")
        st.dataframe(staff_full.sort_values("House Points This Week", ascending=False).reset_index(drop=True))

    except Exception as e:
        st.error(f"Error loading CSV: {e}")
else:
    st.info("Please upload your CSV file to begin analysis.")

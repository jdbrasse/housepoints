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

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

# --- DATA CLEANING ---
def load_and_clean(file):
    df = pd.read_csv(file)
    # Strip spaces and explicitly set expected column names
    df.columns = df.columns.str.strip()
    expected_columns = ["Pupil Name","House","Form","Year","Reward","Category","Points","Date","Reward Description","Teacher","Dep","Subject"]
    df.columns = expected_columns

    # Clean and prepare columns
    df["Teacher"] = df["Teacher"].astype(str).str.strip().replace("", "Unknown")
    df["Dep"] = df["Dep"].astype(str).str.strip()
    df["Reward"] = df["Reward"].astype(str).str.strip().str.lower()
    df["Category"] = df["Category"].astype(str).str.strip().str.lower()
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    df["House"] = df["House"].astype(str).str.strip().str.upper().map(HOUSE_MAPPING)
    df["Form"] = df["Form"].astype(str).str.strip()
    df["Year"] = df["Year"].astype(str).str.strip()
    return df

# --- SAFE PLOT FUNCTION ---
def safe_plot(data, x, y, title, text=None, orientation="v"):
    if data.empty:
        st.info(f"No data available for {title}")
        return
    fig = px.bar(data, x=x, y=y, text=text, orientation=orientation, title=title)
    fig.update_traces(texttemplate="%{text}", textposition="outside")
    fig.update_layout(title=dict(font=dict(size=20)), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

# --- MAIN APP ---
if uploaded_file is not None:
    try:
        df = load_and_clean(uploaded_file)

        # --- DEBUGGING ---
        st.subheader("🔍 File Structure Check")
        st.write("Columns detected:", df.columns.tolist())
        st.write("Unique Reward values detected:", df["Reward"].unique())
        st.write("Unique House values detected:", df["House"].unique())

        # --- FILTER HOUSE VS CONDUCT POINTS ---
        house_df = df[df["Reward"].str.contains("house", case=False, na=False)]
        conduct_df = df[df["Reward"].str.contains("conduct", case=False, na=False)]

        st.write(f"🏠 House points rows detected: {len(house_df)}")
        st.write(f"⚠️ Conduct points rows detected: {len(conduct_df)}")

        # --- HOUSE POINTS ANALYSIS ---
        if not house_df.empty:
            st.subheader("🏠 House Points Summary")

            # Staff totals
            staff_house = (
                house_df.groupby("Teacher")["Points"].sum().reset_index().rename(columns={"Points": "House Points This Week"})
            ).sort_values("House Points This Week", ascending=False)

            # Department totals
            dept_house = (
                house_df.groupby("Dep")["Points"].sum().reset_index().rename(columns={"Points": "House Points"})
            )

            # Top students
            student_house = (
                house_df.groupby(["Pupil Name", "Form", "Year"])["Points"]
                .sum().reset_index().rename(columns={"Points": "House Points"})
            )

            # House totals
            house_points = house_df.groupby("House")["Points"].sum().reset_index()

            # Category frequency
            cat_freq = house_df.groupby("Category")["Points"].count().reset_index().rename(columns={"Points": "Frequency"})
            cat_freq = cat_freq.sort_values("Frequency", ascending=False)

            # --- CHARTS ---
            col1, col2 = st.columns(2)
            with col1:
                safe_plot(staff_house.head(15), x="Teacher", y="House Points This Week", text="House Points This Week", title="Top 15 Staff (House Points)")
            with col2:
                safe_plot(dept_house, x="Dep", y="House Points", text="House Points", title="House Points by Department")

            col3, col4 = st.columns(2)
            with col3:
                safe_plot(student_house.sort_values("House Points", ascending=False).head(15), x="Pupil Name", y="House Points", text="House Points", title="Top 15 Students (House Points)")
            with col4:
                safe_plot(house_points, x="House", y="Points", text="Points", title="House Points by House")

            st.subheader("📘 House Points Category Frequency")
            safe_plot(cat_freq, x="Category", y="Frequency", text="Frequency", title="House Point Categories Frequency")

        # --- CONDUCT POINTS ANALYSIS ---
        if not conduct_df.empty:
            st.subheader("⚠️ Conduct Points Summary")

            # Staff totals (count conduct points)
            staff_conduct = (
                conduct_df.groupby("Teacher")["Points"].count().reset_index().rename(columns={"Points": "Conduct Points This Week"})
            ).sort_values("Conduct Points This Week", ascending=False)

            # Department totals
            dept_conduct = (
                conduct_df.groupby("Dep")["Points"].count().reset_index().rename(columns={"Points": "Conduct Points"})
            )

            # House totals
            house_conduct = conduct_df.groupby("House")["Points"].count().reset_index().rename(columns={"Points": "Conduct Points"})

            # Category frequency
            cat_freq_conduct = conduct_df.groupby("Category")["Points"].count().reset_index().rename(columns={"Points": "Frequency"})
            cat_freq_conduct = cat_freq_conduct.sort_values("Frequency", ascending=False)

            # --- CHARTS ---
            col5, col6 = st.columns(2)
            with col5:
                safe_plot(staff_conduct.head(15), x="Teacher", y="Conduct Points This Week", text="Conduct Points This Week", title="Top 15 Staff (Conduct Points)")
            with col6:
                safe_plot(dept_conduct, x="Dep", y="Conduct Points", text="Conduct Points", title="Conduct Points by Department")

            col7, col8 = st.columns(2)
            with col7:
                safe_plot(house_conduct, x="House", y="Conduct Points", text="Conduct Points", title="Conduct Points by House")
            with col8:
                safe_plot(cat_freq_conduct, x="Category", y="Frequency", text="Frequency", title="Conduct Categories Frequency")

        # --- WEEKLY STAFF SUMMARY ---
        st.subheader("📅 Weekly Staff Summary (House Points)")
        if 'staff_house' in locals() and not staff_house.empty:
            staff_summary = staff_house.copy()
            staff_summary["On Target (≥15)"] = np.where(staff_summary["House Points This Week"] >= DEFAULT_WEEKLY_TARGET, "✅ Yes", "⚠️ No")
            st.dataframe(staff_summary)
        else:
            st.info("No house points data available to summarize.")

    except Exception as e:
        st.error(f"Error loading CSV: {e}")
else:
    st.info("Please upload your CSV file to begin analysis.")


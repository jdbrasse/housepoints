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

# --- EMBEDDED STAFF INITIALS (alphabetised list you supplied) ---
PERMANENT_STAFF = pd.DataFrame({
    "Teacher": sorted([
        'ACA','AFO','AHU','AJL','AMA','AMD','APE','AZ','BJH','BW','CAH','CB','CD','CDE','CHO','CL','CLT','CSD','CST',
        'CUG','DB','DBE','DBR','DE','DGU','DJM','DOL','DTA','DWI','EBO','EBO2','ECA','EFO','EMC','EMR','EPO','EPO2',
        'ES','FA','FBA','GCO','GDO','GGR','GME','GSM','HBR','HCU','HEW','HME','HRO','HST','HWA','IMI','IMO','JBA',
        'JBO','JDE','JFO','JHA','JHO','JMA','JMU','JPO','JRO','JSI','JSO','JWA','JWI','KFE','KGR','KMI','KST','LA',
        'LGS','LHO','LHU','LJO','LLI','LMI','LPE','LST','LTA','LTH','MAW','MFI','MMI','MMO','MPO','MPU','MR','MRA',
        'MRO','MSA','NHE','NIQ','NMI','NPE','NSM','POT','RBA','RFI','RGA','RLI','RPO','RRA','RWI','SBR','SCO','SMA',
        'SMI','SSA','SSA2','SSP','SWO','SWA','TDU','TLE','TNE','TSM','VLO','VSB','VT','WRO'
    ])
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

# --- Table header style helper (house-coloured headers) ---
def header_style_for_house(house_name: str):
    bg = HOUSE_COLORS.get(house_name, "#333")
    text_color = "#000000" if house_name == "Liddell" else "#FFFFFF"
    return [{"selector": "th", "props": f"background-color: {bg}; color: {text_color};"}]

# --- Staff highlight helper for weekly summary ---
def highlight_staff_target(row):
    color = "#ccffcc" if row["On Target (≥15)"] == "✅ Yes" else "#ffcccc"
    return [f"background-color: {color}"] * len(row)

# --- MAIN APP ---
if uploaded_file is not None:
    try:
        df = load_and_clean(uploaded_file)

        # Split into house vs conduct
        house_df = df[df["Reward"].str.contains("house", case=False, na=False)]
        conduct_df = df[df["Reward"].str.contains("conduct", case=False, na=False)]

        # -------------------------
        # HOUSE POINTS ANALYSIS
        # -------------------------
        if not house_df.empty:
            st.subheader("🏠 House Points Summary")

            staff_house = (
                house_df.groupby("Teacher")["Points"].sum().reset_index()
                .rename(columns={"Points": "House Points This Week"})
            )
            staff_house = PERMANENT_STAFF.merge(staff_house, on="Teacher", how="left").fillna(0)
            staff_house = staff_house.sort_values("House Points This Week", ascending=False)

            dept_house = (
                house_df.groupby("Dep")["Points"].sum().reset_index()
                .rename(columns={"Points": "House Points"})
            )

            student_house = (
                house_df.groupby(["Pupil Name","Form","Year"])["Points"]
                .sum().reset_index().rename(columns={"Points":"House Points"})
            )

            house_points = house_df.groupby("House")["Points"].sum().reset_index()

            form_house = (
                house_df.groupby(["Form","House"])["Points"].sum().reset_index()
                .rename(columns={"Points":"House Points"})
                .sort_values("House Points", ascending=False)
            )

            cat_freq = (
                house_df.groupby("Category")["Points"].count().reset_index()
                .rename(columns={"Points":"Frequency"})
                .sort_values("Frequency", ascending=False)
            )

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
                fig_house = px.bar(
                    house_points, x="House", y="Points", text="Points",
                    color="House", color_discrete_map=HOUSE_COLORS,
                    title="House Points by House"
                )
                fig_house.update_layout(showlegend=False)
                fig_house.update_traces(texttemplate="%{text}", textposition="outside")
                st.plotly_chart(fig_house, use_container_width=True)

            st.subheader("🏫 House Points by Form")
            fig_form_house = px.bar(
                form_house, x="Form", y="House Points", text="House Points",
                color="House", color_discrete_map=HOUSE_COLORS, title="House Points by Form"
            )
            fig_form_house.update_layout(showlegend=False)
            fig_form_house.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_form_house, use_container_width=True)

            st.subheader("📘 House Points Category Frequency")
            safe_plot(cat_freq, x="Category", y="Frequency", text="Frequency",
                      title="House Point Categories Frequency")

        # -------------------------
        # CONDUCT POINTS ANALYSIS
        # -------------------------
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
                fig_conduct_house = px.bar(
                    house_conduct, x="House", y="Conduct Points", text="Conduct Points",
                    color="House", color_discrete_map=HOUSE_COLORS,
                    title="Conduct Points by House"
                )
                fig_conduct_house.update_layout(showlegend=False)
                fig_conduct_house.update_traces(texttemplate="%{text}", textposition="outside")
                st.plotly_chart(fig_conduct_house, use_container_width=True)
            with col8:
                safe_plot(cat_freq_conduct, x="Category", y="Frequency", text="Frequency",
                          title="Conduct Categories Frequency")

            st.subheader("🏫 Conduct Points by Form")
            fig_form_conduct = px.bar(
                form_conduct, x="Form", y="Conduct Points", text="Conduct Points",
                color="House", color_discrete_map=HOUSE_COLORS, title="Conduct Points by Form"
            )
            fig_form_conduct.update_layout(showlegend=False)
            fig_form_conduct.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_form_conduct, use_container_width=True)

        # -------------------------
        # WEEKLY STAFF SUMMARY (with highlight)
        # -------------------------
        st.subheader("📅 Weekly Staff Summary (House Points)")
        full_summary = PERMANENT_STAFF.merge(
            staff_house[["Teacher","House Points This Week"]], on="Teacher", how="left"
        ).fillna(0)
        full_summary["On Target (≥15)"] = np.where(
            full_summary["House Points This Week"] >= DEFAULT_WEEKLY_TARGET, "✅ Yes", "⚠️ No"
        )
        styled_staff = full_summary.sort_values("House Points This Week", ascending=False).style.apply(
            highlight_staff_target, axis=1
        )
        st.dataframe(styled_staff, use_container_width=True)

        # -------------------------
        # INTERACTIVE LEADERBOARDS (Top 15 overall + Top 10 per house + Top 10 per form)
        # -------------------------
        st.markdown("---")
        st.subheader("🏆 Top Students — Leaderboards")

        lb_type = st.selectbox("Select leaderboard type:", ["House Points", "Conduct Points"])

        if lb_type == "House Points" and not house_df.empty:
            # totals per student
            studs = (
                house_df.groupby(["Pupil Name", "Form", "House"], as_index=False)["Points"].sum()
                .rename(columns={"Points": "House Points"})
            )

            # Top 15 overall
            st.markdown("### 🥇 Top 15 Students — Overall (House Points)")
            top15_hp = studs.sort_values("House Points", ascending=False).head(15)
            st.dataframe(top15_hp[["Pupil Name", "Form", "House", "House Points"]],
                         use_container_width=True)

            # Per House (Top 10)
            st.markdown("### 🏠 Top 10 Students per House (House Points)")
            for house in ["Brunel", "Dickens", "Liddell", "Wilberforce"]:
                hdf = studs[studs["House"] == house].sort_values("House Points", ascending=False).head(10)
                if hdf.empty:
                    continue
                styled = (
                    hdf[["Pupil Name", "Form", "House", "House Points"]]
                    .style.set_table_styles(header_style_for_house(house))
                    .hide(axis="index")
                )
                with st.expander(f"{house} — Top 10"):
                    st.dataframe(styled, use_container_width=True)

            # Per Form (Top 10)
            st.markdown("### 🏫 Top 10 Students per Form (House Points)")
            for form_name, g in studs.groupby("Form"):
                g_sorted = g.sort_values("House Points", ascending=False).head(10)
                # color header by most common house in that form
                house_mode = g["House"].mode().iloc[0] if not g["House"].mode().empty else None
                styled = (
                    g_sorted[["Pupil Name", "Form", "House", "House Points"]]
                    .style.set_table_styles(header_style_for_house(house_mode or ""))
                    .hide(axis="index")
                )
                with st.expander(f"Form {form_name} — Top 10"):
                    st.dataframe(styled, use_container_width=True)

        if lb_type == "Conduct Points" and not conduct_df.empty:
            studs_c = (
                conduct_df.groupby(["Pupil Name", "Form", "House"], as_index=False)["Points"].count()
                .rename(columns={"Points": "Conduct Points"})
            )

            # Top 15 overall
            st.markdown("### 🥇 Top 15 Students — Overall (Conduct Points)")
            top15_cp = studs_c.sort_values("Conduct Points", ascending=False).head(15)
            st.dataframe(top15_cp[["Pupil Name", "Form", "House", "Conduct Points"]],
                         use_container_width=True)

            # Per House (Top 10)
            st.markdown("### 🏠 Top 10 Students per House (Conduct Points)")
            for house in ["Brunel", "Dickens", "Liddell", "Wilberforce"]:
                hdf = studs_c[studs_c["House"] == house].sort_values("Conduct Points", ascending=False).head(10)
                if hdf.empty:
                    continue
                styled = (
                    hdf[["Pupil Name", "Form", "House", "Conduct Points"]]
                    .style.set_table_styles(header_style_for_house(house))
                    .hide(axis="index")
                )
                with st.expander(f"{house} — Top 10"):
                    st.dataframe(styled, use_container_width=True)

            # Per Form (Top 10)
            st.markdown("### 🏫 Top 10 Students per Form (Conduct Points)")
            for form_name, g in studs_c.groupby("Form"):
                g_sorted = g.sort_values("Conduct Points", ascending=False).head(10)
                house_mode = g["House"].mode().iloc[0] if not g["House"].mode().empty else None
                styled = (
                    g_sorted[["Pupil Name", "Form", "House", "Conduct Points"]]
                    .style.set_table_styles(header_style_for_house(house_mode or ""))
                    .hide(axis="index")
                )
                with st.expander(f"Form {form_name} — Top 10"):
                    st.dataframe(styled, use_container_width=True)

        if lb_type == "House Points" and house_df.empty:
            st.info("No house points available for leaderboards.")
        if lb_type == "Conduct Points" and conduct_df.empty:
            st.info("No conduct points available for leaderboards.")

    except Exception as e:
        st.error(f"Error loading CSV: {e}")
else:
    st.info("Please upload your CSV file to begin analysis.")

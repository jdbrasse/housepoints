import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- CONFIG ---
st.set_page_config(page_title="House & Conduct Points Analysis", layout="wide")
st.title("🏫 House & Conduct Points Analysis Dashboard")
st.write("Upload your weekly CSV file below to generate the full analysis.")

# --- HOUSE & COLOUR SETTINGS ---
DEFAULT_WEEKLY_TARGET = 15
HOUSE_MAPPING = {"B": "Brunel", "L": "Liddell", "D": "Dickens", "W": "Wilberforce"}
HOUSE_COLORS = {"Brunel": "#FF0000", "Dickens": "#0000FF", "Liddell": "#FFD700", "Wilberforce": "#800080"}
HOUSE_DOT = {"Brunel": "🔴", "Dickens": "🔵", "Liddell": "🟡", "Wilberforce": "🟣"}

# --- SIDEBAR ---
with st.sidebar:
    target_input = st.number_input(
        "Weekly House Points Target",
        min_value=1,
        value=DEFAULT_WEEKLY_TARGET,
        step=1
    )

# --- EMBEDDED STAFF LIST (alphabetised from your uploaded Excel) ---
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

# --- STYLE HELPERS ---
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

def header_style_for_house(house_name: str):
    bg = HOUSE_COLORS.get(house_name, "#333")
    text_color = "#000000" if house_name == "Liddell" else "#FFFFFF"
    return [{"selector": "th", "props": f"background-color: {bg}; color: {text_color};"}]

def highlight_staff_target(row):
    color = "#ccffcc" if row["On Target (≥Target)"] == "✅ Yes" else "#ffcccc"
    return [f"background-color: {color}"] * len(row)

# --- MAIN APP ---
if uploaded_file is not None:
    try:
        df = load_and_clean(uploaded_file)
        df["Teacher"] = df["Teacher"].where(df["Teacher"].isin(PERMANENT_STAFF["Teacher"]), other=np.nan)

        # Separate house and conduct data
        house_df = df[df["Reward"].str.contains("house", case=False, na=False)].copy()
        conduct_df = df[df["Reward"].str.contains("conduct", case=False, na=False)].copy()

        # --- HOUSE POINTS SECTION ---
        st.subheader("🏠 House Points Summary")

        staff_house = (
            house_df.groupby("Teacher", dropna=True)["Points"].sum().reset_index()
            .rename(columns={"Points": "House Points This Week"})
        ) if not house_df.empty else pd.DataFrame(columns=["Teacher", "House Points This Week"])

        staff_house = PERMANENT_STAFF.merge(staff_house, on="Teacher", how="left").fillna(0)
        staff_house["House Points This Week"] = staff_house["House Points This Week"].astype(int)
        staff_house = staff_house.sort_values("House Points This Week", ascending=False)

        dept_house = (
            house_df.groupby("Dep")["Points"].sum().reset_index().rename(columns={"Points": "House Points"})
        ) if not house_df.empty else pd.DataFrame(columns=["Dep", "House Points"])

        student_house = (
            house_df.groupby(["Pupil Name", "Form", "Year"])["Points"]
            .sum().reset_index().rename(columns={"Points": "House Points"})
        ) if not house_df.empty else pd.DataFrame(columns=["Pupil Name", "Form", "Year", "House Points"])

        house_points = (
            house_df.groupby("House")["Points"].sum().reset_index()
        ) if not house_df.empty else pd.DataFrame(columns=["House", "Points"])

        form_house = (
            house_df.groupby(["Form", "House"])["Points"].sum().reset_index()
            .rename(columns={"Points": "House Points"}).sort_values("House Points", ascending=False)
        ) if not house_df.empty else pd.DataFrame(columns=["Form", "House", "House Points"])

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

        # --- CONDUCT POINTS SECTION ---
        st.subheader("⚠️ Conduct Points Summary")
        staff_conduct = (
            conduct_df.groupby("Teacher", dropna=True)["Points"].count().reset_index()
            .rename(columns={"Points": "Conduct Points This Week"})
        ) if not conduct_df.empty else pd.DataFrame(columns=["Teacher", "Conduct Points This Week"])

        staff_conduct = PERMANENT_STAFF.merge(staff_conduct, on="Teacher", how="left").fillna(0)
        staff_conduct["Conduct Points This Week"] = staff_conduct["Conduct Points This Week"].astype(int)
        staff_conduct = staff_conduct.sort_values("Conduct Points This Week", ascending=False)

        dept_conduct = (
            conduct_df.groupby("Dep")["Points"].count().reset_index().rename(columns={"Points": "Conduct Points"})
        ) if not conduct_df.empty else pd.DataFrame(columns=["Dep", "Conduct Points"])

        house_conduct = (
            conduct_df.groupby("House")["Points"].count().reset_index().rename(columns={"Points": "Conduct Points"})
        ) if not conduct_df.empty else pd.DataFrame(columns=["House", "Conduct Points"])

        form_conduct = (
            conduct_df.groupby(["Form", "House"])["Points"].count().reset_index()
            .rename(columns={"Points": "Conduct Points"}).sort_values("Conduct Points", ascending=False)
        ) if not conduct_df.empty else pd.DataFrame(columns=["Form", "House", "Conduct Points"])

        st.subheader("🏫 Conduct Points by Form")
        fig_form_conduct = px.bar(
            form_conduct, x="Form", y="Conduct Points", text="Conduct Points",
            color="House", color_discrete_map=HOUSE_COLORS, title="Conduct Points by Form"
        )
        fig_form_conduct.update_layout(showlegend=False)
        fig_form_conduct.update_traces(texttemplate="%{text}", textposition="outside")
        st.plotly_chart(fig_form_conduct, use_container_width=True)

        # --- LEADERBOARDS ---
        st.markdown("---")
        st.subheader("🏆 Top Students — Leaderboards")

        lb_type = st.selectbox("Select leaderboard type:", ["House Points", "Conduct Points"])

        if lb_type == "House Points" and not house_df.empty:
            studs = (
                house_df.groupby(["Pupil Name", "Form", "House"], as_index=False)["Points"].sum()
                .rename(columns={"Points": "House Points"})
            )

            st.markdown("### 🥇 Top 15 Students — Overall (House Points)")
            top15_hp = studs.sort_values("House Points", ascending=False).head(15)
            st.dataframe(top15_hp[["Pupil Name", "Form", "House", "House Points"]], use_container_width=True)

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
                with st.expander(f"{HOUSE_DOT[house]} {house} — Top 10"):
                    st.dataframe(styled, use_container_width=True)

            st.markdown("### 🏫 Top 10 Students per Form (House Points)")
            for form_name, g in studs.groupby("Form"):
                g_sorted = g.sort_values("House Points", ascending=False).head(10)
                house_mode = g["House"].mode().iloc[0] if not g["House"].mode().empty else None
                display_title = f"{HOUSE_DOT.get(house_mode, '')} Form {form_name} — Top 10"
                styled = (
                    g_sorted[["Pupil Name", "Form", "House", "House Points"]]
                    .style.set_table_styles(header_style_for_house(house_mode or ''))
                    .hide(axis="index")
                )
                with st.expander(display_title):
                    st.dataframe(styled, use_container_width=True)

        elif lb_type == "Conduct Points" and not conduct_df.empty:
            studs_c = (
                conduct_df.groupby(["Pupil Name", "Form", "House"], as_index=False)["Points"].count()
                .rename(columns={"Points": "Conduct Points"})
            )

            st.markdown("### 🥇 Top 15 Students — Overall (Conduct Points)")
            top15_cp = studs_c.sort_values("Conduct Points", ascending=False).head(15)
            st.dataframe(top15_cp[["Pupil Name", "Form", "House", "Conduct Points"]], use_container_width=True)

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
                with st.expander(f"{HOUSE_DOT[house]} {house} — Top 10"):
                    st.dataframe(styled, use_container_width=True)

            st.markdown("### 🏫 Top 10 Students per Form (Conduct Points)")
            for form_name, g in studs_c.groupby("Form"):
                g_sorted = g.sort_values("Conduct Points", ascending=False).head(10)
                house_mode = g["House"].mode().iloc[0] if not g["House"].mode().empty else None
                display_title = f"{HOUSE_DOT.get(house_mode, '')} Form {form_name} — Top 10"
                styled = (
                    g_sorted[["Pupil Name", "Form", "House", "Conduct Points"]]
                    .style.set_table_styles(header_style_for_house(house_mode or ''))
                    .hide(axis="index")
                )
                with st.expander(display_title):
                    st.dataframe(styled, use_container_width=True)

        # --- STAFF SUMMARY ---
        st.markdown("---")
        st.subheader("📅 Weekly Staff Summary (House Points)")
        summary_df = PERMANENT_STAFF.merge(
            staff_house[["Teacher", "House Points This Week"]], on="Teacher", how="left"
        ).fillna(0)
        summary_df["House Points This Week"] = summary_df["House Points This Week"].astype(int)
        summary_df["On Target (≥Target)"] = np.where(
            summary_df["House Points This Week"] >= int(target_input), "✅ Yes", "⚠️ No"
        )
        styled_staff = summary_df.sort_values("House Points This Week", ascending=False).style.apply(
            highlight_staff_target, axis=1
        )
        st.dataframe(styled_staff, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading CSV: {e}")

else:
    st.info("Please upload your CSV file to begin analysis.")

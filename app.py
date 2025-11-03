import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- CONFIG ---
st.set_page_config(page_title="House & Conduct Points Analysis", layout="wide")
st.title("🏫 House & Conduct Points Analysis Dashboard")
st.write("Upload your weekly CSV file below to generate the full analysis.")

# --- HOUSE SETTINGS ---
DEFAULT_WEEKLY_TARGET = 15
HOUSE_MAPPING = {"B": "Brunel", "L": "Liddell", "D": "Dickens", "W": "Wilberforce"}
HOUSE_COLORS = {"Brunel": "#FF0000", "Dickens": "#0000FF", "Liddell": "#FFD700", "Wilberforce": "#800080"}
HOUSE_DOT = {"Brunel": "🔴", "Dickens": "🔵", "Liddell": "🟡", "Wilberforce": "🟣"}

# --- SIDEBAR ---
with st.sidebar:
    target_input = st.number_input("Weekly House Points Target", min_value=1, value=DEFAULT_WEEKLY_TARGET, step=1)
    st.markdown("### 🎨 House Colours")
    for house, color in HOUSE_COLORS.items():
        st.markdown(
            f"<div style='background-color:{color};padding:4px;border-radius:4px;color:white;text-align:center;'>{HOUSE_DOT[house]} {house}</div>",
            unsafe_allow_html=True,
        )

# --- EMBEDDED STAFF LIST (alphabetised) ---
PERMANENT_STAFF = pd.DataFrame({
    "Teacher": sorted([
        'ACA','AFO','AHU','AJL','AMA','AMD','APE','AZ','BJH','BW','CAH','CB','CD','CDE','CHO','CL','CLT','CSD','CST',
        'CUG','DBE','DE','DHY','DLE','DO','DOD','DOL','DRO','DS','DSI','DYH','EFK','EM','EN','EP','EPO','EWH','FA',
        'FRO','GM','GP','HW','IMO','JBR','JCH','JDA','JFA','JHO','JJO','JMA','JMO','JMU','JP','JS','JSA','JSI',
        'KPR','KZI','LBL','LGS','LH','LHO','LJO','LTA','LTH','LVI','MBR','MH','MJ','MLO','MO','MP','MPA','MPN','MPU',
        'NIQ','NPE','NR','NWI','OE','OTH','PHA','POT','PWH','RA','RC','RCO','RLP','RMA','SAB','SBA','SBR','SEE','SH',
        'SPE','SXS','TFU','TNE','TP','TQ','TRA','VM','VSB','VT','WA','WTM'
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

# --- STYLES & HELPERS ---
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

def house_banner(text: str, house: str):
    color = HOUSE_COLORS.get(house, "#444")
    fg = "#000000" if house == "Liddell" else "#FFFFFF"
    st.markdown(
        f"<div style='background-color:{color};padding:6px 10px;border-radius:6px;color:{fg};font-weight:600'>{text}</div>",
        unsafe_allow_html=True,
    )

# --- MAIN APP ---
if uploaded_file is not None:
    try:
        df = load_and_clean(uploaded_file)
        df["Teacher"] = df["Teacher"].where(df["Teacher"].isin(PERMANENT_STAFF["Teacher"]), other=np.nan)
        house_df = df[df["Reward"].str.contains("house", case=False, na=False)]
        conduct_df = df[df["Reward"].str.contains("conduct", case=False, na=False)]

        # =========================
        # 🏠 HOUSE POINTS SUMMARY
        # =========================
        st.subheader("🏠 House Points Summary")

        staff_house = PERMANENT_STAFF.merge(
            house_df.groupby("Teacher")["Points"].sum().reset_index().rename(columns={"Points":"House Points This Week"}),
            on="Teacher", how="left"
        ).fillna(0)
        staff_house["House Points This Week"] = staff_house["House Points This Week"].astype(int)
        staff_house = staff_house.sort_values("House Points This Week", ascending=False)

        student_house = house_df.groupby(["Pupil Name","Form","Year","House"])["Points"].sum().reset_index().rename(columns={"Points":"House Points"})
        house_points = house_df.groupby("House")["Points"].sum().reset_index()
        form_house = house_df.groupby(["Form","House"])["Points"].sum().reset_index().rename(columns={"Points":"House Points"})

        col1, col2 = st.columns(2)
        with col1:
            safe_plot(staff_house.head(15), "Teacher", "House Points This Week", "Top 15 Staff (House Points)", "House Points This Week")
        with col2:
            safe_plot(student_house.sort_values("House Points", ascending=False).head(15),
                      "Pupil Name", "House Points", "Top 15 Students (House Points)", "House Points", color="House", color_map=HOUSE_COLORS)

        col3, col4 = st.columns(2)
        with col3:
            safe_plot(house_points, "House", "Points", "House Points by House", "Points", color="House", color_map=HOUSE_COLORS)
        with col4:
            safe_plot(form_house, "Form", "House Points", "House Points by Form", "House Points", color="House", color_map=HOUSE_COLORS)

        # =========================
        # ⚠️ CONDUCT POINTS SUMMARY
        # =========================
        st.subheader("⚠️ Conduct Points Summary")

        staff_conduct = PERMANENT_STAFF.merge(
            conduct_df.groupby("Teacher")["Points"].count().reset_index().rename(columns={"Points":"Conduct Points This Week"}),
            on="Teacher", how="left"
        ).fillna(0)
        staff_conduct["Conduct Points This Week"] = staff_conduct["Conduct Points This Week"].astype(int)
        staff_conduct = staff_conduct.sort_values("Conduct Points This Week", ascending=False)

        studs_c = conduct_df.groupby(["Pupil Name","Form","House"])["Points"].count().reset_index().rename(columns={"Points":"Conduct Points"})
        form_conduct = conduct_df.groupby(["Form","House"])["Points"].count().reset_index().rename(columns={"Points":"Conduct Points"})

        col5, col6 = st.columns(2)
        with col5:
            safe_plot(staff_conduct.head(15), "Teacher", "Conduct Points This Week", "Top 15 Staff (Conduct Points)", "Conduct Points This Week")
        with col6:
            safe_plot(studs_c.sort_values("Conduct Points", ascending=False).head(15),
                      "Pupil Name", "Conduct Points", "Top 15 Students (Conduct Points)", "Conduct Points", color="House", color_map=HOUSE_COLORS)

        safe_plot(form_conduct, "Form", "Conduct Points", "Conduct Points by Form", "Conduct Points", color="House", color_map=HOUSE_COLORS)

        # =========================
        # 🏆 LEADERBOARDS
        # =========================
        st.markdown("---")
        st.subheader("🏆 Student Leaderboards")

        lb_type = st.selectbox("Select leaderboard type:", ["House Points", "Conduct Points"])

        if lb_type == "House Points":
            studs = house_df.groupby(["Pupil Name","Form","House"], as_index=False)["Points"].sum().rename(columns={"Points":"House Points"})
            st.markdown("### 🥇 Top 15 Students — Overall (House Points)")
            st.dataframe(studs.sort_values("House Points", ascending=False).head(15), use_container_width=True)

            st.markdown("### 🏠 Top 10 Students per House (House Points)")
            for house in HOUSE_MAPPING.values():
                hdf = studs[studs["House"] == house].sort_values("House Points", ascending=False).head(10)
                if not hdf.empty:
                    with st.expander(f"{HOUSE_DOT[house]} {house} — Top 10"):
                        styled = hdf[["Pupil Name","Form","House","House Points"]].style.set_table_styles(header_style_for_house(house)).hide(axis="index")
                        st.dataframe(styled, use_container_width=True)

            st.markdown("### 🏫 Top 10 Students per Form (House Points)")
            for form, g in studs.groupby("Form"):
                g_sorted = g.sort_values("House Points", ascending=False).head(10)
                house_mode = g["House"].mode().iloc[0] if not g["House"].mode().empty else ""
                with st.expander(f"{HOUSE_DOT.get(house_mode,'')} {house_mode} — Form {form}"):
                    styled = g_sorted[["Pupil Name","Form","House","House Points"]].style.set_table_styles(header_style_for_house(house_mode)).hide(axis="index")
                    st.dataframe(styled, use_container_width=True)

        else:
            st.markdown("### 🥇 Top 15 Students — Overall (Conduct Points)")
            st.dataframe(studs_c.sort_values("Conduct Points", ascending=False).head(15), use_container_width=True)

            st.markdown("### 🏠 Top 10 Students per House (Conduct Points)")
            for house in HOUSE_MAPPING.values():
                hdf = studs_c[studs_c["House"] == house].sort_values("Conduct Points", ascending=False).head(10)
                if not hdf.empty:
                    with st.expander(f"{HOUSE_DOT[house]} {house} — Top 10"):
                        styled = hdf[["Pupil Name","Form","House","Conduct Points"]].style.set_table_styles(header_style_for_house(house)).hide(axis="index")
                        st.dataframe(styled, use_container_width=True)

            st.markdown("### 🏫 Top 10 Students per Form (Conduct Points)")
            for form, g in studs_c.groupby("Form"):
                g_sorted = g.sort_values("Conduct Points", ascending=False).head(10)
                house_mode = g["House"].mode().iloc[0] if not g["House"].mode().empty else ""
                with st.expander(f"{HOUSE_DOT.get(house_mode,'')} {house_mode} — Form {form}"):
                    styled = g_sorted[["Pupil Name","Form","House","Conduct Points"]].style.set_table_styles(header_style_for_house(house_mode)).hide(axis="index")
                    st.dataframe(styled, use_container_width=True)

        # =========================
        # 👩‍🏫 STAFF SUMMARY
        # =========================
        st.markdown("---")
        st.subheader("📅 Weekly Staff Summary (House Points)")
        summary_df = PERMANENT_STAFF.merge(staff_house[["Teacher","House Points This Week"]], on="Teacher", how="left").fillna(0)
        summary_df["House Points This Week"] = summary_df["House Points This Week"].astype(int)
        summary_df["On Target (≥Target)"] = np.where(summary_df["House Points This Week"] >= int(target_input), "✅ Yes", "⚠️ No")
        styled_staff = summary_df.sort_values("House Points This Week", ascending=False).style.apply(highlight_staff_target, axis=1)
        st.dataframe(styled_staff, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading CSV: {e}")
else:
    st.info("Please upload your CSV file to begin analysis.")

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from PIL import Image

# -----------------------
# App configuration & style
# -----------------------
st.set_page_config(page_title="House Points Tracker", layout="wide")
st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# Constants
# -----------------------
HOUSE_COLOURS = {
    "B": "red",          # Brunel
    "L": "yellow",       # Liddell
    "D": "blue",         # Dickens
    "W": "purple"        # Wilberforce
}
EXPECTED_COLS = [
    "Pupil Name","House","Form","Year","Reward","Category","Points",
    "Date","Reward Description","Teacher","Dept","Subject","Email"
]

# -----------------------
# Optional logo
# -----------------------
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

# -----------------------
# Functions
# -----------------------
def load_and_clean(uploaded, week_label):
    df = pd.read_csv(uploaded, dtype=str)
    if len(df.columns) == len(EXPECTED_COLS):
        df.columns = EXPECTED_COLS
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0).astype(int)
    df["Category"] = df["Category"].astype(str).str.title()
    df["House"] = df["House"].astype(str).str.strip().str.upper()
    df["Form"] = df["Form"].astype(str).str.strip().str.upper()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Week"] = week_label
    return df

def detect_point_types(df):
    house_mask = df["Category"].str.contains("house|reward", case=False, na=False)
    conduct_mask = df["Category"].str.contains("conduct|behaviour", case=False, na=False)
    if not house_mask.any() and not conduct_mask.any():
        house_mask = df["Points"] > 0
        conduct_mask = df["Points"] < 0
    return house_mask, conduct_mask

# -----------------------
# Sidebar
# -----------------------
st.sidebar.header("⚙️ Settings")
week_label = st.sidebar.text_input("Week label", value=datetime.now().strftime("%Y-%m-%d"))
uploaded = st.sidebar.file_uploader("📤 Upload weekly CSV", type=["csv"])

# -----------------------
# Main
# -----------------------
st.title("🏫 Weekly House & Conduct Dashboard")

if uploaded:
    df = load_and_clean(uploaded, week_label)
    st.success(f"Loaded {len(df):,} records for {week_label}")

    house_mask, conduct_mask = detect_point_types(df)
    house_df = df[house_mask].copy()
    conduct_df = df[conduct_mask].copy()
    conduct_df["Points"] = conduct_df["Points"].abs()

    # ===== 1️⃣ House & Conduct charts side-by-side =====
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏠 House Points by House")
        house_totals = house_df.groupby("House", as_index=False)["Points"].sum().sort_values("Points", ascending=False)
        if not house_totals.empty:
            fig_house = px.bar(
                house_totals, x="House", y="Points",
                color="House", color_discrete_map=HOUSE_COLOURS,
                text="Points", title="Total House Points"
            )
            fig_house.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_house, use_container_width=True)

    with col2:
        st.subheader("⚠️ Conduct Points by House (Lower = Better)")
        conduct_totals = conduct_df.groupby("House", as_index=False)["Points"].sum().sort_values("Points")
        if not conduct_totals.empty:
            fig_conduct = px.bar(
                conduct_totals, x="Points", y="House",
                color="House", color_discrete_map=HOUSE_COLOURS,
                orientation="h", text="Points", title="Total Conduct Points"
            )
            fig_conduct.update_traces(texttemplate="%{text}", textposition="outside")
            fig_conduct.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_conduct, use_container_width=True)

    # ===== 2️⃣ Top Forms per House (side-by-side with Net Points) =====
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("🏫 Top Performing Forms per House")
        form_points = house_df.groupby(["House","Form"], as_index=False)["Points"].sum()
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

    with col4:
        st.subheader("🏆 Net Points by House (House − Conduct)")
        net_df = pd.merge(
            house_totals, conduct_totals, on="House", how="outer",
            suffixes=("_House", "_Conduct")
        ).fillna(0)
        net_df["Net Points"] = net_df["Points_House"] - net_df["Points_Conduct"]
        net_df = net_df.sort_values("Net Points", ascending=False)
        if not net_df.empty:
            fig_net = px.bar(
                net_df, x="Net Points", y="House",
                color="House", color_discrete_map=HOUSE_COLOURS,
                orientation="h", text="Net Points",
                title="Overall Net Points by House"
            )
            fig_net.update_traces(texttemplate="%{text}", textposition="outside")
            st.plotly_chart(fig_net, use_container_width=True)
else:
    st.info("👆 Upload your weekly CSV file in the sidebar to generate the dashboard.")

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from PIL import Image

# -----------------------
# App configuration & style
# -----------------------
st.set_page_config(page_title="House Points Dashboard", layout="wide")
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
# Helper functions
# -----------------------
def load_and_clean(uploaded, week_label):
    df = pd.read_csv(uploaded, dtype=str)
    if len(df.columns) == len(EXPECTED_COLS):
        df.columns = EXPECTED

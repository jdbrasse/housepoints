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
    # Add more as needed 👇
    {"Teacher": "George White", "Dept": "Geography"},
    {"Teacher": "Hannah Black", "Dept": "Computing"},
]

# -----------------------
# Display School Logo
# -----------------------
try:
    logo = Image.open("logo.png")  # Ensure logo.png is in repo root
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
    staff_conduct = conduct_df

from pathlib import Path

import pandas as pd
import streamlit as st

from sen_dashboard.constants import DATE_COLUMN


# Load, clean and chronologically sort the data from the CSV file
@st.cache_data
def load_data(file_path: Path) -> pd.DataFrame:

    data = pd.read_csv(file_path, encoding="utf-8-sig")

    # Convert the date column to datetime format
    data[DATE_COLUMN] = pd.to_datetime(
        data[DATE_COLUMN],
        format="%d-%m-%Y %H:%M:%S",
        errors="coerce",
    )

    # Drop rows with missing or duplicate date values, and sort the data by date
    data = data.dropna(subset=[DATE_COLUMN])
    data = data.sort_values(DATE_COLUMN)

    return data


# returns the data for the selected date
def get_daily_data(data: pd.DataFrame, selected_date) -> pd.DataFrame:
    return data[data[DATE_COLUMN].dt.date == selected_date].copy()

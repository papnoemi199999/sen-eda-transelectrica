from pathlib import Path

import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).parent / "Grafic_SEN (1)(Grafic SEN).csv"
DATE_COLUMN = "Data"
SOLAR_COLUMN = "Foto[MW]"
WIND_COLUMN = "Eolian[MW]"
PRODUCTION_COLUMN = "Productie[MW]"

# Loand and prepare data from the CSV file
@st.cache_data  # streamlit stores data in a cache to avoid reloading it on every rerun. The cache is cleared when the file changes
def load_data(file_path: Path) -> pd.DataFrame:
    data = pd.read_csv(file_path, encoding="utf-8-sig")
    data[DATE_COLUMN] = pd.to_datetime(
        data[DATE_COLUMN],
        format="%d-%m-%Y %H:%M:%S",
        errors="coerce",
    )

    # Drop rows with missing or duplicate timestamps, and sort by timestamp.
    data = data.dropna(subset=[DATE_COLUMN])
    data = data.drop_duplicates().sort_values(DATE_COLUMN)

    # Small negative values are measurement noise, not negative production.
    data[[SOLAR_COLUMN, WIND_COLUMN]] = data[
        [SOLAR_COLUMN, WIND_COLUMN]
    ].clip(lower=0)

    return data


# Filter data for the selected date
def get_daily_data(data: pd.DataFrame, selected_date) -> pd.DataFrame:
    return data[data[DATE_COLUMN].dt.date == selected_date].copy()


def main() -> None:
    st.set_page_config(
        page_title="SEN – Solar & Eolian",
        page_icon="⚡",
        layout="wide",
    )

    st.title("Solar & Eolian – profil zilnic")
    st.write(
        "Selectează o zi pentru a vedea evoluția producției solare și eoliene."
    )

    try:
        data = load_data(DATA_FILE)
    except FileNotFoundError:
        st.error(f"Fișierul de date nu a fost găsit: {DATA_FILE.name}")
        st.stop()

    # Date selection and total production option
    selected_date = st.date_input(
        "Data analizată",
        value=data[DATE_COLUMN].dt.date.min(),
        min_value=data[DATE_COLUMN].dt.date.min(),
        max_value=data[DATE_COLUMN].dt.date.max(),
    )
    show_total_production = st.checkbox("Afișează producția totală")

    daily_data = get_daily_data(data, selected_date)
    if daily_data.empty:
        st.warning("Nu există date pentru ziua selectată.")
        st.stop()

    chart_columns = [SOLAR_COLUMN, WIND_COLUMN]
    if show_total_production:
        chart_columns.append(PRODUCTION_COLUMN)

    chart_data = daily_data[[DATE_COLUMN, *chart_columns]].rename(
        columns={
            SOLAR_COLUMN: "Solar",
            WIND_COLUMN: "Eolian",
            PRODUCTION_COLUMN: "Producție totală",
        }
    )

    st.subheader(f"Profilul zilei de {selected_date:%d.%m.%Y}")
    st.line_chart(
        chart_data,
        x=DATE_COLUMN,
        y=[column for column in chart_data.columns if column != DATE_COLUMN],
        x_label="Ora",
        y_label="Putere (MW)",
        height=500,
    )

    st.caption(
        f"{len(daily_data)} măsurători disponibile pentru ziua selectată."
    )


if __name__ == "__main__":
    main()

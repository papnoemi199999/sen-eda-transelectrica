from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).parent / "Grafic_SEN (1)(Grafic SEN).csv"
DATE_COLUMN = "Data"
SOLAR_COLUMN = "Foto[MW]"
WIND_COLUMN = "Eolian[MW]"
PRODUCTION_COLUMN = "Productie[MW]"

CHART_SERIES = ["Solar", "Eolian", "Producție totală"]
CHART_COLORS = ["#F2C94C", "#2F80ED", "#219653"]


@st.cache_data
def load_data(file_path: Path) -> pd.DataFrame:
    """Load and prepare the SEN data used by the daily chart."""
    data = pd.read_csv(file_path, encoding="utf-8-sig")
    data[DATE_COLUMN] = pd.to_datetime(
        data[DATE_COLUMN],
        format="%d-%m-%Y %H:%M:%S",
        errors="coerce",
    )

    data = data.dropna(subset=[DATE_COLUMN])
    data = data.drop_duplicates().sort_values(DATE_COLUMN)

    # Small negative values are measurement noise, not negative production.
    data[[SOLAR_COLUMN, WIND_COLUMN]] = data[
        [SOLAR_COLUMN, WIND_COLUMN]
    ].clip(lower=0)

    return data


def get_daily_data(data: pd.DataFrame, selected_date) -> pd.DataFrame:
    """Return all measurements recorded on the selected calendar day."""
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

    chart_data = chart_data.melt(
        id_vars=DATE_COLUMN,
        var_name="Sursă",
        value_name="Putere (MW)",
    )
    y_axis_max = data[PRODUCTION_COLUMN].max() * 1.05

    chart = (
        alt.Chart(chart_data)
        .mark_line()
        .encode(
            x=alt.X(f"{DATE_COLUMN}:T", title="Ora"),
            y=alt.Y(
                "Putere (MW):Q",
                title="Putere (MW)",
                scale=alt.Scale(domain=[0, y_axis_max]),
            ),
            color=alt.Color(
                "Sursă:N",
                title="Sursă",
                scale=alt.Scale(
                    domain=CHART_SERIES,
                    range=CHART_COLORS,
                ),
            ),
            tooltip=[
                alt.Tooltip(f"{DATE_COLUMN}:T", title="Ora", format="%H:%M"),
                alt.Tooltip("Sursă:N", title="Sursă"),
                alt.Tooltip("Putere (MW):Q", title="Putere", format=",.0f"),
            ],
        )
        .properties(height=500)
    )

    st.subheader(f"Profilul zilei de {selected_date:%d.%m.%Y}")
    st.altair_chart(chart, use_container_width=True)

    st.caption(
        f"{len(daily_data)} măsurători disponibile pentru ziua selectată."
    )


if __name__ == "__main__":
    main()

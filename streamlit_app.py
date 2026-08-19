from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).parent / "Grafic_SEN (1)(Grafic SEN).csv"
DATE_COLUMN = "Data"
SOLAR_COLUMN = "Foto[MW]"
WIND_COLUMN = "Eolian[MW]"
PRODUCTION_COLUMN = "Productie[MW]"
SHARE_COLUMN = "Pondere regenerabile (%)"

CHART_SERIES = ["Solar", "Eolian", "Producție totală"]
CHART_COLORS = ["#F2C94C", "#2F80ED", "#219653"]

SEASON_COLUMN = "Sezon"
HOUR_COLUMN = "Ora"
SEASON_ORDER = ["Iarnă", "Primăvară", "Vară", "Toamnă"]
SEASON_COLORS = ["#2F80ED", "#27AE60", "#F2C94C", "#B5651D"]
SEASON_BY_MONTH = {
    1: "Iarnă",
    2: "Iarnă",
    3: "Primăvară",
    4: "Primăvară",
    5: "Primăvară",
    6: "Vară",
    7: "Vară",
    8: "Vară",
    9: "Toamnă",
    10: "Toamnă",
    11: "Toamnă",
    12: "Iarnă",
}


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


def calculate_daily_metrics(daily_data: pd.DataFrame) -> dict:
    """Calculate the main solar and wind indicators for one day."""
    solar_peak_index = daily_data[SOLAR_COLUMN].idxmax()
    wind_peak_index = daily_data[WIND_COLUMN].idxmax()

    combined_production = daily_data[SOLAR_COLUMN] + daily_data[WIND_COLUMN]
    combined_peak_index = combined_production.idxmax()

    return {
        "solar_peak": daily_data.loc[solar_peak_index, SOLAR_COLUMN],
        "solar_peak_time": daily_data.loc[solar_peak_index, DATE_COLUMN],
        "wind_average": daily_data[WIND_COLUMN].mean(),
        "wind_peak": daily_data.loc[wind_peak_index, WIND_COLUMN],
        "combined_peak": combined_production.loc[combined_peak_index],
        "combined_peak_time": daily_data.loc[combined_peak_index, DATE_COLUMN],
        "measurement_count": len(daily_data),
    }


def calculate_hourly_renewable_share(daily_data: pd.DataFrame) -> pd.DataFrame:
    """Calculate the hourly solar and wind share of total production."""
    hourly_data = (
        daily_data.set_index(DATE_COLUMN)[
            [SOLAR_COLUMN, WIND_COLUMN, PRODUCTION_COLUMN]
        ]
        .resample("1h")
        .mean()
    )

    renewable_production = (
        hourly_data[SOLAR_COLUMN] + hourly_data[WIND_COLUMN]
    )
    total_production = hourly_data[PRODUCTION_COLUMN].where(
        hourly_data[PRODUCTION_COLUMN] != 0
    )
    hourly_data[SHARE_COLUMN] = renewable_production / total_production * 100

    return hourly_data.dropna(subset=[SHARE_COLUMN]).reset_index()


def calculate_daily_renewable_share(hourly_data: pd.DataFrame) -> float:
    """Calculate the solar and wind share for the entire selected day."""
    renewable_production = (
        hourly_data[SOLAR_COLUMN].sum() + hourly_data[WIND_COLUMN].sum()
    )
    total_production = hourly_data[PRODUCTION_COLUMN].sum()

    return renewable_production / total_production * 100


def calculate_seasonal_hourly_share(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate the typical hourly renewable share for each season."""
    seasonal_data = data[
        [DATE_COLUMN, SOLAR_COLUMN, WIND_COLUMN, PRODUCTION_COLUMN]
    ].copy()
    seasonal_data[SEASON_COLUMN] = seasonal_data[DATE_COLUMN].dt.month.map(
        SEASON_BY_MONTH
    )
    seasonal_data["Zi"] = seasonal_data[DATE_COLUMN].dt.date
    seasonal_data[HOUR_COLUMN] = seasonal_data[DATE_COLUMN].dt.hour

    hourly_data = (
        seasonal_data.groupby(
            [SEASON_COLUMN, "Zi", HOUR_COLUMN],
            as_index=False,
        )[[SOLAR_COLUMN, WIND_COLUMN, PRODUCTION_COLUMN]]
        .mean()
    )

    renewable_production = (
        hourly_data[SOLAR_COLUMN] + hourly_data[WIND_COLUMN]
    )
    total_production = hourly_data[PRODUCTION_COLUMN].where(
        hourly_data[PRODUCTION_COLUMN] != 0
    )
    hourly_data[SHARE_COLUMN] = renewable_production / total_production * 100

    return (
        hourly_data.groupby(
            [SEASON_COLUMN, HOUR_COLUMN],
            as_index=False,
        )[SHARE_COLUMN]
        .mean()
        .dropna(subset=[SHARE_COLUMN])
    )


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

    metrics = calculate_daily_metrics(daily_data)
    hourly_share = calculate_hourly_renewable_share(daily_data)
    daily_renewable_share = calculate_daily_renewable_share(hourly_share)
    seasonal_share = calculate_seasonal_hourly_share(data)

    st.subheader(f"Profilul zilei de {selected_date:%d.%m.%Y}")

    st.markdown(
        "**Formule:** "
        "Vârf solar = `max(Foto)`    "
        "Eolian mediu = `Σ Eolian / n`   "
        "Vârf eolian = `max(Eolian)`    "
        "Vârf solar + eolian = `max(Foto + Eolian)`   "
        "`n` = numărul măsurătorilor"
    )

    metric_columns = st.columns(5)
    metric_columns[0].metric(
        f"Vârf solar · {metrics['solar_peak_time']:%H:%M}",
        f"{metrics['solar_peak']:.0f} MW",
    )
    metric_columns[1].metric(
        "Eolian mediu",
        f"{metrics['wind_average']:.0f} MW",
    )
    metric_columns[2].metric(
        "Vârf eolian",
        f"{metrics['wind_peak']:.0f} MW",
    )
    metric_columns[3].metric(
        f"Vârf solar + eolian · {metrics['combined_peak_time']:%H:%M}",
        f"{metrics['combined_peak']:.0f} MW",
    )
    metric_columns[4].metric(
        "Măsurători",
        metrics["measurement_count"],
    )

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
        .mark_line(
            strokeWidth=3,
            point=alt.OverlayMarkDef(
                filled=True,
                size=45,
            ),
        )
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

    st.altair_chart(chart, use_container_width=True)

    st.subheader("Ponderea orară a producției solare și eoliene")
    st.markdown(
        "**Formula:** "
        "`Pondere regenerabile (%) = "
        "(Solar mediu orar + Eolian mediu orar) / "
        "Producție totală medie orară × 100`"
    )

    share_chart = (
        alt.Chart(hourly_share)
        .mark_line(
            color="#9B51E0",
            strokeWidth=3,
            point=alt.OverlayMarkDef(
                color="#9B51E0",
                filled=True,
                size=80,
            ),
        )
        .encode(
            x=alt.X(
                f"{DATE_COLUMN}:T",
                title="Ora",
                axis=alt.Axis(format="%H:%M", labelAngle=0),
            ),
            y=alt.Y(
                f"{SHARE_COLUMN}:Q",
                title="Pondere (%)",
                scale=alt.Scale(domain=[0, 100]),
            ),
            tooltip=[
                alt.Tooltip(f"{DATE_COLUMN}:T", title="Ora", format="%H:%M"),
                alt.Tooltip(
                    f"{SHARE_COLUMN}:Q",
                    title="Pondere regenerabile",
                    format=".1f",
                ),
            ],
        )
        .properties(height=400)
    )

    share_chart_column, share_metric_column = st.columns([4, 1])

    with share_chart_column:
        st.altair_chart(share_chart, use_container_width=True)

    with share_metric_column:
        st.metric(
            "Pondere zilnică Solar + Eolian",
            f"{daily_renewable_share:.1f}%",
        )
        st.caption(
            "Calculată ca raport între producția solară + eoliană "
            "și producția totală din ziua selectată."
        )

    st.subheader("Evoluția sezonieră a ponderii Solar + Eolian")
    st.write(
        "Fiecare linie reprezintă profilul orar mediu al ponderii "
        "regenerabile pentru un anotimp."
    )

    seasonal_chart = (
        alt.Chart(seasonal_share)
        .mark_line(
            strokeWidth=3,
            point=alt.OverlayMarkDef(
                filled=True,
                size=55,
            ),
        )
        .encode(
            x=alt.X(
                f"{HOUR_COLUMN}:Q",
                title="Ora",
                scale=alt.Scale(domain=[0, 23]),
                axis=alt.Axis(values=list(range(24)), labelAngle=0),
            ),
            y=alt.Y(
                f"{SHARE_COLUMN}:Q",
                title="Pondere medie (%)",
                scale=alt.Scale(domain=[0, 100]),
            ),
            color=alt.Color(
                f"{SEASON_COLUMN}:N",
                title="Anotimp",
                scale=alt.Scale(
                    domain=SEASON_ORDER,
                    range=SEASON_COLORS,
                ),
            ),
            order=alt.Order(f"{HOUR_COLUMN}:Q"),
            tooltip=[
                alt.Tooltip(f"{SEASON_COLUMN}:N", title="Anotimp"),
                alt.Tooltip(f"{HOUR_COLUMN}:Q", title="Ora", format=".0f"),
                alt.Tooltip(
                    f"{SHARE_COLUMN}:Q",
                    title="Pondere medie",
                    format=".1f",
                ),
            ],
        )
        .properties(height=450)
    )

    st.altair_chart(seasonal_chart, use_container_width=True)


if __name__ == "__main__":
    main()

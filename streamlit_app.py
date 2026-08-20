from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).parent / "Grafic_SEN (1)(Grafic SEN).csv"
DATE_COLUMN = "Data"
SOLAR_COLUMN = "Foto[MW]"
WIND_COLUMN = "Eolian[MW]"
PRODUCTION_COLUMN = "Productie[MW]"
CONSUMPTION_COLUMN = "Consum[MW]"
HYDRO_COLUMN = "Ape[MW]"
SHARE_COLUMN = "Pondere regenerabile (%)"
COVERAGE_COLUMN = "Acoperire SRE (%)"
HOURS_ABOVE_50_COLUMN = "Ore peste 50%"
VALID_HOURS_COLUMN = "Ore valide"
MIN_MEASUREMENTS_PER_HOUR = 4

CHART_SERIES = ["Solar", "Eolian", "Hidro", "Producție totală", "Consum"]
CHART_COLORS = ["#F2C94C", "#2F80ED", "#56CCF2", "#219653", "#EB5757"]

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


def calculate_hourly_renewable_coverage(
    daily_data: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate the hourly share of consumption covered by renewables."""
    indexed_data = daily_data.set_index(DATE_COLUMN)
    coverage_columns = [
        SOLAR_COLUMN,
        WIND_COLUMN,
        HYDRO_COLUMN,
        CONSUMPTION_COLUMN,
    ]
    hourly_data = indexed_data[coverage_columns].resample("1h").mean()
    measurements_per_hour = (
        indexed_data[CONSUMPTION_COLUMN].resample("1h").count()
    )
    hourly_data = hourly_data[
        measurements_per_hour >= MIN_MEASUREMENTS_PER_HOUR
    ].copy()

    renewable_production = (
        hourly_data[SOLAR_COLUMN]
        + hourly_data[WIND_COLUMN]
        + hourly_data[HYDRO_COLUMN]
    )
    consumption = hourly_data[CONSUMPTION_COLUMN].where(
        hourly_data[CONSUMPTION_COLUMN] != 0
    )
    hourly_data[COVERAGE_COLUMN] = renewable_production / consumption * 100

    return hourly_data.dropna(subset=[COVERAGE_COLUMN]).reset_index()


def calculate_daily_hours_above_50(data: pd.DataFrame) -> pd.DataFrame:
    """Count valid hours above 50% renewable coverage for every day."""
    indexed_data = data.set_index(DATE_COLUMN)
    coverage_columns = [
        SOLAR_COLUMN,
        WIND_COLUMN,
        HYDRO_COLUMN,
        CONSUMPTION_COLUMN,
    ]
    hourly_data = indexed_data[coverage_columns].resample("1h").mean()
    measurements_per_hour = (
        indexed_data[CONSUMPTION_COLUMN].resample("1h").count()
    )
    hourly_data = hourly_data[
        measurements_per_hour >= MIN_MEASUREMENTS_PER_HOUR
    ].copy()

    renewable_production = (
        hourly_data[SOLAR_COLUMN]
        + hourly_data[WIND_COLUMN]
        + hourly_data[HYDRO_COLUMN]
    )
    consumption = hourly_data[CONSUMPTION_COLUMN].where(
        hourly_data[CONSUMPTION_COLUMN] != 0
    )
    hourly_data[COVERAGE_COLUMN] = renewable_production / consumption * 100
    hourly_data = hourly_data.dropna(subset=[COVERAGE_COLUMN])

    hourly_data.index.name = "DataOra"
    hourly_data[DATE_COLUMN] = hourly_data.index.normalize()
    hourly_data[HOURS_ABOVE_50_COLUMN] = (
        hourly_data[COVERAGE_COLUMN] > 50
    ).astype(int)

    return (
        hourly_data.groupby(DATE_COLUMN, as_index=False)
        .agg(
            **{
                HOURS_ABOVE_50_COLUMN: (HOURS_ABOVE_50_COLUMN, "sum"),
                VALID_HOURS_COLUMN: (COVERAGE_COLUMN, "count"),
            }
        )
    )


def calculate_annual_threshold_metrics(
    daily_threshold_data: pd.DataFrame,
) -> dict:
    """Summarize annual hours above the renewable coverage threshold."""
    hours_above_50 = int(
        daily_threshold_data[HOURS_ABOVE_50_COLUMN].sum()
    )
    valid_hours = int(daily_threshold_data[VALID_HOURS_COLUMN].sum())
    calendar_hours = int(daily_threshold_data[DATE_COLUMN].nunique() * 24)

    return {
        "hours_above_50": hours_above_50,
        "valid_hours": valid_hours,
        "calendar_hours": calendar_hours,
        "calendar_percentage": hours_above_50 / calendar_hours * 100,
        "valid_percentage": hours_above_50 / valid_hours * 100,
    }


def calculate_renewable_coverage_metrics(
    hourly_coverage: pd.DataFrame,
) -> dict:
    """Calculate the main renewable consumption coverage indicators."""
    renewable_production = (
        hourly_coverage[SOLAR_COLUMN].sum()
        + hourly_coverage[WIND_COLUMN].sum()
        + hourly_coverage[HYDRO_COLUMN].sum()
    )
    total_consumption = hourly_coverage[CONSUMPTION_COLUMN].sum()
    daily_coverage = renewable_production / total_consumption * 100

    peak_index = hourly_coverage[COVERAGE_COLUMN].idxmax()

    return {
        "daily_coverage": daily_coverage,
        "peak_coverage": hourly_coverage.loc[peak_index, COVERAGE_COLUMN],
        "peak_time": hourly_coverage.loc[peak_index, DATE_COLUMN],
        "hours_above_50": int(
            (hourly_coverage[COVERAGE_COLUMN] > 50).sum()
        ),
        "valid_hours": len(hourly_coverage),
    }


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


def create_daily_profile_chart(
    daily_data: pd.DataFrame,
    show_total_production: bool,
    show_consumption: bool,
    show_hydro: bool,
    y_axis_max: float,
) -> alt.Chart:
    """Create the daily production and optional consumption chart."""
    chart_columns = [SOLAR_COLUMN, WIND_COLUMN]
    if show_total_production:
        chart_columns.append(PRODUCTION_COLUMN)
    if show_consumption:
        chart_columns.append(CONSUMPTION_COLUMN)
    if show_hydro:
        chart_columns.append(HYDRO_COLUMN)

    chart_data = daily_data[[DATE_COLUMN, *chart_columns]].rename(
        columns={
            SOLAR_COLUMN: "Solar",
            WIND_COLUMN: "Eolian",
            HYDRO_COLUMN: "Hidro",
            PRODUCTION_COLUMN: "Producție totală",
            CONSUMPTION_COLUMN: "Consum",
        }
    )
    chart_data = chart_data.melt(
        id_vars=DATE_COLUMN,
        var_name="Sursă",
        value_name="Putere (MW)",
    )

    return (
        alt.Chart(chart_data)
        .mark_line(
            strokeWidth=3,
            point=alt.OverlayMarkDef(filled=True, size=45),
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


def create_hourly_share_chart(hourly_share: pd.DataFrame) -> alt.Chart:
    """Create the hourly solar and wind share chart for one day."""
    return (
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


def create_seasonal_share_chart(seasonal_share: pd.DataFrame) -> alt.Chart:
    """Create the seasonal comparison of typical hourly renewable shares."""
    return (
        alt.Chart(seasonal_share)
        .mark_line(
            strokeWidth=3,
            point=alt.OverlayMarkDef(filled=True, size=55),
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


def create_hourly_renewable_coverage_chart(
    hourly_coverage: pd.DataFrame,
) -> alt.LayerChart:
    """Create the hourly renewable coverage chart with a 50% threshold."""
    y_axis_max = max(100, hourly_coverage[COVERAGE_COLUMN].max() * 1.05)

    coverage_line = (
        alt.Chart(hourly_coverage)
        .mark_line(
            color="#27AE60",
            strokeWidth=3,
            point=alt.OverlayMarkDef(
                color="#27AE60",
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
                f"{COVERAGE_COLUMN}:Q",
                title="Acoperirea consumului (%)",
                scale=alt.Scale(domain=[0, y_axis_max]),
            ),
            tooltip=[
                alt.Tooltip(f"{DATE_COLUMN}:T", title="Ora", format="%H:%M"),
                alt.Tooltip(
                    f"{COVERAGE_COLUMN}:Q",
                    title="Acoperire SRE",
                    format=".1f",
                ),
            ],
        )
    )

    threshold_line = (
        alt.Chart(pd.DataFrame({"Prag (%)": [50]}))
        .mark_rule(
            color="#EB5757",
            strokeWidth=2,
            strokeDash=[8, 6],
        )
        .encode(
            y=alt.Y("Prag (%):Q"),
            tooltip=[alt.Tooltip("Prag (%):Q", title="Prag")],
        )
    )

    return alt.layer(coverage_line, threshold_line).properties(height=400)


def create_daily_hours_above_50_chart(
    daily_threshold_data: pd.DataFrame,
) -> alt.Chart:
    """Create the annual chart of daily hours above 50% coverage."""
    return (
        alt.Chart(daily_threshold_data)
        .mark_bar(color="#27AE60")
        .encode(
            x=alt.X(f"{DATE_COLUMN}:T", title="Data"),
            y=alt.Y(
                f"{HOURS_ABOVE_50_COLUMN}:Q",
                title="Ore peste 50%",
                scale=alt.Scale(domain=[0, 24]),
                axis=alt.Axis(tickMinStep=1),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{DATE_COLUMN}:T",
                    title="Data",
                    format="%d.%m.%Y",
                ),
                alt.Tooltip(
                    f"{HOURS_ABOVE_50_COLUMN}:Q",
                    title="Ore peste 50%",
                    format=".0f",
                ),
                alt.Tooltip(
                    f"{VALID_HOURS_COLUMN}:Q",
                    title="Ore valide",
                    format=".0f",
                ),
            ],
        )
        .properties(height=400)
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
    option_columns = st.columns(3)
    show_total_production = option_columns[0].checkbox(
        "Afișează producția totală"
    )
    show_consumption = option_columns[1].checkbox("Afișează consumul")
    show_hydro = option_columns[2].checkbox("Afișează hidro")

    daily_data = get_daily_data(data, selected_date)
    if daily_data.empty:
        st.warning("Nu există date pentru ziua selectată.")
        st.stop()

    metrics = calculate_daily_metrics(daily_data)
    hourly_share = calculate_hourly_renewable_share(daily_data)
    hourly_coverage = calculate_hourly_renewable_coverage(daily_data)
    coverage_metrics = calculate_renewable_coverage_metrics(hourly_coverage)
    daily_hours_above_50 = calculate_daily_hours_above_50(data)
    annual_threshold_metrics = calculate_annual_threshold_metrics(
        daily_hours_above_50
    )
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

    y_axis_max = (
        data[[PRODUCTION_COLUMN, CONSUMPTION_COLUMN]].max().max() * 1.05
    )
    daily_profile_chart = create_daily_profile_chart(
        daily_data,
        show_total_production,
        show_consumption,
        show_hydro,
        y_axis_max,
    )

    st.altair_chart(daily_profile_chart, use_container_width=True)

    st.info(
        "**Concluzie:** Producția solară are un profil zilnic de tip "
        "clopot, cu valori maxime în jurul prânzului și valori reduse sau "
        "nule dimineața devreme și seara. Producția eoliană are un profil "
        "neregulat, cu variații pe parcursul întregii zile, fără un maxim "
        "asociat unei anumite ore. Producția solară înregistrează cele mai "
        "mari valori în timpul verii."
    )

    st.subheader("Ponderea orară a producției solare și eoliene")
    st.markdown(
        "**Formula:** "
        "`Pondere regenerabile (%) = "
        "(Solar mediu orar + Eolian mediu orar) / "
        "Producție totală medie orară × 100`"
    )

    hourly_share_chart = create_hourly_share_chart(hourly_share)

    share_chart_column, share_metric_column = st.columns([4, 1])

    with share_chart_column:
        st.altair_chart(hourly_share_chart, use_container_width=True)

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

    seasonal_share_chart = create_seasonal_share_chart(seasonal_share)

    st.altair_chart(seasonal_share_chart, use_container_width=True)

    st.subheader("Acoperirea orară a consumului din surse regenerabile")
    st.markdown(
        "**Formula:** "
        "`Acoperire SRE (%) = "
        "(Eolian mediu orar + Solar mediu orar + Hidro mediu orar) / "
        "Consum mediu orar × 100`"
    )
    st.write(
        "Linia roșie întreruptă marchează pragul de 50% din consum."
    )

    coverage_metric_columns = st.columns(4)
    coverage_metric_columns[0].metric(
        "Acoperire zilnică SRE",
        f"{coverage_metrics['daily_coverage']:.1f}%",
    )
    coverage_metric_columns[1].metric(
        f"Acoperire maximă · {coverage_metrics['peak_time']:%H:%M}",
        f"{coverage_metrics['peak_coverage']:.1f}%",
    )
    coverage_metric_columns[2].metric(
        "Ore peste 50%",
        f"{coverage_metrics['hours_above_50']} / "
        f"{coverage_metrics['valid_hours']}",
    )
    coverage_metric_columns[3].metric(
        "Ore valide",
        coverage_metrics["valid_hours"],
    )

    coverage_chart = create_hourly_renewable_coverage_chart(hourly_coverage)
    st.altair_chart(coverage_chart, use_container_width=True)

    st.subheader("Numărul zilnic de ore cu acoperire SRE peste 50%")
    st.write(
        "Fiecare bară arată în câte ore din zi sursele regenerabile "
        "au acoperit mai mult de 50% din consum."
    )
    st.caption(
        f"O oră este considerată validă dacă are cel puțin "
        f"{MIN_MEASUREMENTS_PER_HOUR} măsurători."
    )

    daily_threshold_chart = create_daily_hours_above_50_chart(
        daily_hours_above_50
    )

    annual_chart_column, annual_metric_column = st.columns([4, 1])

    with annual_chart_column:
        st.altair_chart(daily_threshold_chart, use_container_width=True)

    with annual_metric_column:
        st.metric(
            "Ore peste 50% în 2025",
            f"{annual_threshold_metrics['hours_above_50']:,} / "
            f"{annual_threshold_metrics['calendar_hours']:,}",
        )
        st.caption(
            f"{annual_threshold_metrics['calendar_percentage']:.1f}% "
            "din toate orele anului."
        )
        st.caption(
            f"Ore valide: {annual_threshold_metrics['valid_hours']:,} / "
            f"{annual_threshold_metrics['calendar_hours']:,} · "
            f"{annual_threshold_metrics['valid_percentage']:.1f}% "
            "din orele valide au depășit pragul."
        )


if __name__ == "__main__":
    main()

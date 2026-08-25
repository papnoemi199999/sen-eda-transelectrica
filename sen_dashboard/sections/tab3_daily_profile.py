"""UI for tab 3: the daily solar and wind production profile question."""

import altair as alt
import pandas as pd
import streamlit as st

from sen_dashboard.constants import DATE_COLUMN, SOLAR_COLUMN, WIND_COLUMN

ANNUAL_SOLAR_LABEL = "Solar"
ANNUAL_WIND_LABEL = "Eolian"
ANNUAL_COMBINED_LABEL = "Solar + Eolian"


def calculate_daily_metrics(daily_data: pd.DataFrame) -> dict:
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


def create_annual_solar_wind_chart(
    data: pd.DataFrame,
    visible_series: list[str],
) -> alt.Chart:
    """Show solar, wind, and their combined daily means for the whole year."""
    chart_data = data[[DATE_COLUMN, SOLAR_COLUMN, WIND_COLUMN]].copy()
    chart_data[DATE_COLUMN] = chart_data[DATE_COLUMN].dt.normalize()
    daily_data = chart_data.groupby(DATE_COLUMN, as_index=False).agg(
        **{
            ANNUAL_SOLAR_LABEL: (SOLAR_COLUMN, "mean"),
            ANNUAL_WIND_LABEL: (WIND_COLUMN, "mean"),
        }
    )
    daily_data[ANNUAL_COMBINED_LABEL] = (
        daily_data[ANNUAL_SOLAR_LABEL] + daily_data[ANNUAL_WIND_LABEL]
    )
    series_order = [
        ANNUAL_SOLAR_LABEL,
        ANNUAL_WIND_LABEL,
        ANNUAL_COMBINED_LABEL,
    ]
    long_data = daily_data.melt(
        id_vars=DATE_COLUMN,
        value_vars=visible_series,
        var_name="Serie",
        value_name="Putere medie (MW)",
    )

    return (
        alt.Chart(long_data)
        .mark_line(
            strokeWidth=2,
            point=alt.OverlayMarkDef(filled=True, size=18),
        )
        .encode(
            x=alt.X(
                f"{DATE_COLUMN}:T",
                title="Luna",
                axis=alt.Axis(format="%b", labelAngle=0, tickCount=12),
            ),
            y=alt.Y(
                "Putere medie (MW):Q",
                title="Putere medie zilnică (MW)",
                scale=alt.Scale(zero=True),
            ),
            color=alt.Color(
                "Serie:N",
                title="Serie",
                scale=alt.Scale(
                    domain=series_order,
                    range=["#F2C94C", "#2F80ED", "#27AE60"],
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{DATE_COLUMN}:T",
                    title="Data",
                    format="%d.%m.%Y",
                ),
                alt.Tooltip("Serie:N", title="Serie"),
                alt.Tooltip(
                    "Putere medie (MW):Q",
                    title="Putere medie",
                    format=",.0f",
                ),
            ],
        )
        .properties(height=440)
    )


def render_daily_profile(
    data: pd.DataFrame,
    daily_data: pd.DataFrame,
    selected_date,
) -> None:
    st.header("3. Cum arată profilul zilnic al solarului (clopot în jurul prânzului) și cel al eolianului (neregulat)?")

    metrics = calculate_daily_metrics(daily_data)
    metric_columns = st.columns(5)
    metric_columns[0].metric(
        f"Vârf solar · {metrics['solar_peak_time']:%H:%M}",
        f"{metrics['solar_peak']:.0f} MW",
    )
    metric_columns[1].metric(
        "Eolian mediu", f"{metrics['wind_average']:.0f} MW"
    )
    metric_columns[2].metric(
        "Vârf eolian", f"{metrics['wind_peak']:.0f} MW"
    )
    metric_columns[3].metric(
        f"Vârf solar + eolian · {metrics['combined_peak_time']:%H:%M}",
        f"{metrics['combined_peak']:.0f} MW",
    )
    metric_columns[4].metric("Măsurători", metrics["measurement_count"])

    st.caption(f"Data afișată: {selected_date:%d.%m.%Y}")

    st.markdown(
        "**Evoluția anuală a producției solare și eoliene · medii zilnice**"
    )
    series_options = [
        ANNUAL_SOLAR_LABEL,
        ANNUAL_WIND_LABEL,
        ANNUAL_COMBINED_LABEL,
    ]
    option_columns = st.columns(len(series_options))
    visible_series = [
        series
        for column, series in zip(option_columns, series_options, strict=True)
        if column.checkbox(
            series,
            value=True,
            key=f"annual_daily_profile_{series}",
        )
    ]
    if visible_series:
        st.altair_chart(
            create_annual_solar_wind_chart(data, visible_series),
            use_container_width=True,
        )
    else:
        st.info("Selectează cel puțin o serie pentru a afișa graficul anual.")

    st.info(
        """**Concluzie:**

- Producția solară are un profil zilnic de tip clopot, cu valori maxime în
  jurul prânzului și valori reduse sau nule dimineața devreme și seara.
- Producția eoliană are un profil neregulat, cu variații pe parcursul întregii
  zile, fără un maxim asociat unei anumite ore.
- Aceste caracteristici se observă și în graficul anual, unde producția solară
  urmează un tipar sezonier mai regulat, iar producția eoliană rămâne mult mai
  variabilă."""
    )

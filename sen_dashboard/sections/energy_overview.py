"""Shared daily energy overview shown on every analysis tab."""

import altair as alt
import pandas as pd
import streamlit as st

from sen_dashboard.constants import (
    CHART_COLORS,
    CHART_SERIES,
    CONSUMPTION_COLUMN,
    DATE_COLUMN,
    HYDRO_COLUMN,
    PRODUCTION_COLUMN,
    SOLAR_COLUMN,
    WIND_COLUMN,
)


ENERGY_SERIES = [
    ("Producție totală", PRODUCTION_COLUMN),
    ("Consum", CONSUMPTION_COLUMN),
    ("Hidro", HYDRO_COLUMN),
    ("Eolian", WIND_COLUMN),
    ("Solar", SOLAR_COLUMN),
]


def create_energy_overview_chart(
    daily_data: pd.DataFrame,
    visible_columns: list[str],
    y_axis_max: float,
) -> alt.Chart:
    chart_data = daily_data[[DATE_COLUMN, *visible_columns]].rename(
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
            point=alt.OverlayMarkDef(filled=True, size=25),
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
                scale=alt.Scale(domain=CHART_SERIES, range=CHART_COLORS),
            ),
            tooltip=[
                alt.Tooltip(f"{DATE_COLUMN}:T", title="Ora", format="%H:%M"),
                alt.Tooltip("Sursă:N", title="Sursă"),
                alt.Tooltip("Putere (MW):Q", title="Putere", format=",.0f"),
            ],
        )
        .properties(height=520)
    )


def render_energy_overview(
    data: pd.DataFrame,
    daily_data: pd.DataFrame,
) -> None:
    """Render a large daily chart with local series checkboxes."""
    with st.container(border=True):
        st.subheader("Evoluția zilnică a sistemului energetic")
        st.caption(
            "Selectează seriile afișate: producție, consum, hidro, "
            "eolian și solar."
        )

        option_columns = st.columns(len(ENERGY_SERIES))
        visible_columns = []
        for option_column, (label, column_name) in zip(
            option_columns,
            ENERGY_SERIES,
            strict=True,
        ):
            if option_column.checkbox(
                label,
                value=True,
                key=f"energy_overview_{column_name}",
            ):
                visible_columns.append(column_name)

        if not visible_columns:
            st.info("Selectează cel puțin o serie pentru a afișa graficul.")
            return

        y_axis_max = max(1, data[visible_columns].max().max() * 1.05)
        st.altair_chart(
            create_energy_overview_chart(
                daily_data,
                visible_columns,
                y_axis_max,
            ),
            use_container_width=True,
        )

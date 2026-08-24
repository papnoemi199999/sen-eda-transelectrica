"""UI for tab 1: the renewable production share question."""

import altair as alt
import pandas as pd
import streamlit as st

from sen_dashboard.constants import (
    DATE_COLUMN,
    PRODUCTION_COLUMN,
    SHARE_COLUMN,
    SOLAR_COLUMN,
    WIND_COLUMN,
)

SOLAR_SHARE_COLUMN = "Pondere solară (%)"
WIND_SHARE_COLUMN = "Pondere eoliană (%)"
HOURLY_SHARE_OPTIONS = {
    "Eolian": (WIND_SHARE_COLUMN, "#2F80ED", (WIND_COLUMN,)),
    "Solar": (SOLAR_SHARE_COLUMN, "#F2C94C", (SOLAR_COLUMN,)),
    "Eolian + Solar": (
        SHARE_COLUMN,
        "#9B51E0",
        (WIND_COLUMN, SOLAR_COLUMN),
    ),
}


def calculate_hourly_renewable_share(
    daily_data: pd.DataFrame,
) -> pd.DataFrame:

    hourly_data = (
        daily_data.set_index(DATE_COLUMN)[
            [SOLAR_COLUMN, WIND_COLUMN, PRODUCTION_COLUMN]
        ]
        .resample("1h")
        .mean()
    )

    # Sum the solar and wind production to get the total renewable production
    renewable_production = hourly_data[SOLAR_COLUMN] + hourly_data[WIND_COLUMN]

    total_production = hourly_data[PRODUCTION_COLUMN].where(
        hourly_data[PRODUCTION_COLUMN] != 0
    )

    hourly_data[WIND_SHARE_COLUMN] = (
        hourly_data[WIND_COLUMN] / total_production * 100
    )

    hourly_data[SOLAR_SHARE_COLUMN] = (
        hourly_data[SOLAR_COLUMN] / total_production * 100
    )

    hourly_data[SHARE_COLUMN] = renewable_production / total_production * 100

    return hourly_data.dropna(subset=[SHARE_COLUMN]).reset_index()


def calculate_daily_renewable_share(
    hourly_data: pd.DataFrame,
    production_columns: tuple[str, ...] = (SOLAR_COLUMN, WIND_COLUMN),
) -> float:

    # Calculate the total renewable production
    renewable_production = hourly_data[list(production_columns)].sum().sum()

    # Calculate the total production
    total_production = hourly_data[PRODUCTION_COLUMN].sum()

    if total_production == 0 or pd.isna(total_production):
        return float("nan")

    return renewable_production / total_production * 100


def calculate_yearly_daily_share(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate one solar, wind and combined production share per day."""
    daily_data = (
        data.set_index(DATE_COLUMN)[
            [SOLAR_COLUMN, WIND_COLUMN, PRODUCTION_COLUMN]
        ]
        .resample("1D")
        .sum()
    )

    total_production = daily_data[PRODUCTION_COLUMN].where(
        daily_data[PRODUCTION_COLUMN] != 0
    )
    daily_data[WIND_SHARE_COLUMN] = (
        daily_data[WIND_COLUMN] / total_production * 100
    )
    daily_data[SOLAR_SHARE_COLUMN] = (
        daily_data[SOLAR_COLUMN] / total_production * 100
    )
    daily_data[SHARE_COLUMN] = (
        daily_data[SOLAR_COLUMN] + daily_data[WIND_COLUMN]
    ) / total_production * 100

    return daily_data.dropna(subset=[SHARE_COLUMN]).reset_index()


def create_hourly_share_chart(
    hourly_share: pd.DataFrame,
    share_column: str = SHARE_COLUMN,
    color: str = "#9B51E0",
) -> alt.Chart:
    return (
        alt.Chart(hourly_share)
        .mark_line(
            color=color,
            strokeWidth=3,
            point=alt.OverlayMarkDef(filled=True, size=25),
        )
        .encode(
            x=alt.X(f"{DATE_COLUMN}:T", title="Ora"),
            y=alt.Y(
                f"{share_column}:Q",
                title="Pondere (%)",
                scale=alt.Scale(domain=[0, 100]),
            ),
            tooltip=[
                f"{DATE_COLUMN}:T",
                f"{share_column}:Q",
            ],
        )
        .properties(height=400)
    )


def create_yearly_daily_share_chart(
    daily_share: pd.DataFrame,
    share_column: str = SHARE_COLUMN,
    color: str = "#9B51E0",
) -> alt.Chart:
    base = alt.Chart(daily_share).encode(
        x=alt.X(f"{DATE_COLUMN}:T", title="Data"),
        y=alt.Y(
            f"{share_column}:Q",
            title="Pondere zilnică (%)",
            scale=alt.Scale(zero=True),
        ),
        tooltip=[
            alt.Tooltip(f"{DATE_COLUMN}:T", title="Data", format="%d.%m.%Y"),
            alt.Tooltip(
                f"{share_column}:Q",
                title="Pondere",
                format=".1f",
            ),
        ],
    )

    line = base.mark_line(color=color, strokeWidth=1.5, opacity=0.7)
    points = base.mark_circle(color=color, size=22, opacity=0.55)

    return (line + points).properties(height=350)


def render_renewable_share(
    data: pd.DataFrame,
    daily_data: pd.DataFrame,
    selected_date,
) -> None:

    st.header(
        "1. Care este ponderea orară a surselor regenerabile (eolian și "
        "solar) în producția totală și cum se schimbă pe parcursul zilei?"
    )

    # Hourly
    hourly_share = calculate_hourly_renewable_share(daily_data)

    if hourly_share.empty:
        st.warning("Ponderea nu poate fi calculată pentru ziua selectată.")
        return

    chart_column, metric_column = st.columns([4, 1])

    with chart_column:
        selected_daily_share = st.radio(
            "Sursa regenerabilă afișată pentru profilul orar",
            options=list(HOURLY_SHARE_OPTIONS),
            index=2,
            horizontal=True,
            key="daily_renewable_source",
        )
        daily_share_column, daily_chart_color, production_columns = (
            HOURLY_SHARE_OPTIONS[selected_daily_share]
        )
        st.altair_chart(
            create_hourly_share_chart(
                hourly_share,
                share_column=daily_share_column,
                color=daily_chart_color,
            ),
            use_container_width=True,
        )

    # Daily metric for the selected date
    with metric_column:
        daily_share = calculate_daily_renewable_share(
            hourly_share,
            production_columns,
        )
        st.metric(
            f"Pondere zilnică {selected_daily_share} · "
            f"{selected_date:%d.%m.%Y}",
            f"{daily_share:.1f}%",
        )
        st.caption(
            f"Raportul dintre producția {selected_daily_share.lower()} și "
            "producția totală din ziua selectată."
        )

    st.divider()

    st.subheader("Cum variază ponderea zilnică pe parcursul anului?")

    yearly_daily_share = calculate_yearly_daily_share(data)
    selected_yearly_share = st.radio(
        "Sursa regenerabilă afișată pentru profilul anual",
        options=list(HOURLY_SHARE_OPTIONS),
        index=2,
        horizontal=True,
        key="yearly_renewable_source",
    )
    yearly_share_column, yearly_chart_color, _ = HOURLY_SHARE_OPTIONS[
        selected_yearly_share
    ]
    st.altair_chart(
        create_yearly_daily_share_chart(
            yearly_daily_share,
            share_column=yearly_share_column,
            color=yearly_chart_color,
        ),
        use_container_width=True,
    )

    if not yearly_daily_share.empty:
        daily_series = yearly_daily_share[yearly_share_column]
        minimum_index = daily_series.idxmin()
        maximum_index = daily_series.idxmax()
        st.caption(
            f"Media zilnică: {daily_series.mean():.1f}% · "
            f"Minim: {daily_series.loc[minimum_index]:.1f}% "
            f"({yearly_daily_share.loc[minimum_index, DATE_COLUMN]:%d.%m.%Y}) · "
            f"Maxim: {daily_series.loc[maximum_index]:.1f}% "
            f"({yearly_daily_share.loc[maximum_index, DATE_COLUMN]:%d.%m.%Y})"
        )

        combined_daily_series = yearly_daily_share[SHARE_COLUMN]

        st.info(
            f"""**Concluzii:**

- În 2025, ponderea zilnică a producției eoliene și solare a fost în
  medie de {combined_daily_series.mean():.1f}%, variind între
  {combined_daily_series.min():.1f}% și {combined_daily_series.max():.1f}%.
- La nivelul unei zile, producția solară este aproape zero în timpul
  nopții, crește după răsărit, atinge valorile cele mai ridicate în jurul
  prânzului și scade din nou spre seară.
- Pe parcursul anului, ponderea producției solare prezintă o evoluție
  sezonieră clară: crește din timpul primăverii spre vară și se reduce în
  lunile de toamnă și de iarnă.
- Producția eoliană variază puternic atât de la o oră la alta, cât și de la
  o zi la alta, fără o evoluție sezonieră la fel de clară precum cea a
  producției solare."""
        )

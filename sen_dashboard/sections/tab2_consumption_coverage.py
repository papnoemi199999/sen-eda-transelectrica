"""UI for tab 2: the renewable consumption coverage question."""

import math

import altair as alt
import pandas as pd
import streamlit as st

from sen_dashboard.constants import (
    CONSUMPTION_COLUMN,
    COVERAGE_COLUMN,
    DATE_COLUMN,
    HOURS_ABOVE_50_COLUMN,
    HYDRO_COLUMN,
    MIN_MEASUREMENTS_PER_HOUR,
    SEASON_BY_MONTH,
    SEASON_COLUMN,
    SEASON_ORDER,
    SOLAR_COLUMN,
    VALID_HOURS_COLUMN,
    WIND_COLUMN,
)

RENEWABLE_PRODUCTION_COLUMN = "Producție SRE (MW)"
CONSUMPTION_TOOLTIP_COLUMN = "Consum (MW)"
CALENDAR_WEEK_COLUMN = "Săptămâna anului"
CALENDAR_WEEKDAY_COLUMN = "Ziua săptămânii"
CALENDAR_YEAR_COLUMN = "An"
ROMANIAN_MONTH_ABBREVIATIONS = {
    1: "Ian",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "Mai",
    6: "Iun",
    7: "Iul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}
WEEKDAY_ORDER = [
    "Luni",
    "Marți",
    "Miercuri",
    "Joi",
    "Vineri",
    "Sâmbătă",
    "Duminică",
]
RENEWABLE_SOURCE_OPTIONS = {
    "Hidro": ((HYDRO_COLUMN,), "#56CCF2", "producția hidroelectrică"),
    "Solar": ((SOLAR_COLUMN,), "#F2C94C", "producția solară"),
    "Eolian": ((WIND_COLUMN,), "#2F80ED", "producția eoliană"),
    "Hidro + Solar + Eolian": (
        (HYDRO_COLUMN, SOLAR_COLUMN, WIND_COLUMN),
        "#27AE60",
        "producția hidroelectrică, solară și eoliană",
    ),
}
SOURCE_PROFILE_INTERPRETATIONS = {
    "Hidro": (
        "Profilul hidroelectric reflectă modul în care producția hidro "
        "este ajustată pe parcursul zilei și disponibilitatea resurselor de apă."
    ),
    "Solar": (
        "Profilul solar crește după răsărit, atinge nivelurile cele mai "
        "ridicate în jurul prânzului și revine aproape de zero noaptea."
    ),
    "Eolian": (
        "Producția eoliană poate contribui la orice oră, însă profilul său "
        "este variabil și nu urmează un ciclu zilnic regulat."
    ),
    "Hidro + Solar + Eolian": (
        "Creșterea acoperirii combinate din jurul prânzului coincide cu "
        "intervalul de producție solară ridicată."
    ),
}


def _percentage(numerator: float, denominator: float) -> float:
    """Return a percentage, or NaN when it cannot be calculated."""
    if denominator == 0 or pd.isna(denominator):
        return math.nan
    return numerator / denominator * 100


# calculate the hourly renewable coverage as a percentage of consumption
def calculate_hourly_renewable_coverage(
    data: pd.DataFrame,
    production_columns: tuple[str, ...] = (
        HYDRO_COLUMN,
        SOLAR_COLUMN,
        WIND_COLUMN,
    ),
) -> pd.DataFrame:
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

    renewable_production = hourly_data[list(production_columns)].sum(axis=1)
    hourly_data[RENEWABLE_PRODUCTION_COLUMN] = renewable_production
    hourly_data[CONSUMPTION_TOOLTIP_COLUMN] = hourly_data[CONSUMPTION_COLUMN]

    consumption = hourly_data[CONSUMPTION_COLUMN].where(
        hourly_data[CONSUMPTION_COLUMN] != 0
    )
    hourly_data[COVERAGE_COLUMN] = renewable_production / consumption * 100
    return hourly_data.dropna(subset=[COVERAGE_COLUMN]).reset_index()


# count the number of valid hours above 50% renewable coverage for every day
def calculate_daily_hours_above_50(
    data: pd.DataFrame,
    production_columns: tuple[str, ...] = (
        HYDRO_COLUMN,
        SOLAR_COLUMN,
        WIND_COLUMN,
    ),
) -> pd.DataFrame:
    hourly_data = calculate_hourly_renewable_coverage(
        data,
        production_columns,
    )
    hourly_data[DATE_COLUMN] = hourly_data[DATE_COLUMN].dt.normalize()
    hourly_data[HOURS_ABOVE_50_COLUMN] = (
        hourly_data[COVERAGE_COLUMN] > 50
    ).astype(int)

    return hourly_data.groupby(DATE_COLUMN, as_index=False).agg(
        **{
            HOURS_ABOVE_50_COLUMN: (HOURS_ABOVE_50_COLUMN, "sum"),
            VALID_HOURS_COLUMN: (COVERAGE_COLUMN, "count"),
        }
    )

# Summarize hours above the renewable coverage threshold.
def calculate_annual_threshold_metrics(
    daily_threshold_data: pd.DataFrame,
) -> dict:
    hours_above_50 = int(daily_threshold_data[HOURS_ABOVE_50_COLUMN].sum())
    valid_hours = int(daily_threshold_data[VALID_HOURS_COLUMN].sum())
    calendar_hours = int(daily_threshold_data[DATE_COLUMN].nunique() * 24)

    return {
        "hours_above_50": hours_above_50,
        "valid_hours": valid_hours,
        "calendar_hours": calendar_hours,
        "calendar_percentage": _percentage(hours_above_50, calendar_hours),
        "valid_percentage": _percentage(hours_above_50, valid_hours),
    }


def calculate_seasonal_hours_above_50(
    daily_threshold_data: pd.DataFrame,
) -> dict[str, int]:
    """Sum hours above 50% renewable coverage for each season."""
    seasonal_data = daily_threshold_data.copy()
    seasonal_data[SEASON_COLUMN] = seasonal_data[DATE_COLUMN].dt.month.map(
        SEASON_BY_MONTH
    )
    seasonal_totals = seasonal_data.groupby(SEASON_COLUMN)[
        HOURS_ABOVE_50_COLUMN
    ].sum()

    return {
        season: int(seasonal_totals.get(season, 0))
        for season in SEASON_ORDER
    }


def calculate_renewable_coverage_metrics(
    hourly_coverage: pd.DataFrame,
    production_columns: tuple[str, ...] = (
        HYDRO_COLUMN,
        SOLAR_COLUMN,
        WIND_COLUMN,
    ),
) -> dict:
    """Calculate the main renewable consumption coverage indicators."""
    renewable_production = hourly_coverage[list(production_columns)].sum().sum()
    total_consumption = hourly_coverage[CONSUMPTION_COLUMN].sum()
    peak_index = hourly_coverage[COVERAGE_COLUMN].idxmax()

    return {
        "daily_coverage": _percentage(renewable_production, total_consumption),
        "peak_coverage": hourly_coverage.loc[peak_index, COVERAGE_COLUMN],
        "peak_time": hourly_coverage.loc[peak_index, DATE_COLUMN],
        "hours_above_50": int((hourly_coverage[COVERAGE_COLUMN] > 50).sum()),
        "valid_hours": len(hourly_coverage),
    }


def calculate_energy_totals(hourly_coverage: pd.DataFrame) -> dict[str, float]:
    """Calculate consumed and generated energy over the available hours."""
    source_totals = {
        "hydro": float(hourly_coverage[HYDRO_COLUMN].sum()),
        "solar": float(hourly_coverage[SOLAR_COLUMN].sum()),
        "wind": float(hourly_coverage[WIND_COLUMN].sum()),
    }
    return {
        "consumption": float(hourly_coverage[CONSUMPTION_COLUMN].sum()),
        "renewable_total": sum(source_totals.values()),
        **source_totals,
    }


def render_energy_totals(
    energy_totals: dict[str, float],
    unit: str,
    divisor: float = 1,
) -> None:
    """Render consumption and renewable generation totals in five columns."""
    columns = st.columns(5)
    metric_definitions = [
        ("Consum", "consumption"),
        ("Producție SRE totală", "renewable_total"),
        ("Hidro", "hydro"),
        ("Solar", "solar"),
        ("Eolian", "wind"),
    ]
    for column, (label, key) in zip(
        columns,
        metric_definitions,
        strict=True,
    ):
        column.metric(label, f"{energy_totals[key] / divisor:,.0f} {unit}")


def calculate_annual_coverage_insights(
    hourly_coverage: pd.DataFrame,
    daily_threshold_data: pd.DataFrame,
    production_columns: tuple[str, ...] = (
        HYDRO_COLUMN,
        SOLAR_COLUMN,
        WIND_COLUMN,
    ),
) -> dict:
    """Calculate annual indicators used in the written conclusions."""
    renewable_production = hourly_coverage[
        list(production_columns)
    ].sum().sum()
    total_consumption = hourly_coverage[CONSUMPTION_COLUMN].sum()

    hourly_profile = hourly_coverage.groupby(
        hourly_coverage[DATE_COLUMN].dt.hour
    )[COVERAGE_COLUMN].mean()

    seasonal_data = hourly_coverage.copy()
    seasonal_data[SEASON_COLUMN] = seasonal_data[DATE_COLUMN].dt.month.map(
        SEASON_BY_MONTH
    )
    seasonal_average = seasonal_data.groupby(SEASON_COLUMN)[
        COVERAGE_COLUMN
    ].mean()

    full_days_above_50 = (
        (
            daily_threshold_data[HOURS_ABOVE_50_COLUMN]
            == daily_threshold_data[VALID_HOURS_COLUMN]
        )
        & (daily_threshold_data[VALID_HOURS_COLUMN] == 24)
    ).sum()

    return {
        "annual_coverage": _percentage(
            renewable_production,
            total_consumption,
        ),
        "peak_profile_hour": int(hourly_profile.idxmax()),
        "peak_profile_coverage": float(hourly_profile.max()),
        "days_with_hours_above_50": int(
            (daily_threshold_data[HOURS_ABOVE_50_COLUMN] > 0).sum()
        ),
        "full_days_above_50": int(full_days_above_50),
        "strongest_season": str(seasonal_average.idxmax()),
        "strongest_season_coverage": float(seasonal_average.max()),
        "weakest_season": str(seasonal_average.idxmin()),
        "weakest_season_coverage": float(seasonal_average.min()),
    }


def create_hourly_renewable_coverage_chart(
    hourly_coverage: pd.DataFrame,
    color: str = "#27AE60",
    production_label: str = "Hidro + solar + eolian",
) -> alt.LayerChart:
    y_axis_max = max(100, hourly_coverage[COVERAGE_COLUMN].max() * 1.05)
    coverage_line = (
        alt.Chart(hourly_coverage)
        .mark_line(
            color=color,
            strokeWidth=3,
            point=alt.OverlayMarkDef(filled=True, size=25),
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
                alt.Tooltip(
                    f"{CONSUMPTION_TOOLTIP_COLUMN}:Q",
                    title="Consum",
                    format=",.1f",
                ),
                alt.Tooltip(
                    f"{RENEWABLE_PRODUCTION_COLUMN}:Q",
                    title=production_label,
                    format=",.1f",
                ),
            ],
        )
    )
    threshold_line = (
        alt.Chart(pd.DataFrame({"Prag (%)": [50]}))
        .mark_rule(color="#EB5757", strokeWidth=2, strokeDash=[8, 6])
        .encode(y=alt.Y("Prag (%):Q"))
    )
    return alt.layer(coverage_line, threshold_line).properties(height=400)


def create_annual_generation_consumption_chart(
    hourly_coverage: pd.DataFrame,
    production_columns: tuple[str, ...],
    production_label: str,
    production_color: str,
    show_consumption: bool,
) -> alt.Chart:
    """Show daily mean production and optionally consumption over the year."""
    chart_data = hourly_coverage.copy()
    chart_data["Producție selectată"] = chart_data[
        list(production_columns)
    ].sum(axis=1)
    chart_data[DATE_COLUMN] = chart_data[DATE_COLUMN].dt.normalize()
    daily_chart_data = chart_data.groupby(DATE_COLUMN, as_index=False).agg(
        **{
            production_label: ("Producție selectată", "mean"),
            "Consum": (CONSUMPTION_COLUMN, "mean"),
        }
    )

    visible_series = [production_label]
    series_colors = [production_color]
    if show_consumption:
        visible_series.append("Consum")
        series_colors.append("#EB5757")

    long_chart_data = daily_chart_data.melt(
        id_vars=DATE_COLUMN,
        value_vars=visible_series,
        var_name="Serie",
        value_name="Putere medie (MW)",
    )

    return (
        alt.Chart(long_chart_data)
        .mark_line(
            strokeWidth=2,
            point=alt.OverlayMarkDef(filled=True, size=22),
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
                scale=alt.Scale(domain=visible_series, range=series_colors),
            ),
            tooltip=[
                alt.Tooltip(f"{DATE_COLUMN}:T", title="Data", format="%d.%m.%Y"),
                alt.Tooltip("Serie:N", title="Serie"),
                alt.Tooltip(
                    "Putere medie (MW):Q",
                    title="Putere medie",
                    format=",.0f",
                ),
            ],
        )
        .properties(height=420)
    )


def create_daily_hours_above_50_chart(
    daily_threshold_data: pd.DataFrame,
) -> alt.Chart | alt.FacetChart:
    calendar_data = daily_threshold_data.copy()
    dates = calendar_data[DATE_COLUMN].dt.normalize()
    year_starts = pd.to_datetime(dates.dt.year.astype(str) + "-01-01")
    calendar_starts = year_starts - pd.to_timedelta(
        year_starts.dt.weekday,
        unit="D",
    )
    calendar_data[CALENDAR_WEEK_COLUMN] = (
        (dates - calendar_starts).dt.days // 7 + 1
    )
    calendar_data[CALENDAR_WEEKDAY_COLUMN] = dates.dt.weekday.map(
        dict(enumerate(WEEKDAY_ORDER))
    )
    calendar_data[CALENDAR_YEAR_COLUMN] = dates.dt.year

    # Put each month name at the week containing its first available day. For
    # multi-year data, the rounded median keeps the shared faceted axis stable.
    month_weeks = (
        calendar_data.assign(_month=dates.dt.month)
        .groupby([CALENDAR_YEAR_COLUMN, "_month"])[CALENDAR_WEEK_COLUMN]
        .min()
        .groupby("_month")
        .median()
        .round()
        .astype(int)
    )
    month_axis_labels = {
        int(week): f"{int(week)} · {ROMANIAN_MONTH_ABBREVIATIONS[month]}"
        for month, week in month_weeks.items()
    }
    month_label_expression = "datum.value"
    for week, label in reversed(list(month_axis_labels.items())):
        month_label_expression = (
            f"datum.value === {week} ? '{label}' : "
            f"{month_label_expression}"
        )

    heatmap = (
        alt.Chart(calendar_data)
        .mark_rect(stroke="#0E1117", strokeWidth=1, cornerRadius=2)
        .encode(
            x=alt.X(
                f"{CALENDAR_WEEK_COLUMN}:O",
                title="Săptămâna anului",
                axis=alt.Axis(
                    values=list(month_axis_labels),
                    labelExpr=month_label_expression,
                    labelAngle=0,
                ),
            ),
            y=alt.Y(
                f"{CALENDAR_WEEKDAY_COLUMN}:O",
                title=None,
                sort=WEEKDAY_ORDER,
            ),
            color=alt.Color(
                f"{HOURS_ABOVE_50_COLUMN}:Q",
                title="Ore peste 50%",
                scale=alt.Scale(
                    domain=[0, 24],
                    range=["#E8F5E9", "#27AE60", "#145A32"],
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{DATE_COLUMN}:T", title="Data", format="%d.%m.%Y"
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
        .properties(height=135)
    )

    if calendar_data[CALENDAR_YEAR_COLUMN].nunique() == 1:
        return heatmap

    return heatmap.facet(
        row=alt.Row(
            f"{CALENDAR_YEAR_COLUMN}:O",
            title=None,
            header=alt.Header(labelFontSize=14, labelOrient="top"),
        )
    )


def _data_year_label(data: pd.DataFrame) -> str:
    years = sorted(data[DATE_COLUMN].dt.year.unique())
    if len(years) == 1:
        return str(years[0])
    return f"{years[0]}–{years[-1]}"


def render_consumption_coverage(
    data: pd.DataFrame,
    daily_data: pd.DataFrame,
) -> None:
    st.header("2. Cât din consum este acoperit orar de surse regenerabile (eolian, solar și hidro) și în câte ore depășește 50%?")

    selected_daily_source = st.radio(
        "Sursa afișată pentru acoperirea orară",
        options=list(RENEWABLE_SOURCE_OPTIONS),
        index=3,
        horizontal=True,
        key="daily_consumption_coverage_source",
    )
    daily_columns, daily_color, daily_description = RENEWABLE_SOURCE_OPTIONS[
        selected_daily_source
    ]
    hourly_coverage = calculate_hourly_renewable_coverage(
        daily_data,
        daily_columns,
    )

    # Display metrics and chart for the selected day
    if hourly_coverage.empty:
        st.warning(
            "Nu există suficiente măsurători valide pentru ziua selectată."
        )
        return

    metrics = calculate_renewable_coverage_metrics(
        hourly_coverage,
        daily_columns,
    )
    metric_columns = st.columns(3)
    metric_columns[0].metric(
        f"Acoperire zilnică · {selected_daily_source}",
        f"{metrics['daily_coverage']:.1f}%",
    )
    metric_columns[1].metric(
        f"Acoperire maximă · {metrics['peak_time']:%H:%M}",
        f"{metrics['peak_coverage']:.1f}%",
    )
    metric_columns[2].metric(
        "Ore peste 50%",
        f"{metrics['hours_above_50']} / {metrics['valid_hours']}",
    )

    render_energy_totals(
        calculate_energy_totals(hourly_coverage),
        "MWh",
    )

    chart_column, explanation_column = st.columns([4, 1])
    with chart_column:
        st.altair_chart(
            create_hourly_renewable_coverage_chart(
                hourly_coverage,
                color=daily_color,
                production_label=selected_daily_source,
            ),
            use_container_width=True,
        )
    with explanation_column:
        st.write(
            "Linia roșie întreruptă marchează pragul de 50% din consum."
        )

    st.divider()

    st.subheader("Câte ore depășesc zilnic pragul de 50%?")

    combined_source = "Hidro + Solar + Eolian"
    yearly_columns, _, yearly_description = RENEWABLE_SOURCE_OPTIONS[
        combined_source
    ]
    daily_threshold_data = calculate_daily_hours_above_50(
        data,
        yearly_columns,
    )
    if daily_threshold_data.empty:
        st.warning("Nu există suficiente date pentru analiza pragului anual.")
        st.info(
            f"**Concluzie:** În ziua selectată, {daily_description} a "
            f"acoperit {metrics['daily_coverage']:.1f}% din consum, iar "
            "pragul de 50% a fost depășit în "
            f"{metrics['hours_above_50']} din cele "
            f"{metrics['valid_hours']} ore valide."
        )
        return

    annual_metrics = calculate_annual_threshold_metrics(daily_threshold_data)
    seasonal_hours = calculate_seasonal_hours_above_50(daily_threshold_data)
    annual_hourly_coverage = calculate_hourly_renewable_coverage(
        data,
        yearly_columns,
    )
    annual_insights = calculate_annual_coverage_insights(
        annual_hourly_coverage,
        daily_threshold_data,
        yearly_columns,
    )

    st.markdown(
        "**Evoluția anuală a producției și consumului · medii zilnice**"
    )
    annual_source = st.radio(
        "Sursa afișată pe întregul an",
        options=list(RENEWABLE_SOURCE_OPTIONS),
        index=3,
        horizontal=True,
        key="annual_generation_source",
    )
    annual_columns, annual_color, _ = RENEWABLE_SOURCE_OPTIONS[annual_source]
    show_annual_consumption = st.checkbox(
        "Afișează consumul",
        value=True,
        key="show_annual_consumption",
    )
    st.altair_chart(
        create_annual_generation_consumption_chart(
            annual_hourly_coverage,
            annual_columns,
            annual_source,
            annual_color,
            show_annual_consumption,
        ),
        use_container_width=True,
    )

    st.altair_chart(
        create_daily_hours_above_50_chart(daily_threshold_data),
        use_container_width=True,
    )

    st.markdown("**Ore peste 50% · total și pe anotimp**")
    summary_columns = st.columns(5)
    summary_columns[0].metric(
        f"Total · {_data_year_label(data)}",
        f"{annual_metrics['hours_above_50']:,} ore",
    )
    summary_columns[0].caption(
        f"{annual_metrics['valid_percentage']:.1f}% din "
        f"{annual_metrics['valid_hours']:,} ore valide."
    )
    for column, season in zip(summary_columns[1:], SEASON_ORDER):
        column.metric(season, f"{seasonal_hours[season]:,} ore")

    st.caption(
        f"Ore valide analizate: {annual_metrics['valid_hours']:,} · "
        f"{annual_metrics['valid_percentage']:.1f}% din orele valide "
        "au depășit pragul."
    )


    st.info(
        f"""**Concluzii:**

- În {_data_year_label(data)}, {yearly_description} a
  reprezentat echivalentul a {annual_insights['annual_coverage']:.1f}% din
  consumul total.
- Pragul de 50% a fost depășit în {annual_metrics['hours_above_50']:,} ore,
  adică în {annual_metrics['valid_percentage']:.1f}% din orele cu date
  valide. Cel puțin o astfel de oră a apărut în
  {annual_insights['days_with_hours_above_50']} din cele
  {len(daily_threshold_data)} zile analizate, iar în
  {annual_insights['full_days_above_50']} zile pragul a fost depășit în
  toate cele 24 de ore.
- Cea mai probabilă explicație pentru vârful hidro de la începutul lunii
  decembrie este simplă: noiembrie 2025 a fost foarte ploios("luna noiembrie 2025 se clasează pe locul 4 în topul celor mai ploioase luni noiembrie din perioada 1961-2025"), astfel a ajuns
  mai multă apă în
  râuri și lacurile de acumulare. Cu mai multă apă disponibilă,
  hidrocentralele au putut produce mai mult. În date, media zilnică hidro a
  ajuns la aproape 3.000 MW pe 2 decembrie, apoi a scăzut treptat.
  [Sursa datelor meteo: Administrația Națională de
  Meteorologie](https://www.meteoromania.ro/clim/caracterizare-lunara/cc_2025_11.html).
- **Primăvara**, producția hidro este ridicată, energia solară începe să
  crească, iar consumul este mai redus decât iarna. Din acest motiv, sursele
  regenerabile acoperă mai des peste 50% din consum. **Iarna**, zilele foarte
  verzi apar atunci când producția eoliană și cea hidro sunt simultan
  ridicate. Diferența importantă este că primăvara apare un tipar sezonier
  mai lung, în timp ce iarna sunt doar câteva zile în care se suprapun
  condiții deosebit de favorabile.
- Acoperirea medie a fost cea mai ridicată în
  {annual_insights['strongest_season'].lower()}
  ({annual_insights['strongest_season_coverage']:.1f}%) și cea mai scăzută
  în {annual_insights['weakest_season'].lower()}
  ({annual_insights['weakest_season_coverage']:.1f}%)."""
    )

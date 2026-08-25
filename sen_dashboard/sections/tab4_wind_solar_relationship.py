"""UI for tab 4: the relationship between wind and solar production."""

import math

import altair as alt
import pandas as pd
import streamlit as st

from sen_dashboard.constants import (
    DATE_COLUMN,
    SOLAR_COLUMN,
    WIND_COLUMN,
)

MAX_SCATTER_POINTS = 4_500
SOLAR_ALTAIR_FIELD = SOLAR_COLUMN.replace("[", r"\[").replace("]", r"\]")
WIND_ALTAIR_FIELD = WIND_COLUMN.replace("[", r"\[").replace("]", r"\]")
GRANULARITY_OPTIONS = {
    "10 minute": ("10min", "ten_minute_correlation"),
    "O oră": ("1h", "hourly_correlation"),
    "O zi": ("1D", "daily_correlation"),
}


def _resample_wind_solar(data: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """Return complete wind and solar averages for a time frequency."""
    return (
        data.set_index(DATE_COLUMN)[[SOLAR_COLUMN, WIND_COLUMN]]
        .resample(frequency)
        .mean()
        .dropna()
        .reset_index()
    )


def calculate_wind_solar_relationship(data: pd.DataFrame) -> dict:
    """Measure whether wind and solar production move together over time."""
    ten_minute_data = _resample_wind_solar(data, "10min")
    hourly_data = _resample_wind_solar(data, "1h")
    daily_data = _resample_wind_solar(data, "1D")
    return {
        "ten_minute_correlation": ten_minute_data[SOLAR_COLUMN].corr(
            ten_minute_data[WIND_COLUMN]
        ),
        "hourly_correlation": hourly_data[SOLAR_COLUMN].corr(
            hourly_data[WIND_COLUMN]
        ),
        "daily_correlation": daily_data[SOLAR_COLUMN].corr(
            daily_data[WIND_COLUMN]
        ),
    }


def create_wind_solar_scatter_chart(
    relationship_data: pd.DataFrame,
) -> tuple[alt.Chart, int]:
    """Create a sampled scatter plot of wind and solar production."""
    total_points = len(relationship_data)
    sample_step = max(1, math.ceil(total_points / MAX_SCATTER_POINTS))
    displayed_data = relationship_data.iloc[::sample_step].copy()

    points = (
        alt.Chart(displayed_data)
        .mark_circle(color="#2F80ED", opacity=0.3, size=45)
        .encode(
            x=alt.X(
                f"{SOLAR_ALTAIR_FIELD}:Q",
                title="Producție solară medie (MW)",
                scale=alt.Scale(zero=True),
            ),
            y=alt.Y(
                f"{WIND_ALTAIR_FIELD}:Q",
                title="Producție eoliană medie (MW)",
                scale=alt.Scale(zero=True),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{DATE_COLUMN}:T",
                    title="Începutul intervalului",
                    format="%d.%m.%Y %H:%M",
                ),
                alt.Tooltip(
                    f"{SOLAR_ALTAIR_FIELD}:Q",
                    title="Solar",
                    format=",.1f",
                ),
                alt.Tooltip(
                    f"{WIND_ALTAIR_FIELD}:Q",
                    title="Eolian",
                    format=",.1f",
                ),
            ],
        )
    )

    return points.properties(height=430), len(displayed_data)


def describe_wind_solar_relationship(correlation: float) -> str:
    """Return a plain-language interpretation of a correlation value."""
    if pd.isna(correlation):
        return "nu poate fi calculată din datele disponibile"

    strength = abs(correlation)
    if strength < 0.2:
        strength_text = "foarte slabă"
    elif strength < 0.4:
        strength_text = "slabă"
    elif strength < 0.6:
        strength_text = "moderată"
    elif strength < 0.8:
        strength_text = "puternică"
    else:
        strength_text = "foarte puternică"

    direction = "negativă" if correlation < 0 else "pozitivă"
    return f"{strength_text} și {direction}"


def _format_correlation(value: float) -> str:
    return "N/A" if pd.isna(value) else f"{value:.2f}"


def render_wind_solar_relationship(
    data: pd.DataFrame,
) -> None:
    """Render the answer to analysis question four."""
    st.header("4. Cât de corelate sunt producția eoliană și cea solară? Se compensează sau produc simultan?")
    st.write(
        "Corelația Pearson arată dacă cele două surse tind să crească și "
        "să scadă împreună. Valorile negative indică o tendință de "
        "compensare, iar cele pozitive indică producție simultană."
    )

    metrics = calculate_wind_solar_relationship(data)
    metric_columns = st.columns(3)
    metric_columns[0].metric(
        "Corelație Pearson la 10 minute",
        _format_correlation(metrics["ten_minute_correlation"]),
    )
    metric_columns[1].metric(
        "Corelație orară Pearson",
        _format_correlation(metrics["hourly_correlation"]),
    )
    metric_columns[2].metric(
        "Corelație între mediile zilnice",
        _format_correlation(metrics["daily_correlation"]),
    )

    st.subheader("Diagrama de dispersie")
    selected_granularity = st.selectbox(
        "Granularitatea diagramei",
        options=list(GRANULARITY_OPTIONS),
    )
    frequency, correlation_key = GRANULARITY_OPTIONS[selected_granularity]
    relationship_data = _resample_wind_solar(data, frequency)

    if relationship_data.empty:
        st.warning(
            "Nu există suficiente date pentru diagrama de dispersie "
            "la granularitatea selectată."
        )
    else:
        scatter_chart, displayed_points = create_wind_solar_scatter_chart(
            relationship_data
        )
        st.altair_chart(scatter_chart, use_container_width=True)
        sample_text = ""
        if displayed_points < len(relationship_data):
            sample_text = (
                f" Pentru lizibilitate sunt afișate {displayed_points:,} "
                f"din {len(relationship_data):,} puncte, selectate uniform;"
                " corelația folosește toate punctele."
            )
        st.caption(
            "Fiecare punct reprezintă mediile solară și eoliană pentru "
            f"intervalul selectat. Corelația Pearson este "
            f"{_format_correlation(metrics[correlation_key])}.{sample_text}"
        )

    with st.expander("Cum au fost calculate și ce înseamnă valorile?"):
        st.markdown(
            """
            **1. Corelația la 10 minute**

            Măsurătorile originale au fost grupate pe intervale de 10 minute.
            Pentru fiecare interval s-au calculat producția solară medie și
            producția eoliană medie, apoi coeficientul de corelație Pearson.

            **2. Corelația orară**

            Măsurătorile au fost grupate pe intervale de o oră, iar
            coeficientul Pearson a fost calculat folosind mediile orare.

            **3. Corelația între mediile zilnice**

            Măsurătorile au fost grupate și pe zile, după care s-a aplicat
            același coeficient Pearson mediilor zilnice.

            **Formula Pearson**
            """
        )

        st.latex(
            r"""
            r = \frac{
                \sum_{i=1}^{n}(S_i - \overline{S})(E_i - \overline{E})
            }{
                \sqrt{\sum_{i=1}^{n}(S_i - \overline{S})^2}
                \sqrt{\sum_{i=1}^{n}(E_i - \overline{E})^2}
            }
            """
        )

        st.markdown(
            """
            **Ce reprezintă simbolurile?**

            | Simbol | Semnificație |
            |:--|:--|
            | $i$ | intervalul analizat: 10 minute, o oră sau o zi |
            | $n$ | numărul total de intervale analizate |
            | $r$ | coeficientul de corelație Pearson, între $-1$ și $+1$ |
            | $S_i$ | producția solară medie din intervalul $i$ |
            | $\\overline{S}$ | media producției solare pentru toate intervalele |
            | $E_i$ | producția eoliană medie din intervalul $i$ |
            | $\\overline{E}$ | media producției eoliene pentru toate intervalele |
           

            Pentru **corelația la 10 minute**, fiecare interval $i$ are 10
            minute. Pentru **corelația orară**, fiecare interval este o oră,
            iar pentru **corelația între mediile zilnice**, fiecare interval
            este o zi. O valoare a lui $r$ apropiată de zero indică o relație
            liniară slabă.

            **Cum interpretăm valoarea lui $r$?**

            - **$r > 0$ — corelație pozitivă:** producția solară și cea
              eoliană tind să crească sau să scadă împreună. Valoarea $+1$
              indică o relație liniară pozitivă perfectă.
            - **$r < 0$ — corelație negativă:** atunci când producția uneia
              crește, cealaltă tinde să scadă, deci sursele se pot compensa.
              Valoarea $-1$ indică o relație liniară negativă perfectă.
            - **$r \\approx 0$ — corelație aproape nulă:** nu există o relație
              liniară clară între variațiile celor două surse. Acest lucru nu
              exclude existența unei relații neliniare.
            """
        )

    ten_minute_correlation = metrics["ten_minute_correlation"]
    relationship_text = describe_wind_solar_relationship(
        ten_minute_correlation
    )
    if pd.isna(ten_minute_correlation):
        st.info(
            "**Concluzie:** Corelația nu poate fi calculată din datele "
            "disponibile."
        )
    else:
        st.info(
            f"""**Concluzie:**

- Diagrama de dispersie nu arată o relație liniară clară între producția
  solară și cea eoliană.
- Corelația la 10 minute este {relationship_text}
  (r = {ten_minute_correlation:.2f}).
- Solarul și eolianul se pot compensa parțial, dar relația nu garantează că
  scăderea uneia va fi însoțită de creșterea celeilalte.
- Punctele numeroase din apropierea axei verticale apar deoarece noaptea
  producția solară de pe axa orizontală este zero sau aproape zero, în timp
  ce producția eoliană poate continua."""
        )

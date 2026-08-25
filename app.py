import streamlit as st

from sen_dashboard.constants import DATA_FILE, DATE_COLUMN
from sen_dashboard.data import get_daily_data, load_data
from sen_dashboard.sections import (
    render_consumption_coverage,
    render_daily_profile,
    render_energy_overview,
    render_renewable_share,
    render_wind_solar_relationship,
)

PAGE_TITLE = (
    "Analiză exploratorie (EDA) axată pe Graficul SEN al Transelectrica"
)


def render_introduction() -> None:
    """Introduce the dashboard in the sidebar and identify its data source."""
    st.sidebar.subheader("Despre dashboard")
    st.sidebar.markdown(
        """
        Acest dashboard prezintă o analiză exploratorie a producției și a
        consumului de energie electrică din România. Sunt urmărite contribuția
        surselor regenerabile, acoperirea consumului și relația dintre
        producția solară și cea eoliană.
        """
    )
    st.sidebar.caption(
        "Sursa datelor: [Transelectrica · Grafic SEN]"
        "(https://www.transelectrica.ro/widget/web/tel/sen-grafic/-/"
        "SENGrafic_WAR_SENGraficportlet?display=IS)."
    )


def render_date_selector(data, key: str):
    """Render an independent date selector for a date-dependent chart."""
    min_date = data[DATE_COLUMN].dt.date.min()
    max_date = data[DATE_COLUMN].dt.date.max()

    selected_date = st.date_input(
        "Selectează data",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        key=key,
    )
    st.caption(
        "Perioada disponibilă: "
        f"{min_date:%d.%m.%Y} – {max_date:%d.%m.%Y}"
    )

    return selected_date


# Questions for the analysis, displayed in a container
def render_analysis_questions() -> None:
    with st.container(border=True):
        st.subheader("Întrebările analizei")
        st.markdown(
            """
            1. Care este ponderea orară a surselor regenerabile (eolian și
               solar) în producția totală și cum se schimbă pe parcursul
               zilei?
            2. Cât din consum este acoperit orar de surse regenerabile
               (eolian, solar și hidro)? În câte ore pe zi depășește 50%?
            3. Cum arată profilul zilnic al solarului (clopot în jurul
               prânzului) și cel al eolianului (neregulat)?
            4. Cât de corelate sunt producția eoliană și cea solară? Se
               compensează sau produc simultan?
            """
        )


def main() -> None:

    # Set up the Streamlit page configuration
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon="⚡",
        layout="wide",
    )
    st.title(PAGE_TITLE)
    render_introduction()

    # Render the analysis questions in a container
    render_analysis_questions()

    # Load the data and handle potential errors
    try:
        data = load_data(DATA_FILE)
    except FileNotFoundError:
        st.error(f"Fișierul de date nu a fost găsit: {DATA_FILE.name}")
        st.stop()
    except (KeyError, ValueError) as error:
        st.error(f"Fișierul de date nu poate fi procesat: {error}")
        st.stop()

    if data.empty:
        st.error("Fișierul nu conține măsurători valide.")
        st.stop()

    # Render the overview with its own date selection.
    overview_date = render_date_selector(data, "overview_date")
    overview_daily_data = get_daily_data(data, overview_date)
    if overview_daily_data.empty:
        st.warning("Nu există date pentru ziua selectată.")
    else:
        render_energy_overview(data, overview_daily_data)

    st.divider()

    # Create tabs for each analysis question and render the corresponding sections

    # question_tabs = st.tabs(
    #     [
    #         "1 - Pondere regenerabile",
    #         "2 - Acoperirea consumului",
    #         "3 - Profil zilnic",
    #         "4 - Solar–Eolian",
    #     ]
    # )

    SPACE = "\u2003"

    question_tabs = st.tabs(
        [
            f"{SPACE * 6}1 - Pondere regenerabile{SPACE * 6}",
            f"{SPACE * 6}2 - Acoperirea consumului{SPACE * 6}",
            f"{SPACE * 6}3 - Profil zilnic{SPACE * 6}",
            f"{SPACE * 6}4 - Solar–Eolian{SPACE * 6}",
        ]
    )

    # Render the content for each tab based on the selected question
    with question_tabs[0]:
        renewable_date = render_date_selector(data, "renewable_share_date")
        renewable_daily_data = get_daily_data(data, renewable_date)
        if renewable_daily_data.empty:
            st.warning("Nu există date pentru ziua selectată.")
        else:
            render_renewable_share(
                data,
                renewable_daily_data,
                renewable_date,
            )
    with question_tabs[1]:
        coverage_date = render_date_selector(data, "coverage_date")
        coverage_daily_data = get_daily_data(data, coverage_date)
        if coverage_daily_data.empty:
            st.warning("Nu există date pentru ziua selectată.")
        else:
            render_consumption_coverage(data, coverage_daily_data)
    with question_tabs[2]:
        profile_date = render_date_selector(data, "daily_profile_date")
        profile_daily_data = get_daily_data(data, profile_date)
        if profile_daily_data.empty:
            st.warning("Nu există date pentru ziua selectată.")
        else:
            render_daily_profile(
                data,
                profile_daily_data,
                profile_date,
            )
    with question_tabs[3]:
        render_wind_solar_relationship(data)


if __name__ == "__main__":
    main()

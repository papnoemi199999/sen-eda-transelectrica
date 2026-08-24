"""Question-centred Streamlit sections."""

from sen_dashboard.sections.energy_overview import render_energy_overview
from sen_dashboard.sections.tab1_renewable_share import render_renewable_share
from sen_dashboard.sections.tab2_consumption_coverage import (
    render_consumption_coverage,
)
from sen_dashboard.sections.tab3_daily_profile import render_daily_profile
from sen_dashboard.sections.tab4_wind_solar_relationship import (
    render_wind_solar_relationship,
)

__all__ = [
    "render_consumption_coverage",
    "render_daily_profile",
    "render_energy_overview",
    "render_renewable_share",
    "render_wind_solar_relationship",
]

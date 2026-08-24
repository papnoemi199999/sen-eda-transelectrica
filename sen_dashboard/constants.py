"""Shared data-column names and visual settings."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "Grafic_SEN.csv"

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
MIN_MEASUREMENTS_PER_HOUR = 1

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

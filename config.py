from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DATES_JSON_PATH = DATA_DIR / "dates.json"
USERS_JSON_PATH = DATA_DIR / "users.json"

HEALTH_CHECK_USER_ID = os.getenv("HEALTH_CHECK_USER_ID")

# Скрипт формирования отчёта и маска итогового Excel-файла в корне проекта.
REPORT_SCRIPT_PATH = PROJECT_ROOT / "Авто-отчет.py"
REPORT_OUTPUT_GLOB = "Сводные с приростами_*.xlsx"

TRACKED_URLS: tuple[str, ...] = (
    "https://cbr.ru/statistics/bank_sector/review",
    "https://cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/",
    # "https://fcfng867-5500.euw.devtunnels.ms/"
)

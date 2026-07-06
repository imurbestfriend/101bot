import asyncio
import logging
import os
import sys
from pathlib import Path

from config import PROJECT_ROOT, REPORT_OUTPUT_GLOB, REPORT_SCRIPT_PATH

logger = logging.getLogger(__name__)


def _latest_report() -> Path | None:
    """Возвращает самый свежий сформированный отчет из корня проекта."""
    files = list(PROJECT_ROOT.glob(REPORT_OUTPUT_GLOB))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


async def generate_report() -> Path:
    """Запускает скрипт Авто-отчет.py и возвращает путь к готовому Excel-файлу.

    Скрипт тяжелый и блокирующий, поэтому выполняется в отдельном процессе,
    чтобы не блокировать event loop бота.
    """
    if not REPORT_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Скрипт отчета не найден: {REPORT_SCRIPT_PATH}")

    before = _latest_report()
    before_mtime = before.stat().st_mtime if before else 0.0

    # На Windows stdout подпроцесса по умолчанию кодируется в cp1252, из-за чего
    # print() с кириллицей в скрипте падает с UnicodeEncodeError — форсируем UTF-8.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(REPORT_SCRIPT_PATH),
        cwd=str(PROJECT_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    stdout, _ = await process.communicate()
    output = stdout.decode("utf-8", errors="replace") if stdout else ""

    if process.returncode != 0:
        logger.error("Скрипт отчета завершился с кодом %s:\n%s", process.returncode, output)
        raise RuntimeError(
            f"Скрипт отчета завершился с ошибкой (код {process.returncode}).\n{output[-1000:]}"
        )

    logger.info("Скрипт отчета выполнен успешно:\n%s", output)

    report = _latest_report()
    if report is None or report.stat().st_mtime <= before_mtime:
        raise FileNotFoundError(
            "Отчет не был сформирован — итоговый файл не найден.\n" + output[-1000:]
        )

    return report

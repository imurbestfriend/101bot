import asyncio
import logging
import os
import sys
from pathlib import Path

from config import PROJECT_ROOT, REPORT_OUTPUT_GLOB, REPORT_SCRIPT_PATH

logger = logging.getLogger(__name__)

# Single-flight: одновременные запросы на отчёт не должны плодить параллельные
# запуски тяжёлого скрипта. Все прогоны делят одни и те же папки (Downloads,
# 101_rar, промежуточные CSV) и итоговый файл с фиксированным именем, поэтому
# параллельно они бы затирали друг друга и ломались. Пока один прогон идёт, все,
# кто нажал «Сформировать отчёт» (и авто-запуск по новой 101-форме), ждут и
# получают один и тот же результат. Отчёт зависит только от данных ЦБ, а не от
# того, кто его запросил, — поэтому общий результат корректен для всех.
_run_lock = asyncio.Lock()
_current_run: "asyncio.Task[Path] | None" = None


def _latest_report() -> Path | None:
    """Возвращает самый свежий сформированный отчет из корня проекта."""
    files = list(PROJECT_ROOT.glob(REPORT_OUTPUT_GLOB))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


async def generate_report() -> Path:
    """Возвращает путь к готовому Excel-отчёту, запуская скрипт при необходимости.

    Реализует single-flight: если формирование уже идёт, повторные вызовы не
    стартуют второй процесс, а дожидаются того же результата. Первый вызов после
    завершения предыдущего прогона запускает свежий (данные ЦБ могли обновиться).
    """
    global _current_run
    async with _run_lock:
        if _current_run is None or _current_run.done():
            _current_run = asyncio.create_task(_run_report_once())
        run = _current_run
    # Ждём результат ВНЕ блокировки, чтобы параллельные вызовы могли присоединиться
    # к тому же прогону, а не выстраивались в очередь за ним.
    return await run


async def _run_report_once() -> Path:
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

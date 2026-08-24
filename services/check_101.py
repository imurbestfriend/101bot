import asyncio
import ssl
from datetime import date

import aiohttp
import certifi
from dateutil.relativedelta import relativedelta

from config import CBR_BASE_URL

# Архивы 101-й формы лежат по адресу вида .../101-YYYYMMDD.rar,
# где дата — 1-е число отчётного месяца. База берётся из CBR_BASE_URL,
# поэтому для тестов источник можно подменить локальным симулятором.
REPORT_101_URL_TEMPLATE = CBR_BASE_URL + "/vfs/credit/forms/101-{date}.rar"

# Страница раздела ЦБ, где публикуется отчётность кредитных организаций.
REPORT_101_PAGE_URL = CBR_BASE_URL + "/banking_sector/otchetnost-kreditnykh-organizaciy/"

# Насколько глубоко в прошлое искать самый свежий архив (в месяцах).
SEARCH_DEPTH_MONTHS = 12


async def _archive_exists(session: aiohttp.ClientSession, probe_date: date) -> bool:
    """HEAD-запрос: проверяем наличие архива, не скачивая тело."""
    url = REPORT_101_URL_TEMPLATE.format(date=probe_date.strftime("%Y%m%d"))
    try:
        async with session.head(url, allow_redirects=True) as response:
            return response.status == 200
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return False


async def newest_available_101() -> str | None:
    """Возвращает дату (YYYYMMDD) самого свежего доступного 101-архива
    или None, если ничего не найдено.

    Идём от горизонта (следующий месяц) назад, пока не встретим первый
    существующий архив — он и есть самый свежий. Обратный проход устойчив
    к возможным пропускам месяцев.
    """
    timeout = aiohttp.ClientTimeout(total=20)
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    horizon = date.today().replace(day=1) + relativedelta(months=1)
    floor = horizon - relativedelta(months=SEARCH_DEPTH_MONTHS)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        probe = horizon
        while probe >= floor:
            if await _archive_exists(session, probe):
                return probe.strftime("%Y%m%d")
            probe -= relativedelta(months=1)

    return None

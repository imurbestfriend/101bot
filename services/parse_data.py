import asyncio
import json
import ssl
from datetime import datetime
from json import JSONDecodeError
import aiohttp
import certifi
from bs4 import BeautifulSoup
from config import DATA_DIR, DATES_JSON_PATH, TRACKED_URLS


async def fetch_data(
    urls: tuple[str, ...] = TRACKED_URLS,
    save_to_json: bool = True,
) -> list[str]:
    """Парсим даты обновления с сайта ЦБ."""
    
    update_info: list[str] = [] #возвращаем пользователю
    payload: list[dict[str, str]] = [] #записываем в json

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    timeout = aiohttp.ClientTimeout(total=20)
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        for url in urls:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    html = await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                update_info.append(f"{url}\nОшибка загрузки: {error}")
                payload.append(
                    {
                        "url": url,
                        "title": "",
                        "last_update": "",
                        "status": "request_error",
                        "checked_at": now,
                    }
                )
                continue

            soup = BeautifulSoup(html, "html.parser")

            block_data = soup.find("div", class_="page-info_last-update")
            block_title = soup.find("span", class_="referenceable")
            title_text = block_title.get_text(strip=True) if block_title else ""

            if block_data is None:
                message = f"{url} ({title_text})\nНе удалось найти блок обновления."
                update_info.append(message)
                payload.append(
                    {
                        "url": url,
                        "title": title_text,
                        "last_update": "",
                        "status": "not_found",
                        "checked_at": now,
                    }
                )
                continue

            data_text = block_data.get_text(strip=True)
            update_info.append(f"{url} ({title_text})\n{data_text}")
            payload.append(
                {
                    "url": url,
                    "title": title_text,
                    "last_update": data_text,
                    "status": "ok",
                    "checked_at": now,
                }
            )

        if save_to_json:
            DATA_DIR.mkdir(exist_ok=True)
            # Сливаем свежие данные страниц с уже сохранёнными записями,
            # чтобы не затирать сторонние записи (например, 101-отчёт),
            # которые ведёт другой обработчик.
            try:
                with open(DATES_JSON_PATH, "r", encoding="utf-8") as file:
                    existing = json.load(file)
            except (FileNotFoundError, JSONDecodeError):
                existing = []

            by_url: dict[str, dict] = {}
            for item in existing:
                if isinstance(item, dict) and "url" in item:
                    by_url[item["url"]] = item
            for record in payload:
                by_url[record["url"]] = record

            with open(DATES_JSON_PATH, "w", encoding="utf-8") as file:
                json.dump(list(by_url.values()), file, ensure_ascii=False, indent=2)

    return update_info

import asyncio
import json
import ssl
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
                }
            )

        if save_to_json:
            DATA_DIR.mkdir(exist_ok=True)
            with open(DATES_JSON_PATH, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
        
    return update_info

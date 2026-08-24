import asyncio
import json
import logging
from datetime import datetime
from json import JSONDecodeError
from aiogram import Bot, Router
from aiogram.types import FSInputFile
from config import (
    DATES_JSON_PATH,
    USERS_JSON_PATH,
    HEALTH_CHECK_USER_ID,
)
from services.parse_data import fetch_data
from services.check_101 import newest_available_101, REPORT_101_PAGE_URL
from services.report import generate_report

router = Router()
logger = logging.getLogger(__name__)

# Синтетический "url" записи 101-отчёта внутри dates.json.
# Не совпадает с реальными страницами из TRACKED_URLS, поэтому 101 хранится
# в общем файле, но обрабатывается отдельной веткой.
REPORT_101_KEY = "cbr-101-report"


def find_record(data, url):
    if not isinstance(data, list):
        return None
    for item in data:
        if isinstance(item, dict) and item.get("url") == url:
            return item
    return None


def upsert_record(data, record):
    if not isinstance(data, list):
        data = []
    for index, item in enumerate(data):
        if isinstance(item, dict) and item.get("url") == record["url"]:
            data[index] = record
            return data
    data.append(record)
    return data


def read_json(path):
    try:
        with open(path, "r", encoding='utf-8') as file:
            data = json.load(file)
            return data
        
    except (FileNotFoundError, JSONDecodeError):
        return []


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_users_id():
    users_id = []
    
    data =  read_json(USERS_JSON_PATH)    

    for item in data:
        users_id.append(item['user_id'])

    return users_id


async def health_check(bot: Bot):
    if not HEALTH_CHECK_USER_ID:
        logger.warning("HEALTH_CHECK_USER_ID не задан, пропуск health_check")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    await bot.send_message(
        chat_id=HEALTH_CHECK_USER_ID,
        text=f"Бот работает — {now}",
    )
    logger.info("health_check отправлен пользователю %s", HEALTH_CHECK_USER_ID)


async def check_for_updates(bot: Bot):
    users_id = await asyncio.to_thread(get_users_id)
    
    old_data = await asyncio.to_thread(read_json, DATES_JSON_PATH)

    await fetch_data()

    new_data = await asyncio.to_thread(read_json, DATES_JSON_PATH)

    # Сопоставляем по url, а не по индексу: в dates.json теперь может быть
    # запись 101-отчёта, которую fetch_data не трогает. Её пропускаем —
    # за 101 отвечает check_new_101_report.
    old_by_url = {
        item["url"]: item
        for item in old_data
        if isinstance(item, dict) and "url" in item
    }

    for new_item in new_data:
        if not isinstance(new_item, dict) or "url" not in new_item:
            continue
        if new_item["url"] == REPORT_101_KEY:
            continue

        old_item = old_by_url.get(new_item["url"])
        if old_item and old_item.get("last_update") != new_item.get("last_update"):
            for user_id in users_id:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"Обновление: {new_item['url']}: {old_item.get('last_update')} -> {new_item.get('last_update')}",
                )
                logger.info(
                    "Sent update notification to user_id=%s for url=%s",
                    user_id,
                    new_item["url"],
                )


def _build_101_record(newest: str) -> dict:
    """Собирает запись 101-отчёта для dates.json."""
    return {
        "url": REPORT_101_KEY,
        "title": "Форма 101 (оборотная ведомость КО)",
        "last_update": datetime.strptime(newest, "%Y%m%d").strftime("%d.%m.%Y"),
        "raw_date": newest,
        "status": "ok",
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "page_url": REPORT_101_PAGE_URL,
    }


async def check_new_101_report(bot: Bot):
    """Отдельная ветка: следим за появлением новых 101-архивов на сайте ЦБ.

    Состояние храним в dates.json той же записью, что и страницы (url =
    REPORT_101_KEY), но сравниваем по raw_date (YYYYMMDD). При первом запуске
    фиксируем базовую линию без рассылки, дальше уведомляем всех пользователей
    только при появлении более свежего архива.
    """
    data = await asyncio.to_thread(read_json, DATES_JSON_PATH)
    record = find_record(data, REPORT_101_KEY)
    last_seen = record.get("raw_date") if isinstance(record, dict) else None

    newest = await newest_available_101()
    if not newest:
        logger.info("101: доступных архивов не найдено")
        return

    new_record = _build_101_record(newest)

    if last_seen is None:
        data = upsert_record(data, new_record)
        await asyncio.to_thread(write_json, DATES_JSON_PATH, data)
        logger.info("101: установлена базовая линия %s (без рассылки)", newest)
        return

    if newest <= last_seen:
        # Нового архива нет — обновляем только метку последней проверки.
        data = upsert_record(data, new_record)
        await asyncio.to_thread(write_json, DATES_JSON_PATH, data)
        logger.info("101: нового нет (последний известный %s)", last_seen)
        return

    # Сначала формируем отчёт и только ПОСЛЕ успешной сборки уведомляем
    # пользователей — уведомление приходит вместе с готовым файлом.
    # last_seen фиксируем в самом конце: если бот перезапустят во время сборки,
    # отчёт не потеряется — на следующей проверке всё повторится.
    logger.info("101: найден новый архив %s, запускаю формирование отчёта", newest)
    human_date = new_record["last_update"]
    users_id = await asyncio.to_thread(get_users_id)

    try:
        report_path = await generate_report()
    except Exception:
        logger.exception("101: не удалось сформировать отчёт по новому архиву")
        for user_id in users_id:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        "Обнаружена новая 101-форма, но сформировать отчёт автоматически "
                        "не удалось. Попробуйте позже кнопкой «Сформировать отчет»."
                    ),
                )
            except Exception:
                logger.exception("101: не смог отправить сообщение об ошибке user_id=%s", user_id)
        # Фиксируем last_seen, чтобы не повторять неудачную попытку на каждой проверке.
        data = upsert_record(data, new_record)
        await asyncio.to_thread(write_json, DATES_JSON_PATH, data)
        return

    # Отчёт готов — теперь уведомляем и сразу отправляем файл.
    document = FSInputFile(report_path)
    for user_id in users_id:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"Появился новый 101-отчёт на ЦБ: {human_date}\n{REPORT_101_PAGE_URL}\n"
                    "Отчёт сформирован — файл ниже."
                ),
            )
            await bot.send_document(chat_id=user_id, document=document)
            logger.info("101: уведомление и отчёт отправлены user_id=%s date=%s", user_id, newest)
        except Exception:
            logger.exception("101: не смог отправить уведомление/отчёт user_id=%s", user_id)

    data = upsert_record(data, new_record)
    await asyncio.to_thread(write_json, DATES_JSON_PATH, data)
            

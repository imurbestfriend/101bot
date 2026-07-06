import asyncio
import json
import logging
from datetime import datetime
from json import JSONDecodeError
from aiogram import Bot, Router
from config import DATES_JSON_PATH, USERS_JSON_PATH, HEALTH_CHECK_USER_ID
from services.parse_data import fetch_data

router = Router()
logger = logging.getLogger(__name__)


def read_json(path):
    try:
        with open(path, "r", encoding='utf-8') as file:
            data = json.load(file)
            return data
        
    except (FileNotFoundError, JSONDecodeError):
        return []


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
    
    
    # print(f'ZIP {list(zip(old_data, new_data))} \n')

    for old_item, new_item in zip(old_data, new_data):
        # print(f'OLD ITEM: {old_item}')
        # print(f'NEW ITEM: {new_item}')
        if old_item["url"] == new_item["url"] and old_item["last_update"] != new_item["last_update"]:
            for user_id in users_id:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"Обновление: {old_item['url']}: {old_item['last_update']} -> {new_item['last_update']}",
                )
                logger.info(
                    "Sent update notification to user_id=%s for url=%s",
                    user_id,
                    old_item["url"],
                )
            

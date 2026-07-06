import asyncio
import logging
import os
from pathlib import Path
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from handlers.commands import router as commands
from handlers.notification import check_for_updates, health_check
from handlers.user_messages import router as user_messages

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена")

dp = Dispatcher()
dp.include_router(commands)
dp.include_router(user_messages)

scheduler = AsyncIOScheduler()

LOGS_DIR = Path("logs")
LOG_FILE = LOGS_DIR / "bot.txt"


def setup_logging() -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )

async def main():
    setup_logging()
    bot = Bot(token=TOKEN)

    scheduler.add_job(check_for_updates, "cron", hour="9, 18", minute=40, args=[bot])
    scheduler.add_job(health_check, "interval", hours=1, args=[bot])
    # scheduler.add_job(check_for_updates, "interval", seconds=10, args=[bot])
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

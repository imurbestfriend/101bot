import logging

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from config import HEALTH_CHECK_USER_ID
from keyboard.menu import main_menu_keyboard
from services.load_data import save_user
from handlers.notification import check_new_101_report

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id
    user_name = message.from_user.first_name
    save_user(user_id, user_name)
    await message.answer(
        f"Привет! ",
        reply_markup=main_menu_keyboard
    )


@router.message(Command('help'))
async def help(message: Message):
    await message.answer('Доступные команды: /help, /start, /check101')


@router.message(Command('check101'))
async def check101(message: Message):
    """Служебная команда: вручную запускает проверку новой 101-формы.

    Доступна только администратору (HEALTH_CHECK_USER_ID) — удобно для тестов,
    чтобы не ждать планировщик (10:05 / 13:05 / 17:05).
    """
    if not HEALTH_CHECK_USER_ID or str(message.from_user.id) != str(HEALTH_CHECK_USER_ID):
        return
    await message.answer("Запускаю проверку новой 101-формы…")
    logger.info("Ручной запуск check_new_101_report пользователем %s", message.from_user.id)
    await check_new_101_report(message.bot)

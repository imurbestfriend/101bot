from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from keyboard.menu import main_menu_keyboard
from services.load_data import save_user

router = Router()

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
    await message.answer('Доступные команды: /help, /start')

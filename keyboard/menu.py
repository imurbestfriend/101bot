from aiogram import Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Обновить данные')],
        [KeyboardButton(text='Сформировать отчет')],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт меню"
)

    

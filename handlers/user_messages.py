from aiogram import F, Router
from aiogram.types import Message
from services.parse_data import fetch_data

router = Router()

@router.message(F.text == 'Обновить данные')
async def text_txt(message: Message):
    parsed_data = await fetch_data(save_to_json=False)
    await message.answer("\n\n".join(parsed_data))

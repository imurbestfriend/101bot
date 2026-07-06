import logging

from aiogram import F, Router
from aiogram.types import FSInputFile, Message
from services.parse_data import fetch_data
from services.report import generate_report

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == 'Обновить данные')
async def text_txt(message: Message):
    parsed_data = await fetch_data(save_to_json=False)
    await message.answer("\n\n".join(parsed_data))


@router.message(F.text == 'Сформировать отчет')
async def make_report(message: Message):
    await message.answer("Формирую отчёт, это может занять несколько минут…")
    try:
        report_path = await generate_report()
    except Exception as error:
        logger.exception("Ошибка при формировании отчета")
        await message.answer(f"Не удалось сформировать отчёт:\n{error}")
        return
    await message.answer_document(FSInputFile(report_path))

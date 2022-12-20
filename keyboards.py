from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import SHOP_COMMAND

start_keyboard = InlineKeyboardMarkup()
start_keyboard.add(InlineKeyboardButton(text="Магазин", callback_data=SHOP_COMMAND))
import sqlite3
import asyncio

import aiogram
from aiogram import Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.webhook import get_new_configured_app, SendMessage
from aiogram.types import ChatType, ParseMode, ContentTypes, Message, CallbackQuery, PreCheckoutQuery
from aiogram.utils.markdown import hbold, bold, text, link

import keyboards
import product
from config import ERROR_PAYMENT_MESSAGE, SHOP_COMMAND

class MyBot:
    def __init__(self, token: str, loop: asyncio.AbstractEventLoop):
        self.bot = Bot(token=token, loop=loop)
        self.shop = product.Shop(self.bot)
        self.dp = Dispatcher(bot=self.bot)

        BAD_CONTENT = ContentTypes.PHOTO & ContentTypes.DOCUMENT & ContentTypes.STICKER & ContentTypes.AUDIO

        self.dp.register_message_handler(self.__start_handler, commands=['start'])
        self.dp.register_message_handler(self.__shop_handler, commands=['shop'])
        self.dp.register_message_handler(self.__got_payment, content_types=ContentTypes.SUCCESSFUL_PAYMENT)
        self.dp.register_callback_query_handler(self.__shop_command, lambda c: c.data == SHOP_COMMAND)
        self.dp.register_callback_query_handler(self.__product_command, lambda c: c.data.startswith("product"))
        self.dp.register_callback_query_handler(self.__buy_command, lambda c: c.data.startswith("buy"))
        self.dp.register_pre_checkout_query_handler(self.__checkout_command, lambda query: True)

    def get_configured_app(self, path):
        return get_new_configured_app(self.dp, path=path)

    async def shutdown(self):
        # Remove webhook.
        await self.bot.delete_webhook()
    
    async def startup(self, webhook_url):
        await self.bot.delete_webhook()
        await self.update_shop()
        await self.dp.skip_updates()
        await self.bot.set_webhook(webhook_url)

    async def update_shop(self):
        await self.shop.update_shop()

    async def __start_handler(self, msg: Message):
        await self.bot.send_message(chat_id=msg.from_user.id, text="Выберите действие:", reply_markup=keyboards.start_keyboard)
    async def __shop_handler(self, msg: Message):
        await self.shop.send_start_msg(msg.from_user.id)
    async def __shop_command(self, query: CallbackQuery):
        await self.bot.answer_callback_query(query.id)
        await self.shop.send_start_msg(query.from_user.id)
    async def __product_command(self, query: CallbackQuery):
        index = int(query.data[8:])

        await self.bot.answer_callback_query(query.id)
        await self.shop.next_product(index=index, user_id=query.from_user.id, message_id=query.message.message_id)
    async def __buy_command(self, query: CallbackQuery):
        index = int(query.data[4:])

        await self.bot.answer_callback_query(query.id)
        await self.shop.buy_product(index, query.from_user.id)
    async def __checkout_command(self, pre_checkout_query: PreCheckoutQuery):
        await self.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True, error_message=ERROR_PAYMENT_MESSAGE)
    async def __got_payment(self, message: Message):
        self.shop.save_transaction(message)
        await self.bot.send_message(chat_id=message.from_user.id, text="Поздравляем вас с приобретением!\nВведите одну из команд для продолжения:\n/shop\n/start")
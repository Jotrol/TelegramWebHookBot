from aiogram import Bot
from aiogram.types import LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup, Message
import sqlite3
import time
import json
import asyncio
import os
import database

from config import *
from keyboards import start_keyboard

class Shop:
    class Product:
        def __init__(self, title: str, desciption: str, photo: str):
            self.title = title
            self.description = desciption
            self.photo = photo
            self.total_cost = 0
            self.prices = []

        def add_subproduct(self, label: str, price: int) -> None:
            self.prices.append(LabeledPrice(label=label, amount=price * ONE_UNIT))
            self.total_cost += price

        def make_invoice(self, index: int, user_id: int) -> dict:
            invoice = {}
            invoice['chat_id'] = user_id
            invoice['provider_token'] = PAYMENTS_PROVIDER_TOKEN
            invoice['currency'] = CURRENCY

            invoice['title'] = self.title
            invoice['description'] = self.description
            invoice['payload'] = f"Have been bought product {index} with title {self.title}"
            invoice['start_parameter'] = f"buy-{index}"
            invoice['prices'] = self.prices

            return invoice

    def __init__(self, bot: Bot):
        self.products = []
        self.bot = bot

        self.accounting = sqlite3.connect("paymenst.db")
        self.accounting.execute("""
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                    currency TEXT,
                                    total_amount REAL,
                                    invoice_payload TEXT,
                                    telegram_payment_charge_id TEXT,
                                    provider_payment_charge_id TEXT,
                                    time REAL,
                                    user_id INTEGER)
                                """
                                )

    def __make_keyboard(self, index: int) -> InlineKeyboardMarkup:
        but_prev = InlineKeyboardButton(text="<", callback_data=f"product-{index - 1}")
        but_next = InlineKeyboardButton(text=">", callback_data=f"product-{index + 1}")
        but_buy = InlineKeyboardButton(text="Купить", callback_data=f"buy-{index}")

        keyboard = InlineKeyboardMarkup()
        if index == 0:
            keyboard.add(but_next)
        elif index == len(self.products) - 1:
            keyboard.add(but_prev)
        else:
            keyboard.add(but_prev, but_next)
        keyboard.add(but_buy)
        return keyboard

    def save_transaction(self, msg: Message) -> None:
        info = msg.successful_payment
        self.accounting.execute(
            """INSERT INTO payments(
                                    currency,
                                    total_amount,
                                    invoice_payload,
                                    telegram_payment_charge_id,
                                    provider_payment_charge_id,
                                    time,
                                    user_id) VALUES(?,?,?,?,?,?,?)
                                """,
            (   
                info.currency,
                info.total_amount / ONE_UNIT,
                info.invoice_payload,
                info.telegram_payment_charge_id,
                info.provider_payment_charge_id,
                time.time(),
                msg.from_user.id
            )
        )
        self.accounting.commit()

    async def next_product(self, index: int, user_id: int, message_id: int) -> None:
        product = self.products[index]

        media = f"{{\"type\" : \"photo\", \"media\" : \"{product.photo}\"}}"
        
        await self.bot.edit_message_media(chat_id=user_id, message_id=message_id, media=media)
        await self.bot.edit_message_caption(chat_id=user_id, message_id=message_id, caption=f"{product.title}\nЦена: {product.total_cost}", reply_markup=self.__make_keyboard(index))

    async def send_start_msg(self, user_id: int) -> None:

        if len(self.products) == 0:
            await self.bot.send_message(chat_id=user_id, text="Простите, но магазин сейчас пуст.\nВернитесь позже", reply_markup=start_keyboard)
            return

        keyboard = InlineKeyboardMarkup()
        if len(self.products) > 1:
            keyboard.add(InlineKeyboardButton(
                text=">", callback_data="product-1"))
        keyboard.add(InlineKeyboardButton(
            text="Купить", callback_data="buy-0"))

        product = self.products[0]
        await self.bot.send_photo(chat_id=user_id, photo=product.photo, caption=f"{product.title}\nЦена: {product.total_cost}", reply_markup=keyboard)

    async def buy_product(self, index: int, user_id: int) -> None:
        await self.bot.send_invoice(**self.products[index].make_invoice(index, user_id))
    
    async def update_shop(self) -> None:
        self.products = await self.__load_products()

    async def __load_photos_to_bot(self, products_db: database.ProductsDatabase) -> None:
        # Get all records those photos not been uploaded to bot yet
        not_loaded = products_db.get_all_unloaded()
        if len(not_loaded) == 0:
            return 
        for product in not_loaded:
            if product[4] == "":
                products_db.upload_photo_to_bot(product[0], EMPTY_PHOTO_ID)
                continue
            with open(product[4], "rb") as photo:
                msg = await self.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=photo)
                os.remove(product[4])
                file_id = msg.photo[-1].file_id
                products_db.upload_photo_to_bot(product[0], file_id)

    async def __load_products(self) -> list:
        products_db = database.ProductsDatabase()
        products = []

        await asyncio.gather(self.__load_photos_to_bot(products_db))

        raw_products_list = products_db.get_all_products()
        for product in raw_products_list:
            temp_product = self.Product(product[1], product[2], product[4])
            subproducts_dict = json.loads(product[3])
            for subproduct in subproducts_dict:
                temp_product.add_subproduct(subproduct['label'], int(subproduct['price']))
            products.append(temp_product)
        products_db.close()
        return products
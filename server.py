import asyncio

from aiohttp import web

import aiohttp_jinja2
import jinja2

from config import BOT_TOKEN, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT, WEBHOOK_URL

import views
import bot
import database

class Server:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

        self.bot = bot.MyBot(BOT_TOKEN, self.loop)

        self.app = self.bot.get_configured_app(WEBHOOK_PATH)
        aiohttp_jinja2.setup(self.app, loader=jinja2.FileSystemLoader('./pages'))

        self.app['products'] = database.ProductsDatabase()
        self.app['admins'] = database.AdminsDatabase()
        self.app['bot'] = self.bot
        self.app['bot_running'] = True

        self.app.on_startup.append(self.__on_startup)
        self.app.on_shutdown.append(self.__on_shutdown)

        self.app.router.add_get('/', views.indexHandler)
        self.app.router.add_get('/index', views.indexHandler)
        self.app.router.add_view('/admin', views.AdminLogin)
        self.app.router.add_view('/admin/logout', views.AdminLogout)
        self.app.router.add_view('/admin/actions', views.AdminActionsGet)
        self.app.router.add_view('/admin/actions/{action}', views.AdminActionsPost)

        self.app.router.add_view('/admin/bot_actions/{action}', views.BotActions)

    def run_app(self):
        web.run_app(self.app, host=WEBAPP_HOST, port=WEBAPP_PORT)
    
    async def __on_startup(self, app):
        await self.bot.startup(WEBHOOK_URL)
    async def __on_shutdown(self, app):
        await self.bot.shutdown()


if __name__ == "__main__":
    s = Server()
    s.run_app()
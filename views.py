from config import ADMIN_LOGIN, ADMIN_PASSWORD, BOT_TOKEN, WEBHOOK_URL
from aiohttp import web
from aiohttp.multipart import MultipartReader
from aiohttp_jinja2 import render_template
import uuid

# there's two benefits: I manually store needed data for me in needed me form
# I manually download photo right into file, w/o temp file, little optimization
async def parse_multipart(reader: MultipartReader) -> dict:
    out = {}

    while True:
        part = await reader.next()
        if not part: break
        # we got file; open temp file, than read file and save the dir into filename
        if part.filename:
            random_name = f"./photos/{uuid.uuid4()}.{part.filename.split('.')[-1]}"
            with open(f"{random_name}", "wb") as f:
                while not part.at_eof(): f.write(await part.read_chunk())
            out[part.name] = [ random_name ]
        else:
            if part.name in out: out[part.name].append(await part.text())
            else: out[part.name] = [ await part.text() ]
    return out


def indexHandler(request):
    return web.FileResponse('./pages/index.html')

# Admin login form
class AdminLogin(web.View):
    async def get(self):
        if self.request.app['admins'].check_user(self.request.remote):
            raise web.HTTPFound('/admin/actions')
        return web.FileResponse('./pages/admin_login.html')

    async def post(self):
        data = await self.request.post()

        login = data['username']
        password = data['password']

        if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
            self.request.app['admins'].add_user(self.request.remote)
            raise web.HTTPFound('/admin/actions')
        raise web.HTTPFound('/index')

class AdminLogout(web.View):
    async def post(self):
        self.request.app['admins'].delete_user(self.request.remote)
        raise web.HTTPFound('/index')

# View only to return rendered template of page
class AdminActionsGet(web.View):
    async def get(self):
        products = self.request.app['products'].get_all_products()
        context = {'products': products, 'TOKEN': BOT_TOKEN, 'bot_running': self.request.app['bot_running'] }
        return render_template('admin_actions.html', self.request, context)

# View to handle only posts to page
class AdminActionsPost(web.View):
    async def post(self):
        method = self.request.match_info['action']
        if method == "add_product":
            return await self.add_product()
        elif method == "edit_product":
            return await self.edit_product()
        elif method == "delete_product":
            return await self.delete_product()
        return web.HTTPNotFound()

    async def add_product(self):
        reader = await self.request.multipart()
        data = await parse_multipart(reader) # I store all form inputs in arrays as values in dict, except 'product-file', because I know it'll be only one occurance

        title = data['product-title'][0]
        description = data['product-description'][0]

        labels = data['subproduct-label']
        prices = data['subproduct-price']

        photo_filename = data['product-file'][0]

        self.request.app['products'].add_product(title, description, labels, prices, photo_filename)

        raise web.HTTPFound('/admin/actions')
    async def edit_product(self):
        reader = await self.request.multipart()
        data = await parse_multipart(reader) # I store all form inputs in arrays as values in dict, except 'product-file', because I know it'll be only one occurance

        _id = int(data['product-id'][0])

        title = data['product-title'][0]
        description = data['product-description'][0]

        labels = data['subproduct-label']
        prices = data['subproduct-price']

        photo_filename = data['product-file'][0]
    
        self.request.app['products'].edit_product(_id, title, description, labels, prices, photo_filename)

        raise web.HTTPFound('/admin/actions')
    async def delete_product(self):
        data = await self.request.post()

        _id = int(data['product-id'])
        self.request.app['products'].delete_product(_id)

        raise web.HTTPFound('/admin/actions')

class BotActions(web.View):
    async def post(self):
        method = self.request.match_info['action']
        if method == "update_shop":
            await self.__update_shop()
        elif method == "stop":
            await self.__stop_bot()
        elif method == "start":
            await self.__start_bot()
    
    async def __update_shop(self):
        bot = self.request.app['bot']
        await bot.update_shop()
        raise web.HTTPFound('/admin/actions')

    async def __start_bot(self):
        bot = self.request.app['bot']
        await bot.startup(WEBHOOK_URL)
        self.request.app['bot_running'] = True
        raise web.HTTPFound('/admin/actions')

    async def __stop_bot(self):
        bot = self.request.app['bot']
        await bot.shutdown()
        self.request.app['bot_running'] = False
        raise web.HTTPFound('/admin/actions')
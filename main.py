import os
import asyncio
import logging
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# --- تنظیمات ---
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
MARZBAN_URL = os.getenv("MARZBAN_URL")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

# --- دیتابیس ---
def init_db():
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, expire_date TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- کلاس Marzban ---
class MarzbanAPI:
    def __init__(self): self.token = None
    async def get_token(self):
        async with aiohttp.ClientSession() as session:
            url = f"{MARZBAN_URL.rstrip('/')}/api/admin/token"
            data = {"username": MARZBAN_USERNAME, "password": MARZBAN_PASSWORD}
            async with session.post(url, data=data) as resp:
                if resp.status == 200:
                    self.token = (await resp.json())['access_token']
                    return True
                return False
    async def create_user(self, user_id, plan_name):
        if not self.token: await self.get_token()
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            url = f"{MARZBAN_URL.rstrip('/')}/api/user"
            # استفاده از نام تست طبق خواسته تو
            username = f"Arshavin_test_{user_id}"
            user_data = {"username": username, "proxies": {"vless": {}}, "data_limit": 0}
            async with session.post(url, json=user_data, headers=headers) as resp:
                if resp.status == 200: return (await resp.json())['subscription_url']
                return None

marzban = MarzbanAPI()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- کیبوردها ---
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_plans"), InlineKeyboardButton(text="🎁 تست رایگان", callback_data="free_trial")],
        [InlineKeyboardButton(text="👤 پروفایل من", callback_data="profile"), InlineKeyboardButton(text="🌐 زبان / Dil", callback_data="language")],
        [InlineKeyboardButton(text="👨‍💻 پشتیبانی", callback_data="support")]
    ])

# --- هندلرها ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 خوش آمدید آرشاوین عزیز!\nبه ربات اختصاصی L2TP VPN خوش آمدید.", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("منوی اصلی:", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "profile")
async def cmd_profile(callback: types.CallbackQuery):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT expire_date, status FROM users WHERE user_id=?", (callback.from_user.id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        text = f"👤 پروفایل کاربری:\nوضعیت: {user[1]}\nانقضا: {user[0]}"
    else:
        text = "شما هنوز اشتراکی ندارید."
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]]))

@dp.callback_query(F.data == "support")
async def cmd_support(callback: types.CallbackQuery):
    await callback.message.edit_text("👨‍💻 جهت پشتیبانی با آیدی زیر در ارتباط باشید:\n@Admin_Support_ID", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]]))

@dp.callback_query(F.data == "free_trial")
async def process_free_trial(callback: types.CallbackQuery):
    sub_url = await marzban.create_user(callback.from_user.id, "Free Trial")
    if sub_url:
        await callback.message.answer(f"✅ اشتراک تست با نام `Arshavin_test_{callback.from_user.id}` ایجاد شد.\n\nلینک: `{sub_url}`", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ خطا در ایجاد اشتراک.")

# --- بخش وب‌هوک ---
async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        return web.Response(status=500)

async def main():
    webhook_path = f"/{BOT_TOKEN}"
    webhook_url = f"{RENDER_URL.rstrip('/')}{webhook_path}"
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=webhook_url)
    
    app = web.Application()
    app.router.add_post(webhook_path, handle_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

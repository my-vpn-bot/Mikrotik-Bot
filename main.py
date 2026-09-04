import os
import asyncio
import logging
import sqlite3
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# --- تنظیمات اولیه ---
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
MARZBAN_URL = os.getenv("MARZBAN_URL")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "تعریف نشده")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "تعریف نشده")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

# --- دیتابیس ---
DB_NAME = "users_data.db"
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, expire_date TEXT, free_trial_used INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_name TEXT, status TEXT, receipt_file TEXT)''')
    conn.commit()
    conn.close()

init_db()

PLANS = {
    "plan_1": {"name": "پلن ۱ ماهه (۳۰ گیگ)", "price": "۲۷۰,۰۰۰", "duration": 30},
    "plan_2": {"name": "پلن ۲ ماهه (۶۰ گیگ)", "price": "۵۱۰,۰۰۰", "duration": 60},
    "plan_3": {"name": "پلن ۳ ماهه (۹۰ گیگ)", "price": "۷۳۰,۰۰۰", "duration": 90},
    "renew": {"name": "تمدید ۱ ماهه", "price": "۲۷۰,۰۰۰", "duration": 30},
}

class OrderState(StatesGroup):
    waiting_for_receipt = State()

class MarzbanAPI:
    def __init__(self):
        self.token = None
    async def get_token(self):
        async with aiohttp.ClientSession() as session:
            url = f"{MARZBAN_URL.rstrip('/')}/api/admin/token"
            data = {"username": MARZBAN_USERNAME, "password": MARZBAN_PASSWORD}
            async with session.post(url, data=data) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    self.token = res['access_token']
                    return True
                return False
    async def create_user(self, username, plan_name):
        if not self.token: await self.get_token()
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            url = f"{MARZBAN_URL.rstrip('/')}/api/user"
            user_data = {"username": f"user_{username}_{int(datetime.now().timestamp())}", "proxies": {"vless": {}}, "data_limit": 0}
            async with session.post(url, json=user_data, headers=headers) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    return res['subscription_url']
                return None

marzban = MarzbanAPI()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_plans")],
        [InlineKeyboardButton(text="🎁 تست رایگان (۲۰۰ مگ)", callback_data="free_trial")],
        [InlineKeyboardButton(text="👨‍💻 پشتیبانی", url="https://t.me/your_support_link")]
    ])

def plans_kb():
    kb = [[InlineKeyboardButton(text=f"{info['name']} - {info['price']} تومان", callback_data=f"order_{key}")] for key, info in PLANS.items()]
    kb.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 خوش آمدید آرشاوین عزیز!\n\nبه ربات مدیریت اشتراک V2Ray خوش آمدید.\n💎 تمام پلن‌ها شامل **کاربر نامحدود** هستند.", reply_markup=main_menu_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("منوی اصلی:", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "buy_plans")
async def show_plans(callback: types.CallbackQuery):
    await callback.message.edit_text("💎 پلن‌های موجود:", reply_markup=plans_kb())

@dp.callback_query(F.data.startswith("order_"))
async def process_order(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data.split("_")[1]
    plan = PLANS[plan_key]
    await state.update_data(selected_plan=plan_key, plan_name=plan['name'])
    text = (
        f"✅ **پلن انتخاب شده:** {plan['name']}\n"
        f"💰 **مبلغ قابل واریز:** {plan['price']} تومان\n\n"
        f"💳 **اطلاعات واریز وجه:**\n"
        f"🔢 شماره کارت: `{PAYMENT_CARD}`\n"
        f"👤 به نام: {PAYMENT_NAME}\n\n"
        f"⚠️ *لطفاً پس از واریز، تصویر رسید را ارسال کنید.*"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ بازگشت", callback_data="buy_plans")]]), parse_mode="Markdown")
    await state.set_state(OrderState.waiting_for_receipt)

@dp.message(OrderState.waiting_for_receipt, F.photo)
async def handle_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("plan_name")
    plan_key = data.get("selected_plan")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, plan_name, status) VALUES (?, ?, ?)", (message.from_user.id, plan_name, "PENDING"))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_{order_id}_{message.from_user.id}_{plan_key}")], [InlineKeyboardButton(text="❌ رد", callback_data=f"reject_{order_id}")]])
    await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🔔 درخواست جدید! سفارش #{order_id}", reply_markup=admin_kb)
    await message.answer("✅ رسید دریافت شد.")
    await state.clear()

@dp.callback_query(F.data.startswith("approve_"))
async def approve_order(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    order_id, user_id, plan_key = parts[1], parts[2], parts[3]
    sub_url = await marzban.create_user(user_id, PLANS[plan_key]['name'])
    if sub_url: await bot.send_message(user_id, f"🎉 لینک سابسکریپشن:\n`{sub_url}`", parse_mode="Markdown")
    await callback.message.edit_caption(caption=f"✅ سفارش #{order_id} تایید شد.")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_order(callback: types.CallbackQuery):
    await callback.message.edit_caption(caption="❌ رد شد.")

@dp.callback_query(F.data == "free_trial")
async def process_free_trial(callback: types.CallbackQuery, state: FSMContext):
    sub_url = await marzban.create_user(f"trial_{callback.from_user.id}", "Free Trial")
    if sub_url: await callback.message.answer(f"✅ لینک تست:\n`{sub_url}`", parse_mode="Markdown")

# --- سرور وب برای رندر (Webhook) ---

async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        logging.error(f"Webhook Error: {e}")
        return web.Response(status=500)

async def main():
    webhook_path = f"/{BOT_TOKEN}"
    webhook_url = f"{RENDER_URL.rstrip('/')}{webhook_path}"
    
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=webhook_url)
    logging.info(f"✅ Webhook set to: {webhook_url}")

    app = web.Application()
    app.router.add_post(webhook_path, handle_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🚀 Server starting on port {port}...")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot stopped.")
        import os
import asyncio
import logging
import sqlite3
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# --- تنظیمات ---
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
MARZBAN_URL = os.getenv("MARZBAN_URL")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "تعریف نشده")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "تعریف نشده")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

# --- دیتابیس ---
def init_db():
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, expire_date TEXT, status TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_name TEXT, status TEXT)''')
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
    async def create_user(self, username, plan_name):
        if not self.token: await self.get_token()
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            url = f"{MARZBAN_URL.rstrip('/')}/api/user"
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
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]]))[InlineKeyboardButton(text="👨‍💻 پشتیبانی", callback_data="support")]
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
    await callback.message.edit_text("👨‍💻 جهت پشتیبانی با آیدی زیر در ارتباط باشید:\n@Admin_ID_Here", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")]]))

@dp.rstrip('/')}{webhook_path}")
    app = web.Application()
    app.router.add_post(webhook_path, handle_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())


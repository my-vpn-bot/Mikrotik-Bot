import os
import logging
import asyncio
import sqlite3
from typing import Optional, Dict, Any

from aiohttp import web, ClientSession, ClientTimeout
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ---------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MarzbanBot")

# ---------------------------------------------------------
# Configuration & Environment Variables
# ---------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MARZBAN_URL = os.getenv("MARZBAN_URL", "").rstrip("/")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6037990000000000")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "Support")

# Webhook URL handling with https:// enforcement
raw_host = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
if raw_host and not raw_host.startswith("http"):
    WEBHOOK_HOST = f"https://{raw_host}"
else:
    WEBHOOK_HOST = raw_host

PORT = int(os.getenv("PORT", "10000"))
DB_PATH = "bot_database.db"

# ---------------------------------------------------------
# Database Operations
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            marzban_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_user(telegram_id: int, username: str, marzban_username: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (telegram_id, username, marzban_username)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username = excluded.username,
            marzban_username = COALESCE(excluded.marzban_username, users.marzban_username)
    """, (telegram_id, username, marzban_username))
    conn.commit()
    conn.close()

def get_user(telegram_id: int) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id, username, marzban_username FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"telegram_id": row[0], "username": row[1], "marzban_username": row[2]}
    return None

# ---------------------------------------------------------
# Marzban API Client
# ---------------------------------------------------------
class MarzbanAPI:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token: Optional[str] = None

    async def get_token(self) -> Optional[str]:
        if not self.base_url:
            return None
        url = f"{self.base_url}/api/admin/token"
        data = {"username": self.username, "password": self.password}
        timeout = ClientTimeout(total=10)
        async with ClientSession(timeout=timeout) as session:
            try:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        res_data = await response.json()
                        self.token = res_data.get("access_token")
                        return self.token
                    logger.error(f"Failed to get Marzban token: Status {response.status}")
            except Exception as e:
                logger.error(f"Error connecting to Marzban API: {e}")
        return None

    async def get_user_info(self, marzban_username: str) -> Optional[Dict[str, Any]]:
        if not self.token:
            await self.get_token()
        if not self.token:
            return None

        url = f"{self.base_url}/api/user/{marzban_username}"
        headers = {"Authorization": f"Bearer {self.token}"}
        timeout = ClientTimeout(total=10)
        async with ClientSession(timeout=timeout) as session:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        await self.get_token()
                        headers["Authorization"] = f"Bearer {self.token}"
                        async with session.get(url, headers=headers) as retry_res:
                            if retry_res.status == 200:
                                return await retry_res.json()
            except Exception as e:
                logger.error(f"Error fetching Marzban user info: {e}")
        return None

marzban_client = MarzbanAPI(MARZBAN_URL, MARZBAN_USERNAME, MARZBAN_PASSWORD)

# ---------------------------------------------------------
# FSM States & Router
# ---------------------------------------------------------
class Form(StatesGroup):
    waiting_for_marzban_username = State()

router = Router()

# Keyboards (اصلاح شد: callback_data جایگزین callback_query_data شد)
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 وضعیت اشتراک", callback_data="check_status")],
        [InlineKeyboardButton(text="🔗 ثبت نام کاربری مرزبان", callback_data="set_username")],
        [InlineKeyboardButton(text="💳 شماره کارت پرداخت", callback_data="show_card")],
        [InlineKeyboardButton(text="💬 ارتباط با پشتیبانی", callback_data="contact_support")]
    ])
    return keyboard

# ---------------------------------------------------------
# Handlers
# ---------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    save_user(message.from_user.id, message.from_user.username or "")
    text = (
        f"سلام {message.from_user.first_name} عزیز! 👋\n\n"
        "به ربات مدیریت اشتراک خوش آمدید. لطفاً گزینه مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@router.callback_query(F.data == "set_username")
async def process_set_username(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Form.waiting_for_marzban_username)
    await callback.message.edit_text(
        "لطفاً نام کاربری (Username) اشتراک مرزبان خود را دقیق ارسال کنید:"
    )

@router.message(Form.waiting_for_marzban_username)
async def save_marzban_username(message: Message, state: FSMContext):
    m_username = message.text.strip()
    save_user(message.from_user.id, message.from_user.username or "", m_username)
    await state.clear()
    await message.answer(
        f"✅ نام کاربری `{m_username}` با موفقیت ثبت شد!",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "check_status")
async def check_status(callback: CallbackQuery):
    await callback.answer() # پاسخ سریع به دکمه تلگرام برای جلوگیری از Spinner
    user_data = get_user(callback.from_user.id)
    if not user_data or not user_data.get("marzban_username"):
        await callback.message.edit_text(
            "❌ شما هنوز نام کاربری مرزبان خود را ثبت نکرده‌اید.\n"
            "لطفاً ابتدا از دکمه زیر نام کاربری را تنظیم کنید.",
            reply_markup=get_main_keyboard()
        )
        return

    m_user = user_data["marzban_username"]
    await callback.message.edit_text("⏳ در حال دریافت اطلاعات از سرور...")
    info = await marzban_client.get_user_info(m_user)

    if not info:
        await callback.message.edit_text(
            f"❌ خطایی در دریافت اطلاعات کاربر `{m_user}` رخ داد.\n"
            "ممکن است نام کاربری اشتباه باشد یا سرور مرزبان در دسترس نباشد.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return

    status = info.get("status", "نامشخص")
    data_limit = (info.get("data_limit") or 0) / (1024 ** 3)  # GB
    used_traffic = (info.get("used_traffic") or 0) / (1024 ** 3)  # GB
    expire = info.get("expire", "بدون انقضا")

    res_text = (
        f"📊 **وضعیت اشتراک شما**\n\n"
        f"👤 نام کاربری: `{m_user}`\n"
        f"⚡ وضعیت: `{status}`\n"
        f"📉 مصرفی: `{used_traffic:.2f} GB` از `{data_limit:.2f} GB`\n"
        f"📅 تاریخ انقضا: `{expire}`"
    )
    await callback.message.edit_text(res_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@router.callback_query(F.data == "show_card")
async def show_card(callback: CallbackQuery):
    await callback.answer()
    text = (
        f"💳 **اطلاعات کارت جهت واریز:**\n\n"
        f"`{PAYMENT_CARD}`\n\n"
        "لطفاً پس از واریز، فیش پرداختی را برای پشتیبانی ارسال کنید."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@router.callback_query(F.data == "contact_support")
async def contact_support(callback: CallbackQuery):
    await callback.answer()
    text = f"💬 برای ارتباط مستقیم با پشتیبانی می‌توانید به آیدی زیر پیام دهید:\n\n@{SUPPORT_USERNAME}"
    await callback.message.edit_text(text, reply_markup=get_main_keyboard())

# ---------------------------------------------------------
# Health Check / Render Webhook Server
# ---------------------------------------------------------
async def health_check(request):
    return web.Response(text="Bot is healthy and running!", status=200)

async def on_startup(bot: Bot):
    if WEBHOOK_HOST:
        webhook_url = f"{WEBHOOK_HOST}/webhook"
        logger.info(f"Setting webhook to: {webhook_url}")
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
    else:
        logger.warning("WEBHOOK_HOST is empty! Running without setting webhook.")

def main():
    init_db()
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable missing!")
        return

    masked_token = BOT_TOKEN[:6] + "..." if len(BOT_TOKEN) > 6 else "Invalid"
    logger.info(f"Starting bot with token prefix: {masked_token}")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    if WEBHOOK_HOST:
        dp.startup.register(on_startup)
        app = web.Application()
        app.router.add_get("/", health_check)
        app.router.add_get("/health", health_check)
        
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot
        )
        webhook_requests_handler.register(app, path="/webhook")
        setup_application(app, dp, bot=bot)
        
        logger.info(f"Starting aiohttp server on port {PORT}...")
        web.run_app(app, host="0.0.0.0", port=PORT)
    else:
        logger.info("No WEBHOOK_HOST detected. Fallback to Polling mode...")
        asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    main()

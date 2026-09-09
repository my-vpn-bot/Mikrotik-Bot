import os
import sys
import logging
import asyncio
import sqlite3
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery
)

# Configuration & Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("Mikrotik-Bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    logger.critical("BOT_TOKEN not found!")
    sys.exit(1)

PORT = int(os.getenv("PORT", 10000))
DB_PATH = "bot_database.db"

# اصلاح و نرمال‌سازی لینک پشتیبانی
raw_support = os.getenv("SUPPORT_USERNAME", "L2TP_Support").strip()
if raw_support.startswith("http://") or raw_support.startswith("https://"):
    SUPPORT_URL = raw_support
else:
    clean_username = raw_support.replace("@", "").strip()
    SUPPORT_URL = f"https://t.me/{clean_username}"

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9918-0000-0000").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "رحیمی").strip()

PLAN1_PRICE = os.getenv("PLAN1_PRICE", "۲۵۰,۰۰۰").strip()
PLAN2_PRICE = os.getenv("PLAN2_PRICE", "۴۰۰,۰۰۰").strip()
PLAN3_PRICE = os.getenv("PLAN3_PRICE", "۶۰۰,۰۰۰").strip()

# Database Setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, join_date TEXT, balance INTEGER DEFAULT 0)")
    conn.commit()
    conn.close()

init_db()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Keyboards
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ],
    resize_keyboard=True,
    is_persistent=True
)

plans_inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=f"🔹 پلن ۱ ماهه ({PLAN1_PRICE} تومان)", callback_data="buy_plan_1")],
    [InlineKeyboardButton(text=f"🔹 پلن ۲ ماهه ({PLAN2_PRICE} تومان)", callback_data="buy_plan_2")],
    [InlineKeyboardButton(text=f"🔹 پلن ۳ ماهه ({PLAN3_PRICE} تومان)", callback_data="buy_plan_3")],
    [InlineKeyboardButton(text="🧾 ارسال فیش واریزی", url=SUPPORT_URL)]
])

support_inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💬 ارتباط با پشتیبانی / ارسال رسید", url=SUPPORT_URL)]
])

# Handlers
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, join_date) VALUES (?, ?, ?, ?)",
        (message.from_user.id, message.from_user.username or "", message.from_user.full_name or "", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    await message.answer(f"سلام {message.from_user.full_name} عزیز! 🌹\nبه ربات رسمی فروش و مدیریت اشتراک خوش آمدید.", reply_markup=main_keyboard)

@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy(message: types.Message):
    await message.answer("🛍️ لیست پلن‌های فعال اشتراک اختصاصی:\n\n👇 لطفاً پلن مورد نظر خود را انتخاب کنید:", reply_markup=plans_inline_keyboard)

@dp.callback_query(F.data.startswith("buy_plan_"))
async def handle_plan_callback(callback: CallbackQuery):
    plan_id = callback.data.split("_")[-1]
    prices = {"1": PLAN1_PRICE, "2": PLAN2_PRICE, "3": PLAN3_PRICE}
    await callback.message.answer(
        f"💳 اطلاعات پرداخت:\nمبلغ: {prices.get(plan_id)} تومان\nشماره کارت: `{CARD_NUMBER}`\nبه نام: **{CARD_HOLDER}**",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧾 ارسال فیش واریزی", url=SUPPORT_URL)]])
    )
    await callback.answer()

@dp.message(F.text == "💰 شارژ حساب")
async def handle_wallet_charge(message: types.Message):
    await message.answer(
        f"💳 شماره کارت: `{CARD_NUMBER}`\n👤 به نام: **{CARD_HOLDER}**\n\nپس از واریز، عکس رسید را به پشتیبانی ارسال کنید:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧾 ارسال فیش واریزی", url=SUPPORT_URL)]])
    )

@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: types.Message):
    await message.answer("👥 واحد پشتیبانی:", reply_markup=support_inline_keyboard)

@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account_info(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, join_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    balance = row[0] if row else 0
    join_date = row[1] if row else "نامشخص"

    info_text = (
        f"📊 اطلاعات حساب کاربری شما:\n\n"
        f"🆔 شناسه کاربری: `{user_id}`\n"
        f"👤 نام: {message.from_user.full_name}\n"
        f"💰 موجودی کیف پول: {balance:,} تومان\n"
        f"📅 تاریخ عضویت: {join_date}"
    )
    await message.answer(info_text, parse_mode="Markdown")

@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: types.Message):
    await message.answer("💎 در حال حاضر اشتراک فعالی برای شما ثبت نشده است.\nبرای تهیه اشتراک از گزینه «🛒 خرید اشتراک» استفاده کنید.")

@dp.message(F.text == "❓ سوالات متداول")
async def handle_faq(message: types.Message):
    faq_text = (
        "❓ سوالات متداول:\n\n"
        "۱. تحویل اشتراک چقدر زمان می‌برد؟\n"
        "پس از ارسال فیش و تایید، در سریع‌ترین زمان ارسال می‌شود.\n\n"
        "۲. آیا سرویس‌ها دارای ضمانت هستند؟\n"
        "بله، تمام پلن‌ها دارای پشتیبانی و ضمانت کیفیت در طول دوره هستند."
    )
    await message.answer(faq_text)

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs(message: types.Message):
    await message.answer(f"⚙️ راهنمای اتصال و کانفیگ‌ها:\n\n📢 برای دریافت آخرین نرم‌افزارها و آموزش‌ها به کانال ما مراجعه کنید:\n{CHANNEL_URL}")

# Health Check & Server
async def health_check(request):
    return web.Response(text="Mikrotik-Bot is active!", status=200)

async def main():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

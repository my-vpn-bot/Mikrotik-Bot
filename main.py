import os
import asyncio
import logging
import sqlite3
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputFile
)
from aiohttp import web

# ==================== تنظیمات و متغیرها ====================
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENpw5te1pehmjX0X")
ADMIN_ID = int(os.getenv("ADMIN_ID", "2786850266"))
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/")
PORT = int(os.getenv("PORT", 10000))

# مقادیر فنی ثابت
VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "GAPGPTMASKTOKENpw5te1pehmjX1X"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== دیتابیس ====================
DB_NAME = "bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_name TEXT,
            amount INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def add_user_to_db(user_id, username, full_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                   (user_id, username, full_name))
    conn.commit()
    conn.close()

def log_order(user_id, plan_name, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, plan_name, amount) VALUES (?, ?, ?)",
                   (user_id, plan_name, amount))
    conn.commit()
    conn.close()

# ==================== استیت‌ها (FSM) ====================
class SupportState(StatesGroup):
    waiting_for_message = State()

class PaymentState(StatesGroup):
    waiting_for_receipt = State()

# ==================== کیبوردهای اصلی ====================
def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🛒 خرید اشتراک"),
        KeyboardButton("🔄 تمدید اشتراک"),
        KeyboardButton("📊 پنل کاربری IBSng"),
        KeyboardButton("🎁 طرح جبرانی مشترکین"),
        KeyboardButton("📱 راهنمای اتصال"),
        KeyboardButton("💬 پشتیبانی آنلاین"),
        KeyboardButton("📢 کانال رسمی")
    )
    return kb

def get_plans_inline_keyboard():
    ikb = InlineKeyboardMarkup(row_width=1)
    # پلن‌های ماهانه عادی + ۱۰ گیگ هدیه
    ikb.add(
        InlineKeyboardButton("🔹 اشتراک ۱ ماهه تک کاربره (+۱۰ گیگ هدیه) — ۲۰۰,۰۰۰ تومان", callback_data="buy_1m_1u"),
        InlineKeyboardButton("🔹 اشتراک ۱ ماهه دو کاربره (+۱۰ گیگ هدیه) — ۲۵۰,۰۰۰ تومان", callback_data="buy_1m_2u"),
        InlineKeyboardButton("🔹 اشتراک ۲ ماهه تک کاربره (+۱۰ گیگ هدیه) — ۳۸۰,۰۰۰ تومان", callback_data="buy_2m_1u"),
        InlineKeyboardButton("🔹 اشتراک ۲ ماهه دو کاربره (+۱۰ گیگ هدیه) — ۴۳۰,۰۰۰ تومان", callback_data="buy_2m_2u"),
        InlineKeyboardButton("🔹 اشتراک ۳ ماهه تک کاربره (+۱۰ گیگ هدیه) — ۵۵۰,۰۰۰ تومان", callback_data="buy_3m_1u"),
        InlineKeyboardButton("🔹 اشتراک ۳ ماهه دو کاربره (+۱۰ گیگ هدیه) — ۶۰۰,۰۰۰ تومان", callback_data="buy_3m_2u"),
        # پلن‌های VIP ترافیک نامحدود
        InlineKeyboardButton("⭐ اشتراک VIP ترافیک نامحدود (تک کاربره) — ۳۰۰,۰۰۰ تومان", callback_data="buy_vip_1u"),
        InlineKeyboardButton("⭐ اشتراک VIP ترافیک نامحدود (دو کاربره) — ۴۰۰,۰۰۰ تومان", callback_data="buy_vip_2u")
    )
    return ikb

# دیکشنری اطلاعات پلن‌ها
PLANS = {
    "buy_1m_1u": ("۱ ماهه تک کاربره (+۱۰ گیگ هدیه)", 200000),
    "buy_1m_2u": ("۱ ماهه دو کاربره (+۱۰ گیگ هدیه)", 250000),
    "buy_2m_1u": ("۲ ماهه تک کاربره (+۱۰ گیگ هدیه)", 380000),
    "buy_2m_2u": ("۲ ماهه دو کاربره (+۱۰ گیگ هدیه)", 430000),
    "buy_3m_1u": ("۳ ماهه تک کاربره (+۱۰ گیگ هدیه)", 550000),
    "buy_3m_2u": ("۳ ماهه دو کاربره (+۱۰ گیگ هدیه)", 600000),
    "buy_vip_1u": ("VIP ترافیک نامحدود تک کاربره", 300000),
    "buy_vip_2u": ("VIP ترافیک نامحدود دو کاربره", 400000),
}

# ==================== هندلرهای پیام ====================
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    add_user_to_db(message.from_user.id, message.from_user.username, message.from_user.full_name)
    welcome_text = (
        f"سلام {message.from_user.first_name} عزیز! 🌹\n\n"
        "به ربات رسمی فروش و مدیریت سرویس‌های **L2TP VPN 24/7** خوش آمدید.\n\n"
        "⚡ سرورهای پرسرعت اختصاصی آلمان با پایداری کامل و آی‌پی ثابت\n"
        "برای انتخاب سرویس یا تمدید اشتراک، از دکمه‌های زیر استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text in ["🛒 خرید اشتراک", "🔄 تمدید اشتراک"])
async def buy_handler(message: types.Message):
    msg_text = (
        "🛍 **لیست تعرفه‌های رسمی اشتراک L2TP VPN 24/7** 🛍\n\n"
        "🎁 تمامی پلن‌های حجمی شامل **۱۰ گیگابایت ترافیک هدیه** هستند.\n"
        "⭐ پلن‌های VIP دارای **ترافیک کاملاً نامحدود** می‌باشند.\n\n"
        "👇 لطفاً پلن مورد نظر خود را برای صدور فاکتور انتخاب نمایید:"
    )
    await message.answer(msg_text, reply_markup=get_plans_inline_keyboard(), parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def process_plan_selection(callback_query: types.CallbackQuery, state: FSMContext):
    plan_key = callback_query.data
    if plan_key in PLANS:
        plan_name, price = PLANS[plan_key]
        await state.update_data(plan_name=plan_name, price=price)
        
        invoice_text = (
            f"🧾 **پیش‌فاکتور سفارش شما:**\n\n"
            f"🔹 **سرویس:** {plan_name}\n"
            f"💰 **مبلغ قابل پرداخت:** {price:,} تومان\n\n"
            f"💳 **شماره کارت جهت واریز:**\n"
            f"`{PAYMENT_CARD}`\n"
            f"👤 **به نام:** {PAYMENT_NAME}\n\n"
            "📌 لطفاً پس از واریز، **تصویر فیش واریزی** خود را در همین قسمت ارسال نمایید تا سفارش شما ثبت و تحویل داده شود."
        )
        await bot.send_message(callback_query.from_user.id, invoice_text, parse_mode="Markdown")
        await PaymentState.waiting_for_receipt.set()
    await callback_query.answer()

@dp.message_handler(state=PaymentState.waiting_for_receipt, content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT])
async def process_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("plan_name", "نامشخص")
    price = data.get("price", 0)
    
    log_order(message.from_user.id, plan_name, price)
    
    # ارسال به ادمین
    admin_alert = (
        f"🔔 **رسید پرداخت جدید دریافت شد!**\n\n"
        f"👤 کاربر: {message.from_user.full_name} (`{message.from_user.id}`)\n"
        f"🆔 آیدی: @{message.from_user.username or 'ندارد'}\n"
        f"📦 پلن انتخابی: {plan_name}\n"
        f"💰 مبلغ: {price:,} تومان"
    )
    if message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_alert, parse_mode="Markdown")
    elif message.document:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=admin_alert, parse_mode="Markdown")

    await message.answer("✅ فیش واریزی شما با موفقیت دریافت شد و در صف تایید قرار گرفت. پس از بررسی ادمین، مشخصات اکانت برای شما ارسال خواهد شد.", reply_markup=get_main_keyboard())
    await state.finish()

# ==================== پنل IBSng ====================
@dp.message_handler(lambda msg: msg.text == "📊 پنل کاربری IBSng")
async def ibsng_panel_handler(message: types.Message):
    text = (
        "📊 **ورود به پنل کاربری IBSng**\n\n"
        "جهت مشاهده میزان مصرف حجم، روزهای باقیمانده و وضعیت اتصال خود روی لینک زیر کلیک کنید:\n\n"
        f"🌐 [ورود به سامانه IBSng]({IBSNG_PANEL_URL})\n\n"
        "⚠️ **هشدار مهم:**\n"
        "«برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.»"
    )
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

# ==================== طرح جبرانی ====================
@dp.message_handler(lambda msg: msg.text == "🎁 طرح جبرانی مشترکین")
async def compensation_handler(message: types.Message):
    text = (
        "🎁 **طرح ویژهٔ جبرانی مشترکین وفادار**\n\n"
        "کاربران گرامی که در طول دوره‌های گذشته اشتراک فعال داشته‌اند و به هر دلیل سرویس آن‌ها قطع بوده است:\n\n"
        "📌 کافیست **نام کاربری قبلی** یا **تصویر فیش واریزی** خود را برای پشتیبانی ارسال فرمایید.\n"
        "سرویس شما به صورت کامل، از نو و به همراه **۱۰ گیگابایت ترافیک هدیه** فعال‌سازی خواهد شد."
    )
    await message.answer(text, parse_mode="Markdown")

# ==================== راهنما و اطلاعات اتصال ====================
@dp.message_handler(lambda msg: msg.text == "📱 راهنمای اتصال")
async def connection_guide_handler(message: types.Message):
    guide_text = (
        "📱 **اطلاعات و تنظیمات اتصال L2TP VPN:**\n\n"
        f"🌐 **Server Address / سرور:** `{VPN_SERVER_IP}`\n"
        f"🔑 **IPsec Pre-Shared Key / کلید امنیتی:** `{IPSEC_SECRET}`\n"
        "👤 **Username & Password:** نام کاربری و رمزعبور اختصاصی شما\n\n"
        "📌 قابل اتصال در انواع گوشی‌های آیفون (iOS)، اندروید، ویندوز و مودم/روتر بدون نیاز به نصب نرم‌افزار جانبی."
    )
    await message.answer(guide_text, parse_mode="Markdown")

# ==================== پشتیبانی و کانال ====================
@dp.message_handler(lambda msg: msg.text == "💬 پشتیبانی آنلاین")
async def support_info(message: types.Message):
    await message.answer(f"💬 جهت ارتباط با واحد پشتیبانی و رفع مشکلات:\n👉 {SUPPORT_ID}")

@dp.message_handler(lambda msg: msg.text == "📢 کانال رسمی")
async def channel_info(message: types.Message):
    await message.answer(f"📢 عضویت در کانال اطلاع‌رسانی آخرین اخبار و سرورها:\n👉 {CHANNEL_URL}")

# ==================== دستورات ادمین ====================
@dp.message_handler(commands=['stats', 'report'], user_id=ADMIN_ID)
async def admin_stats(message: types.Message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM orders")
    order_data = cursor.fetchone()
    total_orders = order_data[0] or 0
    total_revenue = order_data[1] or 0
    conn.close()
    
    report_text = (
        "📊 **گزارش آماری سرور و ربات:**\n\n"
        f"👥 کل کاربران ثبت‌شده: {total_users:,} نفر\n"
        f"📦 کل سفارشات ثبت‌شده: {total_orders:,} عدد\n"
        f"💰 مجموع فروش: {total_revenue:,} تومان\n"
    )
    await message.answer(report_text, parse_mode="Markdown")

# ==================== وب‌سرور برای Render (Keep-Alive) ====================
async def health_check(request):
    return web.Response(text="Bot is running active!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    await start_server()
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())

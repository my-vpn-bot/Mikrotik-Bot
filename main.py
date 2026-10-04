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

# ==================== تنظیمات و لاگ ====================
logging.basicConfig(level=logging.INFO)

# دریافت توکن دقیق از متغیر محیطی رندر
BOT_TOKEN = os.environ["BOT_TOKEN"]

# مدیریت و استخراج صحیح ID ادمین
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "02786850266").strip()
clean_admin_id = ADMIN_ID_RAW.lstrip('0')
ADMIN_ID = int(clean_admin_id) if clean_admin_id.isdigit() else 2786850266

SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/").strip()
OPENVPN_FILE_PATH = os.getenv("OPENVPN_FILE_PATH", "files/openvpn/client.ovpn").strip()

# آدرس سرور L2TP VPN و کلید پیش‌فرض IPsec
VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = ".12345678"

CARD_IMAGE_PATH = "شماره کارت1.jpg"
TARIFF_IMAGE_PATH = "تعرفه.jpg"

# ساختار ربات با توکن محیطی
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== دیتابیس SQLite ====================
DB_FILE = "bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    join_date TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    plan_name TEXT,
                    amount_toman INTEGER,
                    order_date TEXT
                )''')
    conn.commit()
    conn.close()

def add_user_to_db(user: types.User):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date_str, _, _ = get_persian_datetime()
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name, username, join_date) VALUES (?, ?, ?, ?)",
        (user.id, user.full_name or "", user.username or "", date_str)
    )
    conn.commit()
    conn.close()

def record_order_in_db(user_id: int, plan_name: str, price_str: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date_str, _, _ = get_persian_datetime()
    amount = 0
    try:
        clean_price = price_str.replace("تومان", "").replace(",", "").strip()
        amount = int(''.join(filter(str.isdigit, clean_price)))
    except Exception:
        amount = 0
    c.execute(
        "INSERT INTO orders (user_id, plan_name, amount_toman, order_date) VALUES (?, ?, ?, ?)",
        (user_id, plan_name, amount, date_str)
    )
    conn.commit()
    conn.close()

def get_daily_sales_report():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date_str, _, _ = get_persian_datetime()
    c.execute("SELECT COUNT(*), SUM(amount_toman) FROM orders WHERE order_date = ?", (date_str,))
    row = c.fetchone()
    conn.close()
    count = row[0] if row and row[0] else 0
    total_sum = row[1] if row and row[1] else 0
    return count, total_sum

def get_total_users_count() -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

init_db()

# ==================== وضعیت‌های FSM ====================
class OrderState(StatesGroup):
    waiting_for_receipt = State()

class ChargeState(StatesGroup):
    waiting_for_receipt = State()
    waiting_for_username = State()

class SupportState(StatesGroup):
    waiting_for_username_and_msg = State()

# ==================== تعرفه‌ها ====================
PLANS = {
    "vip_1u": {"name": "⭐ اشتراک 1 ماهه VIP تک کاربره ترافیک نامحدود", "price": "350,000 تومان"},
    "1m_1u": {"name": "اشتراک 1 ماهه تک کاربره (30 گیگ + 10 گیگ هدیه)", "price": "200,000 تومان"},
    "1m_2u": {"name": "اشتراک 1 ماهه دو کاربره (30 گیگ + 10 گیگ هدیه)", "price": "250,000 تومان"},
    "2m_1u": {"name": "اشتراک 2 ماهه تک کاربره (60 گیگ + 10 گیگ هدیه)", "price": "380,000 تومان"},
    "2m_2u": {"name": "اشتراک 2 ماهه دو کاربره (60 گیگ + 10 گیگ هدیه)", "price": "430,000 تومان"},
    "3m_1u": {"name": "اشتراک 3 ماهه تک کاربره (90 گیگ + 10 گیگ هدیه)", "price": "550,000 تومان"},
    "3m_2u": {"name": "اشتراک 3 ماهه دو کاربره (90 گیگ + 10 گیگ هدیه)", "price": "600,000 تومان"},
}

# ==================== تاریخ شمسی ====================
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    jy = 0 if gy <= 1600 else 979
    gy -= 621 if gy <= 1600 else 1600
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    jy += (days - 1) // 365
    if days > 0: days = (days - 1) % 365
    jm = (days // 31) + 1 if days < 186 else 7 + ((days - 186) // 30)
    jd = 1 + (days % 31 if days < 186 else (days - 186) % 30)
    return jy, jm, jd

def get_persian_datetime():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    time_str = now.strftime("%H:%M:%S")
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    days_fa = {5: "شنبه", 6: "یک‌شنبه", 0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه"}
    day_name = days_fa.get(now.weekday(), "")
    date_str = f"{jy}/{jm:02d}/{jd:02d}"
    return date_str, time_str, day_name

# ==================== کیبوردها ====================
BTN_BACK = "🔙 برگشت به منوی اصلی"

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🛒 خرید اشتراک"), KeyboardButton("📊 اطلاعات حساب"))
    kb.add(KeyboardButton("🌐 پنل کاربری IBSng"), KeyboardButton("💰 تمدید اکانت"))
    kb.add(KeyboardButton("👥 پشتیبانی"), KeyboardButton("❓ سوالات متداول"))
    kb.add(KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return kb

def get_back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(BTN_BACK))
    return kb

# ==================== هندلرها ====================
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    add_user_to_db(message.from_user)
    date_str, time_str, day_name = get_persian_datetime()
    welcome_text = (
        f"سلام <b>{message.from_user.first_name}</b> عزیز، خوش آمدید! 🌹\n\n"
        f"📅 تاریخ: <code>{date_str}</code> | ساعت: <code>{time_str}</code>\n\n"
        "👇 یکی از گزینه‌ها را انتخاب کنید:"
    )
    await message.reply(welcome_text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda m: m.text == "💰 تمدید اکانت", state="*")
async def handle_charge(message: types.Message, state: FSMContext):
    await state.finish()
    await ChargeState.waiting_for_receipt.set()
    caption = (
        "💰 <b>تمدید اکانت کاربری</b>\n\n"
        f"💳 شماره کارت: <code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 لطفاً تصویر فیش واریزی را ارسال نمایید:"
    )
    await message.reply(caption, reply_markup=get_back_keyboard())

@dp.message_handler(lambda m: m.text == "🌐 پنل کاربری IBSng", state="*")
async def handle_ibsng_panel(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "🌐 <b>پنل کاربری IBSng</b>\n\n"
        f"{IBSNG_PANEL_URL}\n\n"
        "💡 <b>برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.</b>"
    )
    await message.reply(text, reply_markup=get_main_keyboard())

# بقیه هندلرها اینجا ادامه می‌یابند (طبق کد قبلی)...
# برای جلوگیری از طولانی شدن بیش از حد، فقط بخش‌های تغییر یافته نمایش داده شد.

@dp.message_handler(state="*")
async def handle_other_messages(message: types.Message):
    await message.reply("لطفاً از منوی زیر استفاده نمایید 👇", reply_markup=get_main_keyboard())

# ==================== اجرای ربات ====================
async def run_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running."))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await run_server()
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())

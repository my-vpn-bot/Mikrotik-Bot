import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from html import escape
from zoneinfo import ZoneInfo

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

# ----------------- لاگینگ -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ----------------- متغیرهای محیطی Render -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENuv6tybcj2dX0X")
ADMIN_ID = os.getenv("ADMIN_ID", "02786850266")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support")
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", 10000))

VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "12345678."
BOT_USERNAME = "@L2TP_Arshavin_Bot"

# ----------------- دیتابیس -----------------
DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str, full_name: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
        """, (user_id, username, full_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database error: {e}")

def get_users_count():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Database error: {e}")
        return 0

# ----------------- تقویم شمسی و ساعت تهران -----------------
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy if gm > 2 else gy - 1
    days = 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd

def get_persian_date_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now = datetime.now(tehran_tz)
    except Exception:
        now = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
    
    weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یک‌شنبه"]
    weekday_name = weekdays[now.weekday()]
    
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    persian_months = [
        "", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
    ]
    date_str = f"{jd} {persian_months[jm]} {jy}"
    time_str = now.strftime("%H:%M")
    return weekday_name, date_str, time_str

# ----------------- استیت‌های ماشین وضعیت -----------------
class RenewalStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_receipt = State()

class PurchaseStates(StatesGroup):
    waiting_for_receipt = State()

# ----------------- کیبوردهای اصلی -----------------
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 خرید اشتراک")],
            [KeyboardButton(text="🔄 تمدید اشتراک")],
            [KeyboardButton(text="💳 تعرفه‌ها و قیمت‌ها")],
            [KeyboardButton(text="📚 راهنمای اتصال و سوالات متداول")],
            [KeyboardButton(text="🌐 ورود به پنل کاربری IBSng")],
            [KeyboardButton(text="⚙️ تنظیمات و اطلاعات سرور")],
            [KeyboardButton(text="💬 ارتباط با پشتیبانی")],
            [KeyboardButton(text="📢 کانال تلگرام")]
        ],
        resize_keyboard=True
    )

def get_plans_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔹 ۱ ماهه | تک کاربره - ۲۰۰,۰۰۰ تومان", callback_data="buy_1m_1u")],
            [InlineKeyboardButton(text="🔹 ۱ ماهه | دو کاربره - ۲۵۰,۰۰۰ تومان", callback_data="buy_1m_2u")],
            [InlineKeyboardButton(text="🔹 ۲ ماهه | تک کاربره - ۳۸۰,۰۰۰ تومان", callback_data="buy_2m_1u")],
            [InlineKeyboardButton(text="🔹 ۲ ماهه | دو کاربره - ۴۳۰,۰۰۰ تومان", callback_data="buy_2m_2u")],
            [InlineKeyboardButton(text="🔹 ۳ ماهه | تک کاربره - ۵۵۰,۰۰۰ تومان", callback_data="buy_3m_1u")],
            [InlineKeyboardButton(text="🔹 ۳ ماهه | دو کاربره - ۶۰۰,۰۰۰ تومان", callback_data="buy_3m_2u")],
            [InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data="cancel_action")]
        ]
    )

def get_help_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍏 راهنمای اتصال آیفون و آیپد (iOS)", callback_data="help_ios")],
            [InlineKeyboardButton(text="🤖 راهنمای اتصال گوشی‌های اندروید (Android)", callback_data="help_android")],
            [InlineKeyboardButton(text="💻 راهنمای اتصال ویندوز (Windows)", callback_data="help_windows")],
            [InlineKeyboardButton(text="🍎 راهنمای اتصال مک‌بوک (macOS)", callback_data="help_mac")],
            [InlineKeyboardButton(text="📡 راهنمای تنظیم روی مودم و روتر", callback_data="help_router")],
            [InlineKeyboardButton(text="❓ سوالات متداول و رفع خطاهای رایج", callback_data="help_faq")],
            [InlineKeyboardButton(text="❌ بستن راهنما", callback_data="cancel_action")]
        ]
    )

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ انصراف و بازگشت به منو")]],
        resize_keyboard=True
    )

# ----------------- پیام‌های ثابت -----------------
def get_welcome_text(user_full_name: str):
    weekday, pdate, ptime = get_persian_date_time()
    name_clean = escape(user_full_name)
    return (
        f"سلام و عرض ادب خدمت <b>{name_clean}</b> گرامی 🌹\n"
        f"به ربات رسمی و اختصاصی <b>L2TP VPN 24/7</b> خوش آمدید.\n\n"
        f"📅 امروز: <b>{weekday} - {pdate}</b>\n"
        f"⏰ ساعت: <b>{ptime}</b>\n\n"
        "⚡️ <b>وضعیت شبکه:</b> پایدار و متصل به قدرتمندترین سرورهای پرسرعت اختصاصی\n"
        "🌐 پروتکل امن L2TP/IPsec با پایداری کامل برای تمام اپراتورها\n\n"
        "📌 <b>لینک‌های رسمی و ارتباطی:</b>\n"
        f"📢 کانال تلگرام: {CHANNEL_URL}\n"
        f"💬 پشتیبانی آنلاین: {SUPPORT_ID}\n"
        f"🤖 شناسه ربات: {BOT_USERNAME}\n\n"
        "🌐 <b>پنل کاربری IBSng:</b>\n"
        f"🔗 {IBSNG_PANEL_URL}\n"
        "⚠️ <i>برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.</i>\n\n"
        "👇 لطفاً برای استفاده از خدمات، گزینه مورد نظر خود را از منوی زیر انتخاب نمایید:"
    )

def get_tariffs_text():
    return (
        "📊 <b>لیست تعرفه‌ها و قیمت سرویس‌ها (L2TP VPN L2TP 24/7):</b>\n\n"
        "🔹 <b>پلن‌های ۱ ماهه:</b>\n"
        "• یک ماهه تک کاربره: <code>200,000</code> تومان\n"
        "• یک ماهه دو کاربره: <code>250,000</code> تومان\n\n"
        "🔹 <b>پلن‌های ۲ ماهه:</b>\n"
        "• دو ماهه تک کاربره: <code>380,000</code> تومان\n"
        "• دو ماهه دو کاربره: <code>430,000</code> تومان\n\n"
        "🔹 <b>پلن‌های ۳ ماهه:</b>\n"
        "• سه ماهه تک کاربره: <code>550,000</code> تومان\n"
        "• سه ماهه دو کاربره: <code>600,000</code> تومان\n\n"
        "🎁 <b>هدیه ویژه:</b> تمامی پلن‌ها شامل <b>۱۰ گیگابایت ترافیک هدیه</b> می‌باشند.\n\n"
        "💳 <b>شماره کارت جهت واریز وجه:</b>\n"
        f"<code>{PAYMENT_CARD}</code>\n"
        f"به نام: <b>{PAYMENT_NAME}</b>\n\n"
        "جهت خرید یا تمدید اشتراک، از گزینه‌های منو استفاده فرمایید."
    )

# ----------------- راه‌اندازی ربات -----------------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ----------------- هندلرهای اصلی -----------------
@dp.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    await state.clear()
    add_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or ""
    )
    await message.answer(get_welcome_text(message.from_user.full_name), reply_markup=get_main_keyboard())

@dp.message(Command("stats"))
async def handle_stats(message: Message):
    if str(message.from_user.id) == str(ADMIN_ID):
        count = get_users_count()
        await message.answer(f"📊 <b>آمار اعضای ربات:</b>\n\nتعداد کل کاربران ثبت‌شده: <b>{count}</b> نفر")
    else:
        await message.answer("⛔️ این دستور فقط برای مدیریت قابل مشاهده است.")

@dp.message(F.text == "❌ انصراف و بازگشت به منو")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("عملیات لغو شد. به منوی اصلی برگشتید.", reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "cancel_action")
async def cancel_callback_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("عملیات لغو شد. به منوی اصلی برگشتید.", reply_markup=get_main_keyboard())
    await callback.answer()

@dp.message(F.text == "🛍 خرید اشتراک")
async def buy_subscription_menu(message: Message):
    await message.answer(
        "🛍 <b>خرید اشتراک اختصاصی L2TP VPN</b>\n\n"
        "لطفاً پلن مورد نظر خود را انتخاب نمایید:\n"
        "<i>(تمامی پلن‌ها ۱۰ گیگابایت حجم هدیه به همراه دارند)</i>",
        reply_markup=get_plans_keyboard()
    )

@dp.message(F.text == "🔄 تمدید اشتراک")
async def renew_subscription(message: Message, state: FSMContext):
    await state.set_state(RenewalStates.waiting_for_username)
    await message.answer(
        "🔄 <b>تمدید اشتراک</b>\n\n"
        "لطفاً <b>نام کاربری (Username)</b> اکانت قبلی خود را ارسال کنید:",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(RenewalStates.waiting_for_username)
async def process_renewal_username(message: Message, state: FSMContext):
    username = message.text.strip()
    await state.update_data(renew_username=username)
    await state.set_state(RenewalStates.waiting_for_receipt)
    await message.answer(
        f"اکانت وارد شده جهت تمدید: <b>{escape(username)}</b>\n\n"
        "لطفاً مبلغ اشتراک انتخابی را به شماره کارت زیر انتقال داده و سپس <b>تصویر فیش واریزی</b> را ارسال نمایید:\n\n"
        f"💳 شماره کارت: <code>{PAYMENT_CARD}</code>\n"
        f"👤 به نام: <b>{PAYMENT_NAME}</b>\n\n"
        "در انتظار ارسال تصویر رسید پرداخت...",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(RenewalStates.waiting_for_receipt, F.photo)
async def process_renewal_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("renew_username", "نامشخص")
    photo_id = message.photo[-1].file_id

    caption_admin = (
        "🔔 <b>درخواست تمدید اشتراک</b>\n\n"
        f"👤 کاربر تلگرام: @{message.from_user.username or 'ندارد'}\n"
        f"🆔 آیدی عددی: <code>{message.from_user.id}</code>\n"
        f"🔑 نام کاربری: <code>{escape(username)}</code>"
    )

    try:
        if ADMIN_ID:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption_admin)
    except Exception as e:
        logger.error(f"Error sending renewal receipt to admin: {e}")

    await state.clear()
    await message.answer(
        "✅ فیش واریزی با موفقیت به پشتیبانی تحویل شد.\n"
        "اکانت شما در اسرع وقت تمدید و فعال‌سازی خواهد شد.",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "💳 تعرفه‌ها و قیمت‌ها")
async def show_tariffs(message: Message):
    await message.answer(get_tariffs_text())

# ----------------- بخش راهنمای اتصال و سوالات متداول -----------------
@dp.message(F.text == "📚 راهنمای اتصال و سوالات متداول")
async def show_help_center(message: Message):
    await message.answer(
        "📚 <b>مرکز راهنما و سوالات متداول اتصال به L2TP VPN:</b>\n\n"
        "دستگاه یا سیستم‌عامل خود را از لیست زیر انتخاب کنید تا آموزش تنظیم دقیق برای شما نمایش داده شود:",
        reply_markup=get_help_keyboard()
    )

@dp.callback_query(F.data.startswith("help_"))
async def process_help_callback(callback: CallbackQuery):
    action = callback.data
    
    if action == "help_ios":
        text = (
            "🍏 <b>راهنمای اتصال در آیفون و آیپد (iOS):</b>\n\n"
            "1️⃣ به تنظیمات گوشی (<b>Settings</b>) بروید.\n"
            "2️⃣ وارد بخش <b>VPN & Device Management</b> و سپس <b>VPN</b> شوید.\n"
            "3️⃣ گزینه <b>Add VPN Configuration...</b> را انتخاب کنید.\n"
            "4️⃣ مشخصات را دقیقاً به شکل زیر وارد نمایید:\n"
            "• <b>Type:</b> <code>L2TP</code>\n"
            "• <b>Description:</b> <code>L2TP VPN</code>\n"
            f"• <b>Server:</b> <code>{VPN_SERVER_IP}</code>\n"
            "• <b>Account:</b> نام کاربری شما\n"
            "• <b>RSA SecurID:</b> خاموش (Off)\n"
            "• <b>Password:</b> رمز عبور شما\n"
            f"• <b>Secret:</b> <code>{IPSEC_SECRET}</code>\n"
            "• <b>Send All Traffic:</b> روشن (On)\n"
            "5️⃣ روی <b>Done</b> کلیک کرده و اتصال را روشن کنید."
        )
    elif action == "help_android":
        text = (
            "🤖 <b>راهنمای اتصال در گوشی‌های اندروید (Android):</b>\n\n"
            "1️⃣ وارد تنظیمات گوشی (<b>Settings</b>) شوید.\n"
            "2️⃣ بخش <b>اتصال‌ها (Connections)</b> یا <b>Network & Internet</b> را باز کنید.\n"
            "3️⃣ وارد <b>More connection settings</b> و سپس <b>VPN</b> شوید.\n"
            "4️⃣ گزینه افزودن پروفایل (+) یا <b>Add VPN</b> را بزنید.\n"
            "• <b>Name:</b> <code>L2TP VPN</code>\n"
            "• <b>Type:</b> <code>L2TP/IPSec PSK</code>\n"
            f"• <b>Server address:</b> <code>{VPN_SERVER_IP}</code>\n"
            "• <b>IPSec identifier:</b> خالی بگذارید\n"
            f"• <b>IPSec pre-shared key:</b> <code>{IPSEC_SECRET}</code>\n"
            "• <b>Username:</b> نام کاربری شما\n"
            "• <b>Password:</b> پسورد شما\n"
            "5️⃣ ذخیره (Save) کنید و متصل شوید."
        )
    elif action == "help_windows":
        text = (
            "💻 <b>راهنمای اتصال در ویندوز (Windows 10 / 11):</b>\n\n"
            "1️⃣ کلیدهای <b>Win + I</b> را بزنید و به بخش <b>Network & internet > VPN</b> بروید.\n"
            "2️⃣ روی دکمه <b>Add VPN</b> کلیک کنید.\n"
            "• <b>VPN provider:</b> Windows (built-in)\n"
            "• <b>Connection name:</b> <code>L2TP 24/7</code>\n"
            f"• <b>Server name or address:</b> <code>{VPN_SERVER_IP}</code>\n"
            "• <b>VPN type:</b> <code>L2TP/IPsec with pre-shared key</code>\n"
            f"• <b>Pre-shared key:</b> <code>{IPSEC_SECRET}</code>\n"
            "• <b>Type of sign-in info:</b> User name and password\n"
            "• نام کاربری و پسورد اکانت خود را وارد کنید.\n"
            "3️⃣ ذخیره کنید و دکمه <b>Connect</b> را بزنید."
        )
    elif action == "help_mac":
        text = (
            "🍎 <b>راهنمای اتصال در مک‌بوک (macOS):</b>\n\n"
            "1️⃣ به <b>System Settings</b> و بخش <b>Network</b> بروید.\n"
            "2️⃣ روی علامت (+) کلیک کرده و <b>Add VPN Configuration > L2TP over IPSec</b> را انتخاب کنید.\n"
            f"• <b>Server Address:</b> <code>{VPN_SERVER_IP}</code>\n"
            "• <b>Account Name:</b> نام کاربری اکانت شما\n"
            "3️⃣ روی <b>Authentication Settings</b> کلیک کنید:\n"
            "• <b>Password:</b> رمز عبور شما\n"
            f"• <b>Shared Secret:</b> <code>.\n"
            "2️⃣ روی دکمه <b>Add VPN</b> کلیک کنید.\n"
            "• <b>VPN provider:</b> Windows (built-in)\n"
            "• <b>Connection name:</b> <code>L2TP 24/7</code>\n"
            f"• <b>Server name or address:</b> <code>{VPN_SERVER_IP}</code>\n"
            "• <b>VPN type:</b> <code>L2TP/IPsec with pre-shared key</code>\n"
            f"• <b>Pre-shared key:</b> <code>{IPSEC_SECRET}</code>\n"
            "• <b>Type of sign-in info:</b> User name and password\n"
            "• نام کاربری و پسورد اکانت خود را وارد کنید.\n"
            "3️⃣ ذخیره کنید و دکمه <b>Connect</b> را بزنید."
        )
    elif action == "help_mac":
        text = (
            "🍎 <b>راهنمای اتصال در مک‌بوک (macOS):</b>\n\n"
            "1️⃣ به <b>System Settings</b> و بخش <b>Network</b> بروید.\n"
            "2️⃣ روی علامت (+) کلیک کرده و <b>Add VPN Configuration > L2TP over IPSec</b> را انتخاب کنید.\n"
            f"• <b>Server Address:</b> <code>{VPN_SERVER_IP}</code>\n"
            "• <b>Account Name:</b> نام کاربری اکانت شما\n"
            "3️⃣ روی <b>Authentication Settings</b> کلیک کنید:\n"
            "• <b>Password:</b> رمز عبور شما\n"
            f"• <b>Shared Secret:</b> <code>{IPSEC_SECRET}</code>\n"
            "4️⃣ تیک گزینه <b>Send all traffic over VPN connection</b> را در تنظیمات پیشرفته بزنید و وصل شوید."
        )
    elif action == "help_router":
        text = (
            "📡 <b>راهنمای تنظیم روی مودم و روتر (Router / Modem):</b> بار حالت پرواز را روشن و خاموش کنید و مجدداً متصل شوید."
        )

    await callback.message.answer(text)
    await callback.answer()

@dp.message(F.text == "🌐 ورود به پنل کاربری IBSng")
async def show_ibsng_panel(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 ورود به پنل کاربری IBSng", url=IBSNG_PANEL_URL)]
        ]
    )
    text = (
        "🌐 <b>پنل کاربری سرور اکانتینگ IBSng:</b>\n\n"
        "جهت مشاهده میزان مصرف حجم، تاریخ انقضا و وضعیت آنلاین بودن اکانت خود وارد پنل شوید.\n\n"
        "⚠️ <b>نکته مهم:</b>\n"
        "<i>برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.</i>"
    )
    await message.answer(text, reply_markup=keyboard)

@dp.message(F.text == "⚙️ تنظیمات و اطلاعات سرور")
async def show_server_config(message: Message):
    text = (
        "⚙️ <b>مشخصات اتصال شبکه L2TP VPN:</b>\n\n"
        f"🖥 <b>آدرس سرور (Server IP):</b>\n<code>{VPN_SERVER_IP}</code>\n\n"
        f"🔑 <b>کلید امنیتی (IPsec Secret):</b>\n<code>{IPSEC_SECRET}</code>\n\n"
        "نوع پروتکل: <code>L2TP/IPsec with Pre-shared Key</code>"
    )
    await message.answer(text)

@dp.message(F.text == "💬 ارتباط با پشتیبانی")
async def show_support(message: Message):
    support_user = SUPPORT_ID.replace("@", "")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 ارسال پیام به پشتیبانی تلگرام", url=f"https://t.me/{support_user}")]
        ]
    )
    await message.answer(
        f"در صورت نیاز به مشاوره، راهنمایی یا پیگیری سفارش با ما در ارتباط باشید:\n"
        f"👤 پشتیبان رسمی: {SUPPORT_ID}",
        reply_markup=keyboard
    )

@dp.message(F.text == "📢 کانال تلگرام")
async def show_channel(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 عضویت در کانال رسمی", url=CHANNEL_URL)]
        ]
    )
    await message.answer("برای دریافت آخرین اخبار، سرورها و اطلاعیه‌های رسمی در کانال عضو شوید:", reply_markup=keyboard)

# ----------------- هندلرهای فرآیند خرید -----------------
@dp.callback_query(F.data.startswith("buy_"))
async def process_plan_selection(callback: CallbackQuery, state: FSMContext):
    plans = {
        "buy_1m_1u": ("۱ ماهه | تک کاربره", "200,000"),
        "buy_1m_2u": ("۱ ماهه | دو کاربره", "250,000"),
        "buy_2m_1u": ("۲ ماهه | تک کاربره", "380,000"),
        "buy_2m_2u": ("۲ ماهه | دو کاربره", "430,000"),
        "buy_3m_1u": ("۳ ماهه | تک کاربره", "550,000"),
        "buy_3m_2u": ("۳ ماهه | دو کاربره", "600,000"),
    }
    plan_info = plans.get(callback.data)
    if not plan_info:
        await callback.answer()
        return

    plan_title, plan_price = plan_info
    await state.update_data(selected_plan=plan_title, selected_price=plan_price)
    await state.set_state(PurchaseStates.waiting_for_receipt)

    await callback.message.answer(
        f"✅ پلن انتخابی: <b>{plan_title}</b>\n"
        f"💰 مبلغ قابل پرداخت: <b>{plan_price} تومان</b>\n\n"
        f"💳 شماره کارت: <code>{PAYMENT_CARD}</code>\n"
        f"👤 به نام: <b>{PAYMENT_NAME}</b>\n\n"
        "پس از واریز، لطفاً تصویر فیش پرداخت را همین‌جا ارسال کنید.",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@dp.message(PurchaseStates.waiting_for_receipt, F.photo)
async def process_purchase_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_title = data.get("selected_plan", "نامشخص")
    plan_price = data.get("selected_price", "نامشخص")
    photo_id = message.photo[-1].file_id

    caption_admin = (
        "🔔 <b>درخواست خرید اشتراک جدید</b>\n\n"
        f"👤 کاربر تلگرام: @{message.from_user.username or 'ندارد'}\n"
        f"🆔 آیدی عددی: <code>{message.from_user.id}</code>\n"
        f"📦 پلن: <b>{plan_title}</b>\n"
        f"💰 مبلغ: <b>{plan_price} تومان</b>"
    )

    try:
        if ADMIN_ID:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption_admin)
    except Exception as e:
        logger.error(f"Error sending purchase receipt to admin: {e}")

    await state.clear()
    await message.answer(
        "✅ فیش واریزی دریافت شد.\n"
        "اطلاعات اکانت شما به زودی و پس از بررسی ارسال خواهد شد.\n\n"
        "از شکیبایی شما سپاسگزاریم 🌹",
        reply_markup=get_main_keyboard()
    )

# ----------------- وب‌سرور Render -----------------
async def health_check(request):
    return web.Response(text="Bot is running smoothly!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

# ----------------- تابع اصلی اجرای برنامه -----------------
async def main():
    init_db()
    logger.info("Database ready.")

    asyncio.create_task(start_web_server())

    logger.info("Starting Polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except TelegramConflictError:
        logger.warning("Conflict error detected. Waiting 5s...")
        await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

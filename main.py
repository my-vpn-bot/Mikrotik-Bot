import os
import sys
import asyncio
import logging
import sqlite3
from datetime import datetime, timezone, timedelta

from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ============================
# تنظیمات لاگینگ
# ============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("L2TP_VPN_BOT")

# ============================
# دریافت متغیرهای محیطی
# ============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENik41nwp457X0X")
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "2786850266")
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    ADMIN_ID = 2786850266

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/")
PORT = int(os.getenv("PORT", 10000))

SERVER_IP = "94.184.43.106"
IPSEC_SECRET = ".12345678"

# ============================
# سیستم تبدیل تاریخ به شمسی (سبک و داخلی)
# ============================
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gm > 2:
        gy2 = gy
    else:
        gy2 = gy - 1
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd

def get_current_shamsi_datetime():
    tz_tehran = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tz_tehran)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    date_str = f"{jy:04d}/{jm:02d}/{jd:02d}"
    time_str = now.strftime("%H:%M:%S")
    return date_str, time_str

# ============================
# دیتابیس SQLite
# ============================
DB_PATH = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_user(user_id: int, username: str, full_name: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        date_str, time_str = get_current_shamsi_datetime()
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name, join_date)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, full_name, f"{date_str} {time_str}"))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving user to DB: {e}")

def get_total_users():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

# ============================
# وضعیت‌های FSM (State Management)
# ============================
class OrderStates(StatesGroup):
    waiting_for_plan = State()
    waiting_for_receipt = State()

class RenewStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_receipt = State()

# ============================
# کیبوردهای منوی ربات
# ============================
def get_main_keyboard():
    kb = [
        [KeyboardButton(text="🛍 خرید اشتراک جدید")],
        [KeyboardButton(text="🔄 تمدید اشتراک"), KeyboardButton(text="📋 تعرفه‌ها و قیمت‌ها")],
        [KeyboardButton(text="🌐 ورود به پنل کاربری (IBSng)"), KeyboardButton(text="⚙️ مشخصات سرور و تنظیمات")],
        [KeyboardButton(text="📚 آموزش و راهنمای اتصال"), KeyboardButton(text="💬 پشتیبانی و ارتباط با ما")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_keyboard():
    kb = [
        [KeyboardButton(text="❌ انصراف و بازگشت به منوی اصلی")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_plans_inline_keyboard():
    inline_kb = [
        [InlineKeyboardButton(text="🔹 ۱ ماهه تک کاربره (۲۰۰,۰۰۰ ت)", callback_data="buy_1m_1u")],
        [InlineKeyboardButton(text="🔹 ۱ ماهه دو کاربره (۲۵۰,۰۰۰ ت)", callback_data="buy_1m_2u")],
        [InlineKeyboardButton(text="🔹 ۲ ماهه تک کاربره (۳۸۰,۰۰۰ ت)", callback_data="buy_2m_1u")],
        [InlineKeyboardButton(text="🔹 ۲ ماهه دو کاربره (۴۳۰,۰۰۰ ت)", callback_data="buy_2m_2u")],
        [InlineKeyboardButton(text="🔹 ۳ ماهه تک کاربره (۵۵۰,۰۰۰ ت)", callback_data="buy_3m_1u")],
        [InlineKeyboardButton(text="🔹 ۳ ماهه دو کاربره (۶۰۰,۰۰۰ ت)", callback_data="buy_3m_2u")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_kb)

PLANS_INFO = {
    "buy_1m_1u": ("۱ ماهه تک کاربره", "۲۰۰,۰۰۰ تومان"),
    "buy_1m_2u": ("۱ ماهه دو کاربره", "۲۵۰,۰۰۰ تومان"),
    "buy_2m_1u": ("۲ ماهه تک کاربره", "۳۸۰,۰۰۰ تومان"),
    "buy_2m_2u": ("۲ ماهه دو کاربره", "۴۳۰,۰۰۰ تومان"),
    "buy_3m_1u": ("۳ ماهه تک کاربره", "۵۵۰,۰۰۰ تومان"),
    "buy_3m_2u": ("۳ ماهه دو کاربره", "۶۰۰,۰۰۰ تومان"),
}

# ============================
# راه‌اندازی بات و دیسپچر
# ============================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ============================
# هندلرهای اصلی (Handlers)
# ============================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    save_user(user.id, user.username or "", user.full_name or "")
    
    date_shamsi, time_shamsi = get_current_shamsi_datetime()
    
    welcome_text = (
        f"سلام {user.first_name} عزیز 👋\n"
        f"به ربات رسمی سرویس **L2TP VPN 24/7** خوش آمدید.\n\n"
        f"📅 تاریخ: `{date_shamsi}`\n"
        f"⏰ ساعت: `{time_shamsi}`\n"
        f"📢 کانال اطلاع‌رسانی: {CHANNEL_URL}\n\n"
        f"از منوی زیر گزینه مورد نظرتان را انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(F.text == "❌ انصراف و بازگشت به منوی اصلی")
async def process_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("عملیات لغو شد. به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total = get_total_users()
    date_shamsi, time_shamsi = get_current_shamsi_datetime()
    await message.answer(
        f"📊 **آمار کاربران ربات**\n\n"
        f"👥 کل کاربران ثبت‌شده: `{total}` نفر\n"
        f"⏱ زمان گزارش: `{date_shamsi} - {time_shamsi}`",
        parse_mode="Markdown"
    )

# --- تعرفه‌ها ---
@dp.message(F.text == "📋 تعرفه‌ها و قیمت‌ها")
async def show_tariffs(message: types.Message):
    text = (
        "⚡️ **تعرفه‌ها و پلن‌های L2TP VPN 24/7**\n\n"
        "▫️ **۱ ماهه تک کاربره:** ۲۰۰,۰۰۰ تومان\n"
        "▫️ **۱ ماهه دو کاربره:** ۲۵۰,۰۰۰ تومان\n"
        "▫️ **۲ ماهه تک کاربره:** ۳۸۰,۰۰۰ تومان\n"
        "▫️ **۲ ماهه دو کاربره:** ۴۳۰,۰۰۰ تومان\n"
        "▫️ **۳ ماهه تک کاربره:** ۵۵۰,۰۰۰ تومان\n"
        "▫️ **۳ ماهه دو کاربره:** ۶۰۰,۰۰۰ تومان\n\n"
        "🎁 *تمامی پلن‌ها شامل ۱۰ گیگابایت ترافیک هدیه می‌باشند.*\n"
        "🔒 پایدار، بدون قطعی، مناسب تمامی اپراتورها و دستگاه‌ها."
    )
    await message.answer(text, parse_mode="Markdown")

# --- خرید اشتراک جدید ---
@dp.message(F.text == "🛍 خرید اشتراک جدید")
async def start_buy_process(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "لطفاً پلن مورد نظر خود را برای خرید انتخاب کنید:",
        reply_markup=get_plans_inline_keyboard()
    )

@dp.callback_query(F.data.startswith("buy_"))
async def process_plan_selection(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data
    if plan_key not in PLANS_INFO:
        await callback.answer("پلن نامعتبر است.")
        return
    
    plan_name, plan_price = PLANS_INFO[plan_key]
    await state.update_data(plan_name=plan_name, plan_price=plan_price)
    await state.set_state(OrderStates.waiting_for_receipt)
    
    text = (
        f"✅ پلن انتخابی شما: **{plan_name}**\n"
        f"💰 مبلغ قابل پرداخت: **{plan_price}**\n\n"
        f"💳 شماره کارت جهت واریز:\n"
        f"`{PAYMENT_CARD}`\n"
        f"👤 به نام: **{PAYMENT_NAME}**\n\n"
        f"📸 لطفاً پس از واریز، **عکس فیش واریزی** یا شماره پیگیری تراکنش را در همین چت ارسال فرمایید."
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.message.answer("در انتظار ارسال فیش واریزی...", reply_markup=get_cancel_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "cancel_action")
async def process_inline_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("عملیات خرید لغو شد.")
    await callback.message.answer("به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())
    await callback.answer()

@dp.message(OrderStates.waiting_for_receipt, F.photo | F.document | F.text)
async def process_receipt_submission(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("plan_name", "نامشخص")
    plan_price = data.get("plan_price", "نامشخص")
    user = message.from_user
    date_shamsi, time_shamsi = get_current_shamsi_datetime()
    
    admin_caption = (
        f"🔔 **درخواست خرید اشتراک جدید**\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 شناسه: `{user.id}`\n"
        f"📦 پلن: **{plan_name}** ({plan_price})\n"
        f"📅 زمان: `{date_shamsi} - {time_shamsi}`\n"
    )
    
    try:
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_caption, parse_mode="Markdown")
        elif message.document:
            await bot.send_document(chat_id=ADMIN_ID, document=message.document.file_id, caption=admin_caption, parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=f"{admin_caption}\n📝 متن/کد پیگیری: {message.text}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error forwarding receipt to admin: {e}")
    
    await state.clear()
    await message.answer(
        "✅ فیش واریزی شما با موفقیت برای مدیریت ارسال شد.\n"
        "پس از بررسی، مشخصات اکانت برای شما ارسال خواهد شد. از شکیبایی شما سپاسگزاریم.",
        reply_markup=get_main_keyboard()
    )

# --- تمدید اشتراک ---
@dp.message(F.text == "🔄 تمدید اشتراک")
async def start_renew_process(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(RenewStates.waiting_for_username)
    await message.answer(
        "لطفاً **نام کاربری (Username)** اکانت فعلی خود را وارد کنید:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(RenewStates.waiting_for_username, F.text)
async def process_renew_username(message: types.Message, state: FSMContext):
    if message.text == "❌ انصراف و بازگشت به منوی اصلی":
        await state.clear()
        await message.answer("به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())
        return

    await state.update_data(vpn_username=message.text.strip())
    await state.set_state(RenewStates.waiting_for_receipt)
    
    text = (
        f"اکانت جهت تمدید: `{message.text.strip()}`\n\n"
        f"💳 شماره کارت جهت واریز:\n"
        f"`{PAYMENT_CARD}`\n"
        f"👤 به نام: **{PAYMENT_NAME}**\n\n"
        f"📸 لطفاً پس از واریز، **عکس فیش واریزی** را ارسال کنید."
    )
    await message.answer(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")

@dp.message(RenewStates.waiting_for_receipt, F.photo | F.document | F.text)
async def process_renew_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    vpn_user = data.get("vpn_username", "نامشخص")
    user = message.from_user
    date_shamsi, time_shamsi = get_current_shamsi_datetime()
    
    admin_caption = (
        f"🔄 **درخواست تمدید اشتراک**\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 شناسه: `{user.id}`\n"
        f"🔑 نام کاربری سرویس: `{vpn_user}`\n"
        f"📅 زمان: `{date_shamsi} - {time_shamsi}`\n"
    )
    
    try:
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_caption, parse_mode="Markdown")
        elif message.document:
            await bot.send_document(chat_id=ADMIN_ID, document=message.document.file_id, caption=admin_caption, parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=f"{admin_caption}\n📝 توضیحات: {message.text}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error forwarding renew to admin: {e}")
    
    await state.clear()
    await message.answer(
        "✅ اطلاعات تمدید برای مدیریت ارسال شد و به زودی سرویس شما تمدید می‌گردد.",
        reply_markup=get_main_keyboard()
    )

# --- مشخصات سرور و تنظیمات ---
@dp.message(F.text == "⚙️ مشخصات سرور و تنظیمات")
async def show_server_config(message: types.Message):
    text = (
        "⚙️ **مشخصات سرور و اتصال L2TP/IPSec**\n\n"
        f"🌐 **Server Address / IP:** `{SERVER_IP}`\n"
        f"🔑 **IPSec Pre-Shared Key (Secret):** `{IPSEC_SECRET}`\n"
        "🔒 **Protocol:** L2TP / IPSec (Pre-shared key)\n\n"
        "💡 *نام کاربری و رمز عبور اختصاصی خود را در بخش مربوطه وارد نمایید.*"
    )
    await message.answer(text, parse_mode="Markdown")

# --- ورود به پنل کاربری IBSng ---
@dp.message(F.text == "🌐 ورود به پنل کاربری (IBSng)")
async def show_ibsng_panel(message: types.Message):
    text = (
        "🌐 **پنل مدیریت مصرف و حساب کاربری (IBSng)**\n\n"
        f"🔗 آدرس ورود به پنل:\n{IBSNG_PANEL_URL}\n\n"
        "⚠️ **توجه مهم:**\n"
        "برای ارتباط بهتر و ورود سریع به پنل، لطفاً **وی‌پی‌ان خود را خاموش کنید** و بعد از اتمام مشاهده حساب، دوباره روشن فرمایید."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 ورود مستقیم به پنل IBSng", url=IBSNG_PANEL_URL)]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# --- آموزش و راهنما ---
@dp.message(F.text == "📚 آموزش و راهنمای اتصال")
async def show_guides(message: types.Message):
    text = (
        "📚 **راهنمای اتصال به سرویس L2TP VPN 24/7**\n\n"
        "🔹 **آیفون (iOS):**\n"
        "Settings > VPN & Device Management > Add VPN Configuration\n"
        f"Type: L2TP | Server: `{SERVER_IP}` | Secret: `{IPSEC_SECRET}`\n\n"
        "🔹 **اندروید (Android):**\n"
        "تنظیمات > اتصالات بیشتر > VPN > افزودن VPN\n"
        f"نوع: L2TP/IPSec PSK | آدرس: `{SERVER_IP}` | کلید پیش‌مشترک: `{IPSEC_SECRET}`\n\n"
        "🔹 **ویندوز (Windows):**\n"
        "Settings > Network & Internet > VPN > Add VPN Connection\n"
        f"VPN Provider: Windows (built-in) | Type: L2TP/IPsec with pre-shared key | Server: `{SERVER_IP}` | Secret: `{IPSEC_SECRET}`\n\n"
        "🔹 **مودم / روتر:**\n"
        f"بخش L2TP Client را فعال کرده و Server IP را `{SERVER_IP}` قرار دهید."
    )
    await message.answer(text, parse_mode="Markdown")

# --- پشتیبانی ---
@dp.message(F.text == "💬 پشتیبانی و ارتباط با ما")
async def show_support(message: types.Message):
    text = (
        "💬 **پشتیبانی و ارتباط با مدیریت**\n\n"
        f"👤 آیدی پشتیبانی: {SUPPORT_ID}\n"
        f"📢 کانال تلگرام: {CHANNEL_URL}\n\n"
        "در صورت بروز هرگونه مشکل یا سوال، با پشتیبانی در ارتباط باشید."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 ارتباط با پشتیبانی", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}")],
        [InlineKeyboardButton(text="📢 عضویت در کانال", url=CHANNEL_URL)]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# ============================
# سرور سبک وب برای Render (Health Check)
# ============================
async def handle_health_check(request):
    return web.Response(text="Bot is running smoothly 24/7!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check web server started on port {PORT}")

# ============================
# اجرای اصلی (Main Entry Point)
# ============================
async def main():
    init_db()
    logger.info("Database initialized successfully.")
    
    # اجرای وب‌سرور داخلی در پس‌زمینه
    await start_web_server()
    
    # حذف وب‌هوک‌های قبلی در صورت وجود و شروع Polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

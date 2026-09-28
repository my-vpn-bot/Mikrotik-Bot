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
    ReplyKeyboardRemove,
)

# ----------------- تنظیمات لاگ -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ----------------- متغیرهای محیطی -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENgm4uzyw7k6cX0X")
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
CHANNEL_USERNAME = "@L2tp_vpn402"

# ----------------- دیتابیس کاربران -----------------
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

# ----------------- توابع تاریخ شمسی و زمان -----------------
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

# ----------------- استیت‌های FSM -----------------
class RenewalStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_receipt = State()

class PurchaseStates(StatesGroup):
    waiting_for_receipt = State()

# ----------------- کیبوردها -----------------
def get_main_keyboard():
    # خرید اشتراک در ردیف اول به صورت یک خط کامل
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 خرید اشتراک")],
            [KeyboardButton(text="💳 تعرفه‌ها و قیمت‌ها"), KeyboardButton(text="🔄 تمدید اشتراک")],
            [KeyboardButton(text="🌐 ورود به پنل کاربری IBSng"), KeyboardButton(text="⚙️ تنظیمات و اطلاعات سرور")],
            [KeyboardButton(text="💬 ارتباط با پشتیبانی"), KeyboardButton(text="📢 کانال تلگرام")]
        ],
        resize_keyboard=True
    )

def get_plans_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="۱ ماهه | تک کاربره (۲۰۰ ت)", callback_data="buy_1m_1u"),
                InlineKeyboardButton(text="۱ ماهه | دو کاربره (۲۵۰ ت)", callback_data="buy_1m_2u")
            ],
            [
                InlineKeyboardButton(text="۲ ماهه | تک کاربره (۳۸۰ ت)", callback_data="buy_2m_1u"),
                InlineKeyboardButton(text="۲ ماهه | دو کاربره (۴۳۰ ت)", callback_data="buy_2m_2u")
            ],
            [
                InlineKeyboardButton(text="۳ ماهه | تک کاربره (۵۵۰ ت)", callback_data="buy_3m_1u"),
                InlineKeyboardButton(text="۳ ماهه | دو کاربره (۶۰۰ ت)", callback_data="buy_3m_2u")
            ],
            [
                InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_action")
            ]
        ]
    )

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ انصراف و بازگشت به منو")]],
        resize_keyboard=True
    )

# ----------------- متن‌ها و پیام‌ها -----------------
def get_tariffs_text():
    return (
        "📊 <b>تعرفه‌ها و تعرفه سرویس‌ها (L2TP VPN L2TP 24/7):</b>\n\n"
        "🔹 <b>پلن‌های ۱ ماهه:</b>\n"
        "• یک ماهه تک کاربره: <code>200,000</code> تومان\n"
        "• یک ماهه دو کاربره: <code>250,000</code> تومان\n\n"
        "🔹 <b>پلن‌های ۲ ماهه:</b>\n"
        "• دو ماهه تک کاربره: <code>380,000</code> تومان\n"
        "• دو ماهه دو کاربره: <code>430,000</code> تومان\n\n"
        "🔹 <b>پلن‌های ۳ ماهه:</b>\n"
        "• سه ماهه تک کاربره: <code>550,000</code> تومان\n"
        "• سه ماهه دو کاربره: <code>600,000</code> تومان\n\n"
        "🎁 <b>تمامی پلن‌ها شامل ۱۰ گیگابایت ترافیک هدیه می‌باشند.</b>\n"
        "💳 شماره کارت جهت واریز:\n"
        f"<code>{PAYMENT_CARD}</code>\n"
        f"به نام: <b>{PAYMENT_NAME}</b>\n\n"
        "جهت خرید یا تمدید می‌توانید از گزینه‌های منو اقدام نمایید."
    )

def get_welcome_text(user_full_name: str):
    weekday, pdate, ptime = get_persian_date_time()
    name_clean = escape(user_full_name)
    return (
        f"سلام <b>{name_clean}</b> عزیز، خوش آمدید! 🌹\n\n"
        f"📅 امروز: <b>{weekday} {pdate}</b>\n"
        f"⏰ ساعت: <b>{ptime}</b>\n\n"
        "🚀 به ربات رسمی <b>L2TP VPN 24/7</b> خوش آمدید.\n\n"
        "📌 <b>راه‌های ارتباطی و کانال رسمی:</b>\n"
        f"📢 کانال تلگرام: {CHANNEL_URL}\n"
        f"💬 پشتیبانی آنلاین: {SUPPORT_ID}\n"
        f"🤖 ربات رسمی: {BOT_USERNAME}\n\n"
        "از منوی زیر گزینه مورد نظر خود را انتخاب کنید:"
    )

# ----------------- راه‌اندازی ربات -----------------
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ----------------- هندلرها -----------------
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
        await message.answer(f"📊 <b>آمار کاربران ربات:</b>\n\nتعداد کل کاربران ثبت‌شده: <b>{count}</b> نفر")
    else:
        await message.answer("⛔️ این دستور مختص مدیریت می‌باشد.")

@dp.message(F.text == "❌ انصراف و بازگشت به منو")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("عملیات لغو شد. به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())

@dp.message(F.text == "🛍 خرید اشتراک")
async def buy_subscription_menu(message: Message):
    await message.answer(
        "پلن مورد نظر خود را برای خرید انتخاب کنید:\n"
        "<i>(تمامی پلن‌ها شامل ۱۰ گیگ هدیه هستند)</i>",
        reply_markup=get_plans_keyboard()
    )

@dp.message(F.text == "💳 تعرفه‌ها و قیمت‌ها")
async def show_tariffs(message: Message):
    await message.answer(get_tariffs_text())

@dp.message(F.text == "🔄 تمدید اشتراک")
async def renew_subscription(message: Message, state: FSMContext):
    await state.set_state(RenewalStates.waiting_for_username)
    await message.answer(
        "🔄 <b>تمدید اشتراک</b>\n\n"
        "لطفاً نام کاربری (Username) اکانت فعلی خود را ارسال فرمایید:",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(RenewalStates.waiting_for_username)
async def process_renewal_username(message: Message, state: FSMContext):
    username = message.text.strip()
    await state.update_data(renew_username=username)
    await state.set_state(RenewalStates.waiting_for_receipt)
    await message.answer(
        f"نام کاربری: <b>{escape(username)}</b>\n\n"
        "لطفاً مبلغ دوره مورد نظر خود را به شماره کارت زیر واریز فرموده و سپس <b>تصویر فیش واریزی</b> را همین‌جا ارسال نمایید:\n\n"
        f"💳 شماره کارت: <code>{PAYMENT_CARD}</code>\n"
        f"👤 به نام: <b>{PAYMENT_NAME}</b>\n\n"
        "منتظر ارسال تصویر فیش واریزی هستیم...",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(RenewalStates.waiting_for_receipt, F.photo)
async def process_renewal_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data.get("renew_username", "نامشخص")
    photo_id = message.photo[-1].file_id

    caption_admin = (
        "🔔 <b>درخواست تمدید اشتراک جدید</b>\n\n"
        f"👤 کاربر تلگرام: @{message.from_user.username or 'ندارد'}\n"
        f"🆔 آیدی عددی: <code>{message.from_user.id}</code>\n"
        f"🔑 نام کاربری برای تمدید: <code>{escape(username)}</code>"
    )

    try:
        if ADMIN_ID:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption_admin)
    except Exception as e:
        logger.error(f"Error sending renewal to admin: {e}")

    await state.clear()
    await message.answer(
        "✅ فیش واریزی و اطلاعات شما با موفقیت برای پشتیبانی ارسال شد.\n"
        "پس از بررسی، اکانت شما تمدید و به شما اطلاع داده خواهد شد.\n\n"
        "از شکیبایی شما سپاسگزاریم.",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data.startswith("buy_"))
async def process_plan_selection(callback: CallbackQuery, state: FSMContext):
    plans = {
        "buy_1m_1u": ("۱ ماهه تک کاربره", "200,000"),
        "buy_1m_2u": ("۱ ماهه دو کاربره", "250,000"),
        "buy_2m_1u": ("۲ ماهه تک کاربره", "380,000"),
        "buy_2m_2u": ("۲ ماهه دو کاربره", "430,000"),
        "buy_3m_1u": ("۳ ماهه تک کاربره", "550,000"),
        "buy_3m_2u": ("۳ ماهه دو کاربره", "600,000"),
    }
    plan_info = plans.get(callback.data)
    if not plan_info:
        await callback.answer()
        return

    plan_title, plan_price = plan_info
    await state.update_data(selected_plan=plan_title, selected_price=plan_price)
    await state.set_state(PurchaseStates.waiting_for_receipt)

    await callback.message.delete()
    await callback.message.answer(
        f"پلن انتخابی شما: <b>{plan_title}</b>\n"
        f"مبلغ قابل پرداخت: <b>{plan_price} تومان</b>\n\n"
        f"لطفاً مبلغ را به شماره کارت زیر واریز کرده و <b>عکس فیش واریزی</b> را ارسال نمایید:\n\n"
        f"💳 شماره کارت: <code>{PAYMENT_CARD}</code>\n"
        f"👤 به نام: <b>{PAYMENT_NAME}</b>\n\n"
        "منتظر ارسال عکس فیش هستیم...",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "cancel_action")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("عملیات لغو شد.", reply_markup=get_main_keyboard())
    await callback.answer()

@dp.message(PurchaseStates.waiting_for_receipt, F.photo)
async def process_purchase_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_title = data.get("selected_plan", "نامشخص")
    plan_price = data.get("selected_price", "نامشخص")
    photo_id = message.photo[-1].file_id

    caption_admin = (
        "🛍 <b>درخواست خرید اشتراک جدید</b>\n\n"
        f"👤 کاربر تلگرام: @{message.from_user.username or 'ندارد'}\n"
        f"🆔 آیدی عددی: <code>{message.from_user.id}</code>\n"
        f"📦 پلن انتخابی: <b>{plan_title}</b>\n"
        f"💰 مبلغ: <b>{plan_price} تومان</b>"
    )

    try:
        if ADMIN_ID:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption_admin)
    except Exception as e:
        logger.error(f"Error sending purchase to admin: {e}")

    await state.clear()
    await message.answer(
        "✅ فیش واریزی با موفقیت دریافت شد.\n"
        "مشخصات اکانت شما حداکثر تا دقایقی دیگر پس از تایید مالی ارسال خواهد شد.\n\n"
        "با تشکر از اعتماد شما 🌹",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🌐 ورود به پنل کاربری IBSng")
async def show_ibsng_panel(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 ورود مستقیم به پنل کاربری", url=IBSNG_PANEL_URL)]
        ]
    )
    text = (
        "🌐 <b>پنل کاربری سرور اکانتینگ IBSng:</b>\n\n"
        "⚠️ <b>نکته مهم:</b>\n"
        "<i>برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.</i>\n\n"
        "جهت ورود به پنل و مشاهده حجم باقیمانده، وضعیت اکانت و تاریخ انقضا روی دکمه زیر کلیک کنید:"
    )
    await message.answer(text, reply_markup=keyboard)

@dp.message(F.text == "⚙️ تنظیمات و اطلاعات سرور")
async def show_server_config(message: Message):
    text = (
        "⚙️ <b>مشخصات اتصال به شبکه L2TP VPN:</b>\n\n"
        f"🖥 <b>آدرس سرور (Server IP):</b>\n<code>{VPN_SERVER_IP}</code>\n\n"
        f"🔑 <b>کلید امنیتی اشتراکی (IPsec Secret):</b>\n<code>{IPSEC_SECRET}</code>\n\n"
        "📌 <b>راهنمای اتصال:</b>\n"
        "نوع اتصال: <code>L2TP/IPsec with Pre-shared key</code>\n"
        "نام کاربری و رمز عبور اختصاصی خود را وارد کرده و متصل شوید."
    )
    await message.answer(text)

@dp.message(F.text == "💬 ارتباط با پشتیبانی")
async def show_support(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 ارتباط مستقیم با پشتیبانی", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}")]
        ]
    )
    await message.answer(
        f"در صورت بروز هرگونه مشکل یا سوال می‌توانید با پشتیبانی در ارتباط باشید:\n"
        f"آیدی پشتیبانی: {SUPPORT_ID}",
        reply_markup=keyboard
    )

@dp.message(F.text == "📢 کانال تلگرام")
async def show_channel(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 عضویت در کانال", url=CHANNEL_URL)]
        ]
    )
    await message.answer("جهت اطلاع از آخرین اخبار و آدرس سرورها عضو کانال ما شوید:", reply_markup=keyboard)

# ----------------- وب‌سرور سبک برای Render Health Check -----------------
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

# ----------------- اجرای همزمان -----------------
async def main():
    init_db()
    logger.info("Initializing Database...")
    
    # راه‌اندازی وب‌سرور Render
    asyncio.create_task(start_web_server())

    logger.info("Starting Telegram Bot Polling...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except TelegramConflictError:
        logger.warning("TelegramConflictError: Another instance is running. Retrying in 5 seconds...")
        await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

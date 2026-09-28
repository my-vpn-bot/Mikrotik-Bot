import os
import logging
import asyncio
import sqlite3
from datetime import datetime
import pytz

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ----------------- تنظیمات لاگینگ -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ----------------- متغیرهای محیطی (Render) -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKEN0us537irlcoaX0X").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "02786850266").strip()
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support").strip()
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی").strip()
PORT = int(os.getenv("PORT", 10000))

# سرورها و اتصالات
VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = ".12345678"
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/").strip()

# ----------------- دیتابیس SQLite برای آمار کاربران -----------------
DB_PATH = "bot_users.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

def register_user(user_id: int, username: str, full_name: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO users (user_id, username, full_name)
                VALUES (?, ?, ?)
                """,
                (user_id, username or "", full_name or "")
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error registering user {user_id}: {e}")

def get_users_count() -> int:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            row = cursor.fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.error(f"Error reading stats: {e}")
        return 0

# ----------------- استیت‌های FSM -----------------
class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

class ErrorReportStates(StatesGroup):
    waiting_for_report = State()

class CompensationStates(StatesGroup):
    waiting_for_details = State()

# ----------------- لیست تعرفه‌ها و قیمت‌های جدید -----------------
PLANS = {
    "1m_1u": {
        "title": "یک‌ماهه تک کاربره",
        "price": "۲۰۰,۰۰۰ تومان",
        "price_num": 200000,
        "details": "اشتراک ۱ ماهه اختصاصی تک کاربره + ۱۰ گیگابایت هدیه"
    },
    "1m_2u": {
        "title": "یک‌ماهه دو کاربره",
        "price": "۲۵۰,۰۰۰ تومان",
        "price_num": 250000,
        "details": "اشتراک ۱ ماهه اختصاصی دو کاربره همزمان + ۱۰ گیگابایت هدیه"
    },
    "2m_1u": {
        "title": "دو‌ماهه تک کاربره",
        "price": "۳۸۰,۰۰۰ تومان",
        "price_num": 380000,
        "details": "اشتراک ۲ ماهه اختصاصی تک کاربره + ۱۰ گیگابایت هدیه"
    },
    "2m_2u": {
        "title": "دو‌ماهه دو کاربره",
        "price": "۴۳۰,۰۰۰ تومان",
        "price_num": 430000,
        "details": "اشتراک ۲ ماهه اختصاصی دو کاربره همزمان + ۱۰ گیگابایت هدیه"
    },
    "3m_1u": {
        "title": "سه‌ماهه تک کاربره",
        "price": "۵۵۰,۰۰۰ تومان",
        "price_num": 550000,
        "details": "اشتراک ۳ ماهه اختصاصی تک کاربره + ۱۰ گیگابایت هدیه"
    },
    "3m_2u": {
        "title": "سه‌ماهه دو کاربره",
        "price": "۶۰۰,۰۰۰ تومان",
        "price_num": 600000,
        "details": "اشتراک ۳ ماهه اختصاصی دو کاربره همزمان + ۱۰ گیگابایت هدیه"
    },
}

# ----------------- ابزار تاریخ و زمان شمسی -----------------
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gm > 2:
        gy2 = gy + 1
    else:
        gy2 = gy
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

def get_current_jalali_datetime():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    date_str = f"{jy:04d}/{jm:02d}/{jd:02d}"
    time_str = now.strftime("%H:%M:%S")
    return date_str, time_str

# ----------------- کیبوردهای بات -----------------
def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🛍️ خرید اشتراک و تعرفه‌ها"), KeyboardButton(text="👤 حساب کاربری")],
        [KeyboardButton(text="🎁 طرح جبرانی مشترکین"), KeyboardButton(text="🌐 مشخصات سرور و اتصال")],
        [KeyboardButton(text="📊 ورود به پنل مصرف (IBSng)"), KeyboardButton(text="💬 پشتیبانی 24/7")],
        [KeyboardButton(text="⚠️ گزارش قطعی / پشتیبانی"), KeyboardButton(text="📢 کانال اطلاع‌رسانی")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_plans_inline_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="1️⃣ ۱ ماهه تک (۲۰۰ ت)", callback_data="buy_1m_1u"),
            InlineKeyboardButton(text="👥 ۱ ماهه دوکاربره (۲۵۰ ت)", callback_data="buy_1m_2u"),
        ],
        [
            InlineKeyboardButton(text="2️⃣ ۲ ماهه تک (۳۸۰ ت)", callback_data="buy_2m_1u"),
            InlineKeyboardButton(text="👥 ۲ ماهه دوکاربره (۴۳۰ ت)", callback_data="buy_2m_2u"),
        ],
        [
            InlineKeyboardButton(text="3️⃣ ۳ ماهه تک (۵۵۰ ت)", callback_data="buy_3m_1u"),
            InlineKeyboardButton(text="👥 ۳ ماهه دوکاربره (۶۰۰ ت)", callback_data="buy_3m_2u"),
        ],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data="cancel_action")]]
    )

# ----------------- هندلرهای اصلی -----------------
dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN)

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    date_str, time_str = get_current_jalali_datetime()
    welcome_text = (
        f"سلام {message.from_user.first_name} عزیز، به ربات رسمی **L2TP VPN 24/7** خوش آمدید!\n\n"
        f"📅 تاریخ: `{date_str}`\n"
        f"⏰ ساعت: `{time_str}` (به وقت تهران)\n\n"
        f"⚡ ارائه دهنده پایدارترین سرویس‌های L2TP / IPsec با پینگ مناسب و تضمین کیفیت.\n"
        f"تمامی تعرفه‌ها شامل **۱۰ گیگابایت ترافیک هدیه** می‌باشند.\n\n"
        f"جهت خرید یا مدیریت حساب از منوی زیر استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# آمار کل کاربران ربات (مخصوص ادمین)
@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    count = get_users_count()
    await message.answer(f"📊 **آمار کاربران ربات:**\n\nتعداد کل اعضا: `{count}` کاربر", parse_mode="Markdown")

# تعرفه‌ها و خرید اشتراک
@dp.message(F.text == "🛍️ خرید اشتراک و تعرفه‌ها")
async def show_tariffs(message: Message):
    tariffs_text = (
        "💎 **لیست تعرفه‌های سرویس L2TP VPN 24/7**\n"
        "*(تمامی پلن‌ها شامل ۱۰ گیگابایت ترافیک هدیه هستند)*\n\n"
        "🔹 **۱ ماهه تک کاربره:** ۲۰۰,۰۰۰ تومان\n"
        "🔹 **۱ ماهه دو کاربره:** ۲۵۰,۰۰۰ تومان\n\n"
        "🔹 **۲ ماهه تک کاربره:** ۳۸۰,۰۰۰ تومان\n"
        "🔹 **۲ ماهه دو کاربره:** ۴۳۰,۰۰۰ تومان\n\n"
        "🔹 **۳ ماهه تک کاربره:** ۵۵۰,۰۰۰ تومان\n"
        "🔹 **۳ ماهه دو کاربره:** ۶۰۰,۰۰۰ تومان\n\n"
        "💳 **شماره کارت جهت واریز:**\n"
        f"`{PAYMENT_CARD}`\n"
        f"به نام: **{PAYMENT_NAME}**\n\n"
        "👇 پلن مورد نظر خود را برای ثبت سفارش انتخاب فرمایید:"
    )
    await message.answer(tariffs_text, reply_markup=get_plans_inline_keyboard(), parse_mode="Markdown")

# کال‌بک خرید پلن‌ها
@dp.callback_query(F.data.startswith("buy_"))
async def process_plan_choice(call: CallbackQuery, state: FSMContext):
    plan_key = call.data.replace("buy_", "")
    if plan_key not in PLANS:
        await call.answer("پلن یافت نشد.", show_alert=True)
        return

    plan = PLANS[plan_key]
    await state.update_data(chosen_plan=plan["title"], price=plan["price"])
    await state.set_state(PaymentStates.waiting_for_receipt)

    text = (
        f"✅ شما پلن **{plan['title']}** را انتخاب کردید.\n"
        f"مبلغ قابل پرداخت: **{plan['price']}**\n\n"
        f"💳 شماره کارت جهت واریز:\n`{PAYMENT_CARD}`\n"
        f"به نام: **{PAYMENT_NAME}**\n\n"
        "📸 لطفاً **تصویر فیش واریزی** خود را ارسال نمایید:"
    )
    await call.message.edit_text(text, reply_markup=get_cancel_inline_keyboard(), parse_mode="Markdown")
    await call.answer()

# دریافت فیش پرداخت
@dp.message(PaymentStates.waiting_for_receipt, F.photo)
async def process_payment_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    chosen_plan = data.get("chosen_plan", "نامشخص")
    price = data.get("price", "نامشخص")

    photo_id = message.photo[-1].file_id
    caption = (
        f"📩 **فیش پرداخت جدید دریافت شد!**\n\n"
        f"👤 کاربر: {message.from_user.full_name} (@{message.from_user.username or 'ندارد'})\n"
        f"🆔 شناسه کاربری: `{message.from_user.id}`\n"
        f"📦 پلن انتخابی: {chosen_plan}\n"
        f"💰 مبلغ: {price}"
    )

    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption, parse_mode="Markdown")
        await message.answer(
            "✅ فیش واریزی شما با موفقیت برای مدیریت ارسال شد.\nسرویس شما پس از بررسی در سریع‌ترین زمان ممکن تحویل داده خواهد شد.",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Error forwarding receipt to admin: {e}")
        await message.answer("⚠️ در ارسال فیش خطایی رخ داد. لطفاً فیش را مستقیماً به پشتیبانی ارسال فرمایید.", reply_markup=get_main_keyboard())

    await state.clear()

# ----------------- طرح جبرانی مشترکین ۲ تا ۳ سال گذشته -----------------
@dp.message(F.text == "🎁 طرح جبرانی مشترکین")
async def compensation_info(message: Message, state: FSMContext):
    await state.set_state(CompensationStates.waiting_for_details)
    text = (
        "🎁 **طرح ویژهٔ جبران حق مشترکین قدیمی (۲ تا ۳ سال گذشته)**\n\n"
        "مشترکین عزیزی که در گذشته سرویس آن‌ها حین غیبت قطع شده و هزینه پرداخت کرده بودند:\n"
        "با ارسال مشخصات، اکانت شما **با دورهٔ کامل و ۱۰ گیگابایت ترافیک هدیه** از نو فعال می‌گردد.\n\n"
        "✍️ لطفاً **نام کاربری قبلی** به همراه **فیش یا مستندات واریزی قبلی** را در یک پیام (یا تصویر فیش با کپشن نام کاربری) ارسال کنید:"
    )
    await message.answer(text, reply_markup=get_cancel_inline_keyboard(), parse_mode="Markdown")

@dp.message(CompensationStates.waiting_for_details)
async def process_compensation_details(message: Message, state: FSMContext):
    caption = (
        f"🎁 **درخواست طرح جبرانی مشترک قدیمی!**\n\n"
        f"👤 کاربر: {message.from_user.full_name} (@{message.from_user.username or 'ندارد'})\n"
        f"🆔 شناسه: `{message.from_user.id}`\n"
    )

    try:
        if message.photo:
            caption += f"📝 توضیحات: {message.caption or 'بدون توضیح'}"
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
        else:
            caption += f"📝 اطلاعات ارسالی:\n{message.text}"
            await bot.send_message(chat_id=ADMIN_ID, text=caption, parse_mode="Markdown")

        await message.answer(
            "✅ مشخصات شما جهت بررسی طرح جبرانی برای مدیریت ارسال شد.\nاکانت شما با دوره کامل و ۱۰ گیگابایت هدیه فعال و به شما تحویل داده می‌شود.",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Error forwarding compensation details: {e}")
        await message.answer("⚠️ خطا در ارسال اطلاعات به مدیریت. لطفاً مستقیماً به پشتیبانی پیام دهید.", reply_markup=get_main_keyboard())

    await state.clear()

# مشخصات سرور و اتصال
@dp.message(F.text == "🌐 مشخصات سرور و اتصال")
async def show_connection_specs(message: Message):
    text = (
        "⚙️ **تنظیمات اتصال سرویس L2TP / IPsec:**\n\n"
        f"🌐 **Server Address / IP:** `{VPN_SERVER_IP}`\n"
        f"🔑 **IPsec Pre-Shared Key (Secret):** `{IPSEC_SECRET}`\n\n"
        "📌 *نکته:* شناسه کاربری و کلمه عبور اختصاصی پس از تایید خرید تحویل داده می‌شود."
    )
    await message.answer(text, parse_mode="Markdown")

# ورود به پنل مصرف (IBSng) با تذکر مهم
@dp.message(F.text == "📊 ورود به پنل مصرف (IBSng)")
async def show_ibsng_panel(message: Message):
    text = (
        "📊 **پنل کاربری و بررسی میزان مصرف اینترنت (IBSng):**\n\n"
        f"🔗 آدرس پنل:\n{IBSNG_PANEL_URL}\n\n"
        "⚠️ **توجه مهم:**\n"
        "برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید."
    )
    await message.answer(text, parse_mode="Markdown")

# حساب کاربری
@dp.message(F.text == "👤 حساب کاربری")
async def show_user_account(message: Message):
    text = (
        f"👤 **اطلاعات کاربری:**\n\n"
        f"نام: {message.from_user.full_name}\n"
        f"شناسه عددی: `{message.from_user.id}`\n"
        f"نام کاربری: @{message.from_user.username or 'ندارد'}\n\n"
        "جهت بررسی مدت اعتبار یا حجم، از بخش پنل مصرف (IBSng) استفاده نمایید."
    )
    await message.answer(text, parse_mode="Markdown")

# پشتیبانی
@dp.message(F.text == "💬 پشتیبانی 24/7")
async def show_support_info(message: Message):
    text = (
        "💬 **پشتیبانی ۲۴ ساعته L2TP VPN:**\n\n"
        f"جهت ارتباط با پشتیبانی، پیگیری خرید یا رفع اشکال:\n"
        f"👉 {SUPPORT_ID}"
    )
    await message.answer(text, parse_mode="Markdown")

# گزارش خطا
@dp.message(F.text == "⚠️ گزارش قطعی / پشتیبانی")
async def start_error_report(message: Message, state: FSMContext):
    await state.set_state(ErrorReportStates.waiting_for_report)
    await message.answer(
        "📝 لطفاً شرح مشکل یا قطعی خود را در قالب یک پیام ارسال کنید تا برای تیم پشتیبانی ارسال گردد:",
        reply_markup=get_cancel_inline_keyboard()
    )

@dp.message(ErrorReportStates.waiting_for_report)
async def process_error_report(message: Message, state: FSMContext):
    report_text = (
        f"⚠️ **گزارش قطعی/خطا جدید!**\n\n"
        f"از: {message.from_user.full_name} (@{message.from_user.username or 'ندارد'})\n"
        f"شناسه: `{message.from_user.id}`\n\n"
        f"متن گزارش:\n{message.text}"
    )
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=report_text, parse_mode="Markdown")
        await message.answer("✅ گزارش شما ثبت شد و به زودی پیگیری می‌شود.", reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Error sending error report: {e}")
        await message.answer("⚠️ خطا در ارسال گزارش. لطفاً به پشتیبانی پیام دهید.", reply_markup=get_main_keyboard())

    await state.clear()

# کانال اطلاع‌رسانی
@dp.message(F.text == "📢 کانال اطلاع‌رسانی")
async def show_channel_info(message: Message):
    text = f"📢 برای دریافت آخرین اخبار سرورها و اطلاعیه‌ها به کانال ما بپیوندید:\n{CHANNEL_URL}"
    await message.answer(text)

# انصراف کلی
@dp.callback_query(F.data == "cancel_action")
async def cancel_action_handler(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ عملیات لغو شد.")
    await call.answer("لغو شد")

# ----------------- وب سرور جهت Health Check در Render -----------------
async def handle_ping(request):
    return web.Response(text="Bot is running smoothly 24/7!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check server running on port {PORT}")

# ----------------- تابع اصلی اجرای برنامه -----------------
async def main():
    init_db()
    logger.info("Database initialized successfully.")
    
    # اجرای وب‌سرور داخلی برای سرویس وب Render
    await start_web_server()
    
    logger.info("Bot starting polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

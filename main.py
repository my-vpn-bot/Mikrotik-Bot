import os
import asyncio
import logging
import sqlite3
from datetime import datetime
import jdatetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ----------------------------------------------------
# 1. تنظیمات لاگینگ و متغیرهای محیطی
# ----------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "Arshavin_Support")

# مشخصات واریز کارت به کارت
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9918-0000-0000")
CARD_HOLDER = os.getenv("CARD_HOLDER", "سجاد رحیمی")

PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    logger.error("❌ خطای حیاتی: BOT_TOKEN در متغیرهای محیطی تنظیم نشده است!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ----------------------------------------------------
# 2. توابع زمان شمسی و دیتابیس کاربران
# ----------------------------------------------------
DB_FILE = "bot_users.db"

def get_current_shamsi_datetime():
    persian_days = {
        "Saturday": "شنبه",
        "Sunday": "یکشنبه",
        "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه",
        "Wednesday": "چهارشنبه",
        "Thursday": "پنج‌شنبه",
        "Friday": "جمعه"
    }
    now_j = jdatetime.datetime.now()
    day_en = now_j.strftime("%A")
    day_fa = persian_days.get(day_en, day_en)
    date_str = now_j.strftime("%Y/%m/%d")
    time_str = now_j.strftime("%H:%M")
    return day_fa, date_str, time_str

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            shamsi_join_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_or_update_user(user_id: int, full_name: str, username: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        day_fa, date_str, time_str = get_current_shamsi_datetime()
        shamsi_join_date = f"{day_fa} {date_str} - {time_str}"
        
        if not exists:
            cursor.execute(
                "INSERT INTO users (user_id, full_name, username, shamsi_join_date) VALUES (?, ?, ?, ?)",
                (user_id, full_name, username, shamsi_join_date)
            )
        else:
            cursor.execute(
                "UPDATE users SET full_name = ?, username = ? WHERE user_id = ?",
                (full_name, username, user_id)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطا در ثبت اطلاعات کاربر در دیتابیس: {e}")

def get_user_info(user_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, username, shamsi_join_date FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row
    except Exception as e:
        logger.error(f"خطا در دریافت اطلاعات کاربر: {e}")
        return None

def get_total_users_count():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

init_db()

# ----------------------------------------------------
# 3. ماشین وضعیت خرید اشتراک (FSM)
# ----------------------------------------------------
class PurchaseStates(StatesGroup):
    waiting_for_receipt = State()

# ----------------------------------------------------
# 4. تعرفه‌ها و کیبوردهای ربات
# ----------------------------------------------------
PLANS_DATA = {
    "plan_1m_30g": {
        "title": "⚡ پلن ۱ ماهه (۳۰ گیگابایت)",
        "traffic": "۳۰ گیگابایت",
        "duration": "۱ ماهه",
        "price": "۳۵۰,۰۰۰ تومان"
    },
    "plan_2m_60g": {
        "title": "⚡ پلن ۲ ماهه (۶۰ گیگابایت)",
        "traffic": "۶۰ گیگابایت",
        "duration": "۲ ماهه",
        "price": "۶۵۰,۰۰۰ تومان"
    },
    "plan_3m_90g": {
        "title": "⚡ پلن ۳ ماهه (۹۰ گیگابایت)",
        "traffic": "۹۰ گیگابایت",
        "duration": "۳ ماهه",
        "price": "۹۵۰,۰۰۰ تومان"
    },
    "plan_unlimited": {
        "title": "👑 پلن اشتراک نامحدود",
        "traffic": "نامحدود (حجم منصفانه)",
        "duration": "۱ ماهه",
        "price": "۱,۸۰۰,۰۰۰ تومان"
    }
}

def clean_username(uname: str) -> str:
    return uname.replace("@", "").strip()

def main_menu_keyboard(is_admin: bool = False):
    clean_support = clean_username(SUPPORT_USERNAME)
    keyboard = [
        [
            InlineKeyboardButton(text="🛍 خرید اشتراک V2Ray", callback_data="buy_service"),
            InlineKeyboardButton(text="👤 حساب کاربری من", callback_data="user_profile")
        ],
        [
            InlineKeyboardButton(text="⚙️ کانفیگ سفارشی", callback_data="custom_config"),
            InlineKeyboardButton(text="📚 راهنما و بسترها", callback_data="help_guide")
        ],
        [
            InlineKeyboardButton(text="💬 ارتباط مستقیم با پشتیبانی", url=f"https://t.me/{clean_support}")
        ]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="📊 آمار بازدیدکنندگان و کاربران", callback_data="admin_stats")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def plans_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🚀 ۱ ماهه (۳۰ گیگ) - ۳۵۰,۰۰۰ تومان", callback_data="plan_1m_30g")],
        [InlineKeyboardButton(text="🚀 ۲ ماهه (۶۰ گیگ) - ۶۵۰,۰۰۰ تومان", callback_data="plan_2m_60g")],
        [InlineKeyboardButton(text="🚀 ۳ ماهه (۹۰ گیگ) - ۹۵۰,۰۰۰ تومان", callback_data="plan_3m_90g")],
        [InlineKeyboardButton(text="👑 نامحدود (سرعت گیگابیت) - ۱,۸۰۰,۰۰۰ تومان", callback_data="plan_unlimited")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_only_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]]
    )

# ----------------------------------------------------
# 5. هندلرهای پیام‌ها و رویدادها
# ----------------------------------------------------

@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    add_or_update_user(user.id, user.full_name, user.username or "")

    day_name, date_str, time_str = get_current_shamsi_datetime()
    is_admin = (str(user.id) == str(ADMIN_ID))

    welcome_text = (
        f"سلام **{user.first_name}** عزیز! بسیار خوش آمدید. 🌹\n\n"
        f"📅 **امروز:** {day_name} {date_str}\n"
        f"⏰ **ساعت:** {time_str}\n\n"
        f"🌐 **سامانه ارائه سرویس‌های اینترنت بین‌الملل**\n"
        f"در حال حاضر سرویس‌ها با نهایت سرعت و پایداری بر بستر پرقدرت **V2Ray** ارائه می‌گردند.\n\n"
        f"جهت خرید یا مدیریت حساب کاربری از گزینه‌های زیر استفاده نمایید:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(is_admin)
    )

@dp.callback_query(F.data == "admin_stats")
async def handle_admin_stats(callback: CallbackQuery):
    if str(callback.from_user.id) != str(ADMIN_ID):
        await callback.answer("⛔ دسترسی به این بخش فقط مخصوص مدیریت است.", show_alert=True)
        return
    
    total = get_total_users_count()
    day_name, date_str, time_str = get_current_shamsi_datetime()
    
    stats_text = (
        f"📊 **گزارش آمار ربات:**\n\n"
        f"👥 تعداد کل اعضا و بازدیدکنندگان ثبت‌شده در دیتابیس: **{total} نفر**\n"
        f"📅 تاریخ استعلام: {day_name} {date_str}\n"
        f"⏰ ساعت: {time_str}"
    )
    await callback.message.edit_text(stats_text, parse_mode="Markdown", reply_markup=back_only_keyboard())

@dp.callback_query(F.data == "user_profile")
async def handle_user_profile(callback: CallbackQuery):
    user = callback.from_user
    user_data = get_user_info(user.id)
    join_date = user_data[2] if user_data and user_data[2] else "نامشخص"

    profile_text = (
        f"👤 **اطلاعات حساب کاربری شما:**\n\n"
        f"▫️ نام شما: **{user.full_name}**\n"
        f"▫️ شناسه عددی (ID): `{user.id}`\n"
        f"▫️ نام کاربری: @{user.username if user.username else 'تعیین نشده'}\n"
        f"▫️ تاریخ ثبت نام: `{join_date}`\n"
        f"▫️ وضعیت اشتراک: ⚠️ **فاقد سرویس فعال**\n\n"
        f"برای تهیه یا تمدید اشتراک به بخش **خرید اشتراک V2Ray** مراجعه نمایید."
    )
    await callback.message.edit_text(profile_text, parse_mode="Markdown", reply_markup=back_only_keyboard())

@dp.callback_query(F.data == "buy_service")
async def handle_buy_service(callback: CallbackQuery):
    text = (
        "🛍 **لیست پلن‌های پرسرعت V2Ray:**\n\n"
        "تمامی پلن‌ها دارای سرورهای اختصاصی با پینگ پایین، آی‌پی تمیز و بدون محدودیت سرعت هستند.\n"
        "لطفاً پلن مد نظر خود را انتخاب کنید:"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=plans_keyboard())

@dp.callback_query(F.data.startswith("plan_"))
async def handle_plan_selection(callback: CallbackQuery, state: FSMContext):
    plan_key = callback.data
    if plan_key not in PLANS_DATA:
        await callback.answer("پلن انتخاب‌شده نامعتبر است.", show_alert=True)
        return

    plan = PLANS_DATA[plan_key]
    await state.update_data(selected_plan=plan_key)
    await state.set_state(PurchaseStates.waiting_for_receipt)

    clean_support = clean_username(SUPPORT_USERNAME)

    invoice_text = (
        f"💎 **پیش‌فاکتور سفارش شما:**\n\n"
        f"📌 سرویس: **{plan['title']}**\n"
        f"⏱ مدت اعتبار: **{plan['duration']}**\n"
        f"📊 حجم ترافیک: **{plan['traffic']}**\n"
        f"💰 مبلغ قابل پرداخت: **{plan['price']}**\n\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"💳 **اطلاعات پرداخت کارت به کارت:**\n"
        f"شماره کارت: `{CARD_NUMBER}`\n"
        f"به نام: **{CARD_HOLDER}**\n"
        f"➖➖➖➖➖➖➖➖➖➖\n\n"
        f"⚠️ **مراحل تکمیل خرید:**\n"
        f"۱. مبلغ را واریز نمایید.\n"
        f"۲. **تصویر فیش واریزی (رسید)** را مستقیماً همینجا ارسال کنید.\n\n"
        f"📞 در صورت هرگونه سوال یا مشکل با آیدی @{clean_support} در ارتباط باشید."
    )

    await callback.message.edit_text(invoice_text, parse_mode="Markdown", reply_markup=back_only_keyboard())

@dp.message(PurchaseStates.waiting_for_receipt, F.photo)
async def handle_receipt_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_key = data.get("selected_plan", "plan_1m_30g")
    plan = PLANS_DATA.get(plan_key, {"title": "نامشخص", "price": "نامشخص"})
    
    day_name, date_str, time_str = get_current_shamsi_datetime()

    await message.answer(
        "✅ **رسید پرداخت شما با موفقیت دریافت شد.**\n\n"
        "همکاران ما در واحد پشتیبانی پس از بررسی و تایید واریزی، کانفیگ اختصاصی شما را ارسال خواهند کرد.\n"
        "از صبوری و اعتماد شما سپاسگزاریم. 🌸",
        parse_mode="Markdown"
    )

    if ADMIN_ID:
        try:
            admin_caption = (
                f"🔔 **رسید خرید جدید ثبت شد!**\n\n"
                f"👤 نام خریدار: {message.from_user.full_name}\n"
                f"🆔 شناسه کاربر: `{message.from_user.id}`\n"
                f"🔗 یوزرنیم: @{message.from_user.username if message.from_user.username else 'ندارد'}\n"
                f"📦 پلن انتخابی: {plan['title']}\n"
                f"💰 مبلغ: {plan['price']}\n"
                f"📅 زمان ارسال: {day_name} {date_str} - ساعت {time_str}"
            )
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=admin_caption
            )
        except Exception as e:
            logger.error(f"خطا در ارسال تصویر فیش به ادمین: {e}")

    await state.clear()

@dp.callback_query(F.data == "custom_config")
async def handle_custom_config(callback: CallbackQuery):
    clean_support = clean_username(SUPPORT_USERNAME)
    text = (
        "⚙️ **سفارش کانفیگ اختصاصی و حجم سفارشی:**\n\n"
        "چنانچه نیاز به حجم بالاتر، آی‌پی ثابت اختصاصی ترید، یا چندکاربره برای سازمان‌ها دارید، "
        f"لطفاً مستقیماً با مدیریت پشتیبانی به آیدی @{clean_support} در ارتباط باشید."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_only_keyboard())

@dp.callback_query(F.data == "help_guide")
async def handle_help_guide(callback: CallbackQuery):
    clean_support = clean_username(SUPPORT_USERNAME)
    text = (
        "📚 **راهنمای پروتکل‌ها و بستر سرویس‌ها:**\n\n"
        "🚀 **بستر فعال و اصلی:**\n"
        "هم‌اکنون تمامی اشتراک‌ها بر بستر پروتکل‌های نسل جدید **V2Ray (Vless / Vmess)** ارائه می‌شوند که نهایت سازگاری، سرعت، پایداری و دور زدن اختلالات را برای کلیه اپراتورها فراهم می‌آورد.\n\n"
        "🔜 **بسترهای در حال پیاده‌سازی و اتصال در آینده:**\n"
        "به زودی اتصال روی پروتکل‌های زیر نیز به پنل اضافه خواهد شد:\n"
        "• **L2TP / IPsec** (اتصال مستقیم و پایدار بر روی روتر میکروتیک و سیستم‌عامل‌ها)\n"
        "• **PPTP** (اتصال سریع و سبک)\n"
        "• **OpenVPN** (بالاترین سطح رمزنگاری و تونلینگ ایمن)\n\n"
        f"جهت دریافت اپلیکیشن‌های پیشنهادی و آموزش‌ها با آیدی @{clean_support} در تماس باشید."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_only_keyboard())

@dp.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    day_name, date_str, time_str = get_current_shamsi_datetime()
    is_admin = (str(user.id) == str(ADMIN_ID))

    text = (
        f"منوی اصلی ربات:\n\n"
        f"📅 **امروز:** {day_name} {date_str} | ⏰ **ساعت:** {time_str}\n"
        f"لطفاً یکی از بخش‌های زیر را انتخاب کنید:"
    )
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(is_admin)
    )

# ----------------------------------------------------
# 6. وب‌سرور داخلی برای پاسخ به Health Checkهای Render
# ----------------------------------------------------
async def health_check_handler(request):
    return web.Response(text="Mikrotik-Bot is Running Perfectly on Port 10000! 🚀")

async def start_internal_server():
    app = web.Application()
    app.router.add_get('/', health_check_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"✅ وب‌سرور رندر با موفقیت روی پورت {PORT} راه‌اندازی شد.")

# ----------------------------------------------------
# 7. راه‌اندازی اصلی
# ----------------------------------------------------
async def main():
    await start_internal_server()
    logger.info("🤖 ربات تلگرام در حال گوش دادن به پیام‌ها (Polling)...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"خطای بحرانی در اجرای ربات: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ربات متوقف شد.")

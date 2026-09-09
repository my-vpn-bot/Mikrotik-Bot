import os
import sys
import logging
import asyncio
import sqlite3
import jdatetime
from datetime import datetime, timezone, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery
)

# ==================== لاگینگ ====================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("Mikrotik-Bot")

# ==================== تنظیمات و متغیرهای محیطی ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "")
PORT = int(os.getenv("PORT", 10000))
DB_PATH = "bot_database.db"

# قیمت پلن‌ها
PLAN1_PRICE = os.getenv("PLAN1_PRICE", "250,000 تومان")
PLAN2_PRICE = os.getenv("PLAN2_PRICE", "400,000 تومان")
PLAN3_PRICE = os.getenv("PLAN3_PRICE", "600,000 تومان")

# دریافت اطلاعات کارت بانکی (پشتیبانی از هر دو نام‌گذاری در Render)
def get_card_info():
    num = os.getenv("PAYMENT_CARD") or os.getenv("CARD_NUMBER") or "وارد نشده"
    holder = os.getenv("PAYMENT_NAME") or os.getenv("CARD_HOLDER") or "مدیریت"
    return num.strip(), holder.strip()

# پاکسازی و استانداردسازی آدرس‌های URL و آیدی‌ها
def make_clean_url(val: str, default_username: str) -> str:
    raw = (val or default_username).strip()
    raw = raw.replace("https://t.me/", "").replace("http://t.me/", "").replace("tg://resolve?domain=", "")
    username = raw.lstrip("@").strip()
    return f"https://t.me/{username}"

SUPPORT_LINK = make_clean_url(os.getenv("SUPPORT_ID") or os.getenv("SUPPORT_USERNAME"), "L2TP_Support")
CHANNEL_LINK = make_clean_url(os.getenv("CHANNEL_URL") or os.getenv("CHANNEL_USERNAME"), "L2tp_vpn402")

# ==================== دیتابیس ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance INTEGER DEFAULT 0,
            active_subscriptions INTEGER DEFAULT 0,
            join_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user_if_not_exists(user_id: int, username: str, full_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, full_name, join_date)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, full_name, now_str))
    conn.commit()
    conn.close()

def get_user_stats(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, active_subscriptions, join_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0], row[1], row[2]
    return 0, 0, "نامشخص"

init_db()

# ==================== ربات و دیسپچر ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# کیبورد اصلی (دقیقاً ۴ ردیف، بدون تست رایگان و بدون زیرمجموعه‌گیری)
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

# کیبورد اینلاین پلن‌ها
def build_plans_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔹 پلن ۱ ماهه ({PLAN1_PRICE})", callback_data="buy_plan_1")],
        [InlineKeyboardButton(text=f"🔹 پلن ۲ ماهه ({PLAN2_PRICE})", callback_data="buy_plan_2")],
        [InlineKeyboardButton(text=f"🔹 پلن ۳ ماهه ({PLAN3_PRICE})", callback_data="buy_plan_3")],
        [InlineKeyboardButton(text="🧾 ارتباط با پشتیبانی / ارسال فیش", url=SUPPORT_LINK)],
        [InlineKeyboardButton(text="❌ بستن منو", callback_data="close_menu")]
    ])

# روزهای هفته به زبان فارسی
WEEKDAYS_FA = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنجشنبه",
    "Friday": "جمعه"
}

# ==================== هندلرها ====================

# متن کامل خوش‌آمدگویی دقیقاً مطابق با نسخه اصلی
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    user = message.from_user
    add_user_if_not_exists(user.id, user.username or "", user.full_name)
    
    tehran_tz = timezone(timedelta(hours=3, minutes=30))
    now_tehran = datetime.now(tehran_tz)
    now_jalali = jdatetime.datetime.fromgregorian(datetime=now_tehran.replace(tzinfo=None))
    weekday_en = now_tehran.strftime("%A")
    weekday_fa = WEEKDAYS_FA.get(weekday_en, "")
    
    welcome_msg = (
        f"سلام {user.full_name} عزیز! 🌹\n\n"
        f"📅 امروز: <b>{weekday_fa} {now_jalali.strftime('%Y/%m/%d')}</b>\n"
        f"⏰ ساعت: <b>{now_jalali.strftime('%H:%M:%S')}</b>\n\n"
        f"به دنیای سرعت و پایداری خوش آمدید! 🚀\n"
        f"ربات رسمی ارائه سرویس‌های اختصاصی L2TP VPN\n\n"
        f"⚡️ <b>سرعت و پایداری بسیار بالا</b>\n"
        f"🛡 <b>اتصال رمزنگاری‌شده و امن</b>\n"
        f"🌐 <b>حجم کاملاً نامحدود</b>\n"
        f"🕒 <b>پشتیبانی دائمی و سریع</b>\n\n"
        f"📢 کانال اطلاع‌رسانی: {CHANNEL_LINK}\n\n"
        f"👇 برای شروع و مدیریت سرویس‌ها، از منوی زیر استفاده کنید:"
    )
    await message.answer(welcome_msg, reply_markup=main_keyboard, parse_mode="HTML")

@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy(message: types.Message):
    await message.answer("🛍️ لطفاً یکی از پلن‌های زیر را انتخاب کنید:", reply_markup=build_plans_keyboard())

@dp.callback_query(F.data.startswith("buy_plan_"))
async def handle_plan_callback(callback: CallbackQuery):
    plan_code = callback.data.split("_")[-1]
    plans_info = {
        "1": ("۱ ماهه", PLAN1_PRICE),
        "2": ("۲ ماهه", PLAN2_PRICE),
        "3": ("۳ ماهه", PLAN3_PRICE)
    }
    duration, price = plans_info.get(plan_code, ("نامشخص", "تماس با پشتیبانی"))
    card_num, card_holder = get_card_info()
    
    text = (
        f"💳 <b>اطلاعات پرداخت برای خرید اشتراک {duration}</b>\n\n"
        f"💵 مبلغ قابل پرداخت: <b>{price}</b>\n"
        f"💳 شماره کارت: <code>{card_num}</code>\n"
        f"👤 به نام: <b>{card_holder}</b>\n\n"
        f"📌 لطفاً پس از واریز، تصویر فیش پرداختی خود را به همراه نام کاربری تلگرام برای پشتیبانی ارسال کنید تا اشتراک شما فعال گردد."
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 ارسال فیش به پشتیبانی", url=SUPPORT_LINK)],
        [InlineKeyboardButton(text="❌ بستن پیام", callback_data="close_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)

@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account_info(message: types.Message):
    user = message.from_user
    balance, active_subs, join_date = get_user_stats(user.id)
    
    text = (
        f"📊 <b>اطلاعات حساب کاربری شما:</b>\n\n"
        f"👤 نام: <b>{user.full_name}</b>\n"
        f"🆔 شناسه عددی (ID): <code>{user.id}</code>\n"
        f"💰 موجودی کیف پول: <b>{balance:,} تومان</b>\n"
        f"💎 تعداد اشتراک‌های فعال: <b>{active_subs}</b>\n"
        f"📅 تاریخ عضویت: <code>{join_date}</code>"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: types.Message):
    await message.answer(
        "💎 در حال حاضر اشتراک فعالی برای شما ثبت نشده است یا در صورت خرید، کانفیگ شما تحویل داده شده است.\n\n"
        "جهت استعلام سرویس یا تمدید، با پشتیبانی در ارتباط باشید.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 پشتیبانی", url=SUPPORT_LINK)]
        ])
    )

@dp.message(F.text == "💰 شارژ حساب")
async def handle_charge(message: types.Message):
    card_num, card_holder = get_card_info()
    text = (
        f"💰 <b>شارژ موجودی حساب کاربری:</b>\n\n"
        f"جهت افزایش موجودی، مبلغ دلخواه را به شماره کارت زیر واریز نمایید:\n\n"
        f"💳 شماره کارت: <code>{card_num}</code>\n"
        f"👤 به نام: <b>{card_holder}</b>\n\n"
        f"📌 سپس عکس فیش واریزی را جهت اعمال در کیف پول ارسال کنید."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 ارسال فیش واریزی", url=SUPPORT_LINK)]
    ]))

@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: types.Message):
    text = (
        "👥 <b>واحد پشتیبانی و فروش:</b>\n\n"
        "برای پیگیری سفارشات، دریافت کانفیگ، رفع اشکال در اتصال یا هرگونه سوال دیگر، از دکمه زیر استفاده کنید:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 چت با پشتیبانی", url=SUPPORT_LINK)]
    ]))

@dp.message(F.text == "❓ سوالات متداول")
async def handle_faq(message: types.Message):
    faq_text = (
        "❓ <b>سوالات متداول (FAQ):</b>\n\n"
        "۱. <b>سرویس L2TP روی چه دستگاه‌هایی کار می‌کند؟</b>\n"
        "پاسخ: این پروتکل به صورت پیش‌فرض روی ویندوز، مک، اندروید و آیفون بدون نیاز به نصب نرم‌افزار اضافی قابل تنظیم است.\n\n"
        "۲. <b>تحویل سرویس چقدر زمان می‌برد؟</b>\n"
        "پاسخ: پس از ارسال فیش به پشتیبانی، حداکثر ظرف ۵ الی ۱۵ دقیقه اشتراک تحویل می‌گردد.\n\n"
        "۳. <b>آیا حجم دانلود محدود است؟</b>\n"
        "پاسخ: خیر، تمامی پلن‌ها کاملاً نامحدود هستند."
    )
    await message.answer(faq_text, parse_mode="HTML")

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs(message: types.Message):
    text = (
        f"⚙️ <b>راهنمای اتصال و کانفیگ‌ها:</b>\n\n"
        f"تمام آموزش‌های تصویری و ویدیویی اتصال به همراه آخرین اخبار در کانال رسمی قرار داده شده است.\n\n"
        f"📢 آدرس کانال رسمی ما:\n{CHANNEL_LINK}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 عضویت در کانال", url=CHANNEL_LINK)]
    ]))

@dp.callback_query(F.data == "close_menu")
async def close_menu(callback: CallbackQuery):
    await callback.message.delete()

# ==================== سرور Aiohttp و چرخه اصلی ====================
async def health_check(request):
    return web.Response(text="Mikrotik-Bot is Running and Healthy!")

async def main():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/healthz", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot polling is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

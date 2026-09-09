import os
import sys
import logging
import asyncio
import sqlite3
import jdatetime
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery
)

# ==================== تنظیمات لاگ ====================
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s", 
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Mikrotik-Bot")

# ==================== متغیرهای محیطی ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", 10000))
DB_PATH = "bot_database.db"

# نرمال‌سازی لینک پشتیبانی و کانال
raw_support = os.getenv("SUPPORT_USERNAME", "L2TP_Support").strip()
SUPPORT_URL = f"https://t.me/{raw_support.replace('@', '')}"

raw_channel = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CHANNEL_URL = raw_channel if raw_channel.startswith("http") else f"https://t.me/{raw_channel.replace('@', '')}"

CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9918-0000-0000").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "رحیمی").strip()

PLAN1_PRICE = os.getenv("PLAN1_PRICE", "۲۵۰,۰۰۰").strip()
PLAN2_PRICE = os.getenv("PLAN2_PRICE", "۴۰۰,۰۰۰").strip()
PLAN3_PRICE = os.getenv("PLAN3_PRICE", "۶۰۰,۰۰۰").strip()

# ==================== دیتابیس ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TEXT,
            balance INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==================== راه‌اندازی ربات ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== منوی اصلی ۴ ردیفه ====================
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

# ==================== هندلر پیام خوش‌آمدگویی ====================
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    # ثبت کاربر در دیتابیس در صورت عدم وجود
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, join_date) VALUES (?, ?, ?, ?)",
        (
            message.from_user.id, 
            message.from_user.username or "", 
            message.from_user.full_name or "", 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    conn.commit()
    conn.close()

    # تبدیل تاریخ و زمان به شمسی
    now = jdatetime.datetime.now()
    weekday_map = {
        "Saturday": "شنبه", "Sunday": "یکشنبه", "Monday": "دوشنبه", 
        "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه", "Thursday": "پنجشنبه", "Friday": "جمعه"
    }
    persian_weekday = weekday_map.get(now.strftime("%A"), now.strftime("%A"))
    jalali_date = now.strftime("%Y/%m/%d")
    current_time = now.strftime("%H:%M:%S")

    welcome_msg = (
        f"سلام {message.from_user.full_name} عزیز! 🌹\n\n"
        f"📅 امروز {persian_weekday} {jalali_date}\n"
        f"⏰ ساعت: {current_time}\n\n"
        "به دنیای سرعت و پایداری خوش آمدید! 🚀 ربات رسمی L2TP VPN با افتخار سرویس‌های اینترنت پرسرعت و نامحدود را برای شما ارائه می‌دهد.\n\n"
        "🌟 ویژگی‌های سرویس اختصاصی:\n"
        "⚡ سرعت و پایداری بالا: بدون افت سرعت، ایده‌آل برای وب‌گردی و گیمینگ\n"
        "🛡 اتصال رمزنگاری‌شده و امن: حفظ کامل حریم خصوصی و امنیت داده‌ها\n"
        "🌐 حجم کاملاً نامحدود: بدون محدودیت مصرف در طول دوره اشتراک\n"
        "🕒 پشتیبانی ۲۴ ساعته: همراهی مستمر در تمام ساعات شبانه‌روز\n\n"
        f"📢 کانال اطلاع‌رسانی و آموزش: {CHANNEL_URL}\n\n"
        "👇 برای شروع، از منوی زیر گزینه مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(welcome_msg, reply_markup=main_keyboard)

# ==================== هندلر خرید اشتراک ====================
@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy(message: types.Message):
    buy_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔹 پلن ۱ ماهه اختصاصی ({PLAN1_PRICE} تومان)", callback_data="buy_plan_1")],
        [InlineKeyboardButton(text=f"🔹 پلن ۲ ماهه اختصاصی ({PLAN2_PRICE} تومان)", callback_data="buy_plan_2")],
        [InlineKeyboardButton(text=f"🔹 پلن ۳ ماهه اختصاصی ({PLAN3_PRICE} تومان)", callback_data="buy_plan_3")],
        [InlineKeyboardButton(text="🧾 ارسال فیش واریزی به پشتیبانی", url=SUPPORT_URL)]
    ])
    await message.answer(
        "🛍️ **لیست پلن‌های فعال اشتراک اختصاصی:**\n\n"
        "تمام پلن‌ها با حجم نامحدود، آی‌پی ثابت و پایداری بالا ارائه می‌شوند.\n"
        "👇 لطفاً پلن مورد نظر خود را انتخاب کنید:", 
        reply_markup=buy_kb,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("buy_plan_"))
async def handle_plan_callback(callback: CallbackQuery):
    plan_id = callback.data.split("_")[-1]
    prices = {"1": PLAN1_PRICE, "2": PLAN2_PRICE, "3": PLAN3_PRICE}
    durations = {"1": "یک‌ماهه", "2": "دو‌ماهه", "3": "سه‌ماهه"}
    
    selected_price = prices.get(plan_id, PLAN1_PRICE)
    selected_dur = durations.get(plan_id, "یک‌ماهه")

    payment_info = (
        f"💳 **اطلاعات واریز جهت فعال‌سازی اشتراک {selected_dur}:**\n\n"
        f"💰 مبلغ قابل پرداخت: **{selected_price} تومان**\n"
        f"🔢 شماره کارت: `{CARD_NUMBER}`\n"
        f"👤 به نام: **{CARD_HOLDER}**\n\n"
        "⚠️ **توجه:** پس از پرداخت، تصویر فیش واریزی را از طریق دکمه زیر ارسال فرمایید تا سرویس در کوتاه‌ترین زمان فعال شود."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 ارسال فیش واریزی به پشتیبانی", url=SUPPORT_URL)]
    ])
    await callback.message.answer(payment_info, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

# ==================== هندلر شارژ حساب ====================
@dp.message(F.text == "💰 شارژ حساب")
async def handle_wallet_charge(message: types.Message):
    charge_text = (
        "💰 **افزایش موجودی کیف پول**\n\n"
        "برای شارژ حساب خود، مبلغ مورد نظر را به شماره کارت زیر واریز نمایید:\n\n"
        f"🔢 شماره کارت: `{CARD_NUMBER}`\n"
        f"👤 به نام: **{CARD_HOLDER}**\n\n"
        "📸 سپس تصویر فیش واریزی به همراه شناسه کاربری خود را به پشتیبانی ارسال کنید:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 ارسال فیش به پشتیبانی", url=SUPPORT_URL)]
    ])
    await message.answer(charge_text, parse_mode="Markdown", reply_markup=kb)

# ==================== هندلر پشتیبانی ====================
@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: types.Message):
    support_text = (
        "👥 **واحد پشتیبانی و خدمات مشتریان**\n\n"
        "همکاران ما در بخش پشتیبانی آماده پاسخگویی به سوالات، رفع مشکلات اتصال و تایید فیش‌های واریزی هستند.\n\n"
        "⏱ ساعت پاسخگویی: ۲۴ ساعته / ۷ روز هفته\n"
        "👇 جهت ارتباط مستقیم کلیک کنید:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 ارتباط با پشتیبانی / ارسال رسید", url=SUPPORT_URL)]
    ])
    await message.answer(support_text, parse_mode="Markdown", reply_markup=kb)

# ==================== هندلر اطلاعات حساب ====================
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
        "📊 **اطلاعات حساب کاربری شما:**\n\n"
        f"👤 نام: **{message.from_user.full_name}**\n"
        f"🆔 شناسه کاربری: `{user_id}`\n"
        f"💰 موجودی کیف پول: **{balance:,} تومان**\n"
        f"📅 تاریخ عضویت: `{join_date}`\n"
    )
    await message.answer(info_text, parse_mode="Markdown")

# ==================== هندلر اشتراک‌های من ====================
@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: types.Message):
    sub_text = (
        "💎 **اشتراک‌های فعال شما:**\n\n"
        "در حال حاضر اشتراک فعالی برای حساب شما ثبت نشده است.\n\n"
        "🛍️ برای تهیه اشتراک جدید می‌توانید از دکمه «🛒 خرید اشتراک» استفاده کنید."
    )
    await message.answer(sub_text)

# ==================== هندلر سوالات متداول ====================
@dp.message(F.text == "❓ سوالات متداول")
async def handle_faq(message: types.Message):
    faq_text = (
        "❓ **سوالات متداول کاربران:**\n\n"
        "۱. **نحوه تحویل اشتراک چگونه است؟**\n"
        "پس از واریز مبلغ و ارسال فیش به پشتیبانی، مشخصات کانفیگ و راهنمای اتصال در کمتر از چند دقیقه برای شما ارسال می‌شود.\n\n"
        "۲. **آیا سرویس‌ها دارای محدودیت حجمی هستند؟**\n"
        "خیر، تمامی پلن‌های ارائه شده کاملاً نامحدود هستند.\n\n"
        "۳. **سرویس‌ها روی چه دستگاه‌هایی قابل استفاده هستند؟**\n"
        "این سرویس‌ها روی تمامی سیستم‌عامل‌ها شامل اندروید، iOS (آیفون و آیپد)، ویندوز و مکینتاش با بالاترین کیفیت قابل اتصال می‌باشند.\n\n"
        "۴. **گارانتی و پشتیبانی به چه صورت است؟**\n"
        "تمامی اشتراک‌ها تا آخرین روز اشتراک دارای ضمانت اتصال و پایداری هستند."
    )
    await message.answer(faq_text, parse_mode="Markdown")

# ==================== هندلر کانفیگ‌ها و آموزش ====================
@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs(message: types.Message):
    config_text = (
        "⚙️ **راهنمای جامع اتصال و نرم‌افزارها:**\n\n"
        "📱 **اندروید و iOS:** آخرین نسخه‌های کانکشن و نرم‌افزارهای مورد نیاز را می‌توانید از کانال رسمی دریافت کنید.\n"
        "💻 **ویندوز و مک:** آموزش گام‌به‌گام و فایل‌های نصبی در کانال پین شده است.\n\n"
        f"📢 برای مشاهده ویدیوهای آموزشی و دانلود برنامه‌ها وارد کانال شوید:\n{CHANNEL_URL}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 ورود به کانال آموزش‌ها", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="💬 راهنمایی از پشتیبانی", url=SUPPORT_URL)]
    ])
    await message.answer(config_text, reply_markup=kb)

# ==================== سرور داخلی سلامت (Web Server) ====================
async def health_check(request):
    return web.Response(text="Mikrotik-Bot is active and running perfectly!", status=200)

# ==================== تابع اصلی اجرا ====================
async def main():
    logger.info("Starting Web Health Check Server...")
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check server listening on port {PORT}")

    logger.info("Initializing Telegram Bot Polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped cleanly.")

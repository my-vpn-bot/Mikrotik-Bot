import os
import sys
import logging
import asyncio
from datetime import datetime
import pytz
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ----------------------------------------------------
# 1. تنظیمات لاگ و متغیرهای محیطی
# ----------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("متغیر محیطی BOT_TOKEN تنظیم نشده است!")
    sys.exit(1)

SUPPORT_ID = os.getenv("SUPPORT_ID", "L2tp1support").lstrip("@")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6037990000000000")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_VPN")
PORT = int(os.getenv("PORT", 10000))

# ----------------------------------------------------
# 2. دیکشنری پلن‌ها (بدون تک‌کاربره/دوکاربره)
# ----------------------------------------------------
PLANS = {
    "plan_1m": {"title": "اشتراک ۱ ماهه", "price": "۲۵۰,۰۰۰ تومان", "raw_price": 250000},
    "plan_2m": {"title": "اشتراک ۲ ماهه", "price": "۴۰۰,۰۰۰ تومان", "raw_price": 400000},
    "plan_3m": {"title": "اشتراک ۳ ماهه", "price": "۶۰۰,۰۰۰ تومان", "raw_price": 600000},
}

# ----------------------------------------------------
# 3. توابع کمکی (تبدیل تاریخ شمسی و زمان تهران)
# ----------------------------------------------------
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
        days -= 186
        jm = 7 + (days // 30)
        jd = 1 + (days % 30)
    return jy, jm, jd

WEEKDAYS_FA = {
    "Saturday": "شنبه",
    "Sunday": "یک‌شنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنج‌شنبه",
    "Friday": "جمعه",
}

def get_current_tehran_datetime():
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    weekday_en = now.strftime("%A")
    weekday_fa = WEEKDAYS_FA.get(weekday_en, weekday_en)
    date_str = f"{weekday_fa}، {jy:04d}/{jm:02d}/{jd:02d}"
    time_str = now.strftime("%H:%M:%S")
    return date_str, time_str

# ----------------------------------------------------
# 4. کیبوردهای اصلی و اینلاین
# ----------------------------------------------------
def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_plans_inline_keyboard():
    inline_keyboard = [
        [InlineKeyboardButton(text="۱ ماهه | ۲۵۰,۰۰۰ تومان", callback_data="buy_plan_1m")],
        [InlineKeyboardButton(text="۲ ماهه | ۴۰۰,۰۰۰ تومان", callback_data="buy_plan_2m")],
        [InlineKeyboardButton(text="۳ ماهه | ۶۰۰,۰۰۰ تومان", callback_data="buy_plan_3m")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_payment_support_keyboard():
    support_url = f"https://t.me/{SUPPORT_ID}"
    inline_keyboard = [
        [InlineKeyboardButton(text="ارسال فیش به پشتیبانی 👤", url=support_url)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

# ----------------------------------------------------
# 5. تعریف هندلرها
# ----------------------------------------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name or "کاربر گرامی"
    date_str, time_str = get_current_tehran_datetime()
    welcome_text = (
        f"سلام {user_name} عزیز 👋\n"
        f"به ربات مدیریت سرویس‌های پرسرعت L2TP خوش آمدید.\n\n"
        f"📅 **امروز:** {date_str}\n"
        f"⏰ **ساعت رسمی:** {time_str}\n\n"
        f"لطفاً از منوی زیر گزینه مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy_subscription(message: types.Message):
    text = (
        "🚀 **تعرفه‌های اشتراک پرسرعت:**\n\n"
        "🔹 اشتراک ۱ ماهه: ۲۵۰,۰۰۰ تومان\n"
        "🔹 اشتراک ۲ ماهه: ۴۰۰,۰۰۰ تومان\n"
        "🔹 اشتراک ۳ ماهه: ۶۰۰,۰۰۰ تومان\n\n"
        "لطفاً پلن مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(text, reply_markup=get_plans_inline_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_plan_"))
async def handle_plan_selection(callback: types.CallbackQuery):
    plan_key = callback.data.replace("buy_", "")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("پلن نامعتبر است.", show_alert=True)
        return

    text = (
        f"💎 **سفارش شما:** {plan['title']}\n"
        f"💳 **مبلغ قابل پرداخت:** {plan['price']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **اطلاعات کارت جهت واریز:**\n"
        f"▫️ شماره کارت: `{PAYMENT_CARD}`\n"
        f"▫️ صاحب حساب: **{PAYMENT_NAME}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ **توجه:** پس از واریز مبلغ، روی دکمه زیر کلیک کرده و تصویر فیش واریزی را مستقیماً برای پشتیبانی ارسال نمایید تا سرویس شما فعال شود."
    )
    await callback.message.answer(text, reply_markup=get_payment_support_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: types.Message):
    text = (
        "👥 **پشتیبانی و ارتباط با ما:**\n\n"
        f"جهت ارسال پیام، پیگیری سفارشات یا راهنمایی، مستقیماً به آیدی پشتیبانی پیام دهید:\n"
        f"👤 @{SUPPORT_ID}\n\n"
        f"📢 کانال اطلاع‌رسانی:\n{CHANNEL_URL}"
    )
    support_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ارتباط با پشتیبانی 💬", url=f"https://t.me/{SUPPORT_ID}")],
        [InlineKeyboardButton(text="کانال تلگرام 📢", url=CHANNEL_URL)]
    ])
    await message.answer(text, reply_markup=support_btn)

@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account_info(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "کاربر"
    text = (
        f"📊 **اطلاعات کاربری:**\n\n"
        f"👤 نام: {user_name}\n"
        f"🆔 شناسه کاربری: `{user_id}`\n"
        f"💰 موجودی کیف پول: ۰ تومان\n"
        f"💎 تعداد اشتراک‌های فعال: ۰"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: types.Message):
    text = (
        "💎 **لیست اشتراک‌های شما:**\n\n"
        "در حال حاضر هیچ اشتراک فعالی در حساب شما ثبت نشده است.\n"
        "جهت تهیه اشتراک از بخش «🛒 خرید اشتراک» اقدام فرمایید."
    )
    await message.answer(text)

@dp.message(F.text == "💰 شارژ حساب")
async def handle_wallet_charge(message: types.Message):
    text = (
        "💰 **شارژ کیف پول:**\n\n"
        f"جهت افزایش موجودی، مبلغ مورد نظر را به شماره کارت زیر واریز کرده و فیش را به پشتیبانی (@{SUPPORT_ID}) ارسال فرمایید:\n\n"
        f"💳 شماره کارت: `{PAYMENT_CARD}`\n"
        f"👤 به نام: **{PAYMENT_NAME}**"
    )
    await message.answer(text, reply_markup=get_payment_support_keyboard(), parse_mode="Markdown")

@dp.message(F.text == "❓ سوالات متداول")
async def handle_faq(message: types.Message):
    faq_text = (
        "❓ **سوالات متداول:**\n\n"
        "۱. **سرویس‌ها روی چه دستگاه‌هایی قابل استفاده هستند؟**\n"
        "پاسخ: تمامی سیستم‌عامل‌ها شامل اندروید، iOS، ویندوز، مک و لینوکس.\n\n"
        "۲. **تحویل سرویس چقدر زمان می‌برد؟**\n"
        "پاسخ: بلافاصله پس از ارسال فیش به پشتیبانی و تایید واریزی، کانفیگ ارسال می‌شود.\n\n"
        "۳. **آیا سرعت و کیفیت تضمین شده است؟**\n"
        "پاسخ: بله، تمامی سرورها با پورت اختصاصی و بدون قطعی ارائه می‌شوند."
    )
    await message.answer(faq_text, parse_mode="Markdown")

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs_and_help(message: types.Message):
    text = (
        "⚙️ **آموزش و تنظیمات اتصال:**\n\n"
        f"برای دریافت آخرین آموزش‌های اتصال، برنامه‌های مورد نیاز و کانفیگ‌ها به کانال رسمی ما مراجعه کنید:\n\n"
        f"📢 {CHANNEL_URL}"
    )
    await message.answer(text)

# ----------------------------------------------------
# 6. وب‌سرور هلث‌چک داخلی (برای Render و UptimeRobot)
# ----------------------------------------------------
async def health_check(request):
    return web.Response(text="OK - Mikrotik Bot is running live!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"✅ وب‌سرور هلث‌چک روی پورت {PORT} با موفقیت اجرا شد.")

# ----------------------------------------------------
# 7. تابع اصلی و اجرای هم‌زمان بات و وب‌سرور
# ----------------------------------------------------
async def main():
    logger.info("در حال راه‌اندازی ربات تلگرام و وب‌سرور...")
    await start_web_server()
    # حذف وب‌هوک‌های قبلی در صورت وجود جهت جلوگیری از تعارض (Conflict)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

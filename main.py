import os
import asyncio
from datetime import datetime
import pytz
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart

# ----------------- تنظیمات محیطی -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "L2tp1support").replace("@", "")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ----------------- تبدیل تاریخ میلادی به شمسی -----------------
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

def get_current_tehran_datetime():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یک‌شنبه"]
    day_name = weekdays[now.weekday()]
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    time_str = now.strftime("%H:%M:%S")
    date_str = f"{jy:04d}/{jm:02d}/{jd:02d}"
    return day_name, date_str, time_str

# ----------------- کیبوردهای پایین صفحه (Reply Keyboard) -----------------
# ۱. منوی اصلی ۴ ردیفه
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ],
    resize_keyboard=True
)

# ۲. کیبورد انتخاب پلن خرید (همگی پایین صفحه)
plans_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔹 پلن ۱ ماهه - ۲۵۰,۰۰۰ تومان")],
        [KeyboardButton(text="🔹 پلن ۳ ماهه - ۴۰۰,۰۰۰ تومان")],
        [KeyboardButton(text="🔹 پلن ۶ ماهه - ۶۰۰,۰۰۰ تومان")],
        [KeyboardButton(text="🔙 بازگشت به منوی اصلی")]
    ],
    resize_keyboard=True
)

# ۳. کیبورد بخش کانفیگ‌ها
configs_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 آموزش اتصال اندروید"), KeyboardButton(text="🍏 آموزش اتصال آیفون (iOS)")],
        [KeyboardButton(text="💻 آموزش اتصال ویندوز"), KeyboardButton(text="🌐 دریافت کانفیگ L2TP / V2Ray")],
        [KeyboardButton(text="🔙 بازگشت به منوی اصلی")]
    ],
    resize_keyboard=True
)

# ----------------- هندلرهای دستورات -----------------
@dp.message(CommandStart())
@dp.message(F.text == "🔙 بازگشت به منوی اصلی")
async def start_handler(message: Message):
    day_name, date_str, time_str = get_current_tehran_datetime()
    welcome_text = (
        f"سلام {message.from_user.first_name} عزیز، به ربات شانلی خوش آمدید! 🌸\n\n"
        f"📅 امروز: {day_name} {date_str}\n"
        f"⏰ ساعت رسمی تهران: {time_str}\n"
        f"🆔 شناسه کاربری: `{message.from_user.id}`\n\n"
        f"از منوی پایین صفحه، گزینه مورد نظر خود را انتخاب نمایید:"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_keyboard)

@dp.message(F.text == "🛒 خرید اشتراک")
async def buy_subscription_menu(message: Message):
    text = (
        "🛍 **انتخاب پلن اشتراک**\n\n"
        "لطفاً یکی از پلن‌های زیر را از کیبورد پایین انتخاب کنید:\n\n"
        "۱️⃣ **پلن ۱ ماهه:** ۲۵۰,۰۰۰ تومان\n"
        "۲️⃣ **پلن ۳ ماهه:** ۴۰۰,۰۰۰ تومان\n"
        "۳️⃣ **پلن ۶ ماهه:** ۶۰۰,۰۰۰ تومان\n\n"
        "⚡️ تمام پلن‌ها دارای اتصال با کیفیت بالا و کاربر نامحدود می‌باشند."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=plans_keyboard)

@dp.message(F.text.startswith("🔹 پلن"))
async def plan_selected_handler(message: Message):
    selected_plan = message.text
    text = (
        f"📌 **سفارش شما:** {selected_plan}\n\n"
        f"💳 شماره کارت جهت واریز:\n"
        f"`۶۰۳۷-۹۹۷۵-۱۲۳۴-۵۶۷۸`\n"
        f"به نام: مدیریت شانلی\n\n"
        f"⚠️ **مرحله نهایی:**\n"
        f"پس از واریز مبلغ، تصویر فیش واریزی را مستقیماً به آیدی پشتیبانی زیر ارسال فرمایید تا اشتراک شما فعال شود:\n\n"
        f"👤 پشتیبانی: @{SUPPORT_USERNAME}"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=plans_keyboard)

@dp.message(F.text == "📊 اطلاعات حساب")
async def account_info_handler(message: Message):
    day_name, date_str, time_str = get_current_tehran_datetime()
    text = (
        f"📊 **اطلاعات حساب کاربری شما**\n\n"
        f"👤 نام: {message.from_user.full_name}\n"
        f"🆔 شناسه کاربری: `{message.from_user.id}`\n"
        f"💰 موجودی کیف پول: ۰ تومان\n"
        f"💎 تعداد سرویس فعال: ۰\n\n"
        f"📅 تاریخ استعلام: {date_str} - {time_str}"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard)

@dp.message(F.text == "💎 اشتراک‌های من")
async def my_subs_handler(message: Message):
    text = (
        "💎 **اشتراک‌های فعال شما:**\n\n"
        "در حال حاضر هیچ اشتراک فعالی برای حساب شما ثبت نشده است.\n"
        "برای خرید اشتراک جدید از دکمه «🛒 خرید اشتراک» استفاده کنید."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard)

@dp.message(F.text == "💰 شارژ حساب")
async def charge_wallet_handler(message: Message):
    text = (
        "💰 **افزایش موجودی و شارژ کیف پول**\n\n"
        "جهت شارژ حساب، مبلغ مورد نظر را به شماره کارت زیر واریز کرده و فیش را به پشتیبانی بفرستید:\n\n"
        "`۶۰۳۷-۹۹۷۵-۱۲۳۴-۵۶۷۸`\n\n"
        f"👤 پشتیبانی: @{SUPPORT_USERNAME}"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_keyboard)

@dp.message(F.text == "👥 پشتیبانی")
async def support_handler(message: Message):
    text = (
        "👥 **واحد پشتیبانی شانلی**\n\n"
        "برای پاسخگویی به سوالات، پیگیری سفارش‌ها و فعال‌سازی سرویس با آیدی پشتیبانی در ارتباط باشید:\n\n"
        f"🆔 @{SUPPORT_USERNAME}\n"
        f"📢 کانال اطلاع‌رسانی: {CHANNEL_LINK}"
    )
    await message.answer(text, reply_markup=main_keyboard)

@dp.message(F.text == "❓ سوالات متداول")
async def faq_handler(message: Message):
    faq_text = (
        "❓ **سوالات متداول (FAQ)**\n\n"
        "۱. **تعداد کاربر مجاز چقدر است؟**\n"
        "تمامی سرویس‌ها به صورت **نامحدود کاربر** ارائه می‌شوند.\n\n"
        "۲. **حجم مصرفی سرویس‌ها چقدر است؟**\n"
        "حجم سرویس کاملاً **وابسته به انتخاب پلن** و تعرفه انتخابی شماست.\n\n"
        "۳. **سرویس‌ها روی چه دستگاه‌هایی کار می‌کنند؟**\n"
        "روی اندروید، آیفون (iOS)، ویندوز، مک و لینوکس.\n\n"
        "۴. **آیا سرعت و پایداری تضمین شده است؟**\n"
        "بله، تمامی سرورها با پهنای باند اختصاصی و آپتایم بالا ارائه می‌گردند.\n\n"
        "۵. **تحویل سرویس چقدر زمان می‌برد؟**\n"
        "پس از ارسال فیش به پشتیبانی، اشتراک در کمتر از ۵ الی ۱۵ دقیقه تحویل داده می‌شود.\n\n"
        "۶. **آیا امکان تمدید سرویس قبلی وجود دارد؟**\n"
        "بله، با هماهنگی پشتیبانی قبل از اتمام زمان سرویس می‌توانید آن را تمدید کنید.\n\n"
        "۷. **پروتکل‌های ارائه‌شده کدامند؟**\n"
        "پروتکل‌های پرسرعت L2TP، Cisco، V2Ray و WireGuard بر اساس نیاز شما.\n\n"
        "۸. **در صورت قطع شدن سرور چه اقدامی صورت می‌گیرد؟**\n"
        "سرورهای پشتیبان به صورت خودکار جایگزین خواهند شد.\n\n"
        "۹. **چگونه کانفیگ‌ها را دریافت کنم؟**\n"
        "از طریق بخش «⚙️ کانفیگ‌ها و آموزش اتصال» در منوی ربات.\n\n"
        "۱۰. **پلن‌های قابل سفارش کدامند؟**\n"
        "پلن‌های ۱ ماهه (۲۵۰ هزار)، ۳ ماهه (۴۰۰ هزار) و ۶ ماهه (۶۰۰ هزار تومان)."
    )
    await message.answer(faq_text, parse_mode="Markdown", reply_markup=main_keyboard)

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def configs_menu_handler(message: Message):
    text = "⚙️ **بخش تنظیمات و آموزش‌های اتصال**\n\nلطفاً سیستم‌عامل خود را از دکمه‌های پایین انتخاب نمایید:"
    await message.answer(text, reply_markup=configs_keyboard)

@dp.message(F.text.in_(["📱 آموزش اتصال اندروید", "🍏 آموزش اتصال آیفون (iOS)", "💻 آموزش اتصال ویندوز", "🌐 دریافت کانفیگ L2TP / V2Ray"]))
async def guides_handler(message: Message):
    text = (
        f"📖 راهنمای مربوط به: **{message.text}**\n\n"
        "جهت دریافت کانفیگ‌های اختصاصی یا راهنمایی گام‌به‌گام اتصال، به پشتیبانی پیام دهید:\n\n"
        f"👤 @{SUPPORT_USERNAME}"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=configs_keyboard)

# ----------------- سرور هلث‌چک برای رندر (Port 10000) -----------------
async def health_check(request):
    return web.Response(text="Shanli-Bot is Live & Healthy!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ----------------- نقطه ورود برنامه -----------------
async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

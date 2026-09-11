import os
import asyncio
import logging
from datetime import datetime
import pytz
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# ==================== تنظیمات لاگ ====================
logging.basicConfig(level=logging.INFO)

# ==================== متغیرهای محیطی ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SUPPORT_ID = os.getenv("SUPPORT_ID", "L2tp1support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/")
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443")
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", 10000))

# ==================== راه‌اندازی ربات ====================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ==================== پلن‌ها و تعرفه‌ها ====================
PLANS = {
    "p1": {"name": "اشتراک ۱ ماهه", "price": "۲۵۰,۰۰۰ تومان"},
    "p2": {"name": "اشتراک ۲ ماهه", "price": "۴۰۰,۰۰۰ تومان"},
    "p3": {"name": "اشتراک ۳ ماهه", "price": "۶۰۰,۰۰۰ تومان"},
}

# ==================== تبدیل تاریخ شمسی ====================
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy if gm > 2 else gy - 1
    days = 365 * gy + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
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

WEEKDAYS_FA = {
    "Saturday": "شنبه",
    "Sunday": "یک‌شنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنج‌شنبه",
    "Friday": "جمعه",
}

# ==================== سیستم ثبت و شمارش کاربران ====================
USERS_FILE = "users.txt"

def register_user(user_id: int):
    user_id_str = str(user_id)
    users = set()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = set(line.strip() for line in f if line.strip())
    if user_id_str not in users:
        users.add(user_id_str)
        with open(USERS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{user_id_str}\n")

def get_users_count() -> int:
    if not os.path.exists(USERS_FILE):
        return 0
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = set(line.strip() for line in f if line.strip())
    return len(users)

# ==================== منوی اصلی ۴ ردیفه ====================
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("🛒 خرید اشتراک"))
    kb.row(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    kb.row(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    kb.row(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return kb

# ==================== دستور Start ====================
@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message):
    register_user(message.from_user.id)
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    day_name = WEEKDAYS_FA.get(now.strftime("%A"), "")
    time_str = now.strftime("%H:%M")

    welcome_text = (
        f"سلام {message.from_user.first_name} عزیز! 🌹\n"
        f"به ربات شانلی خوش آمدید.\n\n"
        f"📅 امروز: {day_name} {jd}/{jm}/{jy}\n"
        f"⏰ ساعت: {time_str} (به وقت تهران)\n\n"
        f"از منوی زیر می‌توانید سرویس مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=main_menu())

# ==================== دستور آمار ادمین ====================
@dp.message_handler(commands=["stats"], state="*")
async def cmd_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        count = get_users_count()
        await message.answer(f"📊 <b>آمار کاربران ربات شانلی</b>:\n\n👥 تعداد کل کاربران ثبت‌شده: <code>{count}</code> نفر", parse_mode="HTML")
    else:
        await message.answer("⛔️ شما دسترسی به این بخش را ندارید.")

# ==================== دکمه‌های منو ====================
@dp.message_handler(lambda m: m.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, p_info in PLANS.items():
        kb.add(InlineKeyboardButton(f"{p_info['name']} - {p_info['price']}", callback_data=f"buy_{p_id}"))
    await message.answer("📌 لطفاً اشتراک مورد نظر خود را انتخاب کنید:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "📊 اطلاعات حساب", state="*")
async def handle_account(message: types.Message):
    await message.answer(
        f"👤 شناسه کاربری: <code>{message.from_user.id}</code>\n"
        f"نام: {message.from_user.full_name}\n"
        f"وضعیت حساب: فعال ✅",
        parse_mode="HTML"
    )

@dp.message_handler(lambda m: m.text == "💎 اشتراک‌های من", state="*")
async def handle_my_subscriptions(message: types.Message):
    await message.answer("شما در حال حاضر اشتراک فعالی ندارید. برای خرید از بخش «🛒 خرید اشتراک» اقدام فرمایید.")

@dp.message_handler(lambda m: m.text == "💰 شارژ حساب", state="*")
async def handle_charge(message: types.Message):
    await message.answer(f"جهت شارژ مستقیم حساب کاربری خود لطفاً به پشتیبانی پیام دهید:\n{SUPPORT_USERNAME}")

@dp.message_handler(lambda m: m.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💬 چت مستقیم با پشتیبانی", url=SUPPORT_URL))
    await message.answer(
        f"جهت دریافت پشتیبانی و پاسخ به سوالات می‌توانید با ادمین در ارتباط باشید:\n"
        f"آیدی پشتیبانی: {SUPPORT_USERNAME}",
        reply_markup=kb,
    )

@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message):
    faq_text = (
        "❓ <b>سوالات متداول (FAQ):</b>\n\n"
        "۱. <b>سرویس‌های فعلی بر چه اساسی هستند؟</b>\nدر حال حاضر کلیه سرویس‌ها V2Ray هستند.\n\n"
        "۲. <b>پروتکل‌های دیگر مثل L2TP اضافه می‌شوند؟</b>\nبله، به زودی L2TP, PPTP و OpenVPN اضافه خواهد شد.\n\n"
        "۳. <b>چگونه متصل شوم؟</b>\nاز بخش کانفیگ‌ها برنامه متناسب را دانلود کنید.\n\n"
        "۴. <b>محدودیت سرویس در پلن‌ها چقدر است؟</b>\nپلن‌ها بر اساس مدت زمان اشتراک و با کیفیت اختصاصی مشخص شده‌اند.\n\n"
        "۵. <b>تایید فیش چقدر زمان می‌برد؟</b>\nدر اسرع وقت توسط پشتیبانی تایید می‌شود.\n\n"
        "۶. <b>آیا اشتراک‌ها قابل انتقال هستند؟</b>\nخیر، اشتراک‌ها مختص یک شناسه کاربری هستند.\n\n"
        "۷. <b>چرا سرعت گاهی نوسان دارد؟</b>\nبستگی به نوع اینترنت و اپراتور شما دارد.\n\n"
        "۸. <b>آیا سرورها اختصاصی هستند؟</b>\nتمامی سرورها با پهنای باند اختصاصی می‌باشند.\n\n"
        "۹. <b>چطور گزارش خطا بدهم؟</b>\nاز بخش پشتیبانی می‌توانید به ادمین پیام دهید.\n\n"
        "۱۰. <b>آیا پشتیبانی ۲۴ ساعته است؟</b>\nبله، در سریع‌ترین زمان پاسخگو هستیم.\n\n"
        "۱۱. <b>امنیت اتصالات چطور است؟</b>\nتمامی اتصالات با پروتکل‌های امن رمزنگاری شده هستند.\n\n"
        "۱۲. <b>اگر شارژ کنم چه زمانی فعال می‌شود؟</b>\nپس از ارسال فیش و تایید، آنی فعال می‌شود."
    )
    await message.answer(faq_text, parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def handle_configs(message: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 عضویت در کانال آموزش و کانفیگ", url=CHANNEL_URL))
    await message.answer("برای دریافت نرم‌افزارها و آموزش اتصال به کانال ما بپیوندید:", reply_markup=kb)

# ==================== پیش‌فاکتور و انتقال به پشتیبانی ====================
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"), state="*")
async def callback_buy_plan(query: types.CallbackQuery):
    plan_key = query.data.split("_")[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await query.answer("پلن یافت نشد.", show_alert=True)
        return

    plan_name = plan["name"]
    plan_price = plan["price"]

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("👤 ارسال فیش به پشتیبانی", url=SUPPORT_URL))

    invoice_text = (
        f"🧾 <b>پیش‌فاکتور خرید اشتراک</b>\n\n"
        f"🔹 <b>نوع اشتراک انتخابی:</b> {plan_name}\n"
        f"💰 <b>مبلغ قابل پرداخت:</b> {plan_price}\n\n"
        f"💳 <b>شماره کارت جهت واریز:</b>\n"
        f"<code>{CARD_NUMBER}</code>\n"
        f"👤 <b>به نام:</b> {CARD_HOLDER}\n\n"
        f"⚠️ <b>توجه:</b> پس از واریز مبلغ، لطفاً بر روی دکمه زیر کلیک کرده و تصویر فیش واریزی خود را به همراه ذکر نوع اشتراک ({plan_name}) برای پشتیبانی ارسال فرمایید."
    )

    await query.message.answer(invoice_text, reply_markup=kb, parse_mode="HTML")
    await query.answer()

# ==================== سرور هلث‌چک ====================
async def health_check(request):
    return web.Response(text="OK", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Health check web server started on port {PORT}")

async def on_startup(dp):
    asyncio.create_task(start_web_server())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

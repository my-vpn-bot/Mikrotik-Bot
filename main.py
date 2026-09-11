import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ==============================
# تنظیمات لاگینگ
# ==============================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==============================
# متغیرهای محیطی از رندر (Environment Variables)
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()
try:
    ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW else 0
except ValueError:
    ADMIN_ID = 0

CARD_NUMBER = os.getenv("CARD_NUMBER", "تنظیم نشده در پنل رندر").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "پشتیبانی").strip()

RAW_SUPPORT = os.getenv("SUPPORT_USERNAME", "support").strip()
RAW_CHANNEL = os.getenv("CHANNEL_LINK", "https://t.me").strip()

PORT = int(os.getenv("PORT", 10000))

# ==============================
# نرمال‌سازی لینک‌ها و آیدی‌ها
# ==============================
def normalize_username(val: str) -> str:
    clean = val.replace("https://t.me/", "").replace("http://t.me/", "").replace("@", "").strip().strip("/")
    return f"@{clean}" if clean else "@support"

def normalize_channel_url(val: str) -> str:
    clean = val.strip()
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean
    clean = clean.replace("@", "").strip()
    return f"https://t.me/{clean}" if clean else "https://t.me"

SUPPORT_USERNAME = normalize_username(RAW_SUPPORT)
SUPPORT_URL = f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}"
CHANNEL_LINK = normalize_channel_url(RAW_CHANNEL)

# ==============================
# پلن‌های قیمت (مصوب و بدون تغییر)
# ==============================
PLANS = {
    "plan_1": {
        "title": "یک‌ماهه اختصاصی (تک‌کاربره)",
        "volume": "حجم نامحدود",
        "price": "250,000",
        "desc": "مناسب استفاده روزمره با سرعت عالی و آی‌پی ثابت"
    },
    "plan_2": {
        "title": "سه‌ماهه اقتصادی (دوکاربره)",
        "volume": "حجم نامحدود",
        "price": "400,000",
        "desc": "محبوب‌ترین اشتراک با پایداری حداکثری بدون قطعی"
    },
    "plan_3": {
        "title": "شش‌ماهه ویژه (نامحدود)",
        "volume": "حجم نامحدود",
        "price": "600,000",
        "desc": "بهترین کیفیت، پینگ پایین و پشتیبانی اولویت‌دار"
    }
}

# ==============================
# تابع تقویم جلالی (بدون نیاز به کتابخانه جانبی)
# ==============================
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
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

PERSIAN_WEEKDAYS = {
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنج‌شنبه",
    4: "جمعه",
    5: "شنبه",
    6: "یک‌شنبه"
}

def get_tehran_datetime_details():
    tz_tehran = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tz_tehran)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    weekday_str = PERSIAN_WEEKDAYS[now.weekday()]
    date_str = f"{jy}/{jm:02d}/{jd:02d}"
    time_str = now.strftime("%H:%M:%S")
    return date_str, time_str, weekday_str

# ==============================
# FSM وضعیت دریافت فیش
# ==============================
class ReceiptState(StatesGroup):
    waiting_for_receipt = State()

# ==============================
# کیبورد اصلی (دقیقاً ۴ ردیف توافق‌شده)
# ==============================
def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# ==============================
# ربات و دیسپچر
# ==============================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==============================
# هندلر دستور /start (متن خوش‌آمدگویی کامل و بلند)
# ==============================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    # پاکسازی کیبوردهای به‌جامانده قبلی
    temp_msg = await message.answer("در حال بارگذاری منو...", reply_markup=ReplyKeyboardRemove())
    await temp_msg.delete()

    user_name = message.from_user.first_name or "کاربر گرامی"
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "ندارد"
    date_str, time_str, weekday_str = get_tehran_datetime_details()

    welcome_text = (
        f"سلام {user_name} عزیز! 🌹\n"
        f"به ربات هوشمند مدیریت اشتراک و خدمات اتصال پایدار خوش آمدید.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 مشخصات کاربری شما:\n"
        f"▫️ شناسه عددی: `{user_id}`\n"
        f"▫️ نام کاربری: {username}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 تاریخ: {date_str} ({weekday_str})\n"
        f"⏰ ساعت رسمی: {time_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 کانال اطلاع‌رسانی: {CHANNEL_LINK}\n"
        f"👨‍💻 آیدی پشتیبانی فنی: {SUPPORT_USERNAME}\n\n"
        f"💡 لطفاً برای استفاده از خدمات، از کلیدهای زیر انتخاب فرمایید:"
    )

    await message.answer(welcome_text, reply_markup=get_main_reply_keyboard(), parse_mode="Markdown")

# ==============================
# هندلر: 🛒 خرید اشتراک
# ==============================
@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy_subscription(message: types.Message, state: FSMContext):
    await state.clear()
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🥉 {PLANS['plan_1']['title']} - {PLANS['plan_1']['price']} تومان", callback_data="buy_plan_1")],
            [InlineKeyboardButton(text=f"🥈 {PLANS['plan_2']['title']} - {PLANS['plan_2']['price']} تومان", callback_data="buy_plan_2")],
            [InlineKeyboardButton(text=f"🥇 {PLANS['plan_3']['title']} - {PLANS['plan_3']['price']} تومان", callback_data="buy_plan_3")]
        ]
    )
    text = (
        "🛍 **پلن‌های فعال و پرسرعت:**\n\n"
        "⚡️ تمام اشتراک‌ها بدون افت سرعت، دارای آی‌پی ثابت و تضمین اتصال روی تمام اپراتورها می‌باشند.\n"
        "لطفاً اشتراک مورد نظر خود را انتخاب فرمایید:"
    )
    await message.answer(text, reply_markup=inline_kb, parse_mode="Markdown")

# ==============================
# پردازش انتخاب پلن و نمایش اطلاعات کارت
# ==============================
@dp.callback_query(F.data.startswith("buy_"))
async def process_plan_selection(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data.replace("buy_", "")
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("پلن مورد نظر یافت نشد.", show_alert=True)
        return

    await state.update_data(selected_plan=plan["title"], price=plan["price"])
    await state.set_state(ReceiptState.waiting_for_receipt)

    text = (
        f"📋 **پیش‌فاکتور خرید:**\n"
        f"▫️ سرویس: {plan['title']}\n"
        f"▫️ مشخصات: {plan['desc']}\n"
        f"▫️ مبلغ قابل پرداخت: **{plan['price']} تومان**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 **اطلاعات حساب جهت کارت به کارت:**\n"
        f"▫️ شماره کارت:\n`{CARD_NUMBER}`\n"
        f"▫️ به نام: **{CARD_HOLDER}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📸 **مرحله نهایی:** لطفاً پس از واریز، **عکس فیش واریزی** خود را همین‌جا ارسال نمایید تا در اسرع وقت تأیید و کانفیگ شما تحویل داده شود."
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ==============================
# دریافت فیش واریزی و فوروارد به ادمین
# ==============================
@dp.message(ReceiptState.waiting_for_receipt, F.photo)
async def handle_receipt_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    selected_plan = data.get("selected_plan", "مشخص نشده")
    price = data.get("price", "مشخص نشده")
    
    photo_file_id = message.photo[-1].file_id
    user = message.from_user
    username = f"@{user.username}" if user.username else "ندارد"
    date_str, time_str, _ = get_tehran_datetime_details()

    caption_for_admin = (
        f"🔔 **فیش واریزی جدید دریافت شد!**\n\n"
        f"👤 کاربر: {user.first_name} ({username})\n"
        f"🆔 شناسه کاربر: `{user.id}`\n"
        f"📦 پلن درخواستی: {selected_plan}\n"
        f"💰 مبلغ: {price} تومان\n"
        f"🕒 تاریخ و ساعت: {date_str} - {time_str}"
    )

    if ADMIN_ID and ADMIN_ID != 0:
        try:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=caption_for_admin, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"خطا در ارسال فیش به ادمین: {e}")

    await message.answer(
        "✅ **فیش واریزی شما با موفقیت ثبت شد.**\n\n"
        "کارشناسان ما پس از بررسی، اشتراک و آموزش اتصال را فوراً برای شما ارسال خواهند کرد. صمیمانه از صبوری شما سپاسگزاریم. 🙏",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )
    await state.clear()

@dp.message(ReceiptState.waiting_for_receipt)
async def handle_invalid_receipt(message: types.Message):
    await message.answer("⚠️ لطفاً تنها **عکس واضح فیش واریزی** خود را ارسال فرمایید.")

# ==============================
# هندلر: 📊 اطلاعات حساب
# ==============================
@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account_info(message: types.Message):
    user = message.from_user
    username = f"@{user.username}" if user.username else "ثبت‌نشده"
    date_str, time_str, _ = get_tehran_datetime_details()

    text = (
        f"👤 **اطلاعات حساب کاربری شما:**\n\n"
        f"▫️ نام: {user.first_name}\n"
        f"▫️ شناسه کاربری: `{user.id}`\n"
        f"▫️ نام کاربری تلگرام: {username}\n"
        f"▫️ وضعیت حساب: فعال ✅\n"
        f"▫️ تاریخ بررسی: {date_str} ({time_str})\n\n"
        f"برای مشاهده سرویس‌های فعال خود از دکمه «💎 اشتراک‌های من» استفاده فرمایید."
    )
    await message.answer(text, parse_mode="Markdown")

# ==============================
# هندلر: 💎 اشتراک‌های من
# ==============================
@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: types.Message):
    text = (
        "💎 **اشتراک‌های فعال شما:**\n\n"
        "در حال حاضر هیچ سرویس فعالی به این شناسه متصل نیست یا سرویس شما توسط ادمین در حال تنظیم است.\n"
        "جهت خرید یا فعال‌سازی به بخش «🛒 خرید اشتراک» مراجعه فرمایید یا با پشتیبانی در تماس باشید."
    )
    await message.answer(text, parse_mode="Markdown")

# ==============================
# هندلر: 💰 شارژ حساب
# ==============================
@dp.message(F.text == "💰 شارژ حساب")
async def handle_charge_account(message: types.Message):
    text = (
        f"💰 **شارژ حساب و تمدید اشتراک:**\n\n"
        f"برای تمدید اشتراک فعلی یا افزایش موجودی حساب خود، می‌توانید مبلغ مورد نظر را به شماره کارت زیر واریز کرده و فیش آن را برای پشتیبانی ({SUPPORT_USERNAME}) ارسال نمایید:\n\n"
        f"💳 شماره کارت:\n`{CARD_NUMBER}`\n"
        f"👤 به نام: **{CARD_HOLDER}**"
    )
    await message.answer(text, parse_mode="Markdown")

# ==============================
# هندلر: 👥 پشتیبانی
# ==============================
@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: types.Message):
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 ارسال پیام به پشتیبان", url=SUPPORT_URL)]
        ]
    )
    text = (
        f"👥 **واحد پشتیبانی و پاسخگویی:**\n\n"
        f"تیم پشتیبانی ما آماده پاسخگویی سریع به سوالات، درخواست‌های تمدید و حل مشکلات احتمالی شماست.\n\n"
        f"▫️ آیدی پشتیبان: {SUPPORT_USERNAME}\n"
        f"▫️ کانال رسمی: {CHANNEL_LINK}\n\n"
        f"جهت ارتباط مستقیم می‌توانید روی کلید زیر کلیک کنید:"
    )
    await message.answer(text, reply_markup=inline_kb, parse_mode="Markdown")

# ==============================
# هندلر: ❓ سوالات متداول
# ==============================
@dp.message(F.text == "❓ سوالات متداول")
async def handle_faq(message: types.Message):
    text = (
        "❓ **سوالات پرتکرار کاربران:**\n\n"
        "۱. **روی چه سیستم‌عامل‌هایی قابل استفاده است؟**\n"
        "پاسخ: تمامی سیستم‌عامل‌ها شامل اندروید، iOS (آیفون)، ویندوز و مکینتاش.\n\n"
        "۲. **آیا سرعت سرویس‌ها برای اینستاگرام و یوتیوب مناسب است؟**\n"
        "پاسخ: بله، تمام سرورها از پروتکل‌های پرسرعت با آپ‌تایم بالا و بدون محدودیت حجمی بهره می‌برند.\n\n"
        "۳. **تحویل سرویس بعد از پرداخت چقدر زمان می‌برد؟**\n"
        "پاسخ: بلافاصله پس از بررسی فیش توسط ادمین (معمولاً بین ۵ الی ۱۵ دقیقه)."
    )
    await message.answer(text, parse_mode="Markdown")

# ==============================
# هندلر: ⚙️ کانفیگ‌ها و آموزش اتصال
# ==============================
@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs_and_tutorial(message: types.Message):
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 عضویت در کانال آموزش‌ها", url=CHANNEL_LINK)]
        ]
    )
    text = (
        "⚙️ **راهنمای اتصال و دانلود برنامه‌ها:**\n\n"
        "برای مشاهده آخرین نسخه‌های نرم‌افزارها و ویدیوهای گام‌به‌گام آموزش اتصال در انواع گوشی‌ها و کامپیوتر، به کانال رسمی ما مراجعه فرمایید."
    )
    await message.answer(text, reply_markup=inline_kb, parse_mode="Markdown")

# ==============================
# وب‌سرور سبک جهت رفع محدودیت Port Scan در رندر
# ==============================
async def health_check(request):
    return web.Response(text="OK - Shanli Bot is Live and Healthy!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"وب‌سرور هلث‌چک روی پورت {PORT} با موفقیت اجرا شد.")

# ==============================
# تابع اصلی اجرای ربات
# ==============================
async def main():
    if not BOT_TOKEN:
        logger.error("خطا: BOT_TOKEN در متغیرهای محیطی یافت نشد!")
        return

    # اجرای همزمان وب‌سرور پورت رندر
    await start_web_server()

    # حذف وب‌هوک و آپدیت‌های در صف جهت جلوگیری از تداخل قبلی
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("ربات شانلی با موفقیت راه‌اندازی شد. در حال دریافت پیام‌ها...")

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ربات متوقف گردید.")

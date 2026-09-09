import os
import asyncio
import logging
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiohttp import web

# ==================== لاگ و پیکربندی ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ShanliBot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

# دریافت اطلاعات از متغیرهای محیطی Render بدون هیچ مقدار هاردکد
RAW_SUPPORT = os.getenv("SUPPORT_USERNAME", "").strip().replace("@", "")
RAW_CHANNEL = os.getenv("CHANNEL_LINK", "").strip()

# نرمال‌سازی لینک‌ها و شناسه‌های نمایشی
SUPPORT_USERNAME = f"@{RAW_SUPPORT}" if RAW_SUPPORT else "@Support"
SUPPORT_URL = f"https://t.me/{RAW_SUPPORT}" if RAW_SUPPORT else "https://t.me"

if RAW_CHANNEL.startswith("http://") or RAW_CHANNEL.startswith("https://"):
    CHANNEL_URL = RAW_CHANNEL
    CHANNEL_DISPLAY = RAW_CHANNEL.split("/")[-1]
    if not CHANNEL_DISPLAY.startswith("@"):
        CHANNEL_DISPLAY = f"@{CHANNEL_DISPLAY}"
else:
    ch_clean = RAW_CHANNEL.replace("@", "")
    CHANNEL_URL = f"https://t.me/{ch_clean}" if ch_clean else "https://t.me"
    CHANNEL_DISPLAY = f"@{ch_clean}" if ch_clean else "@Channel"

CARD_NUMBER = os.getenv("CARD_NUMBER", "شماره کارت ثبت نشده است").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "پشتیبانی شانلی").strip()

# قیمت پلن‌ها
PLANS = {
    "plan_1": {"name": "اشتراک ۱ ماهه (تک کاربره)", "price": "۲۵۰,۰۰۰ تومان", "raw_price": 250000},
    "plan_2": {"name": "اشتراک ۲ ماهه (دو کاربره)", "price": "۴۰۰,۰۰۰ تومان", "raw_price": 400000},
    "plan_3": {"name": "اشتراک ۳ ماهه (سه کاربره)", "price": "۶۰۰,۰۰۰ تومان", "raw_price": 600000},
}

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== توابع کمکی تاریخ و تقویم ====================
PERSIAN_WEEKDAYS = {
    "Saturday": "شنبه",
    "Sunday": "یک‌شنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنج‌شنبه",
    "Friday": "جمعه"
}

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if (gm > 2) else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
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

def get_tehran_datetime_details():
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    weekday_en = now.strftime("%A")
    weekday_fa = PERSIAN_WEEKDAYS.get(weekday_en, weekday_en)
    date_str = f"{jy:04d}/{jm:02d}/{jd:02d}"
    time_str = now.strftime("%H:%M:%S")
    return weekday_fa, date_str, time_str

# ==================== کیبوردهای اصلی ====================
def get_main_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("🛒 خرید اشتراک"))
    keyboard.row(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    keyboard.row(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    keyboard.row(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return keyboard

class ReceiptState(StatesGroup):
    waiting_for_plan = State()
    waiting_for_photo = State()

# ==================== هندلر استارت ====================
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    
    weekday_fa, date_str, time_str = get_tehran_datetime_details()
    first_name = message.from_user.first_name or "کاربر گرامی"

    welcome_text = (
        f"سلام <b>{first_name}</b> عزیز، به ربات هوشمند شانلی خوش آمدید! 🌸\n\n"
        f"📅 امروز: <b>{weekday_fa} {date_str}</b>\n"
        f"⏰ ساعت: <b>{time_str}</b>\n\n"
        f"📢 کانال رسمی ما:\n👉 <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>\n\n"
        f"💬 پشتیبانی و ارتباط مستقیم:\n👉 <a href='{SUPPORT_URL}'>{SUPPORT_USERNAME}</a>\n\n"
        "⚡️ برای استفاده از خدمات، تمدید و دریافت اشتراک از دکمه‌های منوی زیر استفاده کنید:"
    )

    await message.answer(welcome_text, reply_markup=get_main_reply_keyboard(), disable_web_page_preview=True)

# ==================== خرید اشتراک ====================
@dp.message_handler(lambda msg: msg.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
    await state.finish()
    text = "🛍 <b>لطفاً پلن اشتراک مورد نظر خود را انتخاب فرمایید:</b>"
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, p_info in PLANS.items():
        kb.add(InlineKeyboardButton(f"{p_info['name']} — {p_info['price']}", callback_data=f"select_{p_id}"))
    await message.answer(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("select_"), state="*")
async def callback_select_plan(query: types.CallbackQuery, state: FSMContext):
    plan_id = query.data.replace("select_", "")
    plan = PLANS.get(plan_id)
    if not plan:
        await query.answer("پلن نامعتبر است.", show_alert=True)
        return

    await state.update_data(selected_plan=plan_id)
    await ReceiptState.waiting_for_photo.set()

    invoice_text = (
        f"🧾 <b>پیش‌فاکتور سفارش:</b>\n\n"
        f"🔹 <b>پلن انتخابی:</b> {plan['name']}\n"
        f"💰 <b>مبلغ قابل پرداخت:</b> {plan['price']}\n\n"
        f"💳 <b>شماره کارت جهت واریز:</b>\n<code>{CARD_NUMBER}</code>\n"
        f"👤 <b>به نام:</b> {CARD_HOLDER}\n\n"
        f"⚠️ لطفاً پس از واریز، عکس فیش پرداخت خود را در همین صفحه ارسال کنید.\n"
        f"کانال اطلاع‌رسانی: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>"
    )

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="cancel_payment"))
    await query.message.edit_text(invoice_text, reply_markup=kb, disable_web_page_preview=True)
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "cancel_payment", state="*")
async def cancel_payment_handler(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.edit_text("❌ عملیات خرید لغو شد.")
    await query.message.answer("منوی اصلی در دسترس شماست:", reply_markup=get_main_reply_keyboard())
    await query.answer()

# ==================== دریافت فیش و ارسال به ادمین ====================
@dp.message_handler(content_types=['photo'], state=ReceiptState.waiting_for_photo)
async def process_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_id = data.get("selected_plan", "plan_1")
    plan = PLANS.get(plan_id, PLANS["plan_1"])

    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "ندارد"
    fullname = message.from_user.full_name or "بدون نام"

    await message.answer(
        "✅ <b>فیش واریزی شما با موفقیت دریافت شد!</b>\n\n"
        "سفارش شما در صف بررسی توسط ادمین قرار گرفت. پس از تأیید نهایی، اکانت برای شما ارسال خواهد شد.\n"
        f"در صورت نیاز به پیگیری فوری: <a href='{SUPPORT_URL}'>{SUPPORT_USERNAME}</a>",
        reply_markup=get_main_reply_keyboard(),
        disable_web_page_preview=True
    )
    await state.finish()

    if ADMIN_ID != 0:
        admin_caption = (
            f"🔔 <b>فیش پرداخت جدید ثبت شد!</b>\n\n"
            f"👤 کاربر: <b>{fullname}</b>\n"
            f"🆔 آیدی عددی: <code>{user_id}</code>\n"
            f"🏷 یوزرنیم: {username}\n"
            f"📦 پلن: <b>{plan['name']}</b> ({plan['price']})\n"
        )
        try:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_caption)
        except Exception as e:
            logger.error(f"خطا در ارسال فیش به ادمین: {e}")

# ==================== اطلاعات حساب ====================
@dp.message_handler(lambda msg: msg.text == "📊 اطلاعات حساب", state="*")
async def handle_account_info(message: types.Message):
    user = message.from_user
    username_str = f"@{user.username}" if user.username else "ثبت نشده"
    name_str = user.full_name or "کاربر شانلی"
    user_id = user.id

    text = (
        "📊 <b>مشخصات حساب کاربری:</b>\n\n"
        f"👤 <b>نام و نام خانوادگی:</b> {name_str}\n"
        f"🆔 <b>شناسه عددی (ID):</b> <code>{user_id}</code>\n"
        f"🏷 <b>یوزرنیم:</b> {username_str}\n"
        f"💎 <b>وضعیت حساب:</b> فعال\n"
        f"💰 <b>موجودی کیف پول:</b> ۰ تومان\n\n"
        f"📢 کانال اطلاع‌رسانی: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>"
    )
    await message.answer(text, reply_markup=get_main_reply_keyboard(), disable_web_page_preview=True)

# ==================== اشتراک‌های من ====================
@dp.message_handler(lambda msg: msg.text == "💎 اشتراک‌های من", state="*")
async def handle_my_subscriptions(message: types.Message):
    text = (
        "💎 <b>لیست سرویس‌ها و اشتراک‌های شما:</b>\n\n"
        "در حال حاضر هیچ سرویس فعالی برای اکانت شما یافت نشد.\n"
        "جهت خرید یا فعال‌سازی از گزینه «🛒 خرید اشتراک» استفاده کنید."
    )
    await message.answer(text, reply_markup=get_main_reply_keyboard())

# ==================== شارژ حساب ====================
@dp.message_handler(lambda msg: msg.text == "💰 شارژ حساب", state="*")
async def handle_wallet_charge(message: types.Message):
    text = (
        "💰 <b>افزایش موجودی و شارژ کیف پول:</b>\n\n"
        f"شماره کارت جهت واریز:\n<code>{CARD_NUMBER}</code>\n"
        f"به نام: <b>{CARD_HOLDER}</b>\n\n"
        f"پس از واریز مبلغ دلخواه، تصویر فیش را به همراه شناسه عددی خود به پشتیبانی ارسال فرمایید:\n"
        f"👉 <a href='{SUPPORT_URL}'>{SUPPORT_USERNAME}</a>"
    )
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("ارتباط مستقیم با پشتیبانی 💬", url=SUPPORT_URL)
    )
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)

# ==================== پشتیبانی ====================
@dp.message_handler(lambda msg: msg.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message):
    support_text = (
        "👥 <b>واحد پشتیبانی و پاسخگویی به مشتریان:</b>\n\n"
        "تیم پشتیبانی ما همه‌روزه آماده پاسخگویی به سوالات، حل مشکلات اتصال و پیگیری سفارشات شماست.\n\n"
        f"🆔 آیدی پشتیبان رسمی: <b>{SUPPORT_USERNAME}</b>\n"
        f"📢 کانال رسمی: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>\n\n"
        "برای گفت‌وگوی مستقیم، دکمه زیر را لمس کنید:"
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"💬 چت با پشتیبانی فنی ({SUPPORT_USERNAME})", url=SUPPORT_URL))
    await message.answer(support_text, reply_markup=kb, disable_web_page_preview=True)

# ==================== سوالات متداول ====================
@dp.message_handler(lambda msg: msg.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message):
    faq_text = (
        "❓ <b>پرسش‌های متداول کاربران:</b>\n\n"
        "۱. <b>سرویس‌ها روی چه دستگاه‌هایی قابل استفاده است؟</b>\n"
        "پاسخ: تمامی سیستم‌عامل‌ها اعم از Android, iOS, Windows و macOS را به طور کامل پشتیبانی می‌کند.\n\n"
        "۲. <b>تحویل اکانت چقدر زمان می‌برد؟</b>\n"
        "پاسخ: پس از ارسال فیش و تأیید اپراتور، بین ۵ الی ۱۵ دقیقه تحویل داده خواهد شد.\n\n"
        "۳. <b>در صورت بروز قطعی چه کار کنم؟</b>\n"
        f"پاسخ: از بخش «👥 پشتیبانی» مستقیماً با {SUPPORT_USERNAME} ارتباط برقرار کنید."
    )
    await message.answer(faq_text, reply_markup=get_main_reply_keyboard())

# ==================== کانفیگ‌ها و آموزش اتصال ====================
@dp.message_handler(lambda msg: msg.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def handle_configs(message: types.Message):
    config_text = (
        "⚙️ <b>آموزش نحوه اتصال و راهنمای نرم‌افزارها:</b>\n\n"
        "📱 <b>اندروید و آیفون:</b>\n"
        "جهت دریافت اپلیکیشن‌های سازگار و آخرین آپدیت کانفیگ‌ها، وارد کانال اطلاع‌رسانی شوید.\n\n"
        f"📢 <b>کانال دریافت آخرین کانفیگ‌ها و آموزش‌ها:</b>\n"
        f"👉 <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>\n\n"
        f"❓ در صورت وجود هرگونه ابهام در راه‌اندازی با پشتیبانی در ارتباط باشید:\n"
        f"👉 <a href='{SUPPORT_URL}'>{SUPPORT_USERNAME}</a>"
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("ورود به کانال تلگرام 📢", url=CHANNEL_URL))
    kb.add(InlineKeyboardButton(f"پشتیبانی فنی 💬", url=SUPPORT_URL))
    await message.answer(config_text, reply_markup=kb, disable_web_page_preview=True)

# ==================== هلث‌چک برای Render (Port 10000) ====================
async def handle_ping(request):
    return web.Response(text="Shanli Bot is alive and running!", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check server running on port {port}")

# ==================== اجرای اصلی ربات ====================
async def main():
    if not BOT_TOKEN:
        logger.error("خطا: BOT_TOKEN در متغیرهای محیطی Render تعریف نشده است!")
        return

    # حذف هرگونه وب‌هوک و آپدیت‌های در انتظار برای جلوگیری از تداخل
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook deleted and pending updates dropped.")

    # راه‌اندازی سرور وب هلث‌چک
    await start_health_server()

    logger.info("Shanli Bot started successfully.")
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

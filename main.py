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
    InlineKeyboardButton
)
from aiohttp import web

# ==================== لاگ‌ها ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ShanliBot")

# ==================== متغیرهای محیطی ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

SUPPORT_RAW = os.getenv("SUPPORT_ID", os.getenv("SUPPORT_USERNAME", "L2tp1support")).strip().replace("@", "")
CHANNEL_RAW = os.getenv("CHANNEL_URL", os.getenv("CHANNEL_LINK", "https://t.me/L2tp_vpn402")).strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", os.getenv("CARD_NUMBER", "6104338904607443")).strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", os.getenv("CARD_HOLDER", "رحیمی")).strip()

SUPPORT_USERNAME = f"@{SUPPORT_RAW}"
SUPPORT_URL = f"https://t.me/{SUPPORT_RAW}"

if CHANNEL_RAW.startswith("http://") or CHANNEL_RAW.startswith("https://"):
    CHANNEL_URL = CHANNEL_RAW
    ch_name = CHANNEL_URL.rstrip("/").split("/")[-1]
    CHANNEL_DISPLAY = ch_name if ch_name.startswith("@") else f"@{ch_name}"
else:
    ch_clean = CHANNEL_RAW.replace("@", "")
    CHANNEL_URL = f"https://t.me/{ch_clean}"
    CHANNEL_DISPLAY = f"@{ch_clean}"

PLANS = {
    "plan_1": {"name": "اشتراک ۱ ماهه (تک کاربره)", "price": "۲۵۰,۰۰۰ تومان", "raw_price": "250,000"},
    "plan_2": {"name": "اشتراک ۲ ماهه (دو کاربره)", "price": "۴۰۰,۰۰۰ تومان", "raw_price": "400,000"},
    "plan_3": {"name": "اشتراک ۳ ماهه (سه کاربره)", "price": "۶۰۰,۰۰۰ تومان", "raw_price": "600,000"},
}

# ==================== ربات و دیسپچر ====================
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== وضعیت‌های FSM ====================
class OrderState(StatesGroup):
    waiting_for_receipt = State()

# ==================== توابع زمان و تقویم جلالی ====================
PERSIAN_WEEKDAYS = {
    "Saturday": "شنبه", "Sunday": "یک‌شنبه", "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه", "Thursday": "پنج‌شنبه", "Friday": "جمعه"
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

def get_tehran_datetime():
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    weekday_fa = PERSIAN_WEEKDAYS.get(now.strftime("%A"), now.strftime("%A"))
    return weekday_fa, f"{jy:04d}/{jm:02d}/{jd:02d}", now.strftime("%H:%M:%S")

# ==================== کیبورد اصلی ۴ ردیفه ====================
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("🛒 خرید اشتراک"))
    keyboard.row(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    keyboard.row(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    keyboard.row(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return keyboard

def get_welcome_text(user: types.User):
    weekday_fa, date_str, time_str = get_tehran_datetime()
    name = user.first_name or "کاربر"
    return (
        f"سلام <b>{name}</b> عزیز، به ربات هوشمند شانلی خوش آمدید! 🌸\n\n"
        f"🆔 شناسه کاربری: <code>{user.id}</code>\n"
        f"📅 امروز: <b>{weekday_fa} {date_str}</b>\n"
        f"⏰ ساعت رسمی تهران: <b>{time_str}</b>\n\n"
        f"📢 کانال رسمی: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>\n"
        f"💬 واحد پشتیبانی: <a href='{SUPPORT_URL}'>{SUPPORT_USERNAME}</a>\n\n"
        "⚡️ برای دسترسی به خدمات از منوی زیر استفاده فرمایید:"
    )

# ==================== هندلرهای پیام متنی ====================
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        get_welcome_text(message.from_user),
        reply_markup=get_main_keyboard(),
        disable_web_page_preview=True
    )

@dp.message_handler(lambda m: m.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, p_info in PLANS.items():
        kb.add(InlineKeyboardButton(f"🔹 {p_info['name']} — {p_info['price']}", callback_data=f"select_{p_id}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="cancel_payment"))
    await message.answer("🛍 <b>لطفاً پلن اشتراک مورد نظر خود را انتخاب فرمایید:</b>", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "📊 اطلاعات حساب", state="*")
async def handle_account_info(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        f"📊 <b>اطلاعات حساب کاربری شما:</b>\n\n"
        f"👤 نام: {message.from_user.full_name}\n"
        f"🆔 شناسه عددی: <code>{message.from_user.id}</code>\n"
        f"💎 وضعیت سرویس: <b>غیرفعال / بدون اشتراک فعال</b>\n"
        f"💰 موجودی کیف پول: <b>۰ تومان</b>"
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda m: m.text == "💎 اشتراک‌های من", state="*")
async def handle_my_subscriptions(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "💎 <b>اشتراک‌های فعال شما:</b>\n\n"
        "⚠️ در حال حاضر هیچ اشتراک فعالی برای حساب شما ثبت نشده است.\n"
        "جهت تهیه اشتراک از گزینه «🛒 خرید اشتراک» استفاده نمایید."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda m: m.text == "💰 شارژ حساب", state="*")
async def handle_wallet_charge(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        f"💰 <b>شارژ حساب و افزایش موجودی:</b>\n\n"
        f"جهت افزایش موجودی، مبلغ مورد نظر را به شماره کارت زیر واریز نموده و فیش را به پشتیبانی ارسال فرمایید:\n\n"
        f"💳 شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 بنام: <b>{CARD_HOLDER}</b>\n\n"
        f"💬 پشتیبانی: <a href='{SUPPORT_URL}'>{SUPPORT_USERNAME}</a>"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), disable_web_page_preview=True)

@dp.message_handler(lambda m: m.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        f"👥 <b>ارتباط با واحد پشتیبانی:</b>\n\n"
        f"در صورت بروز هرگونه مشکل، سوال یا ارسال فیش می‌توانید با آیدی زیر در ارتباط باشید:\n\n"
        f"💬 آیدی پشتیبانی: <a href='{SUPPORT_URL}'>{SUPPORT_USERNAME}</a>\n"
        f"📢 کانال اطلاع‌رسانی: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), disable_web_page_preview=True)

@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "❓ <b>سوالات متداول:</b>\n\n"
        "۱. <b>سرویس‌ها روی چه دستگاه‌هایی قابل استفاده هستند؟</b>\n"
        "تمامی سیستم‌عامل‌های Android، iOS، Windows و macOS پشتیبانی می‌شوند.\n\n"
        "۲. <b>تحویل سرویس چقدر زمان می‌برد؟</b>\n"
        "پس از ارسال فیش واریزی و تایید ادمین، کانفیگ اختصاصی شما بلافاصله ارسال می‌گردد.\n\n"
        "۳. <b>تعداد کاربر مجاز هر پلن به چه معناست؟</b>\n"
        "به معنای اتصال همزمان دستگاه‌ها به سرور است."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda m: m.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def handle_configs_help(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        f"⚙️ <b>آموزش‌های اتصال و دریافت کلاینت‌ها:</b>\n\n"
        f"جهت دریافت نرم‌افزارهای مورد نیاز و آخرین آموزش‌های اتصال به کانال رسمی ما بپیوندید:\n\n"
        f"📢 کانال رسمی: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), disable_web_page_preview=True)

# ==================== هندلرهای اینلاین ====================
@dp.callback_query_handler(lambda c: c.data.startswith("select_"), state="*")
async def callback_select_plan(query: types.CallbackQuery, state: FSMContext):
    plan_id = query.data.replace("select_", "")
    plan = PLANS.get(plan_id)
    if not plan:
        await query.answer("پلن معتبر نیست.", show_alert=True)
        return

    await state.update_data(selected_plan=plan_id, plan_name=plan["name"], plan_price=plan["price"])
    await OrderState.waiting_for_receipt.set()

    invoice_text = (
        f"🧾 <b>پیش‌فاکتور خرید اشتراک</b>\n\n"
        f"📦 پلن انتخابی: <b>{plan['name']}</b>\n"
        f"💵 مبلغ قابل پرداخت: <b>{plan['price']}</b>\n\n"
        f"💳 شماره کارت جهت واریز:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 بنام: <b>{CARD_HOLDER}</b>\n\n"
        "⚠️ <i>لطفاً پس از واریز، تصویر فیش پرداختی (یا اسکرین‌شات) را در همین صفحه ارسال فرمایید.</i>"
    )

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 بازگشت به لیست پلن‌ها", callback_data="back_to_plans"))
    kb.add(InlineKeyboardButton("❌ انصراف و منوی اصلی", callback_data="cancel_payment"))

    await query.message.edit_text(invoice_text, reply_markup=kb)
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "back_to_plans", state="*")
async def callback_back_to_plans(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, p_info in PLANS.items():
        kb.add(InlineKeyboardButton(f"🔹 {p_info['name']} — {p_info['price']}", callback_data=f"select_{p_id}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="cancel_payment"))
    await query.message.edit_text("🛍 <b>لطفاً پلن اشتراک مورد نظر خود را انتخاب فرمایید:</b>", reply_markup=kb)
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "cancel_payment", state="*")
async def callback_cancel_payment(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.message.answer("❌ عملیات لغو شد. به منوی اصلی بازگشتید.", reply_markup=get_main_keyboard())
    await query.answer()

# ==================== دریافت فیش و ارسال به ادمین ====================
@dp.message_handler(content_types=['photo'], state=OrderState.waiting_for_receipt)
async def process_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("plan_name", "نامشخص")
    plan_price = data.get("plan_price", "نامشخص")
    user = message.from_user
    photo_id = message.photo[-1].file_id

    # پیام به کاربر
    await message.answer(
        "✅ <b>فیش واریزی شما با موفقیت دریافت شد.</b>\n\n"
        "سفارش شما در صف بررسی قرار گرفت. پس از تایید توسط مدیریت، کانفیگ اختصاصی برای شما ارسال خواهد شد. 🙏",
        reply_markup=get_main_keyboard()
    )

    # ارسال به ادمین
    if ADMIN_ID and ADMIN_ID != 0:
        admin_caption = (
            f"🔔 <b>فیش واریزی جدید دریافت شد!</b>\n\n"
            f"👤 خریدار: {user.full_name} (@{user.username or 'ندارد'})\n"
            f"🆔 شناسه کاربر: <code>{user.id}</code>\n"
            f"📦 پلن: <b>{plan_name}</b>\n"
            f"💵 مبلغ: <b>{plan_price}</b>"
        )
        try:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_caption)
        except Exception as e:
            logger.error(f"خطا در ارسال فیش به ادمین: {e}")

    await state.finish()

# ==================== وب‌سرور سبک هلث‌چک برای Render ====================
async def handle_health_check(request):
    return web.Response(text="Shanli Bot is alive and running!", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health server running on port {port}")

# ==================== متد اصلی اجرای همزمان ====================
async def main():
    await start_health_server()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot polling started...")
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())

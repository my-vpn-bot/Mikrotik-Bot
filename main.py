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

# ==================== تنظیمات لاگ ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ShanliBot")

# ==================== متغیرهای محیطی ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

RAW_SUPPORT = os.getenv("SUPPORT_ID", "L2tp1support").strip().replace("@", "")
RAW_CHANNEL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()

SUPPORT_USERNAME = f"@{RAW_SUPPORT}"
SUPPORT_URL = f"https://t.me/{RAW_SUPPORT}"

if RAW_CHANNEL.startswith("http://") or RAW_CHANNEL.startswith("https://"):
    CHANNEL_URL = RAW_CHANNEL
    CHANNEL_DISPLAY = CHANNEL_URL.split("/")[-1]
    if not CHANNEL_DISPLAY.startswith("@"):
        CHANNEL_DISPLAY = f"@{CHANNEL_DISPLAY}"
else:
    ch_clean = RAW_CHANNEL.replace("@", "")
    CHANNEL_URL = f"https://t.me/{ch_clean}"
    CHANNEL_DISPLAY = f"@{ch_clean}"

PLANS = {
    "plan_1": {"name": "اشتراک ۱ ماهه (تک کاربره)", "price": "۲۵۰,۰۰۰ تومان"},
    "plan_2": {"name": "اشتراک ۲ ماهه (دو کاربره)", "price": "۴۰۰,۰۰۰ تومان"},
    "plan_3": {"name": "اشتراک ۳ ماهه (سه کاربره)", "price": "۶۰۰,۰۰۰ تومان"},
}

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== توابع تقویم جلالی ====================
PERSIAN_WEEKDAYS = {
    "Saturday": "شنبه", "Sunday": "یک‌شنبه", "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه", "Thursday": "پنج‌شنبه", "Friday": "جمعه"
}

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600: jy = 979; gy -= 1600
    else: jy = 0; gy -= 621
    gy2 = gy + 1 if (gm > 2) else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053); days %= 12053
    jy += 4 * (days // 1461); days %= 1461
    if days > 365: jy += (days - 1) // 365; days = (days - 1) % 365
    if days < 186: jm = 1 + (days // 31); jd = 1 + (days % 31)
    else: jm = 7 + ((days - 186) // 30); jd = 1 + ((days - 186) % 30)
    return jy, jm, jd

def get_tehran_datetime_details():
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    weekday_fa = PERSIAN_WEEKDAYS.get(now.strftime("%A"), now.strftime("%A"))
    return weekday_fa, f"{jy:04d}/{jm:02d}/{jd:02d}", now.strftime("%H:%M:%S")

# ==================== کیبوردهای اصلی ====================
def get_main_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("🛒 خرید اشتراک"))
    keyboard.row(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    keyboard.row(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    keyboard.row(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return keyboard

class ReceiptState(StatesGroup):
    waiting_for_photo = State()

def get_welcome_text(user):
    weekday_fa, date_str, time_str = get_tehran_datetime_details()
    return (
        f"سلام <b>{user.first_name or 'کاربر گرامی'}</b> عزیز، به ربات هوشمند شانلی خوش آمدید! 🌸\n\n"
        f"🆔 شناسه کاربری: <code>{user.id}</code>\n"
        f"📅 امروز: <b>{weekday_fa} {date_str}</b>\n"
        f"⏰ ساعت رسمی تهران: <b>{time_str}</b>\n\n"
        f"📢 کانال رسمی: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>\n"
        f"💬 واحد پشتیبانی: <a href='{SUPPORT_URL}'>{SUPPORT_USERNAME}</a>\n\n"
        "⚡️ برای دسترسی به خدمات از منوی زیر استفاده فرمایید:"
    )

# ==================== هندلرهای اصلی ====================
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(get_welcome_text(message.from_user), reply_markup=get_main_reply_keyboard(), disable_web_page_preview=True)

@dp.message_handler(lambda msg: msg.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, p_info in PLANS.items():
        kb.add(InlineKeyboardButton(f"{p_info['name']} — {p_info['price']}", callback_data=f"select_{p_id}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="cancel_payment"))
    await message.answer("🛍 <b>لطفاً پلن اشتراک مورد نظر خود را انتخاب فرمایید:</b>", reply_markup=kb)

@dp.message_handler(lambda msg: msg.text == "📊 اطلاعات حساب", state="*")
async def handle_account_info(message: types.Message, state: FSMContext):
    await state.finish()
    text = (f"📊 <b>اطلاعات حساب کاربری شما:</b>\n\n👤 نام: {message.from_user.full_name}\n🆔 شناسه: <code>{message.from_user.id}</code>\n💎 وضعیت: فعال نیست")
    await message.answer(text, reply_markup=get_main_reply_keyboard())

@dp.message_handler(lambda msg: msg.text == "💎 اشتراک‌های من", state="*")
async def handle_my_subscriptions(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("💎 <b>اشتراک‌های فعال شما:</b>\n\nدر حال حاضر اشتراک فعالی ندارید.", reply_markup=get_main_reply_keyboard())

@dp.message_handler(lambda msg: msg.text == "💰 شارژ حساب", state="*")
async def handle_wallet_charge(message: types.Message, state: FSMContext):
    await state.finish()
    text = (f"💰 <b>شارژ حساب:</b>\n\nبه کارت <code>{CARD_NUMBER}</code> به نام {CARD_HOLDER} واریز کنید.")
    await message.answer(text, reply_markup=get_main_reply_keyboard())

@dp.message_handler(lambda msg: msg.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(f"👥 <b>واحد پشتیبانی:</b>\n{SUPPORT_USERNAME}", reply_markup=get_main_reply_keyboard())

@dp.message_handler(lambda msg: msg.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("❓ <b>سوالات متداول:</b>\nبه زودی تکمیل می‌شود.", reply_markup=get_main_reply_keyboard())

@dp.message_handler(lambda msg: msg.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def handle_configs_help(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("⚙️ <b>راهنما:</b>\nبه کانال مراجعه کنید.", reply_markup=get_main_reply_keyboard())

# ==================== هندلرهای کال‌بک ====================
@dp.callback_query_handler(lambda c: c.data.startswith("select_"), state="*")
async def callback_select_plan(query: types.CallbackQuery, state: FSMContext):
    plan_id = query.data.replace("select_", "")
    await state.update_data(selected_plan=plan_id)
    await ReceiptState.waiting_for_photo.set()
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به لیست پلن‌ها", callback_data="back_to_plans"))
    await query.message.edit_text("🧾 <b>فیش را ارسال کنید:</b>", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "back_to_plans", state="*")
async def callback_back_to_plans(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, p_info in PLANS.items():
        kb.add(InlineKeyboardButton(f"{p_info['name']} — {p_info['price']}", callback_data=f"select_{p_id}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="cancel_payment"))
    await query.message.edit_text("🛍 <b>پلن را انتخاب کنید:</b>", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "cancel_payment", state="*")
async def callback_cancel_payment(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.delete()
    await query.message.answer("عملیات لغو شد.", reply_markup=get_main_reply_keyboard())

@dp.message_handler(content_types=['photo'], state=ReceiptState.waiting_for_photo)
async def process_receipt(message: types.Message, state: FSMContext):
    await message.answer("✅ فیش شما دریافت شد.", reply_markup=get_main_reply_keyboard())
    await state.finish()

# ==================== وب‌سرور و رانر ====================
async def start_health_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Shanli Bot is alive!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_health_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())

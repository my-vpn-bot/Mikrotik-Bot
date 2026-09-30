import os
import asyncio
import logging
import sqlite3
import random
import string
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputFile
)
from aiohttp import web

# ==================== تنظیمات لاگ و متغیرهای محیطی ====================
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENrbzb6roixklX0X").strip()

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "02786850266").strip()
clean_admin_id = ADMIN_ID_RAW.lstrip('0')
ADMIN_ID = int(clean_admin_id) if clean_admin_id.isdigit() else 2786850266

SUPPORT_ID = os.getenv("SUPPORT_ID", "L2tp1Support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/").strip()

VPN_SERVER_IP
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name,-45244fec"

# مسیر تصاویر
TARIFF_IMAGE_PATH = "تعرفه.jpg"
CARD_IMAGE_PATH = "شماره کارت1.jpg"
IOS_ANDROID_IMAGE_PATH = "ایفون و اندروید.jpg"
MODEM_LAPTOP_IMAGE_PATH = "مودم و لب تاب.jpg"

# ==================== راه‌اندازی ربات ====================
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ==================== دیتابیس کاربران ====================
DB_FILE = "bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            join_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user_to_db(user: types.User):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date_str, _, _, _ = get_persian_datetime()
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name, username, join_date) VALUES (?, ?, ?, ?)",
        (user.id, user.full_name or "", user.username or "", date_str)
    )
    conn.commit()
    conn.close()

def get_total_users_count() -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

init_db()

# ==================== وضعیت‌های FSM ====================
class OrderState(StatesGroup):
    waiting_for_receipt = State()

class ChargeState(StatesGroup):
    waiting_for_receipt = State()
    waiting_for_username = State()

class SupportState(StatesGroup):
    waiting_for_username_and_msg = State()

# ==================== پلن‌ها و پیشوند یوزرنیم اختصاصی ====================
PLANS = {
    "1m_1u": {
        "name": "اشتراک 1 ماهه (تک کاربره + 10 گیگ هدیه)",
        "price": "200,000 تومان",
        "prefix": "1m1u_"
    },
    "1m_2u": {
        "name": "اشتراک 1 ماهه (دو کاربره + 10 گیگ هدیه)",
        "price": "250,000 تومان",
        "prefix": "1m2u_"
    },
    "2m_1u": {
        "name": "اشتراک 2 ماهه (تک کاربره + 10 گیگ هدیه)",
        "price": "380,000 تومان",
        "prefix": "2m1u_"
    },
    "2m_2u": {
        "name": "اشتراک 2 ماهه (دو کاربره + 10 گیگ هدیه)",
        "price": "430,000 تومان",
        "prefix": "2m2u_"
    },
    "3m_1u": {
        "name": "اشتراک 3 ماهه (تک کاربره + 10 گیگ هدیه)",
        "price": "550,000 تومان",
        "prefix": "3m1u_"
    },
    "3m_2u": {
        "name": "اشتراک 3 ماهه (دو کاربره + 10 گیگ هدیه)",
        "price": "600,000 تومان",
        "prefix": "600,000 تومان",
        "prefix": "3m2u_"
    },
}

# ==================== توابع تقویم و تولید اطلاعات ====================
def generate_credentials(prefix="user_"):
    rand_num = random.randint(1000, 9999)
    chars = string.ascii_lowercase + string.digits
    rand_pass = ''.join(random.choice(chars) for _ in range(6))
    return f"{prefix}{rand_num}", rand_pass

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if (gm > 2) else gy
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

def get_persian_datetime():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    time_str = now.strftime("%H:%M:%S")
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    
    month_names = {
        1: "فروردین", 2: "اردیبهشت", 3: "خرداد",
        4: "تیر", 5: "مرداد", 6: "شهریور",
        7: "مهر", 8: "آبان", 9: "آذر",
        10: "دی", 11: "بهمن", 12: "اسفند"
    }
    month_str = month_names.get(jm, "")
    days_fa = {5: "شنبه", 6: "یک‌شنبه", 0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه"}
    day_name = days_fa.get(now.weekday(), "")
    
    date_str = f"{jy:04d}/{jm:02d}/{jd:02d}"
    detailed_date = f"{day_name} {jd} {month_str} ماه سال {jy}"
    return date_str, time_str, day_name, detailed_date

def get_welcome_text(user: types.User):
    date_str, time_str, day_name, detailed_date = get_persian_datetime()
    return (
        f"سلام <b>{user.first_name}</b> گرامی،\n"
        f"به سامانه هوشمند و یکپارچه <b>L2TP VPN 24/7</b> بسیار خوش آمدید.\n\n"
        f"📅 <b>امروز:</b> {detailed_date}\n"
        f"⏰ <b>ساعت رسمی کشور:</b> <code>{time_str}</code>\n\n"
        "⚡️ <b>امکانات سامانه ما:</b>\n"
        "▫️ دسترسی به اینترنت پرسرعت، پایدار و بدون قطعی\n"
        "▫️ مناسب برای تمامی سیستم‌عامل‌ها (iOS، اندروید، ویندوز و مودم)\n"
        "▫️ پنل اختصاصی مدیریت حجم و اشتراک IBSng\n"
        "▫️ پشتیبانی فنی و مانیتورینگ ۲۴ ساعته سرورها\n\n"
        "👇 لطفاً جهت خرید، تمدید یا دریافت راهنمای اتصال، از منوی زیر استفاده نمایید:"
    )

# ==================== کیبورد اصلی اصیل و جدید ====================
BTN_BACK = "🔙 برگشت به منوی اصلی"

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # سطر اول: خرید اشتراک به صورت یک خط کامل و اختصاصی
    kb.add(KeyboardButton("🛒 خرید اشتراک"))
    # سطر دوم: شارژ حساب و پنل کاربری
    kb.add(
        KeyboardButton("💰 شارژ حساب"),
        KeyboardButton("🌐 پنل کاربری IBSng")
    )
    # سطر سوم: اطلاعات حساب و سوالات متداول
    kb.add(
        KeyboardButton("📊 اطلاعات حساب"),
        KeyboardButton("❓ سوالات متداول")
    )
    # سطر چهارTP VPN 24/7</b> بسیار خوش آمدید.\n\n"
        f"📅 <b>امروز:</b> {detailed_date}\n"
        f"⏰ <b>ساعت رسمی کشور:</b> <code>{time_str}</code>\n\n"
        "⚡️ <b>امکانات سامانه ما:</b>\n"
        "▫️ دسترسی به اینترنت پرسرعت، پایدار و بدون قطعی\n"
        "▫️ مناسب برای تمامی سیستم‌عامل‌ها (iOS، اندروید، ویندوز و مودم)\n"
        "▫️ پنل اختصاصی مدیریت حجم و اشتراک IBSng\n"
        "▫️ پشتیبانی فنی و مانیتورینگ ۲۴ ساعته سرورها\n\n"
        "👇 لطفاً جهت خرید، تمدید یا دریافت راهنمای اتصال، از منوی زیر استفاده نمایید:"
    )

# ==================== کیبورد اصلی اصیل و جدید ====================
BTN_BACK = "🔙 برگشت به منوی اصلی"

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # سطر اول: خرید اشتراک به صورت یک خط کامل و اختصاصی
    kb.add(KeyboardButton("🛒 خرید اشتراک"))
    # سطر دوم: شارژ حساب و پنل کاربری
    kb.add(
        KeyboardButton("💰 شارژ حساب"),
        KeyboardButton("🌐 پنل کاربری IBSng")
    )
    # سطر سوم: اطلاعات حساب و سوالات متداول
    kb.add(
        KeyboardButton("📊 اطلاعات حساب"),
        KeyboardButton("❓ سوالات متداول")
    )
    # سطر چهار),
        InlineKeyboardButton("💬 پشتیبانی", url=SUPPORT_URL)
    )
    
    await message.reply(
        get_welcome_text(message.from_user),
        reply_markup=get_main_keyboard()
    )
    await message.answer("🔗 دسترسی‌های سریع و کانال رسمی:", reply_markup=quick_kb)

@dp.message_handler(commands=['stats'], state="*")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total_users = get_total_users_count()
    date_str, time_str, _, detailed_date = get_persian_datetime()
    await message.reply(
        f"📊 <b>آمار زنده ربات:</b>\n\n"
        f"👥 تعداد کل کاربران ثبت‌شده: <b>{total_users:,} نفر</b>\n"
        f"📅 تاریخ: <code>{detailed_date}</code>\n"
        f"⏰ ساعت: <code>{time_str}</code>"
    )

# ==================== خرید اشتراک (کاملاً شیک، خلوت و اصلاح‌شده) ====================
@dp.message_handler(lambda m: m.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
    await state.finish()
    
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, info in PLANS.items():
        kb.add(InlineKeyboardButton(f"💳 {info['name']} ⇦ {info['price']}", callback_data=f"buy_{p_id}"))
    
    text = "👇 <b>لطفاً پلن مورد نظر خود را جهت دریافت شماره کارت و صدور فاکتور انتخاب نمایید:</b>"
    await message.reply(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"), state="*")
async def process_buy_callback(callback_query: types.CallbackQuery, state: FSMContext):
    plan_id = callback_query.data.replace("buy_", "")
    plan = PLANS.get(plan_id)
    if not plan:
        await callback_query.answer("پلن یافت نشد!", show_alert=True)
        return

    await state.update_data(chosen_plan=plan_id)
    await OrderState.waiting_for_receipt.set()

    caption = (
        f"🧾 <b>پیش‌فاکتور خرید اشتراک</b>\n\n"
        f"📦 پلن انتخابی: <b>{plan['name']}</b>\n"
        f"💰 مبلغ قابل پرداخت: <b>{plan['price']}</b>\n\n"
        f"💳 <b>شماره کارت جهت واریز:</b>\n<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 لطفاً پس از واریز، <b>عکس یا اسکرین‌شات فیش واریزی</b> را همین‌جا ارسال فرمایید:"
    )
    
    if os.path.exists(CARD_IMAGE_PATH):
        await bot.send_photo(
            chat_id=callback_query.from_user.id,
            photo=InputFile(CARD_IMAGE_PATH),
            caption=caption,
            reply_markup=get_back_keyboard()
        )
    else:
        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text=caption,
            reply_markup=get_back_keyboard()
        )
    await callback_query.answer()

@dp.message_handler(state=OrderState.waiting_for_receipt, content_types=types.ContentTypes.PHOTO)
async def process_order_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_id = data.get("chosen_plan")
    plan = PLANS.get(plan_id, {"name": "سرویس سفارشی", "price": "نامشخص"})
    user = message.from_user
    date_str, time_str, _, _ = get_persian_datetime()

    admin_caption = (
        "🔔 <b>فیش واریزی جدید (خرید اشتراک جدید)</b>\n\n"
        f"👤 خریدار: <b>{user.full_name}</b>\n"
        f"🆔 شناسه: <code>{user.id}</code>\n"
        f"🔗 یوزرنیم تلگرام: @{user.username or 'ندارد'}\n"
        f"📦 پلن انتخابی: <b>{plan['name']}</b>\n"
        f"💰 مبلغ: <b>{plan['price']}</b>\n"
        f"📅 تاریخ: <code>{date_str}</code> | ساعت: <code>{time_str}</code>"
    )

    admin_kb = InlineKeyboardMarkup(row_width=2)
    admin_kb.row(
        InlineKeyboardButton("✅ تأیید و صدور اکانت", callback_data=f"adm_ok_{user.id}_{plan_id}"),
        InlineKeyboardButton("❌ رد فیش", callback_data=f"adm_no_{user.id}")
    )

    try:
        await bot.send_photo(
            ADMIN_ID,
            photo=message.photo[-1].file_id,
            caption=admin_caption,
            reply_markup=admin_kb
        )
    except Exception as e:
        logging.error(f"Error sending order receipt to admin: {e}")

    await message.reply(
        "✅ <b>فیش واریزی شما با موفقیت برای مدیریت ارسال شد.</b>\n\n"
        "پس از بررسی، مشخصات اتصال اختصاصی مستقیماً در همین چت برای شما ارسال خواهد شد.",
        reply_markup=get_main_keyboard()
    )
    await state.finish()

# ==================== تأیید و رد سفارش خرید ====================
@dp.callback_query_handler(lambda c: c.data.startswith("adm_ok_"), state="*")
async def approve_order_admin(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔️ شما ادمین نیستید.", show_alert=True)
        return

    parts = callback_query.data.split("_")
    user_id = int(parts[2])
    plan_id = "_".join(parts[3:])
    plan = PLANS.get(plan_id, {"name": "سرویس ویژه", "prefix": "user_"})

    prefix = plan.get("prefix", "user_")
    username, password = generate_credentials(prefix)

    delivery_text = (
        "🎉 <b>سفارش شما با موفقیت تأیید شد و اکانت شما فعال گردید!</b>\n\n"
        f"📦 نوع سرویس: <b>{plan['name']}</b>\n"
        f"🌐 آدرس سرور (Server IP): <code>{VPN_SERVER_IP}</code>\n"
        f"🔑 کلید امنیتی (IPsec Secret): <code>{IPSEC_SECRET}</code>\n"
        f"👤 نام کاربری (Username): <code>{username}</code>\n"
        f"🔒 رمز عبور (Password): <code>{password}</code>\n\n"
        f"🌐 <b>پنل کاربری IBSng جهت مشاهده حجم و تغییر رمز:</b>\n{IBSNG_PANEL_URL}\n\n"
        "⚠️ <b>نکته مهم:</b> برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.\n"
        "⚠️ <i>لطفاً پس از اولین ورود، رمز عبور خود را در پنل IBSng تغییر دهید.</i>\n\n"
        f"💬 پشتیبانی: {SUPPORT_USERNAME}\n"
        f"📢 کانال رسمی: @L2tp_vpn402"
    )

    try:
        await bot.send_message(user_id, delivery_text)
        await callback_query.message.reply(f"✅ اکانت <code>{username}</code> برای کاربر <code>{user_id}</code> با موفقیت ارسال شد.")
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        await callback_query.answer(f"خطا در ارسال به کاربر: {e}", show_alert=True)

    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("adm_no_"), state="*")
async def reject_order_admin(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔️ شما ادمین نیستید.", show_alert=True)
        return

    user_id = int(callback_query.data.split("_")[2])
    reject_text = (
        "❌ <b>فیش واریزی ارسالی شما مورد تأیید قرار نگرفت.</b>\n\n"
        "در صورتی که مبلغ از حسابتان کسر گردیده، لطفاً جهت بررسی با پشتیبانی در تماس باشید:\n"
        f"💬 {SUPPORT_USERNAME}"
    )

    try:
        await bot.send_message(user_id, reject_text)
        await callback_query.message.reply(f"❌ فیش کاربر <code>{user_id}</code> رد شد.")
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        await callback_query.answer(f"خطا: {e}", show_alert=True)

    await callback_query.answer()

# ==================== شارژ حساب (با تایید/رد ادمین) ====================
@dp.message_handler(lambda m: m.text == "💰 شارژ حساب", state="*")
async def handle_charge(message: types.Message, state: FSMContext):
    await state.finish()
    await ChargeState.waiting_for_receipt.set()
    
    caption = (
        "💰 <b>شارژ و تمدید حساب کاربری L2TP VPN</b>\n\n"
        "📋 <b>تعرفه‌های رسمی تمدید و شارژ (شامل ۱۰ گیگ هدیه):</b>\n"
        "▫️ ۱ ماهه تک کاربره: <b>200,000 تومان</b>\n"
        "▫️ ۱ ماهه دو کاربره: <b>250,000 تومان</b>\n"
        "▫️ ۲ ماهه تک کاربره: <b>380,000 تومان</b>\n"
        "▫️ ۲ ماهه دو کاربره: <b>430,000 تومان</b>\n"
        "▫️ ۳ ماهه تک کاربره: <b>550,000 تومان</b>\n"
        "▫️ ۳ ماهه دو کاربره: <b>600,000 تومان</b>\n\n"
        f"💳 شماره کارت جهت واریز:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 لطفاً ابتدا مبلغ مورد نظر را واریز نموده و <b>تصویر فیش واریزی</b> را ارسال فرمایید:"
    )
    if os.path.exists(CARD_IMAGE_PATH):
        await message.reply_photo(photo=InputFile(CARD_IMAGE_PATH), caption=caption, reply_markup=get_back_keyboard())
    else:
        await message.reply(caption, reply_markup=get_back_keyboard())

@dp.message_handler(state=ChargeState.waiting_for_receipt, content_types=types.ContentTypes.PHOTO)
async def process_charge_receipt(message: types.Message, state: FSMContext):
    await state.update_data(charge_receipt_id=message.photo[-1].file_id)
    await ChargeState.waiting_for_username.set()
    await message.reply(
        "✍️ فیش دریافت شد.\n\n"
        "حالا لطفاً <b>نام کاربری (یوزرنیم)</b> اکانت قبلی خود را ارسال کنید تا شارژ روی همان اکانت اعمال شود:"
    )

@dp.message_handler(state=ChargeState.waiting_for_username, content_types=types.ContentTypes.TEXT)
async def process_charge_username(message: types.Message, state: FSMContext):
    data = await state.get_data()
    receipt_file_id = data.get("charge_receipt_id")
    account_username = message.text.strip()
    user = message.from_user
    date_str, time_str, _, _ = get_persian_datetime()

    admin_caption = (
        "🔄 <b>درخواست جدید شارژ و تمدید اکانت</b>\n\n"
        f"👤 خریدار: <b>{user.full_name}</b>\n"
        f"🆔 شناسه: <code>{user.id}</code>\n"
        f"🔗 یوزرنیم تلگرام: @{user.username or 'ندارد'}\n"
        f"👤 <b>اکانت جهت شارژ:</b> <code>{account_username}</code>\n"
        f"📅 تاریخ: <code>{date_str}</code> | ساعت: <code>{time_str}</code>"
    )

    admin_kb = InlineKeyboardMarkup(row_width=2)
    admin_kb.row(
        InlineKeyboardButton("✅ تأیید شارژ اکانت", callback_data=f"chg_ok_{user.id}_{account_username}"),
        InlineKeyboardButton("❌ رد درخواست شارژ", callback_data=f"chg_no_{user.id}_{account_username}")
    )

    try:
        await bot.send_photo(ADMIN_ID, photo=receipt_file_id, caption=admin_caption, reply_markup=admin_kb)
    except Exception as e:
        logging.error(f"Error sending charge alert to admin: {e}")

    await message.reply(
        f"✅ <b>درخواست شارژ برای اکانت «{account_username}» برای مدیریت ارسال گردید.</b>\n\n"
        "پس از بررسی و اعمال شارژ در پنل، نتیجه از همین طریق به شما اعلام خواهد شد.",
        reply_markup=get_main_keyboard()
    )
    await state.finish()

# ==================== تأیید و رد شارژ توسط ادمین ====================
@dp.callback_query_handler(lambda c: c.data.startswith("chg_ok_"), state="*")
async def approve_charge_admin(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔️ شما ادمین نیستید.", show_alert=True)
        return

    parts = callback_query.data.split("_")
    user_id = int(parts[2])
    account_username = parts[3]

    delivery_text = (
        "🎉 <b>درخواست تمدید و شارژ اکانت شما با موفقیت تأیید شد!</b>\n\n"
        f"👤 اکانت شارژ شده: <code>{account_username}</code>\n"
        "⚡️ سرویس شما به همراه ۱۰ گیگابایت ترافیک هدیه تمدید گردید و اکنون فعال است.\n\n"
        f"🌐 <b>پنل کاربری IBSng جهت مشاهده جزئیات:</b>\n{IBSNG_PANEL_URL}\n\n"
        "⚠️ <i>برای ورود به پنل، ابتدا VPN را خاموش نمایید.</i>\n\n"
        f"💬 پشتیبانی: {SUPPORT_USERNAME}"
    )

    try:
        await bot.send_message(user_id, delivery_text)
        await callback_query.message.reply(f"✅ شارژ اکانت <code>{account_username}</code> تأیید و پیام آن برای کاربر ارسال شد.")
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        await callback_query.answer(f"خطا در ارسال به کاربر: {e}", show_alert=True)

    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("chg_no_"), state="*")
async def reject_charge_admin(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔️ شما ادمین نیستید.", show_alert=True)
        return

    parts = callback_query.data.split("_")
    user_id = int(parts[2])
    account_username = parts[3]

    reject_text = (
        f"❌ <b>درخواست شارژ برای اکانت «{account_username}» مورد تأیید قرار نگرفت.</b>\n\n"
        "علت: عدم تطابق اطلاعات یا نامعتبر بودن فیش.\n"
        "جهت پیگیری لطفاً به پشتیبانی پیام دهید:\n"
        f"💬 {SUPPORT_USERNAME}"
    )

    try:
        await bot.send_message(user_id, reject_text)
        await callback_query.message.reply(f"❌ درخواست شارژ اکانت <code>{account_username}</code> رد شد.")
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        await callback_query.answer(f"خطا: {e}", show_alert=True)

    await callback_query.answer()

# ==================== پنل کاربری IBSng ====================
@dp.message_handler(lambda m: m.text == "🌐 پنل کاربری IBSng", state="*")
async def handle_ibsng_panel(message: types.Message, state: FSMContext):
    await state.finish()
    ikb = InlineKeyboardMarkup(row_width=1)
    ikb.add(InlineKeyboardButton("🔗 ورود مستقیم به پنل کاربری IBSng", url=IBSNG_PANEL_URL))
    
    text = (
        "🌐 <b>سامانه اختصاصی مشاهده وضعیت و مدیریت اکانت IBSng</b>\n\n"
        f"🔗 <b>لینک ورود به پنل:</b>\n{IBSNG_PANEL_URL}\n\n"
        "⚠️ <b>نکته مهم:</b> برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.\n\n"
        "⚠️ <b>نکته بسیار مهم امنیتی:</b>\n"
        "<b>«حتماً و الزاماً در اولین ورود به پنل کاربری، رمز عبور (پسورد) خود را تغییر دهید تا از هرگونه سوءاستفاده جلوگیری شود.»</b>\n\n"
        "▫️ مشاهده مانده حجم دقیق و ترافیک مصرفی\n"
        "▫️ مشاهده تاریخ انقضای دقیق اشتراک\n"
        "▫️ امکان تغییر پسورد اکانت اتصال"
    )
    await message.reply(text, reply_markup=ikb)

# ==================== اطلاعات حساب ====================
@dp.message_handler(lambda m: m.text == "📊 اطلاعات حساب", state="*")
async def handle_account(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        f"📊 <b>مشخصات حساب کاربری شما:</b>\n\n"
        f"👤 نام: <b>{message.from_user.full_name}</b>\n"
        f"🆔 شناسه عددی تلگرام: <code>{message.from_user.id}</code>\n"
        f"💎 وضعیت عضویت: <b>کاربر ثبت‌شده در سامانه L2TP VPN</b>\n\n"
        "💡 جهت مشاهده دقیق حجم مانده و تاریخ انقضا، به منوی <b>«🌐 پنل کاربری IBSng»</b> مراجعه فرمایید."
    )
    await message.reply(text, reply_markup=get_main_keyboard())

# ==================== پشتیبانی ====================
@dp.message_handler(lambda m: m.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message, state: FSMContext):
    await state.finish()
    await SupportState.waiting_for_username_and_msg.set()
    
    ikb = InlineKeyboardMarkup(row_width=1)
    ikb.add(InlineKeyboardButton("💬 پیام مستقیم به پشتیبان در تلگرام", url=SUPPORT_URL))
    
    text = (
        "👥 <b>پشتیبانی فنی و مانیتورینگ L2TP VPN 24/7</b>\n\n"
        "✍️ لطفاً <b>نام کاربری (یوزرنیم)</b> اکانت به همراه شرح مشکل خود را در قالب یک پیام ارسال فرمایید:\n\n"
        f"💬 ارتباط مستقیم: {SUPPORT_USERNAME}\n"
        f"📢 کانال رسمی: @L2tp_vpn402"
    )
    await message.reply(text, reply_markup=get_back_keyboard())
    await message.answer("ارتباط مستقیم تلگرامی:", reply_markup=ikb)

@dp.message_handler(state=SupportState.waiting_for_username_and_msg, content_types=types.ContentTypes.ANY)
async def process_support_input(message: types.Message, state: FSMContext):
    user = message.from_user
    user_text = message.text or message.caption or "ارسال فایل/عکس بدون متن"
    
    admin_alert = (
        "🚨 <b>درخواست پشتیبانی و بررسی اکانت</b>\n\n"
        f"👤 فرستنده: <b>{user.full_name}</b>\n"
        f"🆔 شناسه: <code>{user.id}</code>\n"
        f"🔗 یوزرنیم تلگرام: @{user.username or 'ندارد'}\n\n"
        f"📝 <b>متن / اطلاعات ارسالی:</b>\n{user_text}"
    )
    
    if ADMIN_ID != 0:
        try:
            if message.photo:
                await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_alert)
            else:
                await bot.send_message(ADMIN_ID, admin_alert)
        except Exception as e:
            logging.error(f"Error alerting admin: {e}")
            
    await message.reply(
        "✅ <b>درخواست شما با موفقیت برای تیم پشتیبانی ارسال شد.</b>\n\n"
        "در کوتاه‌ترین زمان بررسی و به شما پاسخ داده خواهد شد.\n\n"
        f"💬 پیگیری مستقیم: {SUPPORT_USERNAME}",
        reply_markup=get_main_keyboard()
    )
    await state.finish()

# ==================== سوالات متداول (همراه با پاک‌سازی هوشمند) ====================
@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "❓ <b>مرکز جامع راهنما و تنظیمات اتصال L2TP VPN 24/7</b>\n\n"
        "⚡️ <b>مشخصات عمومی اتصال به سرور:</b>\n"
        f"▫️ آدرس سرور (Server IP): <code>{VPN_SERVER_IP}</code>\n"
        f"▫️ کلید امنیتی (IPsec Secret): <code>{IPSEC_SECRET}</code>\n\n"
        "👇 لطفاً دستگاه یا سیستم‌عامل مورد نظر خود را انتخاب کنید:"
    )
    await message.reply(text, reply_markup=get_faq_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("faq_") or c.data == "faq_main", state="*")
async def handle_faq_callbacks(callback_query: types.CallbackQuery):
    action = callback_query.data
    user_id = callback_query.from_user.id
    
    try:
        await bot.delete_message(chat_id=user_id, message_id=callback_query.message.message_id)
    except Exception:
        pass

    back_faq_kb = InlineKeyboardMarkup(row_width=1)
    back_faq_kb.add(InlineKeyboardButton("🔙 بازگشت به منوی راهنما", callback_data="faq_main"))

    if action == "faq_main":
        text = (
            "❓ <b>مرکز جامع راهنما و تنظیمات اتصال L2TP VPN 24/7</b>\n\n"
            "⚡️ <b>مشخصات عمومی اتصال به سرور:</b>\n"
            f"▫️ آدرس سرور (Server IP): <code>{VPN_SERVER_IP}</code>\n"
            f"▫️ کلید امنیتی (IPsec Secret): <code>{IPSEC_SECRET}</code>\n\n"
            "👇 لطفاً دستگاه مورد نظر خود را انتخاب نمایید:"
        )
        await bot.send_message(user_id, text=text, reply_markup=get_faq_keyboard())

    elif action == "faq_ios":
        caption = (
            "📱 <b>راهنمای اتصال در آیفون و آیپد (Apple iOS):</b>\n\n"
            "1. وارد بخش <b>Settings</b> گوشی شوید.\n"
            "2. به مسیر <b>General ⬅️ VPN & Device Management ⬅️ VPN</b> بروید.\n"
            "3. گزینه <b>Add VPN Configuration</b> را لمس کنید.\n"
            "4. بخش <b>Type</b> را روی <b>L2TP</b> قرار دهید.\n"
            f"5. در کادر <b>Server</b> آدرس <code>{VPN_SERVER_IP}</code> را وارد کنید.\n"
            "6. در کادرهای <b>Account</b> و <b>Password</b> مشخصات اشتراک خود را وارد نمایید.\n"
            f"7. در کادر <b>Secret</b> کلید <code>{IPSEC_SECRET}</code> را وارد کرده و Done را بزنید."
        )
        if os.path.exists(IOS_ANDROID_IMAGE_PATH):
            await bot.send_photo(user_id, photo=InputFile(IOS_ANDROID_IMAGE_PATH), caption=caption, reply_markup=back_faq_kb)
        else:
            await bot.send_message(user_id, text=caption, reply_markup=back_faq_kb)

    elif action == "faq_android":
        caption = (
            "🤖 <b>راهنمای اتصال در گوشی‌های اندروید (Android):</b>\n\n"
            "1. وارد تنظیمات (Settings) گوشی شوید.\n"
            "2. به بخش <b>اتصالات (Connections) ⬅️ بیشتر ⬅️ VPN</b> بروید.\n"
            "3. علامت + یا افزودن پروفایل VPN را انتخاب کنید.\n"
            "4. بخش <b>Type</b> را روی <b>L2TP/IPSec PSK</b> تنظیم فرمایید.\n"
            f"5. در کادر <b>Server address</b> مقدار <code>{VPN_SERVER_IP}</code> را وارد کنید.\n"
            f"6. در کادر <b>IPSec pre-shared key</b> مقدار <code>{IPSEC_SECRET}</code> را بنویسید.\n"
            "7. پروفایل را ذخیره کرده و نام کاربری و پسورد خود را بزنید."
        )
        if os.path.exists(IOS_ANDROID_IMAGE_PATH):
            await bot.send_photo(user_id, photo=InputFile(IOS_ANDROID_IMAGE_PATH), caption=caption, reply_markup=back_faq_kb)
        else:
            await bot.send_message(user_id, text=caption, reply_markup=back_faq_kb)

    elif action == "faq_windows":
        caption = (
            "💻 <b>راهنمای اتصال در ویندوز (Windows 10 / 11):</b>\n\n"
            "1. وارد <b>Settings ⬅️ Network & Internet ⬅️ VPN</b> شوید.\n"
            "2. روی <b>Add a VPN connection</b> کلیک کنید.\n"
            "3. VPN provider را روی <b>Windows (built-in)</b> بگذارید.\n"
            "4. VPN type را روی <b>L2TP/IPsec with pre-shared key</b> تنظیم نمایید.\n"
            f"5. در Server name or address مقدار <code>{VPN_SERVER_IP}</code> را وارد فرمایید.\n"
            f"6. در Pre-shared key مقدار <code>{IPSEC_SECRET}</code> را بنویسید.\n"
            "7. نام کاربری و رمز اکانت را وارد نموده و ذخیره (Save) کنید."
        )
        if os.path.exists(MODEM_LAPTOP_IMAGE_PATH):
            await bot.send_photo(user_id, photo=InputFile(MODEM_LAPTOP_IMAGE_PATH), caption=caption, reply_markup=back_faq_kb)
        else:
            await bot.send_message(user_id, text=caption, reply_markup=back_faq_kb)

    elif action == "faq_modem":

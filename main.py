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

# ==================== تنظیمات و لاگ ====================
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "7718919615:AAGZomG_h_n2mG58z0Z43213wR03X9v8YQo").strip()

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

VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = ".12345678"

CARD_IMAGE_PATH = "شماره کارت1.jpg"
TARIFF_IMAGE_PATH = "تعرفه.jpg"

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== دیتابیس ====================
DB_FILE = "bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    join_date TEXT
                )''')
    conn.commit()
    conn.close()

def add_user_to_db(user: types.User):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date_str, _, _ = get_persian_datetime()
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

# ==================== تعرفه‌ها ====================
PLANS = {
    "1m_1u": {"name": "اشتراک 1 ماهه (تک کاربره + 10 گیگ هدیه)", "price": "200,000 تومان"},
    "1m_2u": {"name": "اشتراک 1 ماهه (دو کاربره + 10 گیگ هدیه)", "price": "250,000 تومان"},
    "2m_1u": {"name": "اشتراک 2 ماهه (تک کاربره + 10 گیگ هدیه)", "price": "380,000 تومان"},
    "2m_2u": {"name": "اشتراک 2 ماهه (دو کاربره + 10 گیگ هدیه)", "price": "430,000 تومان"},
    "3m_1u": {"name": "اشتراک 3 ماهه (تک کاربره + 10 گیگ هدیه)", "price": "550,000 تومان"},
    "3m_2u": {"name": "اشتراک 3 ماهه (دو کاربره + 10 گیگ هدیه)", "price": "600,000 تومان"},
}

# ==================== توابع کمکی ====================
def generate_credentials(prefix="arshavin"):
    rand_num = random.randint(1000, 9999)
    chars = string.ascii_lowercase + string.digits
    rand_pass = ''.join(random.choice(chars) for _ in range(6))
    return f"{prefix}{rand_num}", rand_pass

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    jy = 0 if gy <= 1600 else 979
    gy -= 621 if gy <= 1600 else 1600
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    jy += (days - 1) // 365
    if days > 0:
        days = (days - 1) % 365
    jm = (days // 31) + 1 if days < 186 else 7 + ((days - 186) // 30)
    jd = 1 + (days % 31 if days < 186 else (days - 186) % 30)
    return jy, jm, jd

def get_persian_datetime():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    time_str = now.strftime("%H:%M:%S") gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    jy += (days - 1) // 365
    if days > 0:
        days = (days - 1) % 365
    jm = (days // 31) + 1 if days < 186 else 7 + ((days - 186) // 30)
    jd = 1 + (days % 31 if days < 186 else (days - 186) % 30)
    return jy, jm, jd

def get_persian_datetime():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    time_str = now.strftime("%H:%M:%S")
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    days_fa = {5: "شنبه", 6: "یک‌شنبه", 0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه"}
    day_name = days_fa.get(now.weekday(), "")
    date_str = f"{jy}/{jm:02d}/{jd:02d}"
    return date_str, time_str, day_name

# ==================== کیبوردها ====================
BTN_BACK = "🔙 برگشت به منوی اصلی"

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton(" 24/7</b> خوش آمدید.\n"
        "لطفاً جهت استفاده از امکانات ربات، از منوی زیر گزینه‌ای را انتخاب فرمایید:"
    )

# ==================== دستورات اصلی ====================
@dp.message_handler(commands=['start'], state="*")
@dp.message_handler(lambda m: m.text == BTN_BACK, state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    add_user_to_db(message.from_user)
    
    quick_kb = InlineKeyboardMarkup(row_width=2)
    quick_kb.row(
        InlineKeyboardButton("📢 کانال اطلاع‌رسانی", url=CHANNEL_URL),
        InlineKeyboardButton("💬 پشتیبانی", url=SUPPORT_URL)
    )
    
    await message.reply(
        get_welcome_text(message.from_user),
        reply_markup=get_main_keyboard()
    )
    await message.answer("دسترسی‌های سریع:", reply_markup=quick_kb)

@dp.message_handler(commands=['stats'], state="*")
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    total_users = get_total_users_count()
    date_str, time_str, _ = get_persian_datetime()
    await message.reply(
        f"📊 <b>آمار زنده ربات:</b>\n\n"
        f"👥 تعداد کل کاربران ثبت‌شده: <b>{total_users:,} نفر</b>\n"
        f"📅 تاریخ: <code>{date_str}</code> | ساعت: <code>{time_str}</code>"
    )

# ==================== خرید اشتراک ====================
@dp.message_handler(lambda m: m.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, info in PLANS.items():
        kb.add(InlineKeyboardButton(f"🔹 {info['name']} — {info['price']}", callback_data=f"buy_{p_id}"))
    
    caption = (
        "🛍 <b>لیست تعرفه‌های رسمی اشتراک L2TP VPN 24/7</b>\n"
        "🎁 <i>(تمامی پلن‌ها شامل 10 گیگابایت ترافیک هدیه هستند)</i>\n\n"
        "🔹 <b>پلن‌های یک‌ماهه:</b>\n"
        "▫️ یک‌ماهه تک‌کاربره: <b>200,000 تومان</b>\n"
        "▫️ یک‌ماهه دو‌کاربره: <b>250,000 تومان</b>\n\n"
        "🔹 <b>پلن‌های دو‌ماهه:</b>\n"
        "▫️ دو‌ماهه تک‌کاربره: <b>380,000 تومان</b>\n"
        "▫️ دو‌ماهه دو‌کاربره: <b>430,000 تومان</b>\n\n"
        "🔹 <b>پلن‌های سه‌ماهه:</b>\n"
        "▫️ سه‌ماهه تک‌کاربره: <b>550,000 تومان</b>\n"
        "▫️ سه‌ماهه دو‌کاربره: <b>600,000 تومان</b>\n\n"
        "👇 پلن مورد نظر خود را برای صدور فاکتور انتخاب نمایید:"
    )
    if os.path.exists(TARIFF_IMAGE_PATH):
        await message.reply_photo(photo=InputFile(TARIFF_IMAGE_PATH), caption=caption, reply_markup=kb)
    else:
        await message.reply(caption, reply_markup=kb)

# ==================== اطلاعات حساب ====================
@dp.message_handler(lambda m: m.text == "📊 اطلاعات حساب", state="*")
async def handle_account(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        f"📊 <b>مشخصات حساب شما در سیستم:</b>\n\n"
        f"👤 نام: <b>{message.from_user.full_name}</b>\n"
        f"🆔 شناسه عددی تلگرام: <code>{message.from_user.id}</code>\n"
        f"💎 وضعیت عضویت: <b>کاربر ثبت‌شده</b>\n\n"
        "💡 جهت مشاهده دقیق تاریخ انقضا و مانده حجم، وارد <b>«🌐 پنل کاربری IBSng»</b> شوید."
    )
    await message.reply(text, reply_markup=get_main_keyboard())

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

# ==================== شارژ حساب ====================
@dp.message_handler(lambda m: m.text == "💰 شارژ حساب", state="*")
async def handle_charge(message: types.Message, state: FSMContext):
    await state.finish()
    await ChargeState.waiting_for_receipt.set()
    
    caption = (
        "💰 <b>شارژ و تمدید حساب کاربری</b>\n\n"
        "📋 <b>تعرفه‌های رسمی تمدید و شارژ (شامل 10 گیگ هدیه):</b>\n"
        "▫️ 1 ماهه تک کاربره: <b>200,000 تومان</b>\n"
        "▫️ 1 ماهه دو کاربره: <b>250,000 تومان</b>\n"
        "▫️ 2 ماهه تک کاربره: <b>380,000 تومان</b>\n"
        "▫️ 2 ماهه دو کاربره: <b>430,000 تومان</b>\n"
        "▫️ 3 ماهه تک کاربره: <b>550,000 تومان</b>\n"
        "▫️ 3 ماهه دو کاربره: <b>600,000 تومان</b>\n\n"
        f"💳 شماره کارت جهت واریز:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 لطفاً ابتدا مبلغ مورد نظر را واریز نموده و <b>تصویر فیش واریزی</b> را همین‌جا ارسال نمایید:"
    )
    if os.path.exists(CARD_IMAGE_PATH):
        await message.reply_photo(photo=InputFile(CARD_IMAGE_PATH), caption=caption, reply_markup=get_back_keyboard())
    else:
        await message.reply(caption, reply_markup=get_back_keyboard())

# ==================== پشتیبانی ====================
@dp.message_handler(lambda m: m.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message, state: FSMContext):
    await state.finish()
    await SupportState.waiting_for_username_and_msg.set()
    
    ikb = InlineKeyboardMarkup(row_width=1)
    ikb.add(InlineKeyboardButton("💬 پیام مستقیم به پشتیبان تلگرام", url=SUPPORT_URL))
    
    text = (
        "👥 <b>پشتیبانی آنلاین و هوشمند L2TP VPN 24/7</b>\n\n"
        "✍️ <b>لطفاً نام کاربری (یوزرنیم) اکانت وی‌پی‌ان خود را به همراه شرح مشکل یا درخواستتان در یک پیام ارسال کنید تا برای بررسی ارجاع شود:</b>\n\n"
        f"💬 آیدی مستقیم ادمین: {SUPPORT_USERNAME}\n"
        f"📢 کانال رسمی: @L2tp_vpn402"
    )
    await message.reply(text, reply_markup=get_back_keyboard())
    await message.answer("ارتباط از طریق تلگرام:", reply_markup=ikb)

@dp.message_handler(state=SupportState.waiting_for_username_and_msg, content_types=types.ContentTypes.ANY)
async def process_support_input(message: types.Message, state: FSMContext):
    user = message.from_user
    user_text = message.text or message.caption or "ارسال فایل/تصویر بدون متن"
    
    admin_alert = (
        "🚨 <b>درخواست پشتیبانی و بررسی اکانت</b>\n\n"
        f"👤 فرستنده: <b>{user.full_name}</b>\n"
        f"🆔 شناسه: <code>{user.id}</code>\n"
        f"🔗 یوزرنیم تلگرام: @{user.username or 'ندارد'}\n\n"
        f"📝 <b>متن / یوزرنیم ارسالی کاربر:</b>\n{user_text}"
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
        "✅ <b>پشتیبانی درخواست شما را با موفقیت تحویل گرفت.</b>\n\n"
        "اطلاعات اکانت و پیام شما برای اپراتور ارسال شد و در سریع‌ترین زمان ممکن بررسی و پاسخ داده خواهد شد.\n\n"
        f"💬 پیگیری مستقیم: {SUPPORT_USERNAME}",
        reply_markup=get_main_keyboard()
    )
    await state.finish()

# ==================== سوالات متداول و راهنمای اتصال ====================
@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "❓ <b>پاسخ به سوالات متداول و راهنمای جامع اتصال L2TP/IPSec</b>\n\n"
        "⚡️ <b>مشخصات عمومی سرور:</b>\n"
        f"▫️ آدرس سرور (Server Address): <code>{VPN_SERVER_IP}</code>\n"
        f"▫️ کلید امنیتی (IPsec Secret / Pre-Shared Key): <code>{IPSEC_SECRET}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📱 <b>۱. راهنمای اتصال در آیفون و آیپد (Apple iOS):</b>\n"
        "1. وارد Settings ⬅️ General ⬅️ VPN & Device Management ⬅️ VPN شوید.\n"
        "2. گزینه Add VPN Configuration را لمس کنید.\n"
        "3. نوع (Type) را روی <b>L2TP</b> قرار دهید.\n"
        f"4. در بخش Server آدرس <code>{VPN_SERVER_IP}</code> را وارد کنید.\n"
        "5. نام کاربری (Account) و رمز عبور (Password) خود را وارد کنید.\n"
        f"6. در کادر Secret مقدار <code>{IPSEC_SECRET}</code> را وارد و Save را بزنید.\n\n"
        "🤖 <b>۲. راهنمای اتصال در اندروید (Android):</b>\n"
        "1. وارد تنظیمات گوشی ⬅️ اتصالات (Connections) ⬅️ تنظیمات بیشتر (More connection settings) ⬅️ VPN شوید.\n"
        "2. علامت + یا سه نقطه بالا را زده و Add VPN Profile را انتخاب کنید.\n"
        "3. نوع (Type) را روی <b>L2TP/IPSec PSK</b> قرار دهید.\n"
        f"4. در Server address مقدار <code>{VPN_SERVER_IP}</code> را بنویسید.\n"
        f"5. در کادر IPSec pre-shared key مقدار <code>{IPSEC_SECRET}</code> را وارد کنید.\n"
        "6. ذخیره کرده و هنگام اتصال یوزرنیم و پسورد خود را بزنید.\n\n"
        "💻 <b>۳. راهنمای اتصال در ویندوز (Windows 10 / 11):</b>\n"
        "1. وارد Settings ⬅️ Network & Internet 

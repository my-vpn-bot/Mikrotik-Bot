import os
import asyncio
import logging
import sqlite3
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

BOT_TOKEN = os.getenv("BOT_TOKEN", "7963098522:AAHVtM20G7kR82k1n4p4y8_example").strip()

# رفع خطای اعداد با پیشوند صفر
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "6278859256").strip()
clean_admin_id = ADMIN_ID_RAW.lstrip('0')
ADMIN_ID = int(clean_admin_id) if clean_admin_id.isdigit() else 6278859256

SUPPORT_ID = os.getenv("SUPPORT_ID", "L2tp1Support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/").strip()

VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "GAPGPTMASKTOKENifkfxzj28aX0X"

CARD_IMAGE_PATH = "شماره کارت1.jpg"
TARIFF_IMAGE_PATH = "تعرفه.jpg"
OVPN_FILE_PATH = "files/openvpn/client.ovpn"

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

# ==================== تاریخ شمسی ====================
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
    kb.add(KeyboardButton("🛒 خرید اشتراک"))
    kb.add(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("🌐 پنل کاربری IBSng"))
    kb.add(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    kb.add(KeyboardButton("❓ سوالات متداول و آموزش"), KeyboardButton("⚙️ کانفیگ‌ها و دانلود OpenVPN"))
    return kb

def get_back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(BTN_BACK))
    return kb

def get_faq_inline_keyboard():
    ikb = InlineKeyboardMarkup(row_width=2)
    ikb.row(
        InlineKeyboardButton("🍏 راهنمای آیفون / آیپد", callback_data="faq_ios"),
        InlineKeyboardButton("🤖 راهنمای اندروید", callback_data="faq_android")
    )
    ikb.row(
        InlineKeyboardButton("💻 راهنمای ویندوز", callback_data="faq_windows"),
        InlineKeyboardButton("🍏 راهنمای مک‌بوک", callback_data="faq_mac")
    )
    ikb.row(
        InlineKeyboardButton("📶 تنظیم روی مودم و روتر", callback_data="faq_router")
    )
    ikb.row(
        InlineKeyboardButton("🔐 تغییر پسورد و نکات امنیتی", callback_data="faq_security"),
        InlineKeyboardButton("🔄 طرح جبرانی مشترکین", callback_data="faq_plan")
    )
    return ikb

def get_faq_back_keyboard():
    ikb = InlineKeyboardMarkup(row_width=1)
    ikb.add(InlineKeyboardButton("🔙 بازگشت به لیست سوالات", callback_data="faq_home"))
    return ikb

def get_welcome_text(user):
    date_str, time_str, day_name = get_persian_datetime()
    return (
        f"سلام <b>{user.first_name}</b> عزیز، خیلی خوش آمدید! 🌹\n\n"
        f"📅 <b>روز:</b> {day_name}\n"
        f"📆 <b>تاریخ:</b> <code>{date_str}</code> | ⏰ <b>ساعت:</b> <code>{time_str}</code>\n"
        f"🆔 شناسه کاربری: <code>{user.id}</code>\n\n"
        f"⚡️ <b>پروتکل‌های پرسرعت و پایدار L2TP VPN 24/7:</b>\n"
        f"▫️ پروتکل امن <b>L2TP / IPSec</b> (بدون نیاز به نرم‌افزار جانبی)\n"
        f"▫️ پروتکل‌های <b>OpenVPN</b> و <b>PPTP</b> سازگار با انواع سیستم‌عامل‌ها و مودم‌ها\n"
        f"🎁 <b>10 گیگابایت ترافیک هدیه</b> روی تمامی پلن‌های جدید\n\n"
        "👇 جهت استفاده از امکانات، یکی از گزینه‌های منوی زیر را انتخاب نمایید:"
    )

# ==================== هندلرهای عمومی ====================
@dp.message_handler(lambda m: m.text == BTN_BACK, state="*")
async def process_global_back(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply("به منوی اصلی بازگشتید 👇", reply_markup=get_main_keyboard())

@dp.message_handler(commands=['start'], state="*")
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
        "<b>«حتماً و الزاماً در اولین ورود به پنل کاربری، رمز عبور خود را تغییر دهید تا از هرگونه سوءاستفاده جلوگیری شود.»</b>\n\n"
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

# ==================== سوالات متداول تفکیک شده ====================
FAQ_MAIN_TEXT = (
    "❓ <b>مرکز راهنما، آموزش‌ها و سوالات متداول</b>\n\n"
    f"⚡️ <b>اطلاعات اتصال عمومی:</b>\n"
    f"▫️ آدرس سرور: <code>{VPN_SERVER_IP}</code>\n"
    f"▫️ کلید امنیتی (IPsec Secret): <code>{IPSEC_SECRET}</code>\n\n"
    "👇 <b>لطفاً دستگاه یا موضوع مورد نظرتان را برای مشاهده راهنما انتخاب کنید:</b>"
)

@dp.message_handler(lambda m: m.text in ["❓ سوالات متداول", "❓ سوالات متداول و آموزش"], state="*")
async def handle_faq(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply(FAQ_MAIN_TEXT, reply_markup=get_faq_inline_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("faq_"), state="*")
async def process_faq_callbacks(query: types.CallbackQuery):
    action = query.data
    
    if action == "faq_home":
        await query.message.edit_text(FAQ_MAIN_TEXT, reply_markup=get_faq_inline_keyboard())
        await query.answer()
        return

    faq_texts = {
        "faq_ios": (
            "📱 <b>راهنمای اتصال در آیفون و آیپد (iOS):</b>\n\n"
            "1. وارد <b>Settings</b> ⬅️ <b>General</b> ⬅️ <b>VPN & Device Management</b> ⬅️ <b>VPN</b> شوید.\n"
            "2. گزینه <b>Add VPN Configuration</b> را بزنید.\n"
            "3. نوع (Type) را روی <b>L2TP</b> قرار دهید.\n"
            f"4. در کادر Description نام دلخواه و در Server مقدار <code>{VPN_SERVER_IP}</code> را وارد کنید.\n"
            "5. در کادر Account نام کاربری و در Password رمز عبور خود را وارد کنید.\n"
            f"6. در کادر Secret مقدار <code>{IPSEC_SECRET}</code> را بنویسید.\n"
            "7. دکمه Done را بزنید و وصل شوید."
        ),
        "faq_android": (
            "🤖 <b>راهنمای اتصال در گوشی‌های اندروید (Android):</b>\n\n"
            "1. وارد تنظیمات (Settings) ⬅️ اتصالات (Connections) ⬅️ تنظیمات بیشتر ⬅️ <b>VPN</b> شوید.\n"
            "2. روی علامت + یا سه نقطه بالا بزنید و Add VPN Profile را انتخاب کنید.\n"
            "3. نوع (Type) را روی <b>L2TP/IPSec PSK</b> تنظیم کنید.\n"
            f"4. در قسمت Server address آدرس <code>{VPN_SERVER_IP}</code> را بنویسید.\n"
            f"5. در کادر IPSec pre-shared key مقدار <code>{IPSEC_SECRET}</code> را وارد کنید.\n"
            "6. ذخیره (Save) را زده، سپس روی کانکشن ساخته شده کلیک و یوزرنیم و پسوردتان را وارد نمایید."
        ),
        "faq_windows": (
            "💻 <b>راهنمای اتصال در ویندوز (Windows 10 / 11):</b>\n\n"
            "1. وارد Settings ⬅️ Network & Internet ⬅️ <b>VPN</b> شوید و <b>Add VPN</b> را بزنید.\n"
            "2. گزینه VPN Provider را روی <b>Windows (built-in)</b> بگذارید.\n"
            "3. VPN Type را روی <b>L2TP/IPsec with pre-shared key</b> تنظیم کنید.\n"
            f"4. در Server name or address مقدار <code>{VPN_SERVER_IP}</code> را وارد کنید.\n"
            f"5. در Pre-shared key مقدار <code>{IPSEC_SECRET}</code> را تایپ کنید.\n"
            "6. یوزرنیم و پسورد اکانت را وارد کرده و Save و Connect را بزنید."
        ),
        "faq_mac": (
            "🍏 <b>راهنمای اتصال در مک‌بوک (macOS):</b>\n\n"
            "1. وارد <b>System Settings</b> ⬅️ <b>Network</b> شوید.\n"
            "2. روی آیکون سه نقطه / افزودن کلیک کرده و <b>Add VPN Configuration ⬅️ L2TP over IPSec</b> را انتخاب کنید.\n"
            f"3. در Server Address آدرس <code>{VPN_SERVER_IP}</code> را وارد کنید.\n"
            "4. Account Name را یوزرنیم خود بگذارید.\n"
            f"5. در Authentication Settings پسورد و Shared Secret (<code>{IPSEC_SECRET}</code>) را وارد نموده و Apply کنید."
        ),
        "faq_router": (
            "📶 <b>راهنمای تنظیم روی انواع مودم و روتر (Router / Modem):</b>\n\n"
            "1. وارد کنسول وب مودم شوید (آدرس 192.168.1.1 یا 192.168.8.1).\n"
            "2. به منوی <b>VPN ⬅️ L2TP Client</b> مراجعه کنید.\n"
            "3. گزینه را فعال (Enabled) و پروتکل را روی L2TP قرار دهید.\n"
            f"4. در کادر LNS Address / Server آدرس <code>{VPN_SERVER_IP}</code> را بنویسید.\n"
            "5. نام کاربری و رمز عبور اشتراک خود را ثبت و ذخیره (Save/Apply) نمایید."
        ),
        "faq_security": (
            "🔐 <b>نکات مهم امنیتی و تغییر رمز:</b>\n\n"
            "▫️ حتماً در اولین ورود به پنل کاربری IBSng، رمز عبور پیش‌فرض خود را تغییر دهید.\n"
            "▫️ اشتراک‌های تک‌کاربره نباید همزمان روی دو دستگاه روشن باشند تا قطع نشوند.\n"
            "▫️ جهت تست پایداری از خاموش بودن سایر فیلترشکن‌ها حین اتصال مطمئن شوید."
        ),
        "faq_plan": (
            "🔄 <b>طرح جبرانی و پشتیبانی مشترکین:</b>\n\n"
            "▫️ در صورت بروز هرگونه اختلال یا انتقال سرور، مدت زمان قطعی به دوره اشتراک شما اضافه خواهد شد.\n"
            "▫️ با ارسال یوزرنیم و فیش قبلی به پشتیبانی، اشتراک با دوره کامل و ۱۰ گیگ هدیه فعال می‌شود."
        )
    }
    
    text_to_show = faq_texts.get(action, "اطلاعات مورد نظر یافت نشد.")
    await query.message.edit_text(text_to_show, reply_markup=get_faq_back_keyboard())
    await query.answer()

# ==================== کانفیگ‌ها و دانلود OpenVPN ====================
@dp.message_handler(lambda m: m.text in ["⚙️ کانفیگ‌ها و آموزش اتصال", "⚙️ کانفیگ‌ها و دانلود OpenVPN"], state="*")
async def handle_configs(message: types.Message, state: FSMContext):
    await state.finish()
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📥 دریافت و دانلود فایل کانفیگ OpenVPN (.ovpn)", callback_data="download_ovpn"),
        InlineKeyboardButton("📢 عضویت در کانال رسمی آموزش‌ها", url=CHANNEL_URL)
    )
    
    text = (
        "⚙️ <b>مشخصات و دانلود کانفیگ‌های اتصال VPN:</b>\n\n"
        f"🌐 <b>آدرس سرور (Server):</b> <code>{VPN_SERVER_IP}</code>\n"
        f"🔑 <b>کلید مشترک (Pre-Shared Key):</b> <code>{IPSEC_SECRET}</code>\n\n"
        "▫️ <b>پروتکل L2TP/IPSec:</b> بدون نیاز به نصب هیچ برنامه‌ای در آیفون، اندروید و ویندوز قابل اتصال است.\n"
        "▫️ <b>پروتکل OpenVPN:</b> برای اتصال امن از طریق نرم‌افزار رسمی OpenVPN Connect.\n\n"
        "👇 <b>جهت دریافت مستقیم فایل کانفیگ OpenVPN دکمه زیر را لمس کنید:</b>"
    )
    await message.reply(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "download_ovpn", state="*")
async def send_ovpn_file_callback(query: types.CallbackQuery):
    if os.path.exists(OVPN_FILE_PATH):
        caption = (
            "📥 <b>فایل کانفیگ اختصاصی OpenVPN</b>\n\n"
            f"🌐 سرور: <code>{VPN_SERVER_IP}</code>\n"
            "🔐 پروتکل: <b>OpenVPN Client Config</b>\n\n"
            "📖 <b>راهنمای سریع استفاده:</b>\n"
            "1. اپلیکیشن <b>OpenVPN Connect</b> را از اپ‌استور یا گوگل‌پلی نصب کنید.\n"
            "2. این فایل را دانلود و در برنامه Import نمایید.\n"
            "3. نام کاربری و رمز عبور اشتراک خود را وارد کرده و متصل شوید."
        )
        await bot.send_document(
            chat_id=query.message.chat.id,
            document=InputFile(OVPN_FILE_PATH),
            caption=caption
        )
        await query.answer("✅ فایل کانفیگ OpenVPN با موفقیت ارسال شد.")
    else:
        await query.answer("❌ فایل کانفیگ یافت نشد. لطفاً به پشتیبانی پیام دهید.", show_alert=True)

# ==================== کال‌بک خرید و دریافت فیش ====================
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"), state="*")
async def callback_buy_plan(query: types.CallbackQuery, state: FSMContext):
    plan_key = query.data.split("buy_")[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await query.answer("پلن یافت نشد.", show_alert=True)
        return
    
    await state.update_data(plan_name=plan["name"], plan_price=plan["price"])
    await OrderState.waiting_for_receipt.set()
    
    caption = (
        "🧾 <b>پیش‌فاکتور صدور اکانت L2TP VPN 24/7</b>\n\n"
        f"📦 پلن انتخابی: <b>{plan['name']}</b>\n"
        f"💵 مبلغ قابل پرداخت: <b>{plan['price']}</b>\n\n"
        f"💳 شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "لطفاً پس از کارت به کارت، <b>تصویر فیش واریزی</b> را همین‌جا ارسال نمایید:"
    )
    await query.message.delete()
    if os.path.exists(CARD_IMAGE_PATH):
        await bot.send_photo(query.message.chat.id, photo=InputFile(CARD_IMAGE_PATH), caption=caption, reply_markup=get_back_keyboard())
    else:
        await state.get_data()
    plan_name = data.get("plan_name", "خرید اشتkeyboard())
    await query.answer()

@dp.message_handler(content_types=['photo'], state=OrderState.waiting_for_receipt)
async def handle_order_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("plan_name", "خرید اشتراک")
    plan_price = data.get("plan_price", "نامشخص")
    
    caption = (
        "🔔 <b>فیش واریزی جدید (خرید اکانت)</b>\n\n"
        f"👤 کاربر: <b>{message.from_user.full_name}</b>\n"
        f"🆔 شناسه: <code>{message.from_user.id}</code>\n"
        f"🔗 آیدی: @{message.from_user.username or 'ندارد'}\n"
        f"📦 پلن: {plan_name}\n"
        f"💰 مبلغ: {plan_price}"
    )
    if ADMIN_ID != 0:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption)
    
    await message.reply(
        "✅ <b>فیش شما با موفقیت دریافت شد و برای مدیریت ارسال گردید.</b>\n"
        "مشخصات اکانت شما پس از تایید تحویل داده می‌شود.",
        reply_markup=get_main_keyboard()
    )
    await state.finish()

# ==================== شارژ و تمدید حساب ====================
@dp.message_handler(content_types=['photo'], state=ChargeState.waiting_for_receipt)
async def handle_charge_receipt(message: types.Message, state: FSMContext):
    await state.update_data(receipt_file_id=message.photo[-1].file_id)
    await ChargeState.waiting_for_username.set()
    await message.reply(
        "✅ فیش واریزی دریافت شد.\n\n"
        "✍️ اکنون لطفاً <b>نام کاربری (Username)</b> اکانت VPN خود را وارد نمایید تا برای تمدید ارسال گردد:",
        reply_markup=get_back_keyboard()
    )

@dp.message_handler(state=ChargeState.waiting_for_username)
async def handle_charge_username(message: types.Message, state: FSMContext):
    username_val = message.text.strip()
    data = await state.get_data()
    file_id = data.get("receipt_file_id")
    
    caption = (
        "💰 <b>درخواست شارژ / تمدید حساب</b>\n\n"
        f"👤 کاربر: <b>{message.from_user.full_name}</b>\n"
        f"🆔 شناسه: <code>{message.from_user.id}</code>\n"
        f"🔗 آیدی: @{message.from_user.username or 'ندارد'}\n"
        f"🔑 نام کاربری ارسالی: <code>{username_val}</code>"
    )
    if ADMIN_ID != 0 and file_id:
        await 

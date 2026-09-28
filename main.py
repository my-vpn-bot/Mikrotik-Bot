import asyncio
import logging
import os
import sqlite3
from datetime import datetime
import pytz
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.client.default import DefaultBotProperties

# ============================
# تنظیمات لاگینگ
# ============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================
# متغیرهای محیطی
# ============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "2786850266").strip().lstrip("0")
PORT = int(os.getenv("PORT", "10000"))

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support").strip()
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/").strip()
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی").strip()

VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "GAPGPTMASKTOKENr4cfhm6bm9cX0X"

# ============================
# پایگاه داده SQLite
# ============================
DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str, first_name: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username or "", first_name or "")
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"DB Error (add_user): {e}")

def get_total_users():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except Exception as e:
        logger.error(f"DB Error (get_total_users): {e}")
        return 0

init_db()

# ============================
# تاریخ و ساعت شمسی
# ============================
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

def get_current_jalali():
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d}", now.strftime("%H:%M:%S")

# ============================
# ماشین وضعیت (FSM)
# ============================
class OrderStates(StatesGroup):
    choosing_plan = State()
    waiting_for_receipt = State()

class RenewalStates(StatesGroup):
    waiting_for_username = State()
    choosing_plan = State()
    waiting_for_receipt = State()

class SupportStates(StatesGroup):
    waiting_for_message = State()

# ============================
# کیبوردها
# ============================
def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🛍 خرید اشتراک جدید")],
        [KeyboardButton(text="🔄 تمدید اشتراک"), KeyboardButton(text="📊 ورود به پنل کاربری (IBSng)")],
        [KeyboardButton(text="📚 راهنمای اتصال و دانلود"), KeyboardButton(text="💬 پشتیبانی و تماس")],
        [KeyboardButton(text="📢 کانال اطلاع‌رسانی")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_plans_inline_keyboard(prefix: str = "buy"):
    keyboard = [
        [
            InlineKeyboardButton(text="۱ ماهه تک کاربره (۲۰۰ ت)", callback_data=f"{prefix}_1m_1u"),
            InlineKeyboardButton(text="۱ ماهه دو کاربره (۲۵۰ ت)", callback_data=f"{prefix}_1m_2u")
        ],
        [
            InlineKeyboardButton(text="۲ ماهه تک کاربره (۳۸۰ ت)", callback_data=f"{prefix}_2m_1u"),
            InlineKeyboardButton(text="۲ ماهه دو کاربره (۴۳۰ ت)", callback_data=f"{prefix}_2m_2u")
        ],
        [
            InlineKeyboardButton(text="۳ ماهه تک کاربره (۵۵۰ ت)", callback_data=f"{prefix}_3m_1u"),
            InlineKeyboardButton(text="۳ ماهه دو کاربره (۶۰۰ ت)", callback_data=f"{prefix}_3m_2u")
        ],
        [InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data="cancel_action")]
    ])

def get_guides_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📱 راهنمای آیفون (iOS)", callback_data="guide_ios")],
        [InlineKeyboardButton(text="🤖 راهنمای اندروید (Android)", callback_data="guide_android")],
        [InlineKeyboardButton(text="💻 راهنمای ویندوز (Windows)", callback_data="guide_windows")],
        [InlineKeyboardButton(text="🍏 راهنمای مک (macOS)", callback_data="guide_mac")],
        [InlineKeyboardButton(text="🌐 مشخصات کلی و مودم", callback_data="guide_general")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ============================
# تعریف ربات و اطلاعات پلن‌ها
# ============================
bot = Bot(
    token=GAPGPTMASKTOKENr4cfhm6bm9cX1X,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

PLANS_DATA = {
    "1m_1u": ("۱ ماهه تک کاربره", "۲۰۰,۰۰۰ تومان"),
    "1m_2u": ("۱ ماهه دو کاربره", "۲۵۰,۰۰۰ تومان"),
    "2m_1u": ("۲ ماهه تک کاربره", "۳۸۰,۰۰۰ تومان"),
    "2m_2u": ("۲ ماهه دو کاربره", "۴۳۰,۰۰۰ تومان"),
    "3m_1u": ("۳ ماهه تک کاربره", "۵۵۰,۰۰۰ تومان"),
    "3m_2u": ("۳ ماهه دو کاربره", "۶۰۰,۰۰۰ تومان"),
}

# ============================
# هندلرهای اصلی
# ============================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    add_user(user.id, user.username or "", user.first_name or "")
    
    date_str, time_str = get_current_jalali()
    welcome_text = (
        f"سلام <b>{user.first_name}</b> عزیز، به ربات رسمی <b>L2TP VPN 24/7</b> خوش آمدید! 🌹\n\n"
        f"📅 <b>تاریخ امروز:</b> <code>{date_str}</code>\n"
        f"⏰ <b>ساعت جاری:</b> <code>{time_str}</code> (به وقت تهران)\n\n"
        "⚡ <b>سرویس‌های اختصاصی و پایدار L2TP / IPsec</b>\n"
        "🎁 تمامی تعرفه‌ها دارای <b>۱۰ گیگابایت ترافیک هدیه</b> می‌باشند.\n\n"
        f"📢 کانال رسمی اطلاع‌رسانی: <a href='{CHANNEL_URL}'>کلیک کنید</a>\n\n"
        "👇 لطفاً جهت خرید، تمدید یا دریافت راهنما از منوی زیر استفاده فرمایید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), disable_web_page_preview=True)

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if str(message.from_user.id) != ADMIN_ID:
        return
    total_users = get_total_users()
    text = (
        "📊 <b>آمار زنده ربات:</b>\n\n"
        f"👥 تعداد کل اعضا و ورودی‌ها: <code>{total_users}</code> نفر"
    )
    await message.answer(text)

# ============================
# خرید و تمدید اشتراک
# ============================
@dp.message(F.text == "🛍 خرید اشتراک جدید")
async def process_buy(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(OrderStates.choosing_plan)
    text = (
        "💎 <b>لیست تعرفه‌های اشتراک L2TP VPN 24/7</b>\n"
        "<i>(تمامی پلن‌ها شامل ۱۰ گیگابایت ترافیک هدیه می‌باشند)</i>\n\n"
        "🔹 <b>۱ ماهه تک کاربره:</b> ۲۰۰,۰۰۰ تومان\n"
        "🔹 <b>۱ ماهه دو کاربره:</b> ۲۵۰,۰۰۰ تومان\n\n"
        "🔹 <b>۲ ماهه تک کاربره:</b> ۳۸۰,۰۰۰ تومان\n"
        "🔹 <b>۲ ماهه دو کاربره:</b> ۴۳۰,۰۰۰ تومان\n\n"
        "🔹 <b>۳ ماهه تک کاربره:</b> ۵۵۰,۰۰۰ تومان\n"
        "🔹 <b>۳ ماهه دو کاربره:</b> ۶۰۰,۰۰۰ تومان\n\n"
        f"💳 شماره کارت جهت واریز:\n<code>{PAYMENT_CARD}</code>\n"
        f"به نام: <b>{PAYMENT_NAME}</b> (بانک ملت)\n\n"
        "👇 لطفاً پلن مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(text, reply_markup=get_plans_inline_keyboard("buy"))

@dp.message(F.text == "🔄 تمدید اشتراک")
async def process_renewal(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RenewalStates.waiting_for_username)
    text = (
        "🔄 <b>تمدید اشتراک سرویس</b>\n\n"
        "لطفاً <b>نام کاربری (Username)</b> اکانت فعلی خود را ارسال کنید:"
    )
    await message.answer(text, reply_markup=get_cancel_inline_keyboard())

@dp.message(RenewalStates.waiting_for_username)
async def process_renewal_username(message: Message, state: FSMContext):
    await state.update_data(vpn_username=message.text.strip())
    await state.set_state(RenewalStates.choosing_plan)
    text = (
        f"نام کاربری ثبت شد: <code>{message.text.strip()}</code>\n\n"
        "لطفاً مدت زمان تمدید اشتراک خود را انتخاب فرمایید:"
    )
    await message.answer(text, reply_markup=get_plans_inline_keyboard("renew"))

@dp.callback_query(F.data.startswith("buy_") | F.data.startswith("renew_"))
async def process_plan_selection(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 1)
    action_type = parts[0]
    plan_key = parts[1]

    if plan_key not in PLANS_DATA:
        await callback.answer("پلن معتبر نیست.", show_alert=True)
        return

    plan_name, price = PLANS_DATA[plan_key]
    await state.update_data(plan_name=plan_name, price=price, action_type=action_type)

    if action_type == "buy":
        await state.set_state(OrderStates.waiting_for_receipt)
    else:
        await state.set_state(RenewalStates.waiting_for_receipt)

    text = (
        f"📋 <b>جزئیات سفارش:</b>\n"
        f"📦 پلن: <b>{plan_name}</b>\n"
        f"💰 مبلغ قابل پرداخت: <b>{price}</b>\n\n"
        f"💳 <b>شماره کارت واریز:</b>\n<code>{PAYMENT_CARD}</code>\n"
        f"به نام: <b>{PAYMENT_NAME}</b> (بانک ملت)\n\n"
        "📸 لطفاً تصویر فیش واریزی خود را ارسال کنید:"
    )
    await callback.message.edit_text(text, reply_markup=get_cancel_inline_keyboard())
    await callback.answer()

@dp.message(OrderStates.waiting_for_receipt, F.photo)
@dp.message(RenewalStates.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user
    plan_name = data.get("plan_name", "نامشخص")
    price = data.get("price", "نامشخص")
    action_type = data.get("action_type", "buy")
    vpn_user = data.get("vpn_username", "سفارش جدید")

    photo_id = message.photo[-1].file_id
    req_type = "خرید اشتراک جدید" if action_type == "buy" else "تمدید اشتراک"

    admin_caption = (
        "🔔 <b>رسید پرداخت جدید دریافت شد!</b>\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 شناسه: <code>{user.id}</code>\n"
        f"📌 نوع: <b>{req_type}</b>\n"
        f"🔑 نام کاربری اکانت: <code>{vpn_user}</code>\n"
        f"📦 پلن: <b>{plan_name}</b>\n"
        f"💰 مبلغ: <b>{price}</b>"
    )

    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_caption)
    except Exception as e:
        logger.error(f"Error forwarding receipt to admin: {e}")

    await state.clear()
    await message.answer(
        "✅ فیش واریزی شما با موفقیت برای مدیریت ارسال شد.\n"
        "سرویس پس از بررسی فعال و مشخصات برای شما ارسال خواهد شد.",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ عملیات لغو شد.")
    await callback.answer()

# ============================
# پنل IBSng
# ============================
@dp.message(F.text == "📊 ورود به پنل کاربری (IBSng)")
async def ibsng_panel_info(message: Message):
    text = (
        "🌐 <b>پنل مشاهده مصرف و وضعیت اشتراک (IBSng)</b>\n\n"
        "⚠️ <b>توجه مهم:</b>\n"
        "<i>برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.</i>\n\n"
        f"🔗 <b>آدرس پنل IBSng:</b>\n{IBSNG_PANEL_URL}\n\n"
        "💡 نام کاربری و رمز عبور خود را وارد کرده تا میزان حجم مصرفی و روزهای باقیمانده را مشاهده نمایید."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 ورود به پنل کاربری IBSng", url=IBSNG_PANEL_URL)]
    ])
    await message.answer(text, reply_markup=kb)

# ============================
# راهنماها
# ============================
@dp.message(F.text == "📚 راهنمای اتصال و دانلود")
async def show_guides_menu(message: Message):
    text = (
        "📚 <b>راهنمای اتصال به سرویس L2TP VPN 24/7</b>\n\n"
        f"🌐 <b>آدرس سرور VPN:</b> <code>{VPN_SERVER_IP}</code>\n"
        f"🔑 <b>کلید امنیتی (Secret):</b> <code>{IPSEC_SECRET}</code>\n\n"
        "دستگاه مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(text, reply_markup=get_guides_keyboard())

@dp.callback_query(F.data.startswith("guide_"))
async def guide_details(callback: CallbackQuery):
    g_type = callback.data.split("_")[1]
    
    if g_type == "ios":
        text = (
            "📱 <b>راهنمای آیفون و آیپد (iOS):</b>\n\n"
            "۱. وارد <b>Settings</b> و بخش <b>VPN & Device Management</b> شوید.\n"
            "۲. گزینه <b>Add VPN Configuration</b> را انتخاب کنید.\n"
            "۳. نوع (Type) را روی <b>L2TP</b> بگذارید.\n"
            f"۴. در بخش Server مقدار: <code>{VPN_SERVER_IP}</code>\n"
            "۵. در بخش Account نام کاربری و Password رمز خود را بزنید.\n"
            f"۶. در بخش Secret مقدار: <code>{IPSEC_SECRET}</code> را وارد کنید.\n"
            "۷. ذخیره کنید و متصل شوید."
        )
    elif g_type == "android":
        text = (
            "🤖 <b>راهنمای اندروید (Android):</b>\n\n"
            "۱. وارد تنظیمات (Settings) و بخش اتصالات (Connections) شوید.\n"
            "۲. بخش More connection settings و سپس <b>VPN</b> را انتخاب کنید.\n"
            "۳. افزودن (+) را بزنید و نوع را <b>L2TP/IPSec PSK</b> قرار دهید.\n"
            f"۴. آدرس سرور: <code>{VPN_SERVER_IP}</code>\n"
            f"۵. کلید اشتراکی (IPSec pre-shared key): <code>{IPSEC_SECRET}</code>\n"
            "۶. نام کاربری و رمز را وارد نموده و ذخیره کنید."
        )
    elif g_type == "windows":
        text = (
            "💻 <b>راهنمای ویندوز (Windows 10 / 11):</b>\n\n"
            "۱. به <b>Settings > Network & Internet > VPN</b> بروید.\n"
            "۲. روی <b>Add a VPN connection</b> بزنید.\n"
            f"۳. در Server name or address آدرس: <code>{VPN_SERVER_IP}</code>\n"
            "۴. مقدار VPN type را روی <b>L2TP/IPsec with pre-shared key</b> بگذارید.\n"
            f"۵. در Pre-shared key کلید: <code>{IPSEC_SECRET}</code> را وارد کنید.\n"
            "۶. نام کاربری و رمز را وارد کرده و ذخیره نمایید."
        )
    elif g_type == "mac":
        text = (
            "🍏 <b>راهنمای مک‌او‌اس (macOS):</b>\n\n"
            "۱. وارد System Settings و بخش Network شوید.\n"
            "۲. روی گزینه سه نقطه زده و <b>Add VPN Configuration > L2TP over IPSec</b> را انتخاب کنید.\n"
            f"۳. در Server Address مقدار: <code>{VPN_SERVER_IP}</code>\n"
            "۴. نام کاربری خود را وارد کنید.\n"
            f"۵. در Authentication Settings کلید: <code>{IPSEC_SECRET}</code> را ثبت کنید."
        )
    else:
        text = (
            "🌐 <b>مشخصات کلی اتصال برای مودم و روترها:</b>\n\n"
            f"🔹 <b>پروتکل:</b> L2TP / IPsec PSK\n"
            f"🔹 <b>آدرس سرور VPN:</b> <code>{VPN_SERVER_IP}</code>\n"
            f"🔹 <b>کلید امنیتی (Secret):</b> <code>{IPSEC_SECRET}</code>\n"
            f"🔹 <b>سرور اکانتینگ (IBSng):</b> <code>94.184.45.58</code>\n"
        )
    
    await callback.message.edit_text(text, reply_markup=get_guides_keyboard())
    await callback.answer()

# ============================
# پشتیبانی
# ============================
@dp.message(F.text == "💬 پشتیبانی و تماس")
async def support_menu(message: Message):
    text = (
        "💬 <b>مرکز پشتیبانی L2TP VPN 24/7</b>\n\n"
        "جهت پیگیری فنی و سوالات می‌توانید از گزینه‌های زیر استفاده نمایید:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 ارسال تیکت و پیام", callback_data="ticket_start")],
        [InlineKeyboardButton(text="👤 ارتباط مستقیم با پشتیبانی", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}")]
    ])
    await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "ticket_start")
async def ticket_ask_message(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(SupportStates.waiting_for_message)
    await callback.message.edit_text("📝 لطفاً شرح پیام یا مشکل خود را ارسال نمایید:", reply_markup=get_cancel_inline_keyboard())
    await callback.answer()

@dp.message(SupportStates.waiting_for_message)
async def ticket_get_message(message: Message, state: FSMContext):
    user = message.from_user
    admin_msg = (
        "📩 <b>پیام پشتیبانی جدید!</b>\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 شناسه: <code>{user.id}</code>\n\n"
        f"📝 <b>متن پیام:</b>\n{message.text}"
    )
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
    except Exception as e:
        logger.error(f"Error forwarding ticket: {e}")

    await state.clear()
    await message.answer("✅ پیام شما دریافت شد و به زودی پاسخ داده می‌شود.", reply_markup=get_main_keyboard())

# ============================
# کانال اطلاع‌رسانی
# ============================
@dp.message(F.text == "📢 کانال اطلاع‌رسانی")
async def show_channel(message: Message):
    text = "📢 برای دریافت آخرین اخبار و اطلاعیه‌ها به کانال رسمی ما بپیوندید:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 ورود به کانال تلگرام", url=CHANNEL_URL)]
    ])
    await message.answer(text, reply_markup=kb)

# ============================
# وب‌سرور Render (Health Check)
# ============================
async def handle_health_check(request):
    return web.Response(text="Mikrotik-Bot is Running Healthy 24/7!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check server running on port {PORT}")

# ============================
# اجرای اصلی
# ============================
async def main():
    logger.info("Starting Bot with Web Health Server...")
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

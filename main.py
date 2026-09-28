import asyncio
import logging
import os
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher
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
    ReplyKeyboardRemove,
)
from aiogram.client.default import DefaultBotProperties
from magic_filter import F

# ============================
# تنظیمات لاگینگ
# ============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================
# مقادیر و متغیرهای اصلی
# ============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENytzh4ynqajjX0X")
ADMIN_ID = int(os.getenv("ADMIN_ID", "2786850266"))
PORT = int(os.getenv("PORT", "10000"))

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support")
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")

VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "GAPGPTMASKTOKENytzh4ynqajjX1X"

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_name TEXT,
            amount TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str, first_name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username, first_name)
    )
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status='approved'")
    approved_payments = cursor.fetchone()[0]
    conn.close()
    return total_users, approved_payments

init_db()

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
    waiting_for_vpn_username = State()
    waiting_for_message = State()

class CompensationStates(StatesGroup):
    waiting_for_old_username = State()
    waiting_for_old_receipt = State()

# ============================
# کیبوردها
# ============================
def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🛍 خرید اشتراک جدید"), KeyboardButton(text="🔄 تمدید اشتراک")],
        [KeyboardButton(text="📊 ورود به پنل کاربری (IBSng)"), KeyboardButton(text="🎁 طرح جبرانی مشترکین")],
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
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_guides_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📱 راهنمای آیفون (iOS)", callback_data="guide_ios")],
        [InlineKeyboardButton(text="🤖 راهنمای اندروید (Android)", callback_data="guide_android")],
        [InlineKeyboardButton(text="💻 راهنمای ویندوز (Windows)", callback_data="guide_windows")],
        [InlineKeyboardButton(text="🍏 راهنمای مک (macOS)", callback_data="guide_mac")],
        [InlineKeyboardButton(text="🌐 تنظیمات عمومی و مودم", callback_data="guide_general")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ============================
# تعریف ربات و دیسپچر
# ============================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

PLANS_DATA = {
    "1m_1u": ("۱ ماهه - ۱ کاربره", "۲۰۰,۰۰۰ تومان"),
    "1m_2u": ("۱ ماهه - ۲ کاربره", "۲۵۰,۰۰۰ تومان"),
    "2m_1u": ("۲ ماهه - ۱ کاربره", "۳۸۰,۰۰۰ تومان"),
    "2m_2u": ("۲ ماهه - ۲ کاربره", "۴۳۰,۰۰۰ تومان"),
    "3m_1u": ("۳ ماهه - ۱ کاربره", "۵۵۰,۰۰۰ تومان"),
    "3m_2u": ("۳ ماهه - ۲ کاربره", "۶۰۰,۰۰۰ تومان"),
}

# ============================
# هندلرهای دستورات عمومی
# ============================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    add_user(user.id, user.username or "", user.first_name or "")
    
    welcome_text = (
        f"سلام <b>{user.first_name}</b> عزیز! 🌹\n\n"
        "به ربات رسمی مدیریت و پشتیبانی سرویس‌های <b>Arshavin L2TP/IPsec VPN</b> خوش آمدید.\n\n"
        "لطفاً یکی از گزینه‌های زیر را جهت ادامه انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    total_users, approved_payments = get_stats()
    text = (
        "📊 <b>آمار ربات آرشاوین:</b>\n\n"
        f"👥 کل کاربران ثبت‌شده: <code>{total_users}</code> نفر\n"
        f"💳 کل سفارش‌های تأییدشده: <code>{approved_payments}</code> عدد"
    )
    await message.answer(text)

# ============================
# هندلرهای خرید و تمدید
# ============================
@dp.message(F.text == "🛍 خرید اشتراک جدید")
async def process_buy(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(OrderStates.choosing_plan)
    text = (
        "💎 <b>تعرفه‌های اشتراک VPN آرشاوین</b>\n"
        "<i>(تمامی پلن‌ها شامل ۱۰ گیگابایت ترافیک هدیه می‌باشند)</i>\n\n"
        "🔹 <b>۱ ماهه تک کاربره:</b> ۲۰۰,۰۰۰ تومان\n"
        "🔹 <b>۱ ماهه دو کاربره:</b> ۲۵۰,۰۰۰ تومان\n\n"
        "🔹 <b>۲ ماهه تک کاربره:</b> ۳۸۰,۰۰۰ تومان\n"
        "🔹 <b>۲ ماهه دو کاربره:</b> ۴۳۰,۰۰۰ تومان\n\n"
        "🔹 <b>۳ ماهه تک کاربره:</b> ۵۵۰,۰۰۰ تومان\n"
        "🔹 <b>۳ ماهه دو کاربره:</b> ۶۰۰,۰۰۰ تومان\n\n"
        "👇 لطفاً پلن مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(text, reply_markup=get_plans_inline_keyboard("buy"))

@dp.message(F.text == "🔄 تمدید اشتراک")
async def process_renewal(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(RenewalStates.waiting_for_username)
    text = (
        "🔄 <b>تمدید اشتراک سرویس</b>\n\n"
        "لطفاً <b>نام کاربری (Username)</b> فعلی خود در پنل را ارسال کنید:"
    )
    await message.answer(text, reply_markup=ReplyKeyboardRemove())

@dp.message(RenewalStates.waiting_for_username)
async def process_renewal_username(message: Message, state: FSMContext):
    await state.update_data(vpn_username=message.text.strip())
    await state.set_state(RenewalStates.choosing_plan)
    text = (
        f"نام کاربری دریافت شد: <code>{message.text.strip()}</code>\n\n"
        "اکنون لطفاً مدت زمان تمدید اشتراک خود را انتخاب فرمایید:"
    )
    await message.answer(text, reply_markup=get_plans_inline_keyboard("renew"))

@dp.callback_query(F.data.startswith("buy_") | F.data.startswith("renew_"))
async def process_plan_selection(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_", 1)
    action_type = parts[0]
    plan_key = parts[1]

    if plan_key not in PLANS_DATA:
        await callback.answer("پلن نامعتبر است.", show_alert=True)
        return

    plan_name, price = PLANS_DATA[plan_key]
    await state.update_data(plan_name=plan_name, price=price, action_type=action_type)

    if action_type == "buy":
        await state.set_state(OrderStates.waiting_for_receipt)
    else:
        await state.set_state(RenewalStates.waiting_for_receipt)

    await callback.message.delete()
    text = (
        f"📋 <b>جزئیات سفارش:</b>\n"
        f"پلن انتخابی: <b>{plan_name}</b>\n"
        f"مبلغ قابل پرداخت: <b>{price}</b>\n\n"
        f"💳 <b>اطلاعات کارت جهت واریز:</b>\n"
        f"شماره کارت: <code>{PAYMENT_CARD}</code>\n"
        f"به نام: <b>{PAYMENT_NAME}</b> (بانک ملت)\n\n"
        "📸 <i>لطفاً پس از واریز، عکس یا اسکرین‌شات فیش واریزی را ارسال کنید.</i>"
    )
    await callback.message.answer(text)

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

    req_type = "خرید جدید" if action_type == "buy" else "تمدید اشتراک"
    admin_caption = (
        "🔔 <b>رسید پرداخت جدید دریافت شد!</b>\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 آیدی عددی: <code>{user.id}</code>\n"
        f"📌 نوع درخواست: <b>{req_type}</b>\n"
        f"🔑 نام کاربری اکانت: <code>{vpn_user}</code>\n"
        f"📦 پلن: <b>{plan_name}</b>\n"
        f"💰 مبلغ: <b>{price}</b>"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تایید و ارسال اکانت", callback_data=f"adm_ok_{user.id}"),
            InlineKeyboardButton(text="❌ رد رسید", callback_data=f"adm_reject_{user.id}")
        ]
    ])

    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=admin_caption,
            reply_markup=admin_kb
        )
    except Exception as e:
        logger.error(f"Error sending receipt to admin: {e}")

    await state.clear()
    await message.answer(
        "✅ فیش واریزی شما با موفقیت برای مدیریت ارسال شد.\n"
        "پس از بررسی، مشخصات اکانت یا تاییدیه تمدید برای شما ارسال خواهد شد. متشکریم از صبوری شما! 🌹",
        reply_markup=get_main_keyboard()
    )

@dp.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("عملیات لغو شد.", reply_markup=get_main_keyboard())

# ============================
# پنل کاربری IBSng
# ============================
@dp.message(F.text == "📊 ورود به پنل کاربری (IBSng)")
async def ibsng_panel_info(message: Message):
    text = (
        "🌐 <b>پنل مشاهده مصرف و وضعیت اشتراک (IBSng)</b>\n\n"
        "⚠️ <b>توجه مهم:</b>\n"
        "<i>برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.</i>\n\n"
        f"🔗 <b>آدرس پنل IBSng:</b>\n{IBSNG_PANEL_URL}\n\n"
        "💡 نام کاربری و رمز عبور اختصاصی خود را در صفحه بالا وارد کنید تا ترافیک مصرفی و روزهای باقیمانده را مشاهده فرمایید."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 ورود به پنل کاربری IBSng", url=IBSNG_PANEL_URL)]
    ])
    await message.answer(text, reply_markup=kb)

# ============================
# طرح جبرانی مشترکین
# ============================
@dp.message(F.text == "🎁 طرح جبرانی مشترکین")
async def process_compensation_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CompensationStates.waiting_for_old_username)
    text = (
        "🎁 <b>طرح ویژه جبرانی مشترکین قدیمی</b>\n\n"
        "این طرح برای عزیزانی است که طی ۲ تا ۳ سال گذشته اشتراک داشته و به دلیل قطعی‌ها حق آن‌ها محفوظ مانده است.\n\n"
        "با ارسال نام کاربری و فیش واریزی قبلی، اشتراک شما <b>با دورهٔ کامل و ۱۰ گیگابایت ترافیک هدیه</b> مجدداً از نو فعال خواهد شد.\n\n"
        "لطفاً <b>نام کاربری (Username) قبلی</b> خود را ارسال کنید:"
    )
    await message.answer(text, reply_markup=ReplyKeyboardRemove())

@dp.message(CompensationStates.waiting_for_old_username)
async def process_compensation_user(message: Message, state: FSMContext):
    await state.update_data(old_username=message.text.strip())
    await state.set_state(CompensationStates.waiting_for_old_receipt)
    text = (
        f"نام کاربری ثبت شد: <code>{message.text.strip()}</code>\n\n"
        "📸 اکنون لطفاً <b>عکس فیش واریزی قبلی</b> خود را بفرستید:"
    )
    await message.answer(text)

@dp.message(CompensationStates.waiting_for_old_receipt, F.photo)
async def process_compensation_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user
    old_user = data.get("old_username", "نامشخص")
    photo_id = message.photo[-1].file_id

    admin_caption = (
        "🎁 <b>درخواست طرح جبرانی جدید!</b>\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 آیدی عددی: <code>{user.id}</code>\n"
        f"🔑 نام کاربری سابق: <code>{old_user}</code>\n"
        "📌 درخواست: فعال‌سازی مجدد دوره کامل + ۱۰ گیگ هدیه"
    )

    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=admin_caption
        )
    except Exception as e:
        logger.error(f"Error sending compensation to admin: {e}")

    await state.clear()
    await message.answer(
        "✅ درخواست طرح جبرانی شما با موفقیت برای مدیریت ارسال شد.\n"
        "پس از بازبینی فیش قبلی، اکانت جدید با ۱۰ گیگ هدیه برای شما ارسال می‌گردد. متشکریم از همراهی شما! ❤️",
        reply_markup=get_main_keyboard()
    )

# ============================
# راهنمای اتصال به سرویس‌ها
# ============================
@dp.message(F.text == "📚 راهنمای اتصال و دانلود")
async def show_guides_menu(message: Message):
    text = (
        "📚 <b>راهنمای اتصال به سرویس VPN آرشاوین</b>\n\n"
        f"🌐 <b>آدرس سرور VPN:</b> <code>{VPN_SERVER_IP}</code>\n"
        f"🔑 <b>کلید اشتراکی (Secret):</b> <code>{IPSEC_SECRET}</code>\n\n"
        "سیستم عامل یا دستگاه مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(text, reply_markup=get_guides_keyboard())

@dp.callback_query(F.data.startswith("guide_"))
async def guide_details(callback: CallbackQuery):
    g_type = callback.data.split("_")[1]
    
    if g_type == "ios":
        text = (
            "📱 <b>راهنمای آیفون و آیپد (iOS):</b>\n\n"
            "۱. وارد <b>Settings</b> و بخش <b>VPN & Device Management</b> شوید.\n"
            "۲. گزینه <b>Add VPN Configuration</b> را بزنید.\n"
            "۳. نوع (Type) را روی <b>L2TP</b> بگذارید.\n"
            f"۴. در بخش Server آدرس: <code>{VPN_SERVER_IP}</code>\n"
            "۵. در بخش Account نام کاربری و Password رمز خود را وارد کنید.\n"
            f"۶. در بخش Secret عبارت: <code>{IPSEC_SECRET}</code> را وارد کنید.\n"
            "۷. ذخیره کرده و متصل شوید."
        )
    elif g_type == "android":
        text = (
            "🤖 <b>راهنمای اندروید (Android):</b>\n\n"
            "۱. وارد تنظیمات گوشی (Settings) و بخش اتصالات (Connections) شوید.\n"
            "۲. بخش More connection settings و سپس <b>VPN</b> را انتخاب کنید.\n"
            "۳. افزودن (+) را بزنید؛ نوع VPN را <b>L2TP/IPSec PSK</b> انتخاب کنید.\n"
            f"۴. آدرس سرور: <code>{VPN_SERVER_IP}</code>\n"
            f"۵. کلید اشتراکی (IPSec pre-shared key): <code>{IPSEC_SECRET}</code>\n"
            "۶. نام کاربری و رمز را وارد کرده و ذخیره نمایید."
        )
    elif g_type == "windows":
        text = (
            "💻 <b>راهنمای ویندوز (Windows 10 / 11):</b>\n\n"
            "۱. به <b>Settings > Network & Internet > VPN</b> بروید.\n"
            "۲. روی <b>Add a VPN connection</b> کلیک کنید.\n"
            f"۳. در Server name or address مقدار: <code>{VPN_SERVER_IP}</code>\n"
            "۴. فیلد VPN type را روی <b>L2TP/IPsec with pre-shared key</b> قرار دهید.\n"
            f"۵. در Pre-shared key مقدار: <code>{IPSEC_SECRET}</code> را وارد کنید.\n"
            "۶. نام کاربری و رمز را وارد کرده و Save کنید."
        )
    elif g_type == "mac":
        text = (
            "🍏 <b>راهنمای مک‌او‌اس (macOS):</b>\n\n"
            "۱. وارد System Settings و بخش Network شوید.\n"
            "۲. روی علامت سه نقطه کلیک کرده و <b>Add VPN Configuration > L2TP over IPSec</b> را بزنید.\n"
            f"۳. در Server Address مقدار: <code>{VPN_SERVER_IP}</code>\n"
            "۴. نام کاربری را وارد کنید.\n"
            f"۵. در Authentication Settings کلید اشتراکی: <code>{IPSEC_SECRET}</code> را بگذارید."
        )
    else:
        text = (
            "🌐 <b>مشخصات کلی اتصال برای مودم و روترها:</b>\n\n"
            f"🔹 <b>نوع پروتکل:</b> L2TP / IPsec PSK\n"
            f"🔹 <b>آدرس سرور VPN:</b> <code>{VPN_SERVER_IP}</code>\n"
            f"🔹 <b>کلید امنیتی (IPsec Secret):</b> <code>{IPSEC_SECRET}</code>\n"
            f"🔹 <b>سرور اکانتینگ (IBSng):</b> <code>94.184.45.58</code>\n"
        )
    
    await callback.message.edit_text(text, reply_markup=get_guides_keyboard())

# ============================
# سیستم تیکت و پشتیبانی
# ============================
@dp.message(F.text == "💬 پشتیبانی و تماس")
async def support_menu(message: Message):
    text = (
        "💬 <b>مرکز پشتیبانی سرویس آرشاوین</b>\n\n"
        "جهت پیگیری مشکلات فنی، شارژ و سوالات خود می‌توانید به یکی از دو روش زیر اقدام کنید:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 ارسال تیکت درون ربات", callback_data="ticket_start")],
        [InlineKeyboardButton(text="👤 ارتباط با ادمین در تلگرام", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}")]
    ])
    await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data == "ticket_start")
async def ticket_ask_username(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(SupportStates.waiting_for_vpn_username)
    await callback.message.delete()
    await callback.message.answer(
        "لطفاً <b>نام کاربری (اکانت VPN)</b> خود را وارد کنید (در صورتی که اکانت ندارید عبارت «ندارم» را ارسال کنید):",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(SupportStates.waiting_for_vpn_username)
async def ticket_get_user(message: Message, state: FSMContext):
    await state.update_data(ticket_vpn_user=message.text.strip())
    await state.set_state(SupportStates.waiting_for_message)
    await message.answer("لطفاً متن پیام یا شرح مشکل خود را به صورت کامل بنویسید:")

@dp.message(SupportStates.waiting_for_message)
async def ticket_get_message(message: Message, state: FSMContext):
    data = await state.get_data()
    vpn_user = data.get("ticket_vpn_user", "نامشخص")
    user = message.from_user

    admin_msg = (
        "📩 <b>تیکت پشتیبانی جدید!</b>\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 آیدی عددی: <code>{user.id}</code>\n"
        f"🔑 نام کاربری سرویس: <code>{vpn_user}</code>\n\n"
        f"📝 <b>متن پیام:</b>\n{message.text}"
    )

    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
    except Exception as e:
        logger.error(f"Error forwarding ticket: {e}")

    await state.clear()
    await message.answer(
        "✅ پیام شما با موفقیت برای مدیریت ارسال شد. به زودی پاسخ را دریافت خواهید کرد.",
        reply_markup=get_main_keyboard()
    )

# ============================
# کانال اطلاع‌رسانی
# ============================
@dp.message(F.text == "📢 کانال اطلاع‌رسانی")
async def show_channel(message: Message):
    text = (
        "📢 برای دریافت آخرین اخبار، تغییرات سرورها و اطلاعیه‌ها به کانال رسمی ما بپیوندید:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 ورود به کانال تلگرام", url=CHANNEL_URL)]
    ])
    await message.answer(text, reply_markup=kb)

# ============================
# وب‌سرور سلامت Render (Health Check)
# ============================
async def handle_health_check(request):
    return web.Response(text="Mikrotik-Bot is Running Healthy!", status=200)

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
# نقطه شروع برنامه
# ============================
async def main():
    logger.info("Starting Mikrotik-Bot with Aiogram & Web Health Server...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

import os
import asyncio
import logging
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ----------------------------------------------------
# 1. تنظیمات و متغیرهای محیطی
# ----------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SUPPORT_RAW = os.getenv("SUPPORT_USERNAME") or os.getenv("SUPPORT_ID") or os.getenv("ADMIN_USERNAME") or os.getenv("SUPPORT") or "support"
SUPPORT_USERNAME = SUPPORT_RAW.replace("@", "").strip()

CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9918-XXXX-XXXX")
CARD_HOLDER = os.getenv("CARD_HOLDER", "پشتیبانی سرویس")

PORT = int(os.getenv("PORT", 8080))

if not BOT_TOKEN:
    raise ValueError("❌ خطای حیاتی: BOT_TOKEN در متغیرهای محیطی تنظیم نشده است!")

# ----------------------------------------------------
# 2. مدیریت دیتابیس (SQLite)
# ----------------------------------------------------
DB_FILE = "bot_users.db"

def init_db():
    """ایجاد جدول کاربران در صورت عدم وجود"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user_to_db(user_id, full_name, username):
    """ثبت کاربر جدید در دیتابیس"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
            (user_id, full_name, username)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database Error (add_user): {e}")

def get_total_users():
    """دریافت تعداد کل کاربران"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Database Error (get_total): {e}")
        return 0

# اجرای اولیه دیتابیس
init_db()

# ----------------------------------------------------
# 3. ماشین وضعیت (FSM States)
# ----------------------------------------------------
class PurchaseStates(StatesGroup):
    waiting_for_receipt = State()

# ----------------------------------------------------
# 4. تعریف کیبوردهای Inline
# ----------------------------------------------------
def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(text="🛍 خرید اشتراک", callback_data="buy_service"),
            InlineKeyboardButton(text="💳 تمدید سرویس", callback_data="renew_service")
        ],
        [
            InlineKeyboardButton(text="⚙️ کانفیگ سفارشی", callback_data="custom_config"),
            InlineKeyboardButton(text="👤 حساب کاربری", callback_data="user_profile")
        ],
        [
            InlineKeyboardButton(text="📚 راهنمای اتصال", callback_data="help_guide")
        ],
        [
            InlineKeyboardButton(text="💬 پشتیبانی آنلاین", url=f"https://t.me/{SUPPORT_USERNAME}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def plans_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🚀 ۱ ماهه - ۳۰ گیگ (۳۵۰,۰۰۰ ت)", callback_data="plan_1m_30g")],
        [InlineKeyboardButton(text="🚀 ۲ ماهه - ۶۰ گیگ (۶۵۰,۰۰۰ ت)", callback_data="plan_2m_60g")],
        [InlineKeyboardButton(text="⚡️ ۳ ماهه - ۹۰ گیگ (۹۵۰,۰۰۰ ت)", callback_data="plan_3m_90g")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def payment_method_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📸 ارسال رسید کارت‌به‌کارت", callback_data="send_receipt")],
        [InlineKeyboardButton(text="🔙 انصراف و بازگشت", callback_data="back_to_plans")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]]
    )

# ----------------------------------------------------
# 5. هندلرهای تلگرام (Aiogram Handlers)
# ----------------------------------------------------
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    # ذخیره کاربر در دیتابیس
    add_user_to_db(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    
    await state.clear()
    welcome_text = (
        f"سلام {message.from_user.first_name} عزیز! 🌟\n"
        "به ربات مدیریت و خرید سرویس خوش آمدید.\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=main_menu_keyboard())

@dp.message(Command("stats"))
async def stats_handler(message: Message):
    """دستور مخصوص ادمین برای مشاهده آمار"""
    if ADMIN_ID and str(message.from_user.id) != str(ADMIN_ID):
        return # اگر ادمین نبود، هیچ پاسخی داده نشود

    total = get_total_users()
    await message.answer(
        f"📊 **گزارش آماری ربات**\n\n"
        f"👥 تعداد کل کاربران ثبت شده: **{total}** نفر",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "منوی اصلی ربات:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_service")
async def buy_service_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "پلن مورد نظر خود را برای خرید انتخاب کنید:",
        reply_markup=plans_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "custom_config")
async def custom_config_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ جهت دریافت کانفیگ سفارشی، لطفاً به آیدی پشتیبانی پیام دهید:\n\n"
        f"🆔 @{SUPPORT_USERNAME}",
        reply_markup=back_to_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_plans")
async def back_to_plans_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "پلن مورد نظر خود را برای خرید انتخاب کنید:",
        reply_markup=plans_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("plan_"))
async def select_plan_handler(callback: CallbackQuery, state: FSMContext):
    plan_code = callback.data
    await state.update_data(selected_plan=plan_code)
    
    pay_text = (
        "💳 **اطلاعات واریز وجه**\n\n"
        f"🔹 شماره کارت: `{CARD_NUMBER}`\n"
        f"🔹 به نام: **{CARD_HOLDER}**\n\n"
        "⚠️ لطفاً پس از واریز، روی دکمه زیر کلیک کرده و عکس فیش را ارسال نمایید."
    )
    await callback.message.edit_text(
        pay_text,
        reply_markup=payment_method_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "send_receipt")
async def ask_receipt_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PurchaseStates.waiting_for_receipt)
    await callback.message.edit_text(
        "لطفاً تصویر رسید پرداخت خود را ارسال کنید:\n\n"
        "(برای انصراف از دستور /start استفاده کنید)",
        reply_markup=None
    )
    await callback.answer()

@dp.message(PurchaseStates.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    selected_plan = user_data.get("selected_plan", "نامشخص")
    photo_id = message.photo[-1].file_id

    await message.answer(
        "✅ رسید شما با موفقیت دریافت شد و برای مدیریت ارسال گردید.\n"
        "پس از بررسی، کانفیگ برای شما ارسال خواهد شد.",
        reply_markup=main_menu_keyboard()
    )

    if ADMIN_ID:
        try:
            admin_msg = (
                "🔔 **رسید جدید ثبت شد!**\n\n"
                f"👤 کاربر: {message.from_user.full_name} (@{message.from_user.username or 'ندارد'})\n"
                f"🆔 آیدی عددی: `{message.from_user.id}`\n"
                f"📦 پلن انتخابی: `{selected_plan}`"
            )
            await bot.send_photo(
                chat_id=int(ADMIN_ID),
                photo=photo_id,
                caption=admin_msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"خطا در ارسال رسید به ادمین: {e}")

    await state.clear()

@dp.message(PurchaseStates.waiting_for_receipt)
async def process_receipt_invalid(message: Message):
    await message.answer("⚠️ لطفاً رسید را فقط به صورت تصویر (عکس) ارسال کنید.")

@dp.callback_query(F.data == "user_profile")
async def profile_handler(callback: CallbackQuery):
    user = callback.from_user
    profile_text = (
        "👤 **مشخصات کاربری شما**\n\n"
        f"نام: {user.full_name}\n"
        f"آیدی عددی: `{user.id}`\n"
        f"نام کاربری: @{user.username or 'ندارد'}\n"
        "وضعیت سرویس: بدون سرویس فعال"
    )
    await callback.message.edit_text(

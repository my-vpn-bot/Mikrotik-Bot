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
from aiogram.filters import CommandStart
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
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "Support_Admin")

# اطلاعات واریز
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9918-XXXX-XXXX")
CARD_HOLDER = os.getenv("CARD_HOLDER", "پشتیبانی سرویس")

PORT = int(os.getenv("PORT", 8080))

if not BOT_TOKEN:
    logger.error("❌ خطای حیاتی: BOT_TOKEN تنظیم نشده است!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ----------------------------------------------------
# 2. دیتابیس و مدیریت کاربران (آمار بازدیدکنندگان)
# ----------------------------------------------------
DB_FILE = "bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user_to_db(user_id, full_name, username):
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
            (user_id, full_name, username)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database Error: {e}")

def get_total_users():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

init_db()

# ----------------------------------------------------
# 3. ماشین وضعیت (FSM)
# ----------------------------------------------------
class PurchaseStates(StatesGroup):
    waiting_for_receipt = State()

# ----------------------------------------------------
# 4. پلن‌ها و قیمت‌های نهایی
# ----------------------------------------------------
PLANS_DATA = {
    "plan_1m_30g": {"name": "🚀 پلن ۱ ماهه (۳۰ گیگابایت)", "price": "۳۵۰,۰۰۰ تومان"},
    "plan_2m_60g": {"name": "🚀 پلن ۲ ماهه (۶۰ گیگابایت)", "price": "۶۵۰,۰۰۰ تومان"},
    "plan_3m_90g": {"name": "🚀 پلن ۳ ماهه (۹۰ گیگابایت)", "price": "۹۵۰,۰۰۰ تومان"},
}

def main_menu_keyboard(is_admin=False):
    keyboard = [
        [
            InlineKeyboardButton(text="🛍 خرید اشتراک", callback_data="buy_service"),
            InlineKeyboardButton(text="👤 حساب کاربری", callback_data="user_profile")
        ],
        [
            InlineKeyboardButton(text="⚙️ کانفیگ سفارشی", callback_data="custom_config"),
            InlineKeyboardButton(text="📚 راهنما", callback_data="help_guide")
        ],
        [
            InlineKeyboardButton(text="💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")
        ]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="📊 آمار بازدیدکنندگان", callback_data="admin_stats")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def plans_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🚀 ۱ ماهه - ۳۰ گیگ (۳۵۰,۰۰۰ ت)", callback_data="plan_1m_30g")],
        [InlineKeyboardButton(text="🚀 ۲ ماهه - ۶۰ گیگ (۶۵۰,۰۰۰ ت)", callback_data="plan_2m_60g")],
        [InlineKeyboardButton(text="🚀 ۳ ماهه - ۹۰ گیگ (۹۵۰,۰۰۰ ت)", callback_data="plan_3m_90g")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ----------------------------------------------------
# 5. هندلرها
# ----------------------------------------------------

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    add_user_to_db(user_id, message.from_user.full_name, message.from_user.username)
    await state.clear()
    
    is_admin = (str(user_id) == str(ADMIN_ID))
    await message.answer(
        f"سلام {message.from_user.first_name} عزیز! به ربات خوش آمدید.",
        reply_markup=main_menu_keyboard(is_admin)
    )

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    if str(callback.from_user.id) != str(ADMIN_ID):
        await callback.answer("شما دسترسی ادمین ندارید.", show_alert=True)
        return
    
    total = get_total_users()
    await callback.answer(f"📊 کل کاربران ربات: {total} نفر", show_alert=True)

@dp.callback_query(F.data == "buy_service")
async def show_plans(callback: CallbackQuery):
    await callback.message.edit_text("لطفاً پلن مورد نظر خود را انتخاب کنید:", reply_markup=plans_keyboard())

@dp.callback_query(F.data.startswith("plan_"))
async def process_plan_selection(callback: CallbackQuery, state: FSMContext):
    plan_key = callback.data
    if plan_key not in PLANS_DATA:
        await callback.answer("پلن نامعتبر است.", show_alert=True)
        return
        
    await state.update_data(selected_plan=plan_key)
    await state.set_state(PurchaseStates.waiting_for_receipt)
    
    plan_info = PLANS_DATA[plan_key]
    
    text = (f"💎 شما پلن زیر را انتخاب کردید:\n"
            f"`{plan_info['name']}`\n"
            f"💰 مبلغ قابل پرداخت: `{plan_info['price']}`\n\n"
            f"💳 لطفاً مبلغ را به شماره کارت زیر واریز کنید:\n"
            f"`{CARD_NUMBER}`\n"
            f"بنام: {CARD_HOLDER}\n\n"
            f"⚠️ پس از واریز، حتماً **تصویر رسید** را همینجا ارسال کنید.")
    
    await callback.message.edit_text(text, parse_mode="Markdown")

@dp.message(PurchaseStates.waiting_for_receipt, F.photo)
async def handle_receipt_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_key = data.get("selected_plan", "plan_1m_30g")
    plan_name = PLANS_DATA.get(plan_key, {}).get("name", "نامشخص")
    
    await message.answer("✅ رسید شما با موفقیت دریافت شد. پس از تأیید توسط ادمین، اشتراک شما فعال خواهد شد.")
    
    if ADMIN_ID:
        try:
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=f"🔔 **رسید خرید جدید!**\n\n👤 کاربر: `{message.from_user.id}`\n🆔 یوزرنیم: @{message.from_user.username}\n📦 پلن: {plan_name}"
            )
        except Exception as e:
            logger.error(f"Error sending receipt to admin: {e}")
    
    await state.clear()

@dp.callback_query(F.data == "user_profile")
async def user_profile_handler(callback: CallbackQuery):
    user = callback.from_user
    text = (f"👤 **اطلاعات حساب کاربری:**\n\n"
            f"🆔 آیدی عددی: `{user.id}`\n"
            f" نام کاربری: @{user.username if user.username else 'ندارد'}\n"
            f"📊 وضعیت اشتراک: فاقد اشتراک فعال")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "custom_config")
async def custom_config_handler(callback: CallbackQuery):
    text = "⚙️ برای دریافت کانفیگ سفارشی یا اختصاصی، لطفاً با پشتیبانی در ارتباط باشید."
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data == "help_guide")
async def help_guide_handler(callback: CallbackQuery):
    text = (
        "📚 **راهنمای اتصال و سرویس‌ها:**\n\n"
        "سرویس‌های ما بر بستر پروتکل‌های امن و پرسرعت ارائه می‌شوند:\n"
        "• **L2TP / IPsec** (مناسب برای تمامی دستگاه‌ها)\n"
        "• **PPTP** (اتصال سریع و آسان)\n"
        "• **OpenVPN** (امنیت بالا و پایداری فوق‌العاده)\n\n"
        "برای دریافت فایل‌های اتصال یا راهنمایی بیشتر، از طریق پشتیبانی اقدام کنید."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]])
    await callback.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    is_admin = (str(user_id) == str(ADMIN_ID))
    await callback.message.edit_text("به منوی اصلی برگشتید:", reply_markup=main_menu_keyboard(is_admin))

# ----------------------------------------------------
# 6. وب‌سرور برای Render (Health Check)
# ----------------------------------------------------
async def handle_health_check(request):
    return web.Response(text="Bot is running! ✅")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"🚀 Web server (Health Check) started on port {PORT}")

# ----------------------------------------------------
# 7. اجرای نهایی
# ----------------------------------------------------
async def main():
    await start_web_server()
    logger.info("🤖 Starting bot polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Critical error in polling: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")

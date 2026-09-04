import os
import asyncio
import logging
from aiohttp import web
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== پیکربندی لاگ و توکن‌ها ====================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Mikrotik-Bot")

# خواندن متغیرها از محیط (Environment Variables) یا مقادیر پیش‌فرض
BOT_TOKEN = os.getenv("BOT_TOKEN", "توکن_ربات_شما")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # آیدی عددی ادمین
CARD_INFO = os.getenv("CARD_INFO", "💳 شماره کارت: `6037-9918-0000-0000`\n👤 بنام: مدیریت سرور")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DB_PATH = "bot_database.db"

# ==================== ماشین وضعیت (FSM) ====================
class BotStates(StatesGroup):
    # وضعیت‌های خرید
    waiting_for_buy_receipt = State()
    
    # وضعیت‌های تمدید
    waiting_for_renew_username = State()
    waiting_for_renew_receipt = State()

# ==================== تنظیمات دیتابیس ====================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                has_tested INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# ==================== کیبوردهای شیشه‌ای مدرن ====================
def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 خرید اشتراک جدید", callback_data="btn_buy"),
            InlineKeyboardButton(text="🔄 تمدید اشتراک", callback_data="btn_renew")
        ],
        [
            InlineKeyboardButton(text="🎁 دریافت اکانت تست", callback_data="btn_test"),
            InlineKeyboardButton(text="👤 حساب کاربری من", callback_data="btn_profile")
        ],
        [
            InlineKeyboardButton(text="📚 راهنمای اتصال", callback_data="btn_help"),
            InlineKeyboardButton(text=" پشتیبانی و ارتباط", callback_data="btn_support")
        ]
    ])

def plans_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 ۱ ماهه (نامحدود / ۳۰ روز) - ۱۰۰,۰۰۰ تومان", callback_data="plan_1m")],
        [InlineKeyboardButton(text="🔹 ۲ ماهه (نامحدود / ۶۰ روز) - ۱۸۰,۰۰۰ تومان", callback_data="plan_2m")],
        [InlineKeyboardButton(text="🔹 ۳ ماهه (نامحدود / ۹۰ روز) - ۲۵۰,۰۰۰ تومان", callback_data="plan_3m")],
        [InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data="btn_cancel")]
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف و بازگشت به منو", callback_data="btn_cancel")]
    ])

# ==================== هندلرهای ربات ====================

# شروع ربات
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    
    # ثبت کاربر در دیتابیس
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
            (user.id, user.full_name, user.username)
        )
        await db.commit()

    welcome_text = (
        f"سلام {user.first_name} عزیز! 🌸\n\n"
        "⚡️ به سامانه هوشمند ارائه و تمدید اشتراک‌های **L2TP / Cisco AnyConnect / OpenVPN** خوش آمدید.\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب نمایید:"
    )
    await message.answer(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# دکمه بازگشت / انصراف
@dp.callback_query(F.data == "btn_cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("عملیات لغو شد.")
    await callback.message.edit_text(
        " منوی اصلی سامانه:\nلطفاً یکی از گزینه‌های زیر را انتخاب نمایید:",
        reply_markup=main_menu_keyboard()
    )

# ----------------- فلو تمدید اشتراک -----------------
@dp.callback_query(F.data == "btn_renew")
async def renew_service_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(BotStates.waiting_for_renew_username)
    
    renew_prompt = (
        "🔄 **فرآیند تمدید اشتراک فعال / منقضی‌شده**\n\n"
        " لطفاً **نام کاربری (Username)** اشتراک قبلی خود را ارسال فرمایید تا اطلاعات بررسی و تمدید گردد:"
    )
    await callback.message.edit_text(renew_prompt, reply_markup=cancel_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.waiting_for_renew_username, F.text)
async def process_renew_username(message: types.Message, state: FSMContext):
    username_to_renew = message.text.strip()
    await state.update_data(renew_username=username_to_renew)
    await state.set_state(BotStates.waiting_for_renew_receipt)
    
    payment_text = (
        f"✅ نام کاربری ثبت شده جهت تمدید: `{username_to_renew}`\n\n"
        "💳 **اطلاعات واریز وجه:**\n"
        f"{CARD_INFO}\n\n"
        "📌 مبلغ تمدید: **۱۵۰,۰۰۰ تومان** (۱ ماهه)\n\n"
        "📸 لطفاً پس از انتقال وجه، **تصویر واضح از فیش یا رسید واریز** را در همین صفحه ارسال کنید:"
    )
    await message.answer(payment_text, reply_markup=cancel_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.waiting_for_renew_receipt, F.photo)
async def process_renew_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    renew_user = data.get("renew_username", "نامشخص")
    user = message.from_user
    photo_id = message.photo[-1].file_id

    # پیام گزارش به ادمین
    admin_caption = (
        "🔔 **درخواست جدید تمدید اشتراک**\n\n"
        f"👤 **اکانت جهت تمدید:** `{renew_user}`\n"
        f"🆔 **آیدی عددی تلگرام:** `{user.id}`\n"
        f"👤 **نام تلگرام:** {user.full_name}\n"
        f"🔗 **یوزرنیم تلگرام:** @{user.username or 'ندارد'}\n"
        "────────────────────\n"
        "✅ لطفاً پس از تمدید در میکروتیک، به کاربر اطلاع دهید."
    )
    
    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطا در ارسال به ادمین: {e}")

    await state.clear()
    await message.answer(
        "✅ **فیش واریزی و اطلاعات تمدید شما با موفقیت دریافت و برای پشتیبانی ارسال شد.**\n\n"
        "⏱ سرویس شما پس از بررسی حساب (حداکثر ۱۰ دقیقه) فعال خواهد ماند.\n"
        "از شکیبایی شما سپاسگزاریم! 🌺",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

# ----------------- فلو خرید اشتراک جدید -----------------
@dp.callback_query(F.data == "btn_buy")
async def buy_service_handler(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🛒 **پلن‌های اشتراک پرسرعت:**\n\nلطفاً مدت زمان مورد نظر خود را انتخاب نمایید:",
        reply_markup=plans_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("plan_"))
async def plan_chosen_handler(callback: types.CallbackQuery, state: FSMContext):
    plan = callback.data
    plan_names = {
        "plan_1m": "اشتراک ۱ ماهه (۱۰۰,۰۰۰ تومان)",
        "plan_2m": "اشتراک ۲ ماهه (۱۸۰,۰۰۰ تومان)",
        "plan_3m": "اشتراک ۳ ماهه (۲۵۰,۰۰۰ تومان)"
    }
    selected_plan = plan_names.get(plan, "سرویس عادی")
    await state.update_data(selected_plan=selected_plan)
    await state.set_state(BotStates.waiting_for_buy_receipt)
    
    await callback.answer()
    pay_text = (
        f"📦 **پلن انتخابی شما:** {selected_plan}\n\n"
        "💳 **اطلاعات واریز وجه:**\n"
        f"{CARD_INFO}\n\n"
        " لطفاً پس از واریز مبلغ، **عکس فیش بانکی** خود را ارسال کنید:"
    )
    await callback.message.edit_text(pay_text, reply_markup=cancel_keyboard(), parse_mode="Markdown")

@dp.message(BotStates.waiting_for_buy_receipt, F.photo)
async def process_buy_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("selected_plan", "اشتراک جدید")
    user = message.from_user
    photo_id = message.photo[-1].file_id

    admin_caption = (
        "🔔 **درخواست جدید خرید اشتراک**\n\n"
        f"📦 **پلن درخواستی:** {plan_name}\n"
        f"🆔 **آیدی عددی کاربر:** `{user.id}`\n"
        f"👤 **نام:** {user.full_name}\n"
        f"🔗 **یوزرنیم:** @{user.username or 'ندارد'}"
    )

    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطا در ارسال به ادمین: {e}")

    await state.clear()
    await message.answer(
        "✅ **فیش واریزی برای مدیریت ارسال گردید.**\n\n"
        "پس از بررسی، کانفیگ و اطلاعات اتصال برای شما ارسال خواهد شد.",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

# ----------------- دکمه‌های متفرقه (تست، پروفایل، راهنما و پشتیبانی) -----------------
@dp.callback_query(F.data == "btn_test")
async def free_test_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT has_tested FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == 1:
                await callback.answer("⚠️ شما قبلاً اکانت تست رایگان دریافت کرده‌اید!", show_alert=True)
                return
            
            # علامت‌گذاری دریافت تست
            await db.execute("UPDATE users SET has_tested = 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    test_account_info = (
        "🎁 **اکانت تست رایگان شما (مدت اعتبار: ۱ ساعت)**\n\n"
        "🔐 **پروتکل:** L2TP / Cisco\n"
        "🌐 **آدرس سرور:** `vpn.server.com`\n"
        "👤 **نام کاربری:** `test_user`\n"
        "🔑 **رمز عبور:** `123456`\n"
        "🔑 **سکرت (IPSec Secret):** `123456`\n\n"
        "⚠️ برای خرید اکانت اختصاصی و پرسرعت، از بخش خرید اقدام کنید."
    )
    await callback.message.edit_text(test_account_info, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "btn_profile")
async def profile_handler(callback: types.CallbackQuery):
    user = callback.from_user
    profile_text = (
        "👤 **مشخصات حساب کاربری شما**\n\n"
        f"🏷 **نام:** {user.full_name}\n"
        f"🆔 **شناسه تلگرام:** `{user.id}`\n"
        f"🔗 **یوزرنیم:** @{user.username or 'ندارد'}\n"
        "📡 **وضعیت سرویس:** در انتظار سفارش یا تمدید"
    )
    await callback.message.edit_text(profile_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "btn_help")
async def help_handler(callback: types.CallbackQuery):
    help_text = (
        "📚 **راهنمای اتصال به سرویس‌ها:**\n\n"
        "📱 **اندروید و آیفون:** از نرم‌افزارهای Cisco AnyConnect یا VpnCilla استفاده نمایید.\n"
        "💻 **ویندوز:** در بخش تنظیمات Network & Internet یک کانکشن VPN از نوع L2TP/IPsec با کلید پیش‌مشترک ایجاد کنید.\n\n"
        "در صورت نیاز به راهنمایی بیشتر با پشتیبانی در ارتباط باشید."
    )
    await callback.message.edit_text(help_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "btn_support")
async def support_handler(callback: types.CallbackQuery):
    support_text = (
        " **واحد پشتیبانی و فروش:**\n\n"
        "در صورت بروز هرگونه سوال، قطعی یا مشکل در پرداخت می‌توانید با آیدی زیر در ارتباط باشید:\n"
        "👉 @YourSupportID"
    )
    await callback.message.edit_text(support_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

# ==================== وب‌سرور داخلی برای Render ====================
async def handle_health_check(request):
    return web.Response(text="Mikrotik-Bot is Running Healthy!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Health check web server running on port {port}")

# ==================== تابع اصلی اجرای ربات ====================
async def main():
    await init_db()
    
    # راه‌اندازی وب‌سرور برای پاس کردن تست پورت Render
    await start_webserver()
    
    # پاک کردن وب‌هوک‌های قدیمی برای جلوگیری از Conflict Error
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🚀 Bot is starting polling...")
    
    # شروع دریافت پیام‌ها
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

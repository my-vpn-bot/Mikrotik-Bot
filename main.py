import os
import sys
import logging
import asyncio
import sqlite3
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

# ----------------------------------------------------
# 1. Logging Configuration
# ----------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Mikrotik-Bot")

# ----------------------------------------------------
# 2. Environment Variables & Dynamic Configs
# ----------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    logger.critical("BOT_TOKEN is not defined in environment variables! Exiting...")
    sys.exit(1)

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    ADMIN_ID = 0

PORT = int(os.getenv("PORT", 10000))
DB_PATH = "bot_database.db"

# Channel & Support Links
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "L2TP_Support").strip()

# Financial & Card Information (Read directly from Render Environment Variables)
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9918-0000-0000").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "سجاد رحیمی").strip()

# Plans Prices (Toman)
PLAN1_PRICE = os.getenv("PLAN1_PRICE", "۲۵۰,۰۰۰").strip()
PLAN2_PRICE = os.getenv("PLAN2_PRICE", "۴۰۰,۰۰۰").strip()
PLAN3_PRICE = os.getenv("PLAN3_PRICE", "۶۰۰,۰۰۰").strip()

# ----------------------------------------------------
# 3. Database Initialization
# ----------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TEXT,
            balance INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

init_db()

# ----------------------------------------------------
# 4. Telegram Bot & Dispatcher Setup
# ----------------------------------------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ----------------------------------------------------
# 5. Keyboards (Exact 4-Row UI Standard)
# ----------------------------------------------------
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🛒 خرید اشتراک")
        ],
        [
            KeyboardButton(text="📊 اطلاعات حساب"),
            KeyboardButton(text="💎 اشتراک‌های من")
        ],
        [
            KeyboardButton(text="💰 شارژ حساب"),
            KeyboardButton(text="👥 پشتیبانی")
        ],
        [
            KeyboardButton(text="❓ سوالات متداول"),
            KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)

plans_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=f"🔹 پلن ۱ ماهه نامحدود ({PLAN1_PRICE} تومان)", callback_data="buy_plan_1")],
        [InlineKeyboardButton(text=f"🔹 پلن ۲ ماهه نامحدود ({PLAN2_PRICE} تومان)", callback_data="buy_plan_2")],
        [InlineKeyboardButton(text=f"🔹 پلن ۳ ماهه نامحدود ({PLAN3_PRICE} تومان)", callback_data="buy_plan_3")],
        [InlineKeyboardButton(text="💬 ارتباط با پشتیبانی جهت خرید", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")]
    ]
)

# ----------------------------------------------------
# 6. Handlers
# ----------------------------------------------------
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    user = message.from_user
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, join_date) VALUES (?, ?, ?, ?)",
        (user.id, user.username or "", user.full_name or "", datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()

    welcome_text = (
        f"سلام {user.first_name} عزیز! 👋\n\n"
        "به دنیای سرعت و پایداری خوش آمدید! 🚀 ربات رسمی L2TP VPN با افتخار سرویس‌های اینترنت پرسرعت و نامحدود را برای شما ارائه می‌دهد.\n\n"
        "🌟 ویژگی‌های سرویس اختصاصی:\n"
        "• ⚡️ سرعت و پایداری بالا: بدون افت سرعت، ایده‌آل برای وب‌گردی و گیمینگ\n"
        "• 🛡️ اتصال رمزنگاری‌شده و امن: حفظ کامل حریم خصوصی و امنیت داده‌ها\n"
        "• 🌐 حجم کاملاً نامحدود: بدون محدودیت مصرف در طول دوره اشتراک\n"
        "• 🕒 پشتیبانی ۲۴ ساعته: همراهی مستمر در تمام ساعات شبانه‌روز\n\n"
        f"📢 کانال اطلاع‌رسانی و آموزش: {CHANNEL_URL}\n\n"
        "👇 برای شروع، از منوی زیر گزینه مورد نظر خود را انتخاب کنید:"
    )

    await message.answer(welcome_text, reply_markup=main_keyboard)


@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy(message: types.Message):
    text = (
        "🛍 تعرفه اشتراک‌های پرسرعت و نامحدود L2TP VPN:\n\n"
        f"۱️⃣ پلن ۱ ماهه نامحدود: {PLAN1_PRICE} تومان\n"
        f"۲️⃣ پلن ۲ ماهه نامحدود: {PLAN2_PRICE} تومان\n"
        f"۳️⃣ پلن ۳ ماهه نامحدود: {PLAN3_PRICE} تومان\n\n"
        "🔹 تمامی سرویس‌ها دارای حجم نامحدود، آی‌پی ثابت و پشتیبانی دائمی هستند.\n"
        "👇 لطفاً پلن مورد نظر خود را برای خرید انتخاب کنید:"
    )
    await message.answer(text, reply_markup=plans_inline_keyboard)


@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account_info(message: types.Message):
    user = message.from_user
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, join_date FROM users WHERE user_id = ?", (user.id,))
    row = cursor.fetchone()
    conn.close()

    balance = row[0] if row else 0
    join_date = row[1] if row else datetime.now().strftime("%Y-%m-%d %H:%M")

    text = (
        "📊 مشخصات و اطلاعات حساب کاربری شما:\n\n"
        f"👤 شناسه عددی: {user.id}\n"
        f"🏷 نام کاربری: @{user.username if user.username else 'تعیین نشده'}\n"
        f"💰 موجودی کیف پول: {balance:,} تومان\n"
        f"📅 تاریخ عضویت: {join_date}\n"
        "-------------------------------\n"
        "وضعیت سرویس: 🟢 فعال"
    )
    await message.answer(text)


@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: types.Message):
    text = (
        "💎 لیست سرویس‌های فعال شما:\n\n"
        "در حال حاضر سرویس فعالی برای شما ثبت نشده است.\n"
        "برای تهیه سرویس اختصاصی می‌توانید از بخش «🛒 خرید اشتراک» اقدام نمایید."
    )
    await message.answer(text)


@dp.message(F.text == "💰 شارژ حساب")
async def handle_wallet_charge(message: types.Message):
    clean_support = SUPPORT_USERNAME.replace('@', '')
    card_no = os.getenv("CARD_NUMBER", CARD_NUMBER)
    card_name = os.getenv("CARD_HOLDER", CARD_HOLDER)

    text = (
        "💳 افزایش موجودی و شارژ کیف پول:\n\n"
        "لطفاً مبلغ مورد نظر را به شماره کارت زیر واریز نمایید:\n\n"
        f"💳 شماره کارت:\n`{card_no}`\n"
        f"👤 به نام: {card_name}\n\n"
        "⚠️ توجه: پس از واریز، لطفاً تصویر فیش واریزی را به همراه شناسه کاربری خود برای پشتیبانی ارسال نمایید تا موجودی شما شارژ شود."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧾 ارسال فیش به پشتیبانی", url=f"https://t.me/{clean_support}")]
        ]
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: types.Message):
    clean_support = SUPPORT_USERNAME.replace('@', '')
    text = (
        "👥 مرکز پشتیبانی و ارتباط با کارشناسان:\n\n"
        "تیم پشتیبانی به صورت ۲۴ ساعته آماده پاسخگویی به سوالات، حل مشکلات فنی و ارائه راهنمایی می‌باشد.\n\n"
        f"🆔 آیدی پشتیبان: @{clean_support}\n"
        f"📢 کانال اطلاع‌رسانی: {CHANNEL_URL}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 ارسال پیام به پشتیبانی", url=f"https://t.me/{clean_support}")],
            [InlineKeyboardButton(text="📢 عضویت در کانال", url=CHANNEL_URL)]
        ]
    )
    await message.answer(text, reply_markup=keyboard)


@dp.message(F.text == "❓ سوالات متداول")
async def handle_faq(message: types.Message):
    text = (
        "❓ سوالات متداول کاربران:\n\n"
        "۱. سرویس L2TP روی چه سیستم‌عامل‌هایی کار می‌کند؟\n"
        "پاسخ: این پروتکل به صورت پیش‌فرض و نیتیو بر روی اندروید، iOS، ویندوز و مکینتاش بدون نیاز به نرم‌افزارهای سنگین قابل تنظیم است.\n\n"
        "۲. آیا سرویس‌ها محدودیت حجم دارند؟\n"
        "پاسخ: خیر، تمامی پلن‌های ارائه شده با پهنای باند و حجم کاملاً نامحدود هستند.\n\n"
        "۳. نحوه تحویل اکانت چگونه است؟\n"
        "پاسخ: بلافاصله پس از پرداخت و ارسال رسید به پشتیبانی، مشخصات اتصال برای شما ارسال می‌گردد."
    )
    await message.answer(text)


@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs_and_tutorials(message: types.Message):
    text = (
        "⚙️ آموزش اتصال و تنظیمات کانفیگ:\n\n"
        "آموزش‌های گام‌به‌گام اتصال برای تمامی دستگاه‌ها به همراه فایل‌ها و سرورهای جدید در کانال رسمی قرار گرفته است.\n\n"
        f"جهت مشاهده آموزش تصویری به کانال زیر مراجعه کنید:\n"
        f"🔗 {CHANNEL_URL}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 ورود به کانال آموزش‌ها", url=CHANNEL_URL)]
        ]
    )
    await message.answer(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("buy_plan_"))
async def handle_plan_callbacks(callback: CallbackQuery):
    plan_id = callback.data.split("_")[-1]
    plan_details = {
        "1": {"name": "۱ ماهه نامحدود", "price": f"{PLAN1_PRICE} تومان"},
        "2": {"name": "۲ ماهه نامحدود", "price": f"{PLAN2_PRICE} تومان"},
        "3": {"name": "۳ ماهه نامحدود", "price": f"{PLAN3_PRICE} تومان"}
    }
    selected = plan_details.get(plan_id, {"name": "سرویس انتخابی", "price": "تعیین نشده"})
    clean_support = SUPPORT_USERNAME.replace('@', '')
    card_no = os.getenv("CARD_NUMBER", CARD_NUMBER)
    card_name = os.getenv("CARD_HOLDER", CARD_HOLDER)

    await callback.answer()
    text = (
        f"🛒 پیش‌فاکتور خرید:\n"
        f"🔹 پلن انتخابی: {selected['name']}\n"
        f"💰 مبلغ قابل پرداخت: {selected['price']}\n\n"
        f"💳 مشخصات واریز کارت‌به‌کارت:\n"
        f"شماره کارت:\n`{card_no}`\n"
        f"به نام: {card_name}\n\n"
        "📌 پس از واریز، تصویر رسید یا فیش پرداختی را از طریق دکمه زیر برای پشتیبانی ارسال کنید تا اشتراک شما آنی فعال گردد:"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧾 ارسال رسید پرداخت به پشتیبانی", url=f"https://t.me/{clean_support}")]
        ]
    )
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

# ----------------------------------------------------
# 7. Web Server for Render Health Check (Port Binding)
# ----------------------------------------------------
async def health_check(request):
    return web.Response(text="Mikrotik-Bot is healthy and running!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check web server is listening on port {PORT}")

# ----------------------------------------------------
# 8. Main Entrypoint
# ----------------------------------------------------
async def main():
    logger.info("🚀 Launching Mikrotik-Bot...")
    # Start web server to satisfy Render's port detection
    await start_web_server()
    
    # Drop pending updates and clean leftover webhooks to prevent conflicts
    logger.info("🧹 Clearing previous webhooks and pending updates...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start polling
    logger.info("🤖 Starting Telegram Dispatcher polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped gracefully.")

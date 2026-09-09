import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# تنظیمات لاگ
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# دریافت تنظیمات از رندر
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SUPPORT_ID = os.getenv("SUPPORT_ID", "al2tpiSupport")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "")
PORT = int(os.getenv("PORT", 10000))

# تنظیم نام کاربری پشتیبانی با علامت @
if SUPPORT_ID and not SUPPORT_ID.startswith("@"):
    SUPPORT_USERNAME = f"@{SUPPORT_ID}"
else:
    SUPPORT_USERNAME = SUPPORT_ID

if not BOT_TOKEN:
    logger.error("BOT_TOKEN یافت نشد!")
    raise SystemExit("BOT_TOKEN is not set in environment variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# کیبورد اصلی
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_sub"),
            InlineKeyboardButton(text="👤 حساب کاربری", callback_data="my_account")
        ],
        [
            InlineKeyboardButton(text="🛠 پشتیبانی", callback_data="support"),
            InlineKeyboardButton(text="📋 تعرفه‌ها", callback_data="tariffs")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# کیبورد بازگشت
def get_back_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# شروع ربات
@dp.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        f"👋 سلام {message.from_user.first_name} عزیز!\n\n"
        "به ربات مدیریت و خرید سرویس خوش آمدید.\n"
        "از دکمه‌های زیر جهت ثبت سفارش یا مدیریت اکانت استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

# مدیریت کلیک روی دکمه‌ها
@dp.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "منوی اصلی ربات:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "tariffs")
async def process_tariffs(callback: CallbackQuery):
    tariffs_text = (
        "📋 **لیست پلن‌ها و تعرفه‌ها:**\n\n"
        "🔹 **پلن ۱ ماهه:** ۳۰ روزه - ۳۰ گیگابایت\n"
        "🔹 **پلن ۲ ماهه:** ۶۰ روزه - ۶۰ گیگابایت\n"
        "🔹 **پلن ۳ ماهه:** ۹۰ روزه - ۱۰۰ گیگابایت\n\n"
        "جهت سفارش و پرداخت، گزینه «خرید اشتراک» را انتخاب کنید."
    )
    await callback.message.edit_text(tariffs_text, parse_mode="Markdown", reply_markup=get_back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "buy_sub")
async def process_buy(callback: CallbackQuery):
    payment_info = (
        "💳 **اطلاعات پرداخت و خرید اشتراک:**\n\n"
        f"🔹 **شماره کارت:**\n`{PAYMENT_CARD}`\n\n"
        f"🔹 **به نام:** {PAYMENT_NAME}\n\n"
        "⚠️ **مراحل پس از واریز:**\n"
        f"۱. تصویر رسید تراکنش را ذخیره کنید.\n"
        f"۲. رسید را به پشتیبانی ارسال نمایید: {SUPPORT_USERNAME}\n"
        "۳. کانفیگ سرویس پس از بررسی برای شما صادر خواهد شد."
    )
    await callback.message.edit_text(payment_info, parse_mode="Markdown", reply_markup=get_back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "my_account")
async def process_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = f"@{callback.from_user.username}" if callback.from_user.username else "ثبت نشده"
    
    account_text = (
        "👤 **مشخصات کاربری شما:**\n\n"
        f"🆔 شناسه عددی: `{user_id}`\n"
        f"👤 نام کاربری: {username}\n"
        "📊 وضعیت اشتراک: بدون سرویس فعال\n\n"
        "برای خرید اشتراک جدید از منوی خرید اقدام فرمایید."
    )
    await callback.message.edit_text(account_text, parse_mode="Markdown", reply_markup=get_back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "support")
async def process_support(callback: CallbackQuery):
    support_text = (
        "🛠 **واحد پشتیبانی و ارتباط با ما:**\n\n"
        "برای پیگیری سفارشات، ارسال فیش واریزی و پاسخ به سوالات فنی:\n\n"
        f"🔗 آیدی تلگرام: {SUPPORT_USERNAME}"
    )
    await callback.message.edit_text(support_text, reply_markup=get_back_keyboard())
    await callback.answer()

# وب‌سرور داخلی برای Render (Health Check)
async def handle_ping(request):
    return web.Response(text="Bot is running smoothly!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

# تابع اصلی اجرای ربات
async def main():
    logger.info("Initializing Mikrotik-Bot...")
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution terminated.")

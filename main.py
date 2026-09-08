import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, CallbackQuery, Message

# ۱. تنظیمات لاگینگ برای دیدن جزئیات در Render Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ۲. دریافت متغیرهای محیطی (Environment Variables) از Render
# اگر متغیری در رندر تعریف نشده باشد، مقدار پیش‌فرض (بعد از علامت =) قرار می‌گیرد
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@Support_User")
CARD_NUMBER = os.getenv("PAYMENT_CARD", "0000-0000-0000-0000")
HOLDER_NAME = os.getenv("PAYMENT_NAME", "نام صاحب کارت")
PLAN_PRICE = os.getenv("PLAN_PRICE", "350,000")
PLAN_DURATION = os.getenv("PLAN_DURATION", "30")
PLAN_DATA = os.getenv("PLAN_DATA", "30")

# بررسی وجود توکن (بسیار حیاتی برای جلوگیری از کرش)
if not BOT_TOKEN:
    logger.error("خطا: BOT_TOKEN در متغیرهای محیطی یافت نشد!")
    raise SystemExit("BOT_TOKEN is missing!")

# ۳. مقداردهی اولیه بات و دیسپچر
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ۴. توابع کمکی برای ساخت کیبورد (Inline Menu)
def get_main_menu() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_sub"))
    builder.row(InlineKeyboardButton(text="👤 حساب کاربری", callback_data="my_account"))
    builder.row(InlineKeyboardButton(text="🛠 پشتیبانی", callback_data="support"))
    return builder.as_markup()

# ۵. هندلر دستور /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        "👋 سلام! به پنل مدیریت Mikrotik-Bot خوش آمدید.\n\n"
        "لطفاً از منوی زیر برای مدیریت خدمات خود استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

# ۶. هندلر خرید اشتراک (نمایش اطلاعات از ENV)
@dp.callback_query(F.data == "buy_sub")
async def process_buy_sub(callback: CallbackQuery):
    text = (
        "💎 **پلن پیشنهادی ما:**\n\n"
        f"🔹 مدت اعتبار: {PLAN_DURATION} روز\n"
        f"🔹 حجم داده: {PLAN_DATA} گیگابایت\n"
        f"🔹 قیمت: {PLAN_PRICE} تومان\n\n"
        f"💳 **اطلاعات پرداخت:**\n"
        f"شماره کارت: `{CARD_NUMBER}`\n"
        f"به نام: `{HOLDER_NAME}`\n\n"
        "⚠️ پس از واریز، رسید خود را برای پشتیبانی ارسال کنید."
    )
    # استفاده از Markdown برای نمایش بهتر شماره کارت
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_menu())
    await callback.answer()

# ۷. هندلر حساب کاربری (نمونه)
@dp.callback_query(F.data == "my_account")
async def process_my_account(callback: CallbackQuery):
    text = (
        "👤 **اطلاعات حساب کاربری شما:**\n\n"
        "وضعیت: فعال ✅\n"
        "تاریخ انقضا: مشخص نیست (لطفاً با پشتیبانی تماس بگیرید)\n"
        "حجم باقی‌مانده: - GB"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_menu())
    await callback.answer()

# ۸. هندلر پشتیبانی
@dp.callback_query(F.data == "support")
async def process_support(callback: CallbackQuery):
    text = (
        "🛠 **بخش پشتیبانی فنی**\n\n"
        f"برای دریافت راهنمایی و رفع مشکلات، با آیدی زیر در ارتباط باشید:\n\n"
        f"🆔 `{SUPPORT_ID}`\n\n"
        "ما در خدمت شما هستیم."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_menu())
    await callback.answer()

# ۹. تابع اصلی برای اجرای بات (با مدیریت خطا)
async def main():
    logger.info("--- Mikrotik-Bot is starting ---")
    try:
        # شروع به کار بات
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Critical Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    # استفاده از asyncio برای اجرای ایزنکرونوس
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

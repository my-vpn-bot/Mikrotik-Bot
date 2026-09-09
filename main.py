import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramConflictError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# متغیرهای محیطی
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SUPPORT_ID = os.getenv("SUPPORT_ID", "al2tpiSupport")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338994607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", 10000))

if SUPPORT_ID and not SUPPORT_ID.startswith("@"):
    SUPPORT_USERNAME = f"@{SUPPORT_ID}"
else:
    SUPPORT_USERNAME = SUPPORT_ID

if not BOT_TOKEN:
    raise SystemExit("Error: BOT_TOKEN is not set in Environment Variables!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ─── اطلاعات پلن‌ها ───
PLANS = {
    "plan_1m": {"title": "🥉 پلن ۱ ماهه", "volume": "۳۰ گیگابایت", "days": "۳۰ روز", "price": "۳۵۰,۰۰۰ تومان"},
    "plan_2m": {"title": "🥈 پلن ۲ ماهه", "volume": "۶۰ گیگابایت", "days": "۶۰ روز", "price": "۶۵۰,۰۰۰ تومان"},
    "plan_3m": {"title": "🥇 پلن ۳ ماهه", "volume": "۹۰ گیگابایت", "days": "۹۰ روز", "price": "۹۰۰,۰۰۰ تومان"},
}

# ─── کیبوردها ───
def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_sub"),
         InlineKeyboardButton(text="💎 تعرفه‌ها", callback_data="tariffs")],
        [InlineKeyboardButton(text="👤 حساب کاربری", callback_data="my_account"),
         InlineKeyboardButton(text="🎁 تست رایگان", callback_data="free_test")],
        [InlineKeyboardButton(text="🛠 پشتیبانی", callback_data="support")],
    ])

def kb_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])

def kb_plans():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥉 ۱ ماهه | ۳۰ گیگ | ۳۵۰ ت", callback_data="plan_1m")],
        [InlineKeyboardButton(text="🥈 ۲ ماهه | ۶۰ گیگ | ۶۵۰ ت", callback_data="plan_2m")],
        [InlineKeyboardButton(text="🥇 ۳ ماهه | ۹۰ گیگ | ۹۰۰ ت", callback_data="plan_3m")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")],
    ])

def kb_pay():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 ارسال فیش به پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="🔙 بازگشت به پلن‌ها", callback_data="buy_sub")],
    ])

# ─── هندلرها ───
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"👋 سلام **{message.from_user.first_name}** عزیز به ربات خوش اومدی!\n\n"
        "⚡ سرویس‌های پرسرعت و پایدار **L2TP VPN**\n"
        "برای خرید یا دریافت تست، از منوی زیر استفاده کنید:",
        parse_mode="Markdown",
        reply_markup=kb_main()
    )

@dp.callback_query(F.data == "main_menu")
async def cb_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 **منوی اصلی:**\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=kb_main()
    )
    await callback.answer()

@dp.callback_query(F.data == "tariffs")
async def cb_tariffs(callback: CallbackQuery):
    text = (
        "💎 **تعرفه‌های اشتراک اختصاصی:**\n\n"
        "🥉 **پلن ۱ ماهه:** ۳۰ گیگابایت ⬅️ `۳۵۰,۰۰۰ تومان`\n\n"
        "🥈 **پلن ۲ ماهه:** ۶۰ گیگابایت ⬅️ `۶۵۰,۰۰۰ تومان`\n\n"
        "🥇 **پلن ۳ ماهه:** ۹۰ گیگابایت ⬅️ `۹۰۰,۰۰۰ تومان`\n\n"
        "🚀 پورت پرسرعت اختصاصی | بدون قطعی"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_plans())
    await callback.answer()

@dp.callback_query(F.data == "buy_sub")
async def cb_buy(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛒 **پلن مورد نظر خود را برای خرید انتخاب کنید:**",
        parse_mode="Markdown",
        reply_markup=kb_plans()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("plan_"))
async def cb_plan(callback: CallbackQuery):
    plan = PLANS.get(callback.data)
    if not plan:
        await callback.answer("پلن یافت نشد!", show_alert=True)
        return
    text = (
        f"📋 **جزئیات سفارش:**\n"
        f"🔹 عنوان: **{plan['title']}**\n"
        f"📦 حجم: **{plan['volume']}**\n"
        f"⏳ مدت اعتبار: **{plan['days']}**\n"
        f"💰 مبلغ قابل پرداخت: **{plan['price']}**\n\n"
        f"💳 **اطلاعات حساب و واریز:**\n"
        f"شماره کارت: `{PAYMENT_CARD}` (لمس برای کپی)\n"
        f"به نام: **{PAYMENT_NAME}**\n\n"
        "⚠️ لطفاً پس از انتقال وجه، تصویر رسید را با زدن دکمه‌ی زیر برای پشتیبانی ارسال کنید."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_pay())
    await callback.answer()

@dp.callback_query(F.data == "my_account")
async def cb_account(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else "ثبت نشده"
    await callback.message.edit_text(
        "👤 **اطلاعات حساب کاربری شما:**\n\n"
        f"🆔 شناسه کاربری: `{callback.from_user.id}`\n"
        f"👤 نام کاربری: {username}\n"
        f"📊 سرویس فعال: **ندارید**\n\n"
        "جهت خرید سرویس از منوی خرید اشتراک اقدام فرمایید.",
        parse_mode="Markdown",
        reply_markup=kb_back()
    )
    await callback.answer()

@dp.callback_query(F.data == "free_test")
async def cb_free(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎁 **تست رایگان سرویس:**\n\n"
        "جهت دریافت اکانت تست رایگان ۲۴ ساعته، به آیدی پشتیبانی پیام دهید:\n\n"
        f"🆔 {SUPPORT_USERNAME}",
        parse_mode="Markdown",
        reply_markup=kb_back()
    )
    await callback.answer()

@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛠 **واحد پشتیبانی و فروش:**\n\n"
        "پاسخگویی به سوالات، تمدید و تحویل سفارشات:\n\n"
        f"🆔 آیدی تلگرام: {SUPPORT_USERNAME}",
        parse_mode="Markdown",
        reply_markup=kb_back()
    )
    await callback.answer()

# ─── وب‌سرور داخلی برای Render (Health Check) ───
async def handle_ping(request):
    return web.Response(text="Bot is running happily!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health-check web server started on port {PORT}")

# ─── اجرای ربات ───
async def main():
    await start_web_server()
    
    # حذف وب‌هوک و پاکسازی تمام پیام‌های در صف
    logger.info("Dropping pending updates & deleting webhook...")
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(2)  # وقفه کوتاه برای آزادسازی کامل اتصال‌های قبلی
    
    logger.info("Starting Polling loop...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramConflictError:
        logger.error("Conflict detected! Another instance is still alive. Waiting...")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass

import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# متغیرهای محیطی رندر
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SUPPORT_ID = os.getenv("SUPPORT_ID", "al2tpiSupport")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "")
PORT = int(os.getenv("PORT", 10000))

if SUPPORT_ID and not SUPPORT_ID.startswith("@"):
    SUPPORT_USERNAME = f"@{SUPPORT_ID}"
else:
    SUPPORT_USERNAME = SUPPORT_ID

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN is not set.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ─── پلن‌ها ───
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
        [InlineKeyboardButton(text="🥉 ۱ ماهه | ۳۰ گیگ | ۳۵۰ هزار", callback_data="plan_1m")],
        [InlineKeyboardButton(text="🥈 ۲ ماهه | ۶۰ گیگ | ۶۵۰ هزار", callback_data="plan_2m")],
        [InlineKeyboardButton(text="🥇 ۳ ماهه | ۹۰ گیگ | ۹۰۰ هزار", callback_data="plan_3m")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu")],
    ])

def kb_pay(plan_key):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 ارسال رسید به پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="🔙 بازگشت به پلن‌ها", callback_data="buy_sub")],
    ])

# ─── هندلرها ───
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"👋 سلام {message.from_user.first_name} عزیز!\n\n"
        "⚡ به فروشگاه سرویس **L2TP VPN** خوش اومدی.\n\n"
        "🚀 اینترنت آزاد، پرسرعت و پایدار با پشتیبانی ۲۴/۷\n"
        "برای شروع یکی از گزینه‌های زیر رو انتخاب کن:",
        parse_mode="Markdown",
        reply_markup=kb_main()
    )

@dp.callback_query(F.data == "main_menu")
async def cb_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 **منوی اصلی**\n\nیکی از گزینه‌ها رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=kb_main())
    await callback.answer()

@dp.callback_query(F.data == "tariffs")
async def cb_tariffs(callback: CallbackQuery):
    text = (
        "💎 **تعرفه‌های سرویس:**\n\n"
        "🥉 **پلن ۱ ماهه** — ۳۰ روز | ۳۰ گیگابایت\n"
        "💰 قیمت: `۳۵۰,۰۰۰ تومان`\n\n"
        "🥈 **پلن ۲ ماهه** — ۶۰ روز | ۶۰ گیگابایت\n"
        "💰 قیمت: `۶۵۰,۰۰۰ تومان` (۱۵٪ مقرون‌به‌صرفه‌تر)\n\n"
        "🥇 **پلن ۳ ماهه** — ۹۰ روز | ۹۰ گیگابایت\n"
        "💰 قیمت: `۹۰۰,۰۰۰ تومان` ⭐ پرفروش‌ترین\n\n"
        "✅ کیفیت خط ۱ گیگابیت | ✅ پشتیبانی ۲۴/۷ | ✅ تحویل آنی"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_plans())
    await callback.answer()

@dp.callback_query(F.data == "buy_sub")
async def cb_buy(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛒 **خرید اشتراک**\n\nپلن موردنظرت رو انتخاب کن:",
        parse_mode="Markdown", reply_markup=kb_plans())
    await callback.answer()

@dp.callback_query(F.data.startswith("plan_"))
async def cb_plan(callback: CallbackQuery):
    plan = PLANS.get(callback.data)
    if not plan:
        await callback.answer("پلن یافت نشد!", show_alert=True)
        return
    text = (
        f"{plan['title']}\n\n"
        f"📦 حجم: **{plan['volume']}**\n"
        f"⏳ مدت: **{plan['days']}**\n"
        f"💰 قیمت: **{plan['price']}**\n\n"
        f"💳 **پرداخت به کارت زیر:**\n"
        f"➖➖➖➖➖➖➖➖➖\n"
        f"`{PAYMENT_CARD}`\n"
        f"👤 به نام: **{PAYMENT_NAME}**\n"
        f"➖➖➖➖➖➖➖➖➖\n\n"
        "📝 پس از واریز، رسید رو برای پشتیبانی بفرست تا کانفیگ ظرف چند دقیقه تحویل داده بشه."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_pay(callback.data))
    await callback.answer()

@dp.callback_query(F.data == "my_account")
async def cb_account(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else "ندارد"
    await callback.message.edit_text(
        "👤 **حساب کاربری شما:**\n\n"
        f"🆔 شناسه: `{callback.from_user.id}`\n"
        f"👤 یوزرنیم: {username}\n"
        f"📊 اشتراک فعال: ندارد\n\n"
        "برای خرید، از دکمه‌ی «🛒 خرید اشتراک» استفاده کن.",
        parse_mode="Markdown", reply_markup=kb_back())
    await callback.answer()

@dp.callback_query(F.data == "free_test")
async def cb_free(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎁 **تست رایگان ۱ گیگابایت**\n\n"
        "برای دریافت کانفیگ تست، به پشتیبانی پیام بده:\n"
        f"🔗 {SUPPORT_USERNAME}",
        parse_mode="Markdown", reply_markup=kb_back())
    await callback.answer()

@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛠 **پشتیبانی ۲۴/۷**\n\n"
        "برای پیگیری سفارش، ارسال رسید یا رفع مشکل فنی:\n"
        f"🔗 آیدی پشتیبانی: {SUPPORT_USERNAME}\n\n"
        "⏱ میانگین پاسخ‌گویی: کمتر از ۱۰ دقیقه",
        parse_mode="Markdown", reply_markup=kb_back())
    await callback.answer()

# ─── وب‌سرور Health Check ───
async def handle_ping(request):
    return web.Response(text="Bot is alive!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"Web server on port {PORT}")

async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass

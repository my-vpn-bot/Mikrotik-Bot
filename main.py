import os
import asyncio
import logging
from datetime import datetime
import zoneinfo
import jdatetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramConflictError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_ID = os.getenv("SUPPORT_ID", "al2tpiSupport")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338994607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", 10000))

SUPPORT_USERNAME = f"@{SUPPORT_ID}" if SUPPORT_ID and not SUPPORT_ID.startswith("@") else SUPPORT_ID

if not BOT_TOKEN:
    raise SystemExit("Error: BOT_TOKEN is not set in Environment Variables!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Plan Definitions ---
PLANS = {
    "plan_1m": {"title": "🥇 پلن ۱ ماهه", "volume": "۳۰ گیگ", "days": "۳۰ روز", "price": "۳۵۰,۰۰۰ تومان", "color": "🟡"},
    "plan_2m": {"title": "🥈 پلن ۲ ماهه", "volume": "۶۰ گیگ", "days": "۶۰ روز", "price": "۶۵۰,۰۰۰ تومان", "color": "🟠"},
    "plan_3m": {"title": "🥉 پلن ۳ ماهه", "volume": "۹۰ گیگ", "days": "۹۰ روز", "price": "۹۰۰,۰۰۰ تومان", "color": "🟢"},
}

# --- Helper: Tehran Persian Date & Time ---
def get_time_header():
    tehran_tz = zoneinfo.ZoneInfo("Asia/Tehran")
    now_tehran = datetime.now(tehran_tz)
    jalali_datetime = jdatetime.datetime.fromgregorian(datetime=now_tehran)
    return jalali_datetime.strftime("📅 %Y/%m/%d — ⏰ %H:%M")

# --- Keyboards (حرفه‌ای و با دکمه‌های بزرگ) ---
def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک\n💎 مشاهده تعرفه‌ها", callback_data="buy_sub")],
        [InlineKeyboardButton(text="🔮 سرویس‌های آینده\n🌐 L2TP | OpenVPN | WireGuard", callback_data="future_services")],
        [InlineKeyboardButton(text="👤 حساب کاربری من\n📊 وضعیت و مشخصات", callback_data="my_account")],
        [InlineKeyboardButton(text="🛠 پشتیبانی\n💬 پاسخگویی ۲۴/۷", callback_data="support")]
    ])

def kb_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی\n🏠 صفحه اول", callback_data="main_menu")]
    ])

def kb_plans():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥇 پلن ۱ ماهه\n📦 ۳۰ گیگ | 💰 ۳۵۰,۰۰۰ تومان", callback_data="plan_1m")],
        [InlineKeyboardButton(text="🥈 پلن ۲ ماهه\n📦 ۶۰ گیگ | 💰 ۶۵۰,۰۰۰ تومان", callback_data="plan_2m")],
        [InlineKeyboardButton(text="🥉 پلن ۳ ماهه\n📦 ۹۰ گیگ | 💰 ۹۰۰,۰۰۰ تومان", callback_data="plan_3m")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی\n🏠 صفحه اول", callback_data="main_menu")]
    ])

def kb_pay():
    clean_username = SUPPORT_USERNAME.lstrip("@")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 ارسال فیش به پشتیبانی\n💬 برای تمدید و فعال‌سازی سرویس", url=f"https://t.me/{clean_username}")],
        [InlineKeyboardButton(text="🔙 بازگشت به تعرفه‌ها\n💎 نمایش سایر پلن‌ها", callback_data="buy_sub")]
    ])

# --- Handlers ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        f"👋 سلام **{message.from_user.first_name}** عزیز!\n\n"
        "⚡ سرویس‌های پرسرعت و پایدار **V2Ray**\n"
        f"{get_time_header()}\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید 👇"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=kb_main())

@dp.callback_query(F.data == "main_menu")
async def cb_main(callback: CallbackQuery):
    text = (
        f"🏠 **منوی اصلی**\n"
        f"{get_time_header()}\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید 👇"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_main())
    await callback.answer()

@dp.callback_query(F.data == "buy_sub")
async def cb_buy(callback: CallbackQuery):
    plan_list = "\n".join([
        f"{p['color']} **{p['title']}**\n📦 حجم: **{p['volume']}** | ⏳ **{p['days']}** | 💰 `{p['price']}`\n"
        for p in PLANS.values()
    ])
    text = (
        "💎 **تعرفه‌های اشتراک (سرویس V2Ray):**\n\n"
        f"{plan_list}\n"
        "🚀 پورت پرسرعت اختصاصی | بدون قطعی\n"
        "👇 پلن مورد نظرتیرا انتخاب کن:"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_plans())
    await callback.answer()

@dp.callback_query(F.data == "future_services")
async def cb_future_services(callback: CallbackQuery):
    text = (
        "🔮 **سرویس‌های آینده:**\n\n"
        "به‌زودی و تا چند روز آینده سرویس‌های زیر نیز راه‌اندازی و در دسترس شما عزیزان قرار خواهد گرفت:\n\n"
        "🌐 **L2TP / IPsec** — پرسرعت و پایدار\n"
        "🌐 **OpenVPN** — امن و انعطاف‌پذیر\n"
        "🌐 **WireGuard** — مدرن و سبک\n"
        "🌐 **و سایر پروتکل‌های محبوب**\n\n"
        "⚡ برای اطلاع از زمان دقیق فعال‌سازی، با پشتیبانی در ارتباط باشید."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_back())
    await callback.answer()

@dp.callback_query(F.data.startswith("plan_"))
async def cb_plan(callback: CallbackQuery):
    plan = PLANS.get(callback.data)
    if not plan:
        await callback.answer("پلن یافت نشد!", show_alert=True)
        return
    text = (
        f"🎯 **جزئیات سفارش (V2Ray):**\n\n"
        f"{plan['color']} **{plan['title']}**\n"
        f"📦 حجم: **{plan['volume']}**\n"
        f"⏳ مدت اعتبار: **{plan['days']}**\n"
        f"💰 مبلغ قابل پرداخت: **{plan['price']}**\n\n"
        "💳 **اطلاعات حساب و واریز:**\n"
        f"شماره کارت: `{PAYMENT_CARD}`\n"
        f"به نام: **{PAYMENT_NAME}**\n\n"
        "⚠️ لطفاً پس از انتقال وجه، تصویر رسید را با زدن دکمه، برای پشتیبانی ارسال کنید."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_pay())
    await callback.answer()

@dp.callback_query(F.data == "my_account")
async def cb_account(callback: CallbackQuery):
    username = f"@{callback.from_user.username}" if callback.from_user.username else "ثبت نشده"
    text = (
        "👤 **اطلاعات حساب کاربری شما:**\n\n"
        f"🆔 شناسه کاربری: `{callback.from_user.id}`\n"
        f"👤 نام کاربری: {username}\n"
        f"📊 سرویس فعال: **ندارید**\n\n"
        "به‌زودی قابلیت اتصال اکانت به سرویس هم اضافه خواهد شد. جهت خرید از منوی خرید اشتراک اقدام فرمایید."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_back())
    await callback.answer()

@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    text = (
        "🛠 **واحد پشتیبانی و فروش:**\n\n"
        "پاسخگویی به سوالات، تمدید و تحویل سفارشات:\n\n"
        f"🆔 آیدی تلگرام: {SUPPORT_USERNAME}"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb_back())
    await callback.answer()

# --- Internal Web Server (Render Port Binding) ---
async def handle_ping(request):
    return web.Response(text="Bot is running happily!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = Port Binding) ---
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
    logger.info(f"Health-check web server started on port_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramConflictError:
        logger.error("Conflict detected! Another instance might still be running. Waiting...")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        await bot.session.close()
        logger.info("Bot session closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")

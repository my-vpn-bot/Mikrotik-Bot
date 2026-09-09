import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

logging.basicConfig(level=logging.INFO)

# --- متغیرهای محیطی (بدون تغییر و دقیقا طبق تنظیمات شما) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "6278859256")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338994607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "")
SUPPORT_ID = os.getenv("SUPPORT_ID", "aL2tp1Support")
PORT = int(os.getenv("PORT", 10000))

# قیمت‌های مصوب
PLAN1_PRICE = os.getenv("PLAN1_PRICE", "250,000 تومان")
PLAN2_PRICE = os.getenv("PLAN2_PRICE", "400,000 تومان")
PLAN3_PRICE = os.getenv("PLAN3_PRICE", "600,000 تومان")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- کیبورد اصلی (دقیقا منوی درخواستی بدون تست رایگان و زیرمجموعه‌گیری) ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("به روبات فروش قند شکن خوش امدید", reply_markup=main_kb)

@dp.message(F.text == "🛒 خرید اشتراک")
async def buy_plan(message: types.Message):
    plans_text = (
        "🛍 **پلن‌های موجود:**\n\n"
        f"🔹 پلن ۱ ماهه: {PLAN1_PRICE}\n"
        f"🔹 پلن ۲ ماهه: {PLAN2_PRICE}\n"
        f"🔹 پلن ۳ ماهه: {PLAN3_PRICE}\n\n"
        f"💳 شماره کارت جهت واریز:\n`{PAYMENT_CARD}`\n"
        f"👤 بنام: {PAYMENT_NAME}\n\n"
        f"پس از واریز، تصویر فیش را به پشتیبانی (@{SUPPORT_ID}) ارسال کنید."
    )
    await message.answer(plans_text, parse_mode="Markdown")

@dp.message(F.text == "👥 پشتیبانی")
async def support(message: types.Message):
    await message.answer(f"جهت ارتباط با پشتیبانی به آیدی زیر پیام دهید:\n@{SUPPORT_ID}")

@dp.message(F.text == "❓ سوالات متداول")
async def faq(message: types.Message):
    faq_text = (
        "❓ **سوالات متداول:**\n\n"
        "۱. تحویل اشتراک چقدر زمان می‌برد؟\n"
        "بلافاصله پس از تایید فیش واریزی توسط ادمین.\n\n"
        "۲. روی چه دستگاه‌هایی قابل استفاده است؟\n"
        "تمامی سیستم‌عامل‌های اندروید، iOS، ویندوز و مک."
    )
    await message.answer(faq_text, parse_mode="Markdown")

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def tutorial(message: types.Message):
    await message.answer("آموزش‌های اتصال و برنامه‌های مورد نیاز به زودی در این بخش قرار می‌گیرند.")

@dp.message(F.text == "📊 اطلاعات حساب")
async def account_info(message: types.Message):
    user = message.from_user
    await message.answer(f"👤 نام: {user.full_name}\n🆔 شناسه کاربری: `{user.id}`", parse_mode="Markdown")

@dp.message(F.text == "💎 اشتراک‌های من")
async def my_subs(message: types.Message):
    await message.answer("در حال حاضر اشتراک فعالی ندارید.")

@dp.message(F.text == "💰 شارژ حساب")
async def charge_acc(message: types.Message):
    await message.answer(f"جهت افزایش موجودی، به آیدی پشتیبانی @{SUPPORT_ID} پیام دهید.")

# --- وب سرور aiohttp برای رفع ارور ۵۰۳ رندر ---
async def handle_health_check(request):
    return web.Response(text="Bot is Live and Running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Health check web server started on port {PORT}")

async def main():
    # ۱. اجرای وب سرور جهت پاس کردن تست سلامت رندر
    await start_web_server()
    
    # ۲. پاکسازی وب‌هوک و صف پیام‌های قبلی تلگرام جهت جلوگیری از Conflict
    await bot.delete_webhook(drop_pending_updates=True)
    
    # ۳. شروع دریافت پیام‌ها
    logging.info("Starting Telegram Bot Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

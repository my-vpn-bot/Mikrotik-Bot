import os
import sys
import logging
import asyncio
import sqlite3
import jdatetime
from datetime import datetime, timezone, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery
)

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("Mikrotik-Bot")

# خواندن متغیرهای محیطی بر اساس اسکرین‌شات شما
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", 10000))
DB_PATH = "bot_database.db"

# توابع اصلاح‌شده برای خواندن دقیق از پنل Render
def get_card_info():
    # استفاده از کلیدهای دقیقِ موجود در اسکرین‌شات شما
    num = os.getenv("PAYMENT_CARD", "وارد نشده").strip()
    holder = os.getenv("PAYMENT_NAME", "مدیریت").strip()
    return num, holder

def make_clean_url(val: str, default_username: str) -> str:
    # پاکسازی برای تبدیل هر ورودی به لینک t.me استاندارد
    raw = (val or default_username).strip()
    raw = raw.replace("https://t.me/", "").replace("http://t.me/", "").replace("tg://resolve?domain=", "")
    username = raw.lstrip("@").strip()
    return f"https://t.me/{username}"

# دریافت اطلاعات از پنل
SUPPORT_LINK = make_clean_url(os.getenv("SUPPORT_ID", ""), "L2TP_Support")
CHANNEL_LINK = make_clean_url(os.getenv("CHANNEL_URL", ""), "L2tp_vpn402")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# کیبورد اصلی (۴ ردیف)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ],
    resize_keyboard=True,
    is_persistent=True
)

# تابع ساخت کیبورد پلن‌ها
def build_plans_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 پلن ۱ ماهه (۲۵۰,۰۰۰ تومان)", callback_data="buy_plan_1")],
        [InlineKeyboardButton(text="🔹 پلن ۲ ماهه (۴۰۰,۰۰۰ تومان)", callback_data="buy_plan_2")],
        [InlineKeyboardButton(text="🔹 پلن ۳ ماهه (۶۰۰,۰۰۰ تومان)", callback_data="buy_plan_3")],
        [InlineKeyboardButton(text="🧾 ارتباط با پشتیبانی / ارسال فیش", url=SUPPORT_LINK)],
        [InlineKeyboardButton(text="❌ بستن منو", callback_data="close_menu")]
    ])

# استارت و خوش‌آمدگویی با زمان شمسی
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    tehran_tz = timezone(timedelta(hours=3, minutes=30))
    now_tehran = datetime.now(tehran_tz)
    now = jdatetime.datetime.fromgregorian(datetime=now_tehran.replace(tzinfo=None))
    
    welcome_msg = (
        f"سلام {message.from_user.full_name} عزیز! 🌹\n\n"
        f"📅 تاریخ: {now.strftime('%Y/%m/%d')}\n⏰ ساعت: {now.strftime('%H:%M:%S')}\n\n"
        "به دنیای سرعت و پایداری خوش آمدید! 🚀\n\n"
        "👇 برای شروع از منوی زیر استفاده کنید:"
    )
    await message.answer(welcome_msg, reply_markup=main_keyboard)

@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy(message: types.Message):
    await message.answer("🛍️ انتخاب پلن اشتراک:", reply_markup=build_plans_keyboard())

@dp.callback_query(F.data.startswith("buy_plan_"))
async def handle_plan_callback(callback: CallbackQuery):
    card_num, card_holder = get_card_info()
    plan_name = callback.data.split("_")[-1]
    
    text = (
        f"💳 <b>اطلاعات پرداخت:</b>\n\n"
        f"💳 شماره کارت: <code>{card_num}</code>\n"
        f"👤 به نام: <b>{card_holder}</b>\n\n"
        f"📌 لطفاً تصویر فیش واریزی را برای پشتیبانی ارسال کنید."
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 ارسال فیش", url=SUPPORT_LINK)],
        [InlineKeyboardButton(text="❌ بستن", callback_data="close_menu")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)

@dp.message(F.text == "💰 شارژ حساب")
async def handle_charge(message: types.Message):
    card_num, card_holder = get_card_info()
    text = (f"💳 <b>اطلاعات جهت شارژ کیف پول:</b>\n\n"
            f"💳 کارت: <code>{card_num}</code>\n"
            f"👤 به نام: {card_holder}")
    await message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 ارسال فیش", url=SUPPORT_LINK)]
    ]))

@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: types.Message):
    await message.answer("👥 برای ارتباط با واحد پشتیبانی روی دکمه زیر کلیک کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 چت با پشتیبانی", url=SUPPORT_LINK)]
    ]))

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs(message: types.Message):
    await message.answer(f"📢 آموزش‌ها در کانال ما:\n{CHANNEL_LINK}")

@dp.callback_query(F.data == "close_menu")
async def close_menu(callback: CallbackQuery):
    await callback.message.delete()

# راه‌اندازی سرور
async def main():
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

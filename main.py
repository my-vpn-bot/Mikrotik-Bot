import os
import asyncio
import logging
import sqlite3
import jdatetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- تنظیمات اولیه و محیطی ---
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# --- مدیریت دیتابیس (Single Source of Truth) ---
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY, 
                        username TEXT, 
                        subscription_date TEXT)''')
    conn.commit()
    conn.close()

# --- ساختار منوی نهایی (۴ ردیف طبق دستور) ---
def get_main_menu():
    kb = [
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- هندلر استارت (با بازگشت متن کامل و جزئیات زمانی) ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    now = jdatetime.datetime.now()
    date_str = now.strftime('%Y/%m/%d')
    day_name = now.strftime('%A')
    time_str = now.strftime('%H:%M')
    
    # بازگشت متن خوش‌آمدگویی دقیق و طولانی
    welcome_text = (
        f"<b>سلام آرشاوین عزیز، به ربات خوش آمدید.</b>\n\n"
        f"📅 امروز {day_name} - {date_str}\n"
        f"⏰ ساعت: {time_str}\n\n"
        f"لطفاً از منوی زیر برای مدیریت خدمات استفاده کنید."
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

# --- هندلرهای بیزینسی (بدون تغییر در منطق پایه) ---
@dp.message(F.text == "🛒 خرید اشتراک")
async def buy_subscription(message: types.Message):
    # در اینجا لاجیک قیمت‌های 250, 400, 600 طبق کد مرجع قرار می‌گیرد
    await message.answer("لطفاً پلن مورد نظر خود را انتخاب کنید:\n\n"
                         "1️⃣ پلن پایه: ۲۵۰,۰۰۰ تومان\n"
                         "2️⃣ پلن ویژه: ۴۰۰,۰۰۰ تومان\n"
                         "3️⃣ پلن پرمیوم: ۶۰۰,۰۰۰ تومان")

@dp.message(F.text == "📊 اطلاعات حساب")
async def account_info(message: types.Message):
    await message.answer("در حال دریافت اطلاعات حساب شما...")

@dp.message(F.text == "💎 اشتراک‌های من")
async def my_subs(message: types.Message):
    await message.answer("لیست اشتراک‌های فعال شما:")

@dp.message(F.text == "💰 شارژ حساب")
async def charge_account(message: types.Message):
    await message.answer("لطفاً مبلغ مورد نظر برای شارژ را ارسال کنید.")

@dp.message(F.text == "👥 پشتیبانی")
async def support(message: types.Message):
    await message.answer("ارتباط با پشتیبانی برقرار شد...")

@dp.message(F.text == "❓ سوالات متداول")
async def faq(message: types.Message):
    await message.answer("بخش سوالات متداول:")

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def config_help(message: types.Message):
    await message.answer("راهنمای اتصال به سرویس...")

# --- وب‌سرور برای Render ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logging.info(f"Web server started on port {PORT}")

# --- اجرای اصلی ---
async def main():
    init_db()
    await start_web_server()
    # skip_updates=True برای جلوگیری از ConflictError
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")

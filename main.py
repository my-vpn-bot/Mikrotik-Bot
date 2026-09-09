import os
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

# ==================== تنظیمات و لاگینگ ====================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("V2Ray-Bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", 10000))
DB_PATH = "bot_database.db"

# اطلاعات کارت بانکی
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "وارد نشده")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "مدیریت")
SUPPORT_LINK = "https://t.me/" + os.getenv("SUPPORT_USERNAME", "L2TP_Support").replace("@", "")
CHANNEL_LINK = "https://t.me/" + os.getenv("CHANNEL_USERNAME", "L2tp_vpn402").replace("@", "")

# ==================== دیتابیس ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            join_date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==================== ربات و کیبورد ====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ساختار منوی اصلی طبق دستور دقیق ۴ ردیفی
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

def get_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])

# ==================== هندلرها ====================

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    user = message.from_user
    
    # تاریخ و ساعت دقیق شمسی
    tehran_tz = timezone(timedelta(hours=3, minutes=30))
    now_tehran = datetime.now(tehran_tz)
    now_jalali = jdatetime.datetime.fromgregorian(datetime=now_tehran.replace(tzinfo=None))
    weekday_fa = {
        "Saturday": "شنبه", "Sunday": "یکشنبه", "Monday": "دوشنبه", "Tuesday": "سه‌شنبه",
        "Wednesday": "چهارشنبه", "Thursday": "پنجشنبه", "Friday": "جمعه"
    }.get(now_tehran.strftime("%A"), "")
    
    welcome_msg = (
        f"سلام {user.full_name} عزیز! 🌹\n\n"
        f"📅 امروز: <b>{weekday_fa} {now_jalali.strftime('%Y/%m/%d')}</b>\n"
        f"⏰ ساعت: <b>{now_jalali.strftime('%H:%M:%S')}</b>\n\n"
        f"به دنیای سرعت و پایداری خوش آمدید! 🚀\n"
        f"ربات رسمی ارائه سرویس‌های اختصاصی V2Ray\n\n"
        f"⚡️ <b>سرعت و پایداری بسیار بالا</b>\n"
        f"🛡 <b>اتصال رمزنگاری‌شده و امن</b>\n"
        f"🌐 <b>حجم کاملاً نامحدود</b>\n"
        f"🕒 <b>پشتیبانی دائمی و سریع</b>\n\n"
        f"📢 کانال اطلاع‌رسانی: {CHANNEL_LINK}\n\n"
        f"👇 برای شروع و مدیریت سرویس‌ها، از منوی زیر استفاده کنید:"
    )
    await message.answer(welcome_msg, reply_markup=main_keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "main_menu")
async def handle_main_menu_callback(callback: CallbackQuery):
    await callback.message.delete()
    await send_welcome(callback.message)

@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 پلن ۱ ماهه", callback_data="buy_1")],
        [InlineKeyboardButton(text="🔹 پلن ۲ ماهه", callback_data="buy_2")],
        [InlineKeyboardButton(text="🔹 پلن ۳ ماهه", callback_data="buy_3")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])
    await message.answer("🛍️ لطفاً یکی از پلن‌های V2Ray را انتخاب کنید:", reply_markup=markup)

@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account(message: types.Message):
    text = "📊 <b>اطلاعات حساب شما:</b>\n\nوضعیت: <b>فعال</b>\nموجودی: <b>۰ تومان</b>"
    await message.answer(text, reply_markup=get_back_kb(), parse_mode="HTML")

@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subs(message: types.Message):
    await message.answer("💎 در حال حاضر اشتراک فعالی برای شما ثبت نشده است.", reply_markup=get_back_kb())

@dp.message(F.text == "💰 شارژ حساب")
async def handle_charge(message: types.Message):
    text = (f"💰 <b>شارژ موجودی:</b>\n\n"
            f"جهت افزایش موجودی، مبلغ مورد نظر را به شماره کارت زیر واریز و فیش را برای پشتیبانی ارسال کنید:\n\n"
            f"💳 شماره کارت: <code>{PAYMENT_CARD}</code>\n"
            f"👤 به نام: <b>{PAYMENT_NAME}</b>")
    await message.answer(text, reply_markup=get_back_kb(), parse_mode="HTML")

@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 چت با پشتیبانی", url=SUPPORT_LINK)],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])
    await message.answer("👥 <b>واحد پشتیبانی و فروش:</b>\nبرای پیگیری سفارشات با ما در تماس باشید.", reply_markup=markup, parse_mode="HTML")

@dp.message(F.text == "❓ سوالات متداول")
async def handle_faq(message: types.Message):
    faq_text = (
        "❓ <b>سوالات متداول (FAQ):</b>\n\n"
        "1. سرویس V2Ray روی چه سیستم‌عامل‌هایی کار می‌کند؟ (همه دستگاه‌ها)\n"
        "2. آیا امکان استفاده همزمان وجود دارد؟ (بستگی به پلن دارد)\n"
        "3. سرعت سرویس چقدر است؟ (بالاترین کیفیت ممکن)\n"
        "4. آیا سرویس دارای محدودیت حجمی است؟ (خیر، نامحدود)\n"
        "5. مدت زمان تحویل پس از واریز چقدر است؟ (۵ تا ۱۵ دقیقه)\n"
        "6. چگونه کانفیگ را دریافت کنم؟ (از طریق ارسال فیش به پشتیبانی)\n"
        "7. آیا امکان تمدید سرویس وجود دارد؟ (بله)\n"
        "8. پروتکل‌های مورد استفاده چیست؟ (V2Ray / VMess / VLESS)\n"
        "9. آیا آی‌پی ثابت ارائه می‌دهید؟ (بستگی به کانفیگ دارد)\n"
        "10. پشتیبانی در چه ساعاتی فعال است؟ (پشتیبانی دائمی)\n"
        "11. آیا امکان تست قبل از خرید وجود دارد؟ (خیر)"
    )
    await message.answer(faq_text, reply_markup=get_back_kb(), parse_mode="HTML")

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])
    await message.answer("⚙️ <b>راهنمای اتصال V2Ray:</b>\n\nآموزش‌ها و آخرین کانفیگ‌ها در کانال موجود است.", reply_markup=markup, parse_mode="HTML")

# ==================== اجرای سرور ====================
async def health_check(request):
    return web.Response(text="Bot is Running!")

async def main():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    logger.info(f"Bot started on port {PORT}")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

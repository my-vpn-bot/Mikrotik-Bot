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

# Configuration & Logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s", 
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Mikrotik-Bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", 10000))
DB_PATH = "bot_database.db"

# Normalizing Telegram URLs securely
def clean_tg_link(val: str, default: str) -> str:
    cleaned = (val or default).strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    cleaned = cleaned.lstrip("@").strip()
    return f"https://t.me/{cleaned}"

raw_support = os.getenv("SUPPORT_USERNAME", "L2TP_Support")
SUPPORT_URL = clean_tg_link(raw_support, "L2TP_Support")

raw_channel = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
CHANNEL_URL = clean_tg_link(raw_channel, "L2tp_vpn402")

CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9918-0000-0000").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "رحیمی").strip()

PLAN1_PRICE = os.getenv("PLAN1_PRICE", "۲۵۰,۰۰۰").strip()
PLAN2_PRICE = os.getenv("PLAN2_PRICE", "۴۰۰,۰۰۰").strip()
PLAN3_PRICE = os.getenv("PLAN3_PRICE", "۶۰۰,۰۰۰").strip()

# Database Setup
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

init_db()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Keyboards (4-Row Layout)
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

def get_plans_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔹 پلن ۱ ماهه ({PLAN1_PRICE} تومان)", callback_data="buy_plan_1")],
        [InlineKeyboardButton(text=f"🔹 پلن ۲ ماهه ({PLAN2_PRICE} تومان)", callback_data="buy_plan_2")],
        [InlineKeyboardButton(text=f"🔹 پلن ۳ ماهه ({PLAN3_PRICE} تومان)", callback_data="buy_plan_3")],
        [InlineKeyboardButton(text="🧾 ارتباط با پشتیبانی / ارسال فیش", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="❌ بستن پنجره", callback_data="close_menu")]
    ])

# Welcome Handler with Exact Tehran Timezone (UTC+3:30)
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    tehran_tz = timezone(timedelta(hours=3, minutes=30))
    now_tehran = datetime.now(tehran_tz)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, join_date) VALUES (?, ?, ?, ?)",
        (
            message.from_user.id, 
            message.from_user.username or "", 
            message.from_user.full_name or "", 
            now_tehran.strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    conn.commit()
    conn.close()

    now = jdatetime.datetime.fromgregorian(datetime=now_tehran.replace(tzinfo=None))
    weekday_map = {
        "Saturday": "شنبه", "Sunday": "یکشنبه", "Monday": "دوشنبه", 
        "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه", "Thursday": "پنجشنبه", "Friday": "جمعه"
    }
    persian_weekday = weekday_map.get(now.strftime("%A"), now.strftime("%A"))
    jalali_date = now.strftime("%Y/%m/%d")
    current_time = now.strftime("%H:%M:%S")

    welcome_msg = (
        f"سلام {message.from_user.full_name} عزیز! 🌹\n\n"
        f"📅 امروز {persian_weekday} {jalali_date}\n"
        f"⏰ ساعت: {current_time}\n\n"
        "به دنیای سرعت و پایداری خوش آمدید! 🚀 ربات رسمی L2TP VPN با افتخار سرویس‌های اینترنت پرسرعت و نامحدود را برای شما ارائه می‌دهد.\n\n"
        "🌟 ویژگی‌های سرویس اختصاصی:\n"
        "⚡ سرعت و پایداری بالا: بدون افت سرعت، ایده‌آل برای وب‌گردی و گیمینگ\n"
        "🛡 اتصال رمزنگاری‌شده و امن: حفظ کامل حریم خصوصی و امنیت داده‌ها\n"
        "🌐 حجم کاملاً نامحدود: بدون محدودیت مصرف در طول دوره اشتراک\n"
        "🕒 پشتیبانی ۲۴ ساعته: همراهی مستمر در تمام ساعات شبانه‌روز\n\n"
        f"📢 کانال اطلاع‌رسانی و آموزش: {CHANNEL_URL}\n\n"
        "👇 برای شروع، از منوی زیر گزینه مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(welcome_msg, reply_markup=main_keyboard)

@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy(message: types.Message):
    await message.answer(
        "🛍️ لیست پلن‌های فعال اشتراک اختصاصی:\n\n👇 لطفاً پلن مورد نظر خود را انتخاب کنید:", 
        reply_markup=get_plans_keyboard()
    )

@dp.callback_query(F.data.startswith("buy_plan_"))
async def handle_plan_callback(callback: CallbackQuery):
    plan_id = callback.data.split("_")[-1]
    prices = {"1": (PLAN1_PRICE, "۱ ماهه"), "2": (PLAN2_PRICE, "۲ ماهه"), "3": (PLAN3_PRICE, "۳ ماهه")}
    selected_price, plan_name = prices.get(plan_id, (PLAN1_PRICE, "۱ ماهه"))
    
    pay_text = (
        f"💳 **اطلاعات پرداخت اشتراک {plan_name}:**\n\n"
        f"💰 مبلغ قابل پرداخت: **{selected_price}** تومان\n"
        f"💳 شماره کارت: `{CARD_NUMBER}`\n"
        f"👤 به نام: **{CARD_HOLDER}**\n\n"
        f"📌 لطفا پس از واریز، تصویر فیش را برای پشتیبانی ارسال کنید."
    )
    
    pay_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 ارسال فیش واریزی به پشتیبانی", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="🔙 بازگشت به لیست پلن‌ها", callback_data="back_to_plans")],
        [InlineKeyboardButton(text="❌ انصراف و بستن", callback_data="close_menu")]
    ])
    
    # پیام را ویرایش می‌کنیم تا چت شلوغ نشود
    await callback.message.edit_text(pay_text, parse_mode="Markdown", reply_markup=pay_markup)
    await callback.answer()

@dp.callback_query(F.data == "back_to_plans")
async def back_to_plans(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛍️ لیست پلن‌های فعال اشتراک اختصاصی:\n\n👇 لطفاً پلن مورد نظر خود را انتخاب کنید:", 
        reply_markup=get_plans_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "close_menu")
async def close_menu(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_text("❌ عملیات لغو شد.")
    await callback.answer("منو بسته شد.")

@dp.message(F.text == "💰 شارژ حساب")
async def handle_wallet_charge(message: types.Message):
    charge_text = (
        f"💳 **اطلاعات حساب جهت شارژ:**\n\n"
        f"💳 شماره کارت: `{CARD_NUMBER}`\n"
        f"👤 به نام: **{CARD_HOLDER}**\n\n"
        f"📌 پس از واریز مبلغ مورد نظر، عکس رسید را به پشتیبانی ارسال کنید تا حساب شما شارژ شود:"
    )
    charge_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 ارسال فیش واریزی", url=SUPPORT_URL)],
        [InlineKeyboardButton(text="❌ بستن", callback_data="close_menu")]
    ])
    await message.answer(charge_text, parse_mode="Markdown", reply_markup=charge_markup)

@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: types.Message):
    await message.answer(
        "👥 واحد پشتیبانی:\nبرای ارتباط با کارشناسان یا ارسال فیش واریزی روی دکمه زیر کلیک کنید:", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 ارتباط با پشتیبانی / ارسال رسید", url=SUPPORT_URL)],
            [InlineKeyboardButton(text="❌ بستن", callback_data="close_menu")]
        ])
    )

@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account_info(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, join_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    balance = row[0] if row else 0
    join_date = row[1] if row else "نامشخص"
    await message.answer(
        f"📊 اطلاعات حساب کاربری شما:\n🆔 شناسه کاربری: `{user_id}`\n💰 موجودی کیف پول: {balance:,} تومان\n📅 تاریخ عضویت: {join_date}", 
        parse_mode="Markdown"
    )

@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: types.Message):
    await message.answer("💎 در حال حاضر اشتراک فعالی برای شما ثبت نشده است.")

@dp.message(F.text == "❓ سوالات متداول")
async def handle_faq(message: types.Message):
    faq_text = (
        "❓ **سوالات متداول:**\n\n"
        "۱. **تحویل اشتراک چگونه است؟**\n"
        "پس از ارسال فیش واریزی به پشتیبانی، اشتراک شما در سریع‌ترین زمان فعال و اطلاعات آن ارسال می‌شود.\n\n"
        "۲. **آیا سرویس‌ها ضمانت دارند؟**\n"
        "بله، تمامی پلن‌ها تا آخرین روز اشتراک دارای ضمانت سرعت و پایداری می‌باشند."
    )
    await message.answer(faq_text, parse_mode="Markdown")

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs(message: types.Message):
    await message.answer(
        f"⚙️ **راهنمای اتصال و دانلود برنامه‌ها:**\n\n📢 برای دریافت جدیدترین کانفیگ‌ها و آموزش‌های اتصال به کانال رسمی ما بپیوندید:\n{CHANNEL_URL}",
        disable_web_page_preview=True
    )

async def health_check(request):
    return web.Response(text="Mikrotik-Bot is active!", status=200)

async def main():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

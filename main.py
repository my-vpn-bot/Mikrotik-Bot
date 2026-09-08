"""
Mikrotik-Bot — ربات فروش اشتراک VPN
نسخه نهایی و پایدار (ادغام‌شده با وب‌سرور Health Check برای Render)
Python 3.10+ | aiogram 3.x
"""
import asyncio
import logging
import os
import sqlite3
from datetime import datetime

import jdatetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

# ------------------------------------------------#
#  تنظیمات پایه
# ------------------------------------------------#
DATABASE_FILE = os.environ.get("DATABASE_FILE", "bot_users.db")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # عددی — در رندر به‌صورت عدد ست شود

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------#
#  دیتابیس
# ------------------------------------------------#
def init_db():
    """ایجاد جدول‌های لازم"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            shamsi_join_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            shamsi_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_current_shamsi():
    """تاریخ و ساعت شمسی جاری به‌صورت رشته"""
    now = jdatetime.datetime.now()
    return now.strftime("%Y/%m/%d"), now.strftime("%H:%M:%S")


def is_user_registered(user_id: int) -> bool:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def register_user(user_id: int, full_name: str, username: str):
    if is_user_registered(user_id):
        return
    date_str, _ = get_current_shamsi()
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name, username, shamsi_join_date) "
        "VALUES (?, ?, ?, ?)",
        (user_id, full_name, username, date_str),
    )
    conn.commit()
    conn.close()


def log_visit(user_id: int, action: str):
    """ثبت هر کلیک/بازدید برای آمار"""
    try:
        date_str, time_str = get_current_shamsi()
        ts = f"{date_str} {time_str}"
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO stats (user_id, action, shamsi_time) VALUES (?, ?, ?)",
            (user_id, action, ts),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("log_visit failed: %s", exc)


def get_visit_stats():
    """آمار کل بازدیدها، بازدیدکننده‌های یکتا و تفکیک اعمال"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stats")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM stats")
    unique = cursor.fetchone()[0]
    cursor.execute(
        "SELECT action, COUNT(*) FROM stats GROUP BY action ORDER BY COUNT(*) DESC"
    )
    breakdown = cursor.fetchall()
    conn.close()
    return total, unique, breakdown


def total_users() -> int:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    result = cursor.fetchone()[0]
    conn.close()
    return result


def get_join_date(user_id: int) -> str:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT shamsi_join_date FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "—"


# ------------------------------------------------#
#  محتوای ربات
# ------------------------------------------------#
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# پلن‌های اشتراک (بدون پلن نامحدود)
PLANS_DATA = {
    "plan_weekly": {
        "title": "📅 پلن هفتگی",
        "price": "180,000",
        "duration": "۷ روز",
        "detail": "مناسب استفاده کوتاه‌مدت و تست اولیه",
    },
    "plan_monthly": {
        "title": "📆 پلن ماهانه",
        "price": "500,000",
        "duration": "۳۰ روز",
        "detail": "پرکاربردترین پلن — مناسب استفاده روزمره",
    },
    "plan_3months": {
        "title": "📅 پلن ۳ ماهه",
        "price": "1,400,000",
        "duration": "۹۰ روز",
        "detail": "اقتصادی‌ترین انتخاب برای بلندمدت",
    },
}


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_service")],
        [InlineKeyboardButton(text="👤 حساب کاربری", callback_data="user_profile")],
        [InlineKeyboardButton(text="📚 راهنما", callback_data="help")],
        [InlineKeyboardButton(text="📞 پشتیبانی", callback_data="support")],
    ])


# ------------------------------------------------#
#  هندلرهای اصلی پیام
# ------------------------------------------------#
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    register_user(user.id, user.full_name or "", user.username or "")

    reply = (
        f"👋 سلام {user.full_name} عزیز، به ربات فروش اشتراک L2TP VPN خوش آمدید.\n\n"
        f"🔐 با اشتراک، اتصال امن و پایدار به سرور را تجربه خواهید کرد.\n\n"
        f"از منوی زیر گزینه موردنظر را انتخاب کنید:"
    )
    await message.answer(reply, reply_markup=main_keyboard())


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user = message.from_user
    log_visit(user.id, "admin_cmd")
    if user.id != ADMIN_ID:
        await message.answer("⛔ شما دسترسی لازم برای این بخش را ندارید.")
        return
    await show_admin_panel(message)


async def show_admin_panel(message: Message):
    total, unique, breakdown = get_visit_stats()
    text = (
        f"🔧 پنل مدیریت\n"
        f"——————————————\n"
        f"👥 کل کاربران ثبت‌نامی: {total_users()}\n"
        f"👀 کل بازدیدها (کلیک‌ها): {total}\n"
        f"🆕 بازدیدکننده‌های یکتا: {unique}\n\n"
        f"📊 تفکیک فعالیت‌ها:\n"
    )
    if breakdown:
        for action, count in breakdown:
            text += f"    • {action}: {count}\n"
    else:
        text += "    (فعلاً آماری ثبت نشده است.)\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 به‌روزرسانی آمار", callback_data="admin_refresh")],
        [InlineKeyboard • {action}: {count}\n"
    else:
        text += "    (فعلاً آماری ثبت نشده است.)\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 به‌روزرسانی آمار", callback_data="admin_refresh")],
        [InlineKeyboardButton(text="🔙 بازگشت",):
    await callback.answer()
    log_visit(callback.from_user.id, "buy_service")

    text = (
        "🛒 خرید اشتراک\n"
        "——————————————\n"
        "لطفاً یکی از پلن‌های زیر را انتخاب کنید:\n"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{p['title']} — {p['price']} تومان",
                callback_data=pid,
            )]
            for pid, p in PLANS_DATA.items()
        ]
        + [[InlineKeyboardButton(text="🔙 باز",
                callback_data=pid,
            )]
            for pid, p in PLANS_DATA.items()
        ]
        + [[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]]
    )
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data.in_(PLANS_DATA.keys()))
async def handle_plan_selection:{callback.data}")

    text = (
        f"{plan['title']}\n"
        f"——————————————\n"
        f"💰 قیمت: {plan['price']} تومان\n"
        f"⏳ مدت: {plan['duration']}\n"
        f"📝 توضیحات: {plan['detail']}\n\n"
        f"💳 برای خرید، مبلغ را به کارت زیر واریز کنید:\n"
        f"CARD_NUMBER_PLACEHOLDER\n"
        f"به نام: CARD_HOLDER_PLACEHOLDER\n\n"
        f"پس از واریز، تصویر فیش را برای ما ارسال کنید.\n"
        f"پشتیبانی پس از بررسی، اشتراک شما را فعال می‌کند."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ پرداخت انجام شد", callback_data="payment_done")],
        [InlineKeyboardButton(text="🔙 بازگشت به پلن‌ها", callback_data="buy_service")],
        [InlineKeyboardButton(text="🏠 منوی اصلی", callback_data="back_to_main")],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data == "payment_done")
async def handle_payment_done(callback: CallbackQuery):
    await callback.answer()
    log_visit(callback.from_user.id, "payment_done")
    await callback.message.answer(
        "✅ لطفاً تصویر فیش واریزی خود را همین‌جا (به شکل عکس) ارسال کنید.\n"
        "پس از تأیید توسط پشتیبانی، اشتراک شما فعال می‌شود."
    )


@dp.callback_query(F.data == "user_profile")
async def handle_user_profile(callback: CallbackQuery):
    await callback.answer()
    log_visit(callback.from_user.id, "user_profile")
    user = callback.from_user
    text = (
        f"👤 حساب کاربری شما:\n"
        f"——————————————\n"
        f"🆔 شناسه: {user.id}\n"
        f"👤 نام: {user.full_name or '—'}\n"
        f"🆔 نام کاربری: @{user.username or '—'}\n\n"
        f"📅 تاریخ عضویت: {get_join_date(user.id)}\n\n"
        f"💡 برای مشاهده اشتراک فعال و خرید جدید، از منوی اصلی استفاده کنید."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data == "help")
async def handle_help(callback: CallbackQuery):
    await callback.answer()
    log_visit(callback.from_user.id, "help")
    text = (
        "📚 راهنمای استفاده\n"
        "——————————————\n"
        "1️⃣ برای خرید اشتراک، گزینه «خرید اشتراک» را بزنید.\n"
        "2️⃣ پلن دلخواه را انتخاب و مبلغ را به کارت اعلام‌شده واریز کنید.\n"
        "3️⃣ تصویر فیش را در همان گفت‌وگو ارسال کنید.\n"
        "4️⃣ پشتیبانی پس از بررسی، اشتراک شما را فعال می‌کند.\n\n"
        "📞 در صورت نیاز، از گزینه «پشتیبانی» استفاده کنید."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data == "support")
async def handle_support(callback: CallbackQuery):
    await callback.answer()
    log_visit(callback.from_user.id, "support")
    text = (
        "📞 پشتیبانی\n"
        "——————————————\n"
        "برای ارتباط با پشتیبانی، به آیدی زیر پیام دهید:\n"
        f"✉️ @SUPPORT_USERNAME_PLACEHOLDER\n\n"
        "ساعات پاسخ‌گویی: ۹ صبح تا ۱۱ شب"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data == "admin_refresh")
async def handle_admin_refresh(callback: CallbackQuery):
    await callback.answer()
    log_visit(callback.from_user.id, "admin_refresh")
    total, unique, breakdown = get_visit_stats()
    text = (
        f"🔧 پنل مدیریت (به‌روزرسانی‌شده)\n"
        f"——————————————\n"
        f"👥 کل کاربران ثبت‌نامی: {total_users()}\n"
        f"👀 کل بازدیدها (کلیک‌ها): {total}\n"
        f"🆕 بازدیدکننده‌های یکتا: {unique}\n\n"
        f"📊 تفکیک فعالیت‌ها:\n"
    )
    if breakdown:
        for action, count in breakdown:
            text += f"    • {action}: {count}\n"
    else:
        text += "    (فعلاً آماری ثبت نشده است.)\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 به‌روزرسانی آمار", callback_data="admin_refresh")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")],
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery):
    await callback.answer()
    log_visit(callback.from_user.id, "back_to_main")
    await callback.message.edit_text(
        "🏠 منوی اصلی — لطفاً گزینه موردنظر را انتخاب کنید:",
        reply_markup=main_keyboard(),
    )


# ------------------------------------------------#
#  هندلرهای عکس و پیام‌های متفرقه
# ------------------------------------------------#
@dp.message(F.photo)
async def handle_photo(message: Message):
    user = message.from_user
    log_visit(user.id, "payment_proof_photo")
    if ADMIN_ID != 0:
        await message.forward(chat_id=ADMIN_ID)
    await message.answer(
        "✅ فیش شما دریافت و برای پشتیبانی ارسال شد. "
        "پس از تأیید، اشتراک فعال می‌شود."
    )


@dp.message()
async def fallback(message: Message):
    await message.answer("لطفاً از دکمه‌های منو استفاده کنید یا با «پشتیبانی» تماس بگیرید.")


# ------------------------------------------------#
#  وب‌سرور Health Check (برای راضی نگه‌داشتن Render)
# ------------------------------------------------#
async def health_check(request):
    return web.Response(text="Bot is running happily!")


# ------------------------------------------------#
#  اجرای اصلی
# ------------------------------------------------#
async def main():
    init_db()
    logger.info("Mikrotik-Bot starting...")

    # اجرای وب‌سرور سبک برای باز نگه‌داشتن پورت Render
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Dummy Web Server running on port {port}")

    # شروع پولینگ ربات تلگرام
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

import os
import sys
import logging
import asyncio
import sqlite3
import jdatetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ContentType
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- تنظیمات لاگینگ ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- متغیرهای محیطی Render ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6278059256"))
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
CARD_HOLDER = os.getenv("CARD_HOLDER", "رحیمی")
SUPPORT_ID = os.getenv("SUPPORT_ID", "aL2tp1Support").lstrip("@")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/L2tp_vpn402")
PORT = int(os.getenv("PORT", 10000))

PLAN1_PRICE = os.getenv("PLAN1_PRICE", "۲۵۰,۰۰۰")
PLAN2_PRICE = os.getenv("PLAN2_PRICE", "۴۰۰,۰۰۰")
PLAN3_PRICE = os.getenv("PLAN3_PRICE", "۶۰۰,۰۰۰")

# --- راه‌اندازی دیتابیس SQLite ---
conn = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    username TEXT,
    balance INTEGER DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    plan_name TEXT,
    config TEXT,
    created_at TEXT
)
""")
conn.commit()

# --- ماشین وضعیت (FSM) ---
class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- کیبورد اصلی (۴ ردیف ثابت) ---
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 خرید اشتراک")],
            [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
            [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
            [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
        ],
        resize_keyboard=True
    )

def to_persian_digits(text: str) -> str:
    persian_digits = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}
    for en, fa in persian_digits.items():
        text = str(text).replace(en, fa)
    return text

def get_plans_inline_markup():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"پلن ۱: ۳۰ گیگ ۱ ماهه ({PLAN1_PRICE} تومان)", callback_data="buy_plan_1")],
            [InlineKeyboardButton(text=f"پلن ۲: ۶۰ گیگ ۲ ماهه ({PLAN2_PRICE} تومان)", callback_data="buy_plan_2")],
            [InlineKeyboardButton(text=f"پلن ۳: ۳ ماهه نامحدود ({PLAN3_PRICE} تومان)", callback_data="buy_plan_3")],
            [InlineKeyboardButton(text="🔙 انصراف و بستن منو", callback_data="cancel_plan_selection")]
        ]
    )

# --- هندلر /start (متن کامل، اصیل، همراه با کانال و تاریخ/ساعت شمسی) ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    cursor.execute("INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
                   (user.id, user.full_name, user.username or ""))
    conn.commit()

    now = jdatetime.datetime.now()
    day_name = now.strftime("%A")
    date_formatted = to_persian_digits(now.strftime("%d %B %Y"))
    time_formatted = to_persian_digits(now.strftime("%H:%M:%S"))

    welcome_text = (
        f"سلام {user.full_name} عزیز، به ربات هوشمند سرویس اختصاصی V2Ray خوش آمدید 🌹\n\n"
        f"📅 امروز: {day_name}، {date_formatted}\n"
        f"⏰ ساعت: {time_formatted}\n\n"
        f"🛡 **سرویس اینترنت پرسرعت و ضد فیلتر V2Ray**\n"
        f"⚡ پایداری تضمینی، آی‌پی اختصاصی، پینگ فوق‌العاده مناسب برای وب‌گردی، اینستاگرام، یوتیوب، ترید و گیمینگ.\n"
        f"🌐 سازگار با تمامی سیستم‌عامل‌ها (اندروید، iOS، ویندوز و مک).\n\n"
        f"📢 کانال اطلاع‌رسانی، سرورها و آموزش‌ها:\n"
        f"{CHANNEL_LINK}\n\n"
        f"👇 لطفاً یکی از گزینه‌های منوی زیر را جهت خرید یا مدیریت اشتراک انتخاب فرمایید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# --- منوی خرید اشتراک ---
@dp.message(F.text == "🛒 خرید اشتراک")
async def buy_plan_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("📦 لطفاً پلن V2Ray مورد نظر خود را انتخاب کنید:", reply_markup=get_plans_inline_markup())

# انصراف از انتخاب پلن (پاک کردن پیام برای تمیز ماندن چت)
@dp.callback_query(F.data == "cancel_plan_selection")
async def cancel_plan_selection(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("عملیات لغو شد.")

# بازگشت از مرحله فاکتور به منوی پلن‌ها
@dp.callback_query(F.data == "back_to_plans")
async def back_to_plans(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("📦 لطفاً پلن V2Ray مورد نظر خود را انتخاب کنید:", reply_markup=get_plans_inline_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_plan_"))
async def process_plan_choice(callback: types.CallbackQuery, state: FSMContext):
    plan_id = callback.data.split("_")[2]
    plans = {
        "1": ("پلن ۱ (۳۰ گیگ یک‌ماهه)", PLAN1_PRICE),
        "2": ("پلن ۲ (۶۰ گیگ دوماهه)", PLAN2_PRICE),
        "3": ("پلن ۳ (سه‌ماهه نامحدود)", PLAN3_PRICE)
    }
    name, price = plans[plan_id]
    await state.update_data(selected_plan=name, plan_price=price)
    
    # حذف پیام قبلی لیست پلن‌ها برای تمیز ماندن چت
    try:
        await callback.message.delete()
    except Exception:
        pass

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به لیست پلن‌ها", callback_data="back_to_plans")]
        ]
    )
    
    text = (
        f"💳 خرید: **{name}**\n"
        f"مبلغ قابل پرداخت: **{price} تومان**\n\n"
        f"شماره کارت:\n`{PAYMENT_CARD}`\n"
        f"به نام: **{CARD_HOLDER}**\n\n"
        f"⚠️ پس از واریز، تصویر فیش پرداخت خود را ارسال فرمایید:\n"
        f"(یا در صورت تمایل برای تغییر پلن، روی دکمه بازگشت کلیک کنید)"
    )
    await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(PaymentStates.waiting_for_receipt)
    await callback.answer()

# --- دریافت و ارسال فیش به ادمین ---
@dp.message(PaymentStates.waiting_for_receipt, F.content_type == ContentType.PHOTO)
async def process_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("selected_plan", "اشتراک")
    price = data.get("plan_price", "نامشخص")
    photo_id = message.photo[-1].file_id

    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تایید و تحویل", callback_data=f"adm_ok_{message.from_user.id}"),
                InlineKeyboardButton(text="❌ رد درخواست", callback_data=f"adm_no_{message.from_user.id}")
            ]
        ]
    )
    
    admin_caption = (
        f"🧾 **فیش واریزی جدید**\n\n"
        f"👤 کاربر: {message.from_user.full_name} (`{message.from_user.id}`)\n"
        f"آیدی: @{message.from_user.username or 'ندارد'}\n"
        f"📦 پلن انتخابی: {plan_name}\n"
        f"💰 مبلغ: {price} تومان"
    )
    
    await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_caption, reply_markup=admin_kb, parse_mode="Markdown")
    await message.answer("✅ فیش شما با موفقیت برای مدیریت ارسال شد. پس از بررسی و تایید، اشتراک شما ارسال می‌گردد.", reply_markup=get_main_keyboard())
    await state.clear()

# --- مدیریت تایید/رد فیش ---
@dp.callback_query(F.data.startswith("adm_ok_"))
async def admin_approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    await bot.send_message(user_id, "✅ پرداخت شما تایید شد.\nکانفیگ اختصاصی شما به‌زودی از سمت پشتیبانی ارسال می‌گردد.")
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🟢 **تایید شد.**")
    await callback.answer()

@dp.callback_query(F.data.startswith("adm_no_"))
async def admin_reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    await bot.send_message(user_id, "❌ فیش واریزی شما تایید نشد. لطفاً در صورت مغایرت با پشتیبانی در تماس باشید.")
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🔴 **رد شد.**")
    await callback.answer()

# --- اطلاعات حساب و اشتراک‌ها ---
@dp.message(F.text == "📊 اطلاعات حساب")
async def user_info(message: types.Message):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    balance = to_persian_digits(row[0]) if row else "۰"
    await message.answer(
        f"👤 شناسه کاربری: `{message.from_user.id}`\n"
        f"نام: {message.from_user.full_name}\n"
        f"💰 موجودی حساب: {balance} تومان",
        parse_mode="Markdown"
    )

@dp.message(F.text == "💎 اشتراک‌های من")
async def user_subs(message: types.Message):
    cursor.execute("SELECT plan_name, config, created_at FROM subscriptions WHERE user_id = ?", (message.from_user.id,))
    subs = cursor.fetchall()
    if not subs:
        await message.answer("شما در حال حاضر هیچ اشتراک فعالی ندارید.")
        return
    text = "💎 **اشتراک‌های فعال شما:**\n\n"
    for s in subs:
        text += f"📦 پلن: {s[0]}\n🔑 کانفیگ: `{s[1]}`\n📅 تاریخ: {s[2]}\n-------------------\n"
    await message.answer(text, parse_mode="Markdown")

# --- شارژ حساب ---
@dp.message(F.text == "💰 شارژ حساب")
async def charge_account(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💬 ارتباط با پشتیبانی جهت ارسال فیش", url=f"https://t.me/{SUPPORT_ID}")]]
    )
    await message.answer(
        f"💳 **افزایش موجودی و شارژ کیف پول**\n\n"
        f"جهت شارژ حساب کاربری، مبلغ مورد نظر را به شماره کارت زیر واریز نمایید:\n\n"
        f"`{PAYMENT_CARD}`\n"
        f"به نام: **{CARD_HOLDER}**\n\n"
        f"سپس تصویر فیش و شناسه عددی خود را از طریق دکمه زیر برای بخش مالی ارسال فرمایید 👇",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# --- پشتیبانی ---
@dp.message(F.text == "👥 پشتیبانی")
async def support(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💬 ارتباط با پشتیبانی", url=f"https://t.me/{SUPPORT_ID}")]]
    )
    await message.answer("👨‍💻 برای ارتباط مستقیم با کارشناسان فنی و پاسخگویی سریع، روی دکمه زیر کلیک فرمایید:", reply_markup=kb)

# --- کانفیگ‌ها و آموزش اتصال ---
@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def configs_tutorial(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📢 عضویت در کانال آموزش و کانفیگ", url=CHANNEL_LINK)]]
    )
    await message.answer("جهت مشاهده آموزش‌های اتصال (اندروید، آیفون، ویندوز) و دریافت نرم‌افزارهای مورد نیاز، روی دکمه زیر کلیک کنید:", reply_markup=kb)

# --- سوالات متداول ---
@dp.message(F.text == "❓ سوالات متداول")
async def faq(message: types.Message):
    faq_text = (
        "❓ **سوالات متداول کاربران:**\n\n"
        "🔹 **پروتکل اتصال چیست؟**\nکانفیگ‌ها همگی V2Ray اختصاصی و بهینه‌سازی‌شده برای تمامی اپراتورها هستند.\n\n"
        "🔹 **آیا بدون قطعی است؟**\nبله، سرورها دارای آی‌پی تمیز و سوییچ خودکار در زمان اختلال هستند.\n\n"
        "🔹 **چگونه فعال می‌شود؟**\nپس از واریز و ارسال فیش، کانفیگ اختصاصی در کمتر از چند دقیقه تحویل داده می‌شود."
    )
    await message.answer(faq_text, parse_mode="Markdown")

# --- وب‌سرور داخلی aiohttp برای Render ---
async def handle_health_check(request):
    return web.Response(text="Bot is healthy.", status=200)

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    app.router.add_get('/health', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logging.info(f"🚀 Render health server running on port {PORT}")

# --- نقطه اجرای اصلی ---
async def main():
    await run_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("🤖 Bot polling started.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")

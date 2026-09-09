import os
import asyncio
import logging
import sqlite3
import jdatetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# --- تنظیمات لاگینگ و متغیرهای محیطی ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", 10000))
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9918-0000-0000")
CARD_HOLDER = os.getenv("CARD_HOLDER", "مدیریت سرویس")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# --- تعرفه پلن‌های اشتراک ---
PLAN1_PRICE = 250000
PLAN2_PRICE = 400000
PLAN3_PRICE = 600000

# --- ماشین وضعیت برای پرداخت و ارسال فیش ---
class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

# --- مقداردهی دیتابیس ---
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, 
                        username TEXT, 
                        balance INTEGER DEFAULT 0,
                        join_date TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount INTEGER,
                        status TEXT,
                        created_at TEXT)''')
    conn.commit()
    conn.close()

# --- ساختار منوی اصلی ۴ ردیفه استاندارد ---
def get_main_menu():
    kb = [
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_menu():
    kb = [
        [KeyboardButton(text="🔙 بازگشت به منوی اصلی")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- هندلر استارت با متن کامل قدیمی، تاریخ، روز و ساعت شمسی ---
@dp.message(Command("start"))
@dp.message(F.text == "🔙 بازگشت به منوی اصلی")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    # محاسبه زمان و تاریخ شمسی
    now = jdatetime.datetime.now()
    date_str = now.strftime('%Y/%m/%d')
    day_name = now.strftime('%A')
    time_str = now.strftime('%H:%M')
    
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, balance, join_date) VALUES (?, ?, 0, ?)",
                   (user_id, username, f"{day_name} {date_str} {time_str}"))
    conn.commit()
    conn.close()

    welcome_text = (
        f"سلام <b>{message.from_user.first_name}</b> عزیز، به ربات L2TP VPN خوش آمدید.\n\n"
        f"📅 امروز: <b>{day_name}</b> - <b>{date_str}</b>\n"
        f"⏰ ساعت: <b>{time_str}</b>\n\n"
        f"💡 لطفاً جهت استفاده از امکانات و مدیریت سرویس‌های خود، از دکمه‌های منوی زیر استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

# --- خرید اشتراک و لاجیک پرداخت ---
@dp.message(F.text == "🛒 خرید اشتراک")
async def buy_subscription(message: types.Message):
    plans_text = (
        "<b>💎 تعرفه پلن‌های L2TP VPN:</b>\n\n"
        f"1️⃣ <b>پلن ۱ ماهه:</b> {PLAN1_PRICE:,} تومان\n"
        f"2️⃣ <b>پلن ۲ ماهه:</b> {PLAN2_PRICE:,} تومان\n"
        f"3️⃣ <b>پلن ۳ ماهه:</b> {PLAN3_PRICE:,} تومان\n\n"
        "جهت پرداخت و فعال‌سازی، پلن مورد نظر خود را انتخاب فرمایید:"
    )
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"پلن ۱ ({PLAN1_PRICE:,} ت)", callback_data="select_plan_1")],
        [InlineKeyboardButton(text=f"پلن ۲ ({PLAN2_PRICE:,} ت)", callback_data="select_plan_2")],
        [InlineKeyboardButton(text=f"پلن ۳ ({PLAN3_PRICE:,} ت)", callback_data="select_plan_3")],
        [InlineKeyboardButton(text="🔙 بستن منو", callback_data="close_menu")]
    ])
    await message.answer(plans_text, reply_markup=inline_kb)

@dp.callback_query(F.data.startswith("select_plan_"))
async def process_plan_selection(callback: types.CallbackQuery, state: FSMContext):
    plan_id = callback.data.split("_")[-1]
    prices = {"1": PLAN1_PRICE, "2": PLAN2_PRICE, "3": PLAN3_PRICE}
    amount = prices.get(plan_id, PLAN1_PRICE)
    
    await state.update_data(selected_amount=amount, plan_id=plan_id)
    
    pay_text = (
        f"💳 <b>اطلاعات پرداخت پلن {plan_id} ماهه:</b>\n\n"
        f"💵 مبلغ قابل پرداخت: <b>{amount:,} تومان</b>\n"
        f"📌 شماره کارت: <code>{CARD_NUMBER}</code>\n"
        f"👤 بنام: <b>{CARD_HOLDER}</b>\n\n"
        "⚠️ لطفاً پس از کارت‌به‌کارت، روی دکمه زیر کلیک کرده و تصویر فیش واریز را بفرستید:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 ارسال فیش واریزی", callback_data="send_receipt_btn")],
        [InlineKeyboardButton(text="🔙 بازگشت به پلن‌ها", callback_data="back_to_plans")]
    ])
    
    await callback.message.edit_text(pay_text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "back_to_plans")
async def back_to_plans_callback(callback: types.CallbackQuery):
    plans_text = (
        "<b>💎 تعرفه پلن‌های L2TP VPN:</b>\n\n"
        f"1️⃣ <b>پلن ۱ ماهه:</b> {PLAN1_PRICE:,} تومان\n"
        f"2️⃣ <b>پلن ۲ ماهه:</b> {PLAN2_PRICE:,} تومان\n"
        f"3️⃣ <b>پلن ۳ ماهه:</b> {PLAN3_PRICE:,} تومان\n\n"
        "جهت پرداخت و فعال‌سازی، پلن مورد نظر خود را انتخاب فرمایید:"
    )
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"پلن ۱ ({PLAN1_PRICE:,} ت)", callback_data="select_plan_1")],
        [InlineKeyboardButton(text=f"پلن ۲ ({PLAN2_PRICE:,} ت)", callback_data="select_plan_2")],
        [InlineKeyboardButton(text=f"پلن ۳ ({PLAN3_PRICE:,} ت)", callback_data="select_plan_3")],
        [InlineKeyboardButton(text="🔙 بستن منو", callback_data="close_menu")]
    ])
    await callback.message.edit_text(plans_text, reply_markup=inline_kb)
    await callback.answer()

@dp.callback_query(F.data == "close_menu")
async def close_menu_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()

@dp.callback_query(F.data == "send_receipt_btn")
async def ask_for_receipt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PaymentStates.waiting_for_receipt)
    await callback.message.delete()
    await callback.message.answer(
        "📷 لطفاً تصویر فیش واریز را ارسال نمایید:\n(جهت انصراف دکمه بازگشت به منوی اصلی را بزنید)",
        reply_markup=get_cancel_menu()
    )
    await callback.answer()

@dp.message(PaymentStates.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    amount = user_data.get("selected_amount", 0)
    plan_id = user_data.get("plan_id", "-")
    photo_id = message.photo[-1].file_id
    user = message.from_user
    
    now = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO payments (user_id, amount, status, created_at) VALUES (?, ?, 'pending', ?)",
                   (user.id, amount, now))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()

    if ADMIN_ID != 0:
        admin_caption = (
            f"🔔 <b>فیش واریزی جدید</b>\n\n"
            f"🆔 شناسه پرداخت: <code>{payment_id}</code>\n"
            f"👤 خریدار: {user.full_name} (@{user.username or 'ندارد'})\n"
            f"🔢 شناسه عددی: <code>{user.id}</code>\n"
            f"📦 پلن انتخابی: <b>پلن {plan_id}</b>\n"
            f"💰 مبلغ: <b>{amount:,} تومان</b>\n"
            f"📅 زمان: {now}"
        )
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تأیید", callback_data=f"approve_{payment_id}_{user.id}"),
                InlineKeyboardButton(text="❌ رد", callback_data=f"reject_{payment_id}_{user.id}")
            ]
        ])
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_caption, reply_markup=admin_kb)

    await state.clear()
    await message.answer(
        "✅ <b>فیش با موفقیت ثبت و به پشتیبانی ارسال شد.</b>\nبه محض بررسی، نتیجه به اطلاع شما خواهد رسید.",
        reply_markup=get_main_menu()
    )

@dp.message(PaymentStates.waiting_for_receipt)
async def invalid_receipt(message: types.Message):
    await message.answer("⚠️ لطفاً فایل را به صورت تصویر ارسال نمایید یا دکمه بازگشت را انتخاب کنید.", reply_markup=get_cancel_menu())

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: types.CallbackQuery):
    _, payment_id, user_id = callback.data.split("_")
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status = 'approved' WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ <b>تأیید شد.</b>", reply_markup=None)
    await bot.send_message(chat_id=int(user_id), text=f"🎉 <b>فیش واریزی شما (کد {payment_id}) توسط مدیریت تأیید گردید.</b>")
    await callback.answer("تأیید شد.")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: types.CallbackQuery):
    _, payment_id, user_id = callback.data.split("_")
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE payments SET status = 'rejected' WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ <b>رد شد.</b>", reply_markup=None)
    await bot.send_message(chat_id=int(user_id), text=f"⚠️ <b>فیش واریزی شما (کد {payment_id}) مورد تأیید قرار نگرفت.</b>")
    await callback.answer("رد شد.")

# --- بخش‌های اطلاعات حساب و سایر منوها ---
@dp.message(F.text == "📊 اطلاعات حساب")
async def account_info(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, join_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    balance = row[0] if row else 0
    join_date = row[1] if row else "نامشخص"

    info_text = (
        "<b>📊 اطلاعات حساب کاربری:</b>\n\n"
        f"👤 شناسه عددی: <code>{user_id}</code>\n"
        f"💰 موجودی کیف پول: <b>{balance:,} تومان</b>\n"
        f"📅 تاریخ و زمان عضویت: <b>{join_date}</b>\n"
    )
    await message.answer(info_text)

@dp.message(F.text == "💎 اشتراک‌های من")
async def my_subs(message: types.Message):
    await message.answer("💎 <b>اشتراک‌های شما:</b>\n\nدر حال حاضر هیچ اشتراک فعالی ثبت نشده است.")

@dp.message(F.text == "💰 شارژ حساب")
async def charge_account(message: types.Message):
    charge_text = (
        "<b>💰 شارژ حساب کاربری:</b>\n\n"
        f"📌 شماره کارت: <code>{CARD_NUMBER}</code>\n"
        f"👤 بنام: <b>{CARD_HOLDER}</b>\n\n"
        "پس از انتقال وجه، از منوی «🛒 خرید اشتراک» پلن مورد نظر را انتخاب و فیش را بفرستید."
    )
    await message.answer(charge_text)

@dp.message(F.text == "👥 پشتیبانی")
async def support(message: types.Message):
    await message.answer("👥 <b>ارتباط با پشتیبانی:</b>\n\nبرای پیگیری سفارش‌ها و سوالات فنی:\n📩 @AdminSupport")

@dp.message(F.text == "❓ سوالات متداول")
async def faq(message: types.Message):
    faq_text = (
        "<b>❓ سوالات متداول:</b>\n\n"
        "• پروتکل ارائه شده چیست؟ L2TP/IPSec با کلید اختصاصی\n"
        "• روی چه دستگاه‌هایی کار می‌کند؟ اندروید، آیفون، ویندوز و مکینتاش بدون نیاز به نرم‌افزار جانبی."
    )
    await message.answer(faq_text)

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def config_help(message: types.Message):
    help_text = (
        "<b>⚙️ راهنمای اتصال به VPN:</b>\n\n"
        "۱. وارد تنظیمات شبکه و VPN گوشی یا سیستم شوید.\n"
        "۲. یک کانکشن از نوع L2TP/IPSec PSK ایجاد کنید.\n"
        "۳. آدرس سرور، نام کاربری، رمز و Secret دریافتی را وارد نمایید."
    )
    await message.answer(help_text)

# --- وب‌سرور داخلی برای هماهنگی با Health Check در پلتفرم Render ---
async def handle(request):
    return web.Response(text="Bot is running smoothly on Render!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logging.info(f"Web server successfully bound to port {PORT}")

# --- تابع اصلی ---
async def main():
    init_db()
    await start_web_server()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot execution terminated.")

import os
import asyncio
import logging
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

# ---------------------------------------------------------
# تنظیمات لاگینگ
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ArshavinBot")

# ---------------------------------------------------------
# متغیرهای محیطی
# ---------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENqev02inbatX0X")
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "02786850266")
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    ADMIN_ID = 2786850266

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support")
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", "10000"))

# سرورها و تنظیمات پیش‌فرض اتصال
VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = ".12345678"

# ---------------------------------------------------------
# راه‌اندازی دیتابیس SQLite
# ---------------------------------------------------------
DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_name TEXT,
            price TEXT,
            photo_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str, full_name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", "10000"))

# سرورها و تنظیمات پیش‌فرض اتصال
VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = ".12345678"

# ---------------------------------------------------------
# راه‌اندازی دیتابیس SQLite
# ---------------------------------------------------------
DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_name TEXT,
            price TEXT,
            photo_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str, full_name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IG
# کیبوردها
# ---------------------------------------------------------
def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(text="💎 خرید اشتراک جدید", callback_data="buy_service"),
            InlineKeyboardButton(text="📊 تعرفه قیمت‌ها", callback_data="tariffs")
        ],
        [
            InlineKeyboardButton(text="🎁 طرح جبرانی مشترکین قدیمی", callback_data="compensation_plan"),
            InlineKeyboardButton(text="🌐 ورود به پنل کاربری", callback_data="user_panel")
        ],
        [
            InlineKeyboardButton(text="⚙️ مشخصات و راهنمای اتصال", callback_data="connection_info"),
            InlineKeyboardButton(text=" پشتیبانی آنلاین", callback_data="support_info")
        ],
        [
            InlineKeyboardButton(text="📢 عضویت در کانال اطلاع‌رسانی", url=CHANNEL_URL)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def plans_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="۱ ماهه تک‌کاربره (۲۰۰,۰۰۰ ت)", callback_data="plan_1m_1u")],
        [InlineKeyboardButton(text="۱ ماهه دوکاربره (۲۵۰,۰۰۰ ت)", callback_data="plan_1m_2u")],
        [InlineKeyboardButton(text="۲ ماهه تک‌کاربره (۳۸۰,۰۰۰ ت)", callback_data="plan_2m_1u")],
        [InlineKeyboardButton(text="۲ ماهه دوکاربره (۴۳۰,۰۰۰ ت)", callback_data="plan_2m_2u")],
        [InlineKeyboardButton(text="۳ ماهه تک‌کاربره (۵۵۰,۰۰۰ ت)", callback_data="plan_3m_1u")],
        [InlineKeyboardButton(text="۳ ماهه دوکاربره (۶۰۰,۰۰۰ ت)", callback_data="plan_3m_2u")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ])

PLANS_INFO = {
    "plan_1m_1u": ("۱ ماهه تک کاربره (+۱۰ گیگ هدیه)", "۲۰۰,۰۰۰"),
    "plan_1m_2u": ("۱ ماهه دو کاربره (+۱۰ گیگ هدیه)", "۲۵۰,۰۰۰"),
    "plan_2m_1u": ("۲ ماهه تک کاربره (+۱۰ گیگ هدیه)", "۳۸۰,۰۰۰"),
    "plan_2m_2u": ("۲ ماهه دو کاربره (+۱۰ گیگ هدیه)", "۴۳۰,۰۰۰"),
    "plan_3m_1u": ("۳ ماهه تک کاربره (+۱۰ گیگ هدیه)", "۵۵۰,۰۰۰"),
    "plan_3m_2u": ("۳ ماهه دو کاربره (+۱۰ گیگ هدیه)", "۶۰۰,۰۰۰"),
}

# ---------------------------------------------------------
# ساخت ربات و دیسپچر
# ---------------------------------------------------------
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ---------------------------------------------------------
# هندلرهای دستورات و دکمه‌ها
# ---------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    add_user(user.id, user.username, user.full_name)

    welcome_text = (
        f"سلام {user.first_name} عزیز، به ربات رسمی **L2TP VPN 24/7** خوش آمدید! 🌸\n\n"
        "⚡️ ارائه سرورهای پرسرعت و پایدار L2TP / Cisco / OpenVPN\n"
        "✨ مناسب تمامی سیستم‌عامل‌ها (iOS، Android، Windows، Modem Router)\n\n"
        "از دکمه‌های زیر برای انتخاب بخش مورد نظرتان استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_main")
async def cb_back_to_main(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    welcome_text = (
        "🏠 منوی اصلی ربات **L2TP VPN 24/7**:\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب نمایید:"
    )
    await call.message.edit_text(welcome_text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "tariffs")
async def cb_tariffs(call: types.CallbackQuery):
    tariffs_text = (
        "📊 **لیست تعرفه‌ها و قیمت‌های جدید سرویس VPN:**\n\n"
        "🔹 **یک ماهه تک‌کاربره:** ۲۰۰,۰۰۰ تومان\n"
        "🔹 **یک ماهه دوکاربره:** ۲۵۰,۰۰۰ تومان\n"
        "🔸 **دو ماهه تک‌کاربره:** ۳۸۰,۰۰۰ تومان\n"
        "🔸 **دو ماهه دوکاربره:** ۴۳۰,۰۰۰ تومان\n"
        "🔹 **سه ماهه تک‌کاربره:** ۵۵۰,۰۰۰ تومان\n"
        "🔹 **سه ماهه دوکاربره:** ۶۰۰,۰۰۰ تومان\n\n"
        "🎁 **هدیه ویژه:** تمامی پلن‌ها شامل **۱۰ گیگابایت ترافیک هدیه** می‌باشند.\n"
        "💳 شماره کارت جهت واریز:\n"
        f"`{PAYMENT_CARD}`\n"
        f"به نام: **{PAYMENT_NAME}**"
    )
    await call.message.edit_text(tariffs_text, reply_markup=back_keyboard(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "connection_info")
async def cb_connection_info(call: types.CallbackQuery):
    info_text = (
        "⚙️ **مشخصات سرور و راهنمای تنظیم اتصال:**\n\n"
        f"🌐 **Server Address / آدرس سرور:**\n`{VPN_SERVER_IP}`\n\n"
        f"🔑 **IPsec Pre-Shared Key (سکرت):**\n`{IPSEC_SECRET}`\n\n"
        "📌 **نکات مهم:**\n"
        "۱. در تنظیمات L2TP/IPsec گوشی یا مودم، آدرس سرور و کلید بالا را وارد کنید.\n"
        "۲. نام کاربری و رمز عبور اختصاصی خود را وارد نمایید.\n"
        "۳. در صورت بروز هرگونه مشکل با پشتیبانی در ارتباط باشید."
    )
    await call.message.edit_text(info_text, reply_markup=back_keyboard(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "user_panel")
async def cb_user_panel(call: types.CallbackQuery):
    panel_text = (
        "🌐 **ورود به پنل مدیریت اکانت (IBSng):**\n\n"
        "⚠️ **توجه مهم:**\n"
        "«برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.»\n\n"
        f"🔗 [ورود مستقیم به پنل کاربری]({IBSNG_PANEL_URL})\n\n"
        "در پنل کاربری می‌توانید حجم باقی‌مانده، اعتبار زمانی و تاریخ انقضای سرویس خود را مشاهده نمایید."
    )
    await call.message.edit_text(panel_text, reply_markup=back_keyboard(), parse_mode="Markdown", disable_web_page_preview=True)
    await call.answer()

@dp.callback_query(F.data == "support_info")
async def cb_support_info(call: types.CallbackQuery):
    support_text = (
        " **پشتیبانی ۲۴ ساعته سرویس:**\n\n"
        "در صورت وجود هرگونه سؤال، قطعی، نیاز به راهنمایی در کانفیگ یا فعال‌سازی سرویس با آیدی پشتیبانی در ارتباط باشید:\n\n"
        f"👤 پشتیبانی: {SUPPORT_ID}\n"
        f"📢 کانال رسمی: {CHANNEL_URL}\n"
        f"🤖 ربات رسمی: @L2TP_Arshavin_Bot"
    )
    await call.message.edit_text(support_text, reply_markup=back_keyboard(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "compensation_plan")
async def cb_compensation_plan(call: types.CallbackQuery, state: FSMContext):
    comp_text = (
        "🎁 **طرح جبرانی ویژه مشترکین وفادار و قدیمی:**\n\n"
        "مشترکین عزیزی که در طول ۲ تا ۳ سال گذشته اشتراک تهیه کرده بودند و در زمان غیبت ما سرویس‌شان قطع شده بود:\n\n"
        "جهت جبران و حفظ حق شما عزیزان، اکانت شما با **دوره کامل جدید + ۱۰ گیگابایت حجم هدیه** به صورت رایگان تمدید و فعال می‌شود.\n\n"
        "لطفاً **نام کاربری قبلی** یا **تصویر فیش واریزی قدیمی** خود را در یک پیام همین حالا ارسال کنید:"
    )
    await state.set_state(CompensationState.waiting_for_details)
    await call.message.edit_text(comp_text, reply_markup=back_keyboard(), parse_mode="Markdown")
    await call.answer()

@dp.message(CompensationState.waiting_for_details)
async def process_compensation(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    notify_text = (
        f"🚨 **درخواست طرح جبرانی جدید:**\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 شناسه عددی: `{user.id}`\n\n"
        f"📝 پیام/اطلاعات ارسالی کاربر:\n{message.text or '[فایل یا مدیا ارسال شده]'}"
    )
    try:
        await bot.send_message(ADMIN_ID, notify_text, parse_mode="Markdown")
        if message.photo:
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption="فیش طرح جبرانی")
    except Exception as e:
        logger.error(f"Error forwarding compensation to admin: {e}")

    await message.answer(
        "✅ اطلاعات شما برای مدیریت ارسال شد.\nپس از بررسی اکانت، سرویس شما فعال و مشخصات جدید برایتان ارسال خواهد شد.",
        reply_markup=back_keyboard()
    )

@dp.callback_query(F.data == "buy_service")
async def cb_buy_service(call: types.CallbackQuery):
    await call.message.edit_text(
        "💎 لطفاً پلن مد نظر خود را برای خرید انتخاب فرمایید:",
        reply_markup=plans_keyboard(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query(F.data.startswith("plan_"))
async def cb_select_plan(call: types.CallbackQuery, state: FSMContext):
    plan_key = call.data
    if plan_key not in PLANS_INFO:
        await call.answer("پلن نامعتبر است.")
        return

    plan_name, price = PLANS_INFO[plan_key]
    await state.update_data(selected_plan=plan_name, plan_price=price)
    await state.set_state(OrderState.waiting_for_receipt)

    pay_text = (
        f"پلن انتخابی شما: **{plan_name}**\n"
        f"مبلغ قابل پرداخت: **{price} تومان**\n\n"
        "💳 لطفاً مبلغ فوق را به شماره کارت زیر واریز فرمایید:\n"
        f"`{PAYMENT_CARD}`\n"
        f"به نام: **{PAYMENT_NAME}**\n\n"
        "📷 سپس **تصویر رسید (عکس فیش واریزی)** را به صورت عکس در چت ارسال کنید:"
    )
    await call.message.edit_text(pay_text, reply_markup=back_keyboard(), parse_mode="Markdown")
    await call.answer()

@dp.message(OrderState.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("selected_plan", "نامشخص")
    price = data.get("plan_price", "نامشخص")
    photo_id = message.photo[-1].file_id
    user = message.from_user

    receipt_id = save_receipt(user.id, plan_name, price, photo_id)
    await state.clear()

    # ارسال به ادمین
    admin_caption = (
        f"🧾 **فیش واریزی جدید دریافت شد!** (شناسه: #{receipt_id})\n\n"
        f"👤 خریدار: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 شناسه: `{user.id}`\n"
        f"📦 پلن: {plan_name}\n"
        f"💰 مبلغ: {price} تومان"
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=" تایید پرداخت", callback_data=f"verify_{receipt_id}_{user.id}"),
            InlineKeyboardButton(text="❌ رد پرداخت", callback_data=f"reject_{receipt_id}_{user.id}")
        ]
    ])

    try:
        await bot.send_photo(ADMIN_ID, photo_id, caption=admin_caption, reply_markup=admin_kb, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending receipt to admin: {e}")

    await message.answer(
        "✅ فیش واریزی شما با موفقیت دریافت و برای پشتیبانی ارسال شد.\n"
        "پس از بررسی، اکانت شما فوراً صادر و در همین ربات برایتان ارسال خواهد شد. متشکریم از صبوری شما! 🌸",
        reply_markup=back_keyboard()
    )

@dp.message(OrderState.waiting_for_receipt)
async def process_receipt_invalid(message: types.Message):
    await message.answer("لطفاً فیش واریزی را فقط به صورت **عکس (Photo)** ارسال کنید.")

# ---------------------------------------------------------
# هندلرهای ادمین (تایید / رد فیش)
# ---------------------------------------------------------
@dp.callback_query(F.data.startswith("verify_"))
async def cb_admin_verify(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("دسترسی غیرمجاز!", show_alert=True)
        return

    parts = call.data.split("_")
    receipt_id = int(parts[1])
    target_user_id = int(parts[2])

    update_receipt_status(receipt_id, "approved")
    await call.message.edit_caption(
        caption=call.message.caption + "\n\n✅ **تایید شد** توسط مدیریت.",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await call.answer("پرداخت تایید شد.")

    # پیام تایید به خریدار
    msg_to_user = (
        "🎉 **پرداخت شما تایید شد!**\n\n"
        "اکانت اختصاصی شما به زودی فعال و ارسال می‌شود.\n"
        f"سرور اتصال: `{VPN_SERVER_IP}`\n"
        f"سکرت: `{IPSEC_SECRET}`"
    )
    try:
        await bot.send_message(target_user_id, msg_to_user, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Could not notify user {target_user_id}: {e}")

@dp.callback_query(F.data.startswith("reject_"))
async def cb_admin_reject(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("دسترسی غیرمجاز!", show_alert=True)
        return

    parts = call.data.split("_")
    receipt_id = int(parts[1])
    target_user_id = int(parts[2])

    update_receipt_status(receipt_id, "rejected")
    await call.message.edit_caption(
        caption=call.message.caption + "\n\n❌ **رد شد** توسط مدیریت.",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await call.answer("پرداخت رد شد.")

    try:
        await bot.send_message(
            target_user_id,
            f"❌ متأسفانه فیش واریزی ارسالی شما تایید نشد.\nجهت پیگیری لطفاً با پشتیبانی {SUPPORT_ID} در ارتباط باشید.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Could not notify user {target_user_id}: {e}")

# ---------------------------------------------------------
# وب‌سرور داخلی سلامت (Aiohttp Web Server) برای Render
# ---------------------------------------------------------
async def health_check_handler(request):
    return web.Response(text="Bot and Health Server are OK 200", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check web server is listening on port {PORT}")

# ---------------------------------------------------------
# تابع اصلی راه‌اندازی ربات
# ---------------------------------------------------------
async def main():
    logger.info("Initializing database...")
    init_db()

    logger.info("Starting health check web server for Render...")
    await start_web_server()

    logger.info("Resetting webhook and dropping old updates...")
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Starting bot polling...")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

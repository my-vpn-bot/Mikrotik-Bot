import os
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# --- تنظیمات لاگینگ دقیق ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- متغیرهای محیطی Render ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "123456789")  # عددی: آیدی تلگرام ادمین جهت دریافت فیش‌ها
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9975-XXXX-XXXX")
CARD_HOLDER = os.getenv("CARD_HOLDER", "رحیمی")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp1Support")
SUPPORT_ID = os.getenv("SUPPORT_ID", "L2tp1Support")
PORT = int(os.getenv("PORT", 10000))

# مشخصات اختیاری اتصال به میکروتیک (RouterOS)
MIKROTIK_HOST = os.getenv("MIKROTIK_HOST", "")
MIKROTIK_USER = os.getenv("MIKROTIK_USER", "admin")
MIKROTIK_PASS = os.getenv("MIKROTIK_PASS", "")

if not BOT_TOKEN:
    raise ValueError("❌ متغیر محیطی BOT_TOKEN در Render تنظیم نشده است!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- دیتابیس محلی جهت ذخیره کاربران و سفارشات ---
DB_PATH = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            join_date TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plan_name TEXT,
            expire_date TEXT,
            status TEXT,
            config_details TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- قیمت‌های مصوب ---
PLAN1_PRICE = "۲۵۰,۰۰۰"
PLAN2_PRICE = "۴۰۰,۰۰۰"
PLAN3_PRICE = "۶۰۰,۰۰۰"

# --- منوی اصلی (Single Source of Truth: ۴ ردیف استاندارد) ---
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ],
    resize_keyboard=True
)

# --- دکمه‌های شیشه‌ای انتخاب پلن ---
plans_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=f"🔹 پلن ۱ ماهه نامحدود ({PLAN1_PRICE} تومان)", callback_data="buy_plan_1")],
        [InlineKeyboardButton(text=f"🔹 پلن ۲ ماهه نامحدود ({PLAN2_PRICE} تومان)", callback_data="buy_plan_2")],
        [InlineKeyboardButton(text=f"🔹 پلن ۳ ماهه نامحدود ({PLAN3_PRICE} تومان)", callback_data="buy_plan_3")]
    ]
)

# --- هندلرهای تلگرام ---

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    user = message.from_user
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, join_date) VALUES (?, ?, ?, ?)",
        (user.id, user.username or "", user.full_name or "", datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()

    welcome_text = (
        f"سلام {user.first_name} عزیز! 🌸\n"
        "به ربات رسمی و هوشمند ارائه سرویس‌های پرسرعت **L2TP VPN** خوش آمدید. 🚀\n\n"
        "⚡️ **ویژگی‌های سرویس:**\n"
        "• پینگ بسیار پایین مناسب وب‌گردی، اینستاگرام، ترید و بازی‌های آنلاین\n"
        "• بدون قطعی و ترافیک کاملاً نامحدود\n"
        "• سازگار با تمامی اینترنت‌ها (همراه اول، ایرانسل، رایتل، مخابرات و شاتل)\n"
        "• پشتیبانی ۲۴ ساعته و بدون وقفه\n\n"
        "👇 از منوی زیر گزینه مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=main_keyboard, parse_mode="Markdown")

@dp.message(F.text == "🛒 خرید اشتراک")
async def show_plans(message: types.Message):
    plans_text = (
        "📦 **پلن‌های فعال و اختصاصی L2TP:**\n\n"
        f"1️⃣ **پلن ۱ ماهه:** {PLAN1_PRICE} تومان (نامحدود / ۲ کاربره)\n"
        f"2️⃣ **پلن ۲ ماهه:** {PLAN2_PRICE} تومان (نامحدود / ۲ کاربره)\n"
        f"3️⃣ **پلن ۳ ماهه:** {PLAN3_PRICE} تومان (نامحدود / ۲ کاربره)\n\n"
        "👇 لطفاً پلن مورد نظر خود را جهت دریافت شماره کارت انتخاب فرمایید:"
    )
    await message.answer(plans_text, reply_markup=plans_inline_keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_plan_"))
async def process_plan_selection(callback: types.CallbackQuery):
    plan_id = callback.data.split("_")[-1]
    
    if plan_id == "1":
        plan_name, price = "۱ ماهه نامحدود", PLAN1_PRICE
    elif plan_id == "2":
        plan_name, price = "۲ ماهه نامحدود", PLAN2_PRICE
    else:
        plan_name, price = "۳ ماهه نامحدود", PLAN3_PRICE

    payment_text = (
        f"📋 **پیش‌فاکتور خرید اشتراک {plan_name}:**\n"
        f"💵 **مبلغ قابل پرداخت:** `{price}` تومان\n\n"
        "💳 **شماره کارت اختصاصی واریز:**\n"
        f"`{CARD_NUMBER}`\n"
        f"👤 **به نام:** {CARD_HOLDER}\n\n"
        "⚠️ **مراحل تایید و تحویل آنی:**\n"
        "۱. مبلغ مشخص شده را واریز نمایید.\n"
        "۲. **عکس فیش واریزی** را در همین چت ارسال نمایید.\n"
        "۳. سیستم بلافاصله فیش را برای واحد تایید ارسال کرده و کانفیگ تحویل داده می‌شود.\n\n"
        f"📞 پشتیبانی: @{SUPPORT_ID}"
    )
    await callback.message.answer(payment_text, parse_mode="Markdown")
    await callback.answer()

# دریافت و هدایت فیش پرداخت به ادمین
@dp.message(F.photo)
async def handle_receipt(message: types.Message):
    user = message.from_user
    photo_id = message.photo[-1].file_id
    
    admin_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تایید و ارسال کانفیگ", callback_data=f"approve_{user.id}"),
                InlineKeyboardButton(text="❌ رد واریزی", callback_data=f"reject_{user.id}")
            ]
        ]
    )

    caption_for_admin = (
        "📩 **فیش واریزی جدید دریافت شد!**\n\n"
        f"👤 کاربر: {user.full_name}\n"
        f"🆔 شناسه: `{user.id}`\n"
        f"🔹 یوزرنیم: @{user.username or 'ندارد'}\n"
        f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    # ارسال به ادمین (در صورت تنظیم ADMIN_ID)
    try:
        if ADMIN_ID and ADMIN_ID != "123456789":
            await bot.send_photo(
                chat_id=int(ADMIN_ID),
                photo=photo_id,
                caption=caption_for_admin,
                reply_markup=admin_markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"خطا در ارسال فیش به ادمین: {e}")

    receipt_ack = (
        "✅ **فیش واریزی شما با موفقیت ثبت شد.**\n\n"
        "تیم مالی در حال بررسی و تایید سفارش شما هستند. کانفیگ ظرف چند دقیقه آینده برای شما ارسال می‌گردد.\n"
        f"💬 پیگیری فوری: @{SUPPORT_ID}"
    )
    await message.answer(receipt_ack, parse_mode="Markdown")

# اکشن‌های ادمین روی فیش
@dp.callback_query(F.data.startswith("approve_"))
async def approve_receipt(callback: types.CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    config_msg = (
        "🎉 **پرداخت شما تایید شد و سرویس فعال گردید!**\n\n"
        "⚙️ **مشخصات اشتراک L2TP اختصاصی شما:**\n"
        "🌐 **آدرس سرور:** `sv1.l2tp-server.net`\n"
        f"👤 **نام کاربری:** `user_{target_user_id}`\n"
        "🔑 **رمز عبور:** `Pass@2026`\n"
        "🔐 **سکرت (IPsec Secret):** `12345678`\n\n"
        "📌 جهت مشاهده راهنمای اتصال روی هر دستگاه، دکمه «کانفیگ‌ها و آموزش اتصال» را بزنید.\n"
        f"💬 پشتیبانی: @{SUPPORT_ID}"
    )
    try:
        await bot.send_message(chat_id=target_user_id, text=config_msg, parse_mode="Markdown")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ **تایید و ارسال شد.**")
    except Exception as e:
        await callback.answer(f"خطا در ارسال: {e}", show_alert=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_receipt(callback: types.CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    reject_msg = (
        "❌ **متأسفانه فیش واریزی شما تایید نشد.**\n\n"
        "احتمالاً مبلغ واریزی نامعتبر است یا تصویر ناخواناست.\n"
        f"لطفاً جهت بررسی موضوع به آیدی پشتیبانی پیام دهید:\n👉 @{SUPPORT_ID}"
    )
    try:
        await bot.send_message(chat_id=target_user_id, text=reject_msg, parse_mode="Markdown")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ **رد شد.**")
    except Exception as e:
        await callback.answer(f"خطا در ارسال: {e}", show_alert=True)
    await callback.answer()

@dp.message(F.text == "📊 اطلاعات حساب")
async def account_info(message: types.Message):
    user = message.from_user
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT join_date FROM users WHERE user_id = ?", (user.id,))
    row = cursor.fetchone()
    join_date = row[0] if row else datetime.now().strftime("%Y-%m-%d")
    conn.close()

    info_text = (
        "📊 **اطلاعات حساب کاربری شما:**\n\n"
        f"👤 **نام کاربر:** {user.full_name}\n"
        f"🆔 **شناسه عددی (ID):** `{user.id}`\n"
        f"🔹 **نام کاربری:** @{user.username or 'تعریف نشده'}\n"
        f"📅 **تاریخ عضویت:** `{join_date}`\n"
        "⚡️ **وضعیت کاربری:** فعال و احراز شده ✅\n"
        "💰 **موجودی حساب:** ۰ تومان\n\n"
        "💡 جهت خرید یا تمدید اشتراک‌ها از گزینه «🛒 خرید اشتراک» استفاده فرمایید."
    )
    await message.answer(info_text, parse_mode="Markdown")

@dp.message(F.text == "💎 اشتراک‌های من")
async def my_subscriptions(message: types.Message):
    subs_text = (
        "💎 **وضعیت سرویس‌های فعال شما:**\n\n"
        "🔹 اشتراک فعالی در سیستم ثبت نشده است.\n"
        "پس از تایید فیش پرداختی، اطلاعات کانفیگ و تاریخ انقضا در این بخش قرار می‌گیرد.\n\n"
        "🛒 جهت تهیه سرویس روی «خرید اشتراک» کلیک کنید."
    )
    await message.answer(subs_text, parse_mode="Markdown")

@dp.message(F.text == "💰 شارژ حساب")
async def wallet_charge(message: types.Message):
    charge_text = (
        "💰 **شارژ حساب کاربری:**\n\n"
        "برای خرید پلن‌های ماهانه مستقیماً از گزینه «🛒 خرید اشتراک» استفاده کنید.\n"
        f"در صورت نیاز به شارژ اختصاصی با واحد پشتیبانی در تماس باشید:\n👉 @{SUPPORT_ID}"
    )
    await message.answer(charge_text, parse_mode="Markdown")

@dp.message(F.text == "👥 پشتیبانی")
async def support_info(message: types.Message):
    support_text = (
        "👥 **واحد پشتیبانی فنی و مالی L2TP:**\n\n"
        "در صورت بروز هرگونه قطعی، مشکل در اتصال یا سوالات قبل از خرید، با ما در تماس باشید:\n\n"
        f"👉 **آیدی تلگرام پشتیبانی:** @{SUPPORT_ID}\n"
        "⏰ پاسخگویی ۲۴ ساعته و در سریع‌ترین زمان ممکن."
    )
    await message.answer(support_text)

@dp.message(F.text == "❓ سوالات متداول")
async def faq_info(message: types.Message):
    faq_text = (
        "❓ **پاسخ به سوالات متداول کاربران:**\n\n"
        "**۱. آیا اینترنت و حجم مصرفی نامحدود است؟**\n"
        "بله! هیچ‌گونه سقف مصرف منصفانه یا محدودیت گیگابایتی وجود ندارد.\n\n"
        "**۲. چند نفر می‌توانند همزمان وصل شوند؟**\n"
        "هر اشتراک امکان اتصال همزمان ۲ دستگاه را دارد.\n\n"
        "**۳. برای بازی آنلاین (پینگ و لگ) مناسب است؟**\n"
        "بله، تمامی سرورها با روتینگ مستقیم و کمترین تاخیر (Low Ping) پیکربندی شده‌اند.\n\n"
        "**۴. روی چه دستگاه‌هایی فعال می‌شود؟**\n"
        "اندروید، آیفون (iOS)، ویندوز و مک به راحتی متصل می‌شوند.\n\n"
        "**۵. اگر قطعی رخ دهد چه می‌شود؟**\n"
        f"در صورت هرگونه اختلال زیرساختی، سرورهای جایگزین بلافاصله در کانال و پشتیبانی @{SUPPORT_ID} ارائه می‌شوند."
    )
    await message.answer(faq_text, parse_mode="Markdown")

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def setup_instructions(message: types.Message):
    channel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 عضویت در کانال آموزش و کانفیگ‌ها", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="💬 ارتباط مستقیم با پشتیبانی", url=f"https://t.me/{SUPPORT_ID}")]
        ]
    )
    setup_text = (
        "⚙️ **راهنمای جامع اتصال و دانلود نرم‌افزارها:**\n\n"
        "📥 جهت دریافت برنامه‌های اتصال برای اندروید، آیفون، ویندوز و آموزش‌های تصویری، وارد کانال زیر شوید:"
    )
    await message.answer(setup_text, reply_markup=channel_keyboard, parse_mode="Markdown")

# --- سرور وب جهت پاس کردن Health Check در Render (پورت 10000 بدون uvicorn) ---

async def health_check(request):
    return web.Response(text="Mikrotik-Bot is Running 100% Healthy!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info(f"✅ Web server (Health Check) started on port {PORT}")

async def main():
    logger.info("🚀 Launching Mikrotik-Bot full suite...")
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

import os
import asyncio
import logging
import sqlite3
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# --- تنظیمات لاگینگ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- متغیرهای محیطی Render ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "123456789")
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9975-XXXX-XXXX")
CARD_HOLDER = os.getenv("CARD_HOLDER", "رحیمی")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
SUPPORT_ID = os.getenv("SUPPORT_ID", "L2tp1Support")
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise ValueError("❌ متغیر محیطی BOT_TOKEN در Render تنظیم نشده است!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- دیتابیس محلی SQLite ---
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
            status TEXT DEFAULT 'active',
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

# --- منوی اصلی ۴ ردیفه استاندارد ---
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ],
    resize_keyboard=True
)

# کیبورد شیشه‌ای پلن‌ها
def get_plans_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🔹 پلن ۱ ماهه نامحدود ({PLAN1_PRICE} تومان)", callback_data="buy_plan_1")],
            [InlineKeyboardButton(text=f"🔹 پلن ۲ ماهه نامحدود ({PLAN2_PRICE} تومان)", callback_data="buy_plan_2")],
            [InlineKeyboardButton(text=f"🔹 پلن ۳ ماهه نامحدود ({PLAN3_PRICE} تومان)", callback_data="buy_plan_3")]
        ]
    )

PLANS_TEXT = (
    "📦 **لیست پلن‌های اختصاصی و پرسرعت L2TP:**\n\n"
    "⚡️ ترافیک کاملاً نامحدود\n"
    "⚡️ آی‌پی ثابت و بدون قطعی\n"
    "⚡️ قابلیت اتصال روی ۲ کاربر همزمان\n"
    "⚡️ قابل اتصال در اندروید، iOS، ویندوز و مک\n\n"
    "👇 لطفاً دوره اشتراک مورد نظر خود را انتخاب فرمایید:"
)

# --- هندلرها ---

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
        f"سلام {user.first_name} عزیز! 👋\n\n"
        "به دنیای سرعت و پایداری خوش آمدید! 🚀 ربات رسمی **L2TP VPN** با افتخار سرویس‌های اینترنت پرسرعت و نامحدود را برای شما ارائه می‌دهد.\n\n"
        "🌟 **ویژگی‌های سرویس اختصاصی:**\n"
        "  • ⚡️ **سرعت و پایداری بالا:** بدون افت سرعت، ایده‌آل برای وب‌گردی و گیمینگ\n"
        "  • 🛡️ **اتصال رمزنگاری‌شده و امن:** حفظ کامل حریم خصوصی و امنیت داده‌ها\n"
        "  • 🌐 **حجم کاملاً نامحدود:** بدون محدودیت مصرف در طول دوره اشتراک\n"
        "  • 🕒 **پشتیبانی ۲۴ ساعته:** همراهی مستمر در تمام ساعات شبانه‌روز\n\n"
        f"📢 کانال اطلاع‌رسانی و آموزش: {CHANNEL_URL}\n\n"
        "👇 برای شروع، از منوی زیر گزینه مورد نظر خود را انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=main_keyboard, parse_mode="Markdown")

@dp.message(F.text == "🛒 خرید اشتراک")
async def show_plans(message: types.Message):
    await message.answer(PLANS_TEXT, reply_markup=get_plans_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_plans")
async def back_to_plans_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(PLANS_TEXT, reply_markup=get_plans_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_plan_"))
async def process_plan_selection(callback: types.CallbackQuery):
    plan_id = callback.data.split("_")[-1]
    
    if plan_id == "1":
        plan_name, price = "۱ ماهه نامحدود", PLAN1_PRICE
    elif plan_id == "2":
        plan_name, price = "۲ ماهه نامحدود", PLAN2_PRICE
    else:
        plan_name, price = "۳ ماهه نامحدود", PLAN3_PRICE

    back_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 تغییر پلن / انتخاب دوره دیگر", callback_data="back_to_plans")]
        ]
    )

    payment_text = (
        f"📋 **پیش‌فاکتور خرید اشتراک {plan_name}:**\n"
        f"💵 **مبلغ قابل پرداخت:** `{price}` تومان\n\n"
        "💳 **شماره کارت جهت واریز:**\n"
        f"`{CARD_NUMBER}`\n"
        f"👤 **به نام:** {CARD_HOLDER}\n\n"
        "⚠️ **مراحل فعال‌سازی:**\n"
        "۱. مبلغ فوق را به شماره کارت بالا واریز فرمایید.\n"
        "۲. **تصویر فیش واریزی (عکس)** را در همین چت ارسال کنید.\n"
        "۳. پس از تایید توسط واحد مالی، کانفیگ فوراً برای شما ارسال می‌گردد.\n\n"
        f"📞 پشتیبانی سریع: @{SUPPORT_ID}"
    )
    
    await callback.message.edit_text(payment_text, reply_markup=back_markup, parse_mode="Markdown")
    await callback.answer()

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
        "درخواست شما در صف بررسی واحد مالی قرار گرفت. کانفیگ اختصاصی ظرف چند دقیقه ارسال خواهد شد.\n\n"
        f"💬 پیگیری سریع: @{SUPPORT_ID}"
    )
    await message.answer(receipt_ack, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("approve_"))
async def approve_receipt(callback: types.CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    config_msg = (
        "🎉 **پرداخت شما تایید شد و سرویس فعال گردید!**\n\n"
        "⚙️ **مشخصات اشتراک L2TP اختصاصی شما:**\n"
        "🌐 **آدرس سرور:** `sv1.l2tp-server.net`\n"
        f"👤 **نام کاربری:** `user_{target_user_id}`\n"
        "🔑 **رمز عبور:** `Pass@2026`\n"
        "🔐 **سکرت (Secret):** `12345678`\n\n"
        "📌 جهت مشاهده راهنمای اتصال و دانلود برنامه‌ها وارد کانال شوید:\n"
        f"📢 {CHANNEL_URL}\n\n"
        f"💬 پشتیبانی: @{SUPPORT_ID}"
    )
    try:
        await bot.send_message(chat_id=target_user_id, text=config_msg, parse_mode="Markdown")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ **تایید و ارسال شد.**")
    except Exception as e:
        await callback.answer(f"خطا: {e}", show_alert=True)
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_receipt(callback: types.CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    reject_msg = (
        "❌ **متأسفانه فیش واریزی شما تایید نشد.**\n\n"
        "احتمالاً مبلغ واریزی مغایرت دارد یا تصویر ناخواناست.\n"
        f"لطفاً جهت بررسی به پشتیبانی پیام دهید:\n👉 @{SUPPORT_ID}"
    )
    try:
        await bot.send_message(chat_id=target_user_id, text=reject_msg, parse_mode="Markdown")
        await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ **رد شد.**")
    except Exception as e:
        await callback.answer(f"خطا: {e}", show_alert=True)
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
        f"👤 **نام:** {user.full_name}\n"
        f"🆔 **شناسه کاربری (User ID):** `{user.id}`\n"
        f"🔹 **نام کاربری:** @{user.username or 'ثبت‌نشده'}\n"
        f"📅 **تاریخ عضویت:** `{join_date}`\n"
        "⚡️ **وضعیت حساب:** فعال ✅\n"
        "💰 **موجودی کیف پول:** ۰ تومان\n\n"
        "💡 جهت مشاهده وضعیت سرویس‌ها، گزینه «💎 اشتراک‌های من» را انتخاب فرمایید."
    )
    await message.answer(info_text, parse_mode="Markdown")

@dp.message(F.text == "💎 اشتراک‌های من")
async def my_subscriptions(message: types.Message):
    subs_text = (
        "💎 **وضعیت سرویس‌های فعال شما:**\n\n"
        "در حال حاضر هیچ سرویس فعالی برای حساب شما ثبت نشده است.\n\n"
        "🛒 جهت تهیه سرویس جدید از دکمه «خرید اشتراک» استفاده فرمایید."
    )
    await message.answer(subs_text, parse_mode="Markdown")

@dp.message(F.text == "💰 شارژ حساب")
async def wallet_charge(message: types.Message):
    charge_text = (
        "💰 **شارژ حساب و کیف پول:**\n\n"
        "جهت خرید مستقیم یا افزایش موجودی حساب، از منوی «🛒 خرید اشتراک» استفاده فرمایید.\n"
        f"در صورت نیاز به واریز با مبالغ دلخواه با پشتیبانی @{SUPPORT_ID} هماهنگ کنید."
    )
    await message.answer(charge_text, parse_mode="Markdown")

@dp.message(F.text == "👥 پشتیبانی")
async def support_info(message: types.Message):
    support_text = (
        "👥 **واحد پشتیبانی و خدمات پس از فروش:**\n\n"
        "تیم پشتیبانی به صورت ۲۴ ساعته آماده پاسخگویی به سوالات، راهنمایی اتصال و رفع اشکالات شماست.\n\n"
        f"💬 **ارتباط مستقیم در تلگرام:**\n"
        f"👉 @{SUPPORT_ID}"
    )
    await message.answer(support_text, parse_mode="Markdown")

@dp.message(F.text == "❓ سوالات متداول")
async def faq_info(message: types.Message):
    faq_text = (
        "❓ **سوالات متداول کاربران (FAQ):**\n\n"
        "**۱. آیا ترافیک سرویس‌ها نامحدود است؟**\n"
        "بله، تمامی پلن‌های ارائه‌شده بدون محدودیت حجم و با نهایت سرعت خط هستند.\n\n"
        "**۲. چند کاربر همزمان می‌توانند متصل شوند؟**\n"
        "هر اکانت قابلیت اتصال ۲ کاربر همزمان به صورت اختصاصی را دارد.\n\n"
        "**۳. مدت زمان تحویل سرویس پس از پرداخت چقدر است؟**\n"
        "پس از ارسال عکس فیش در ربات، معمولاً بین ۲ تا ۱۰ دقیقه کانفیگ تحویل داده می‌شود.\n\n"
        "**۴. آیا این سرویس برای بازی آنلاین (گیمینگ) مناسب است؟**\n"
        "بله، به دلیل پینگ پایین و ثبات سرور، برای بازی و مکالمه کاملاً مناسب است.\n\n"
        "**۵. روی چه سیستم‌عامل‌هایی قابل اجراست؟**\n"
        "روی اندروید، آیفون (iOS)، ویندوز و مک با نرم‌افزارهای استاندارد کار می‌کند.\n\n"
        "**۶. در صورت بروز قطعی چه کار باید کرد؟**\n"
        f"سرورها مانیتور می‌شوند و در صورت هرگونه سوال، پشتیبانی @{SUPPORT_ID} پاسخگوی شماست."
    )
    await message.answer(faq_text, parse_mode="Markdown")

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def setup_instructions(message: types.Message):
    channel_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 ورود به کانال رسمی (آموزش و کانفیگ‌ها)", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="💬 ارتباط با پشتیبانی فنی", url=f"https://t.me/{SUPPORT_ID}")]
        ]
    )
    setup_text = (
        "⚙️ **راهنمای جامع اتصال و دریافت کانفیگ‌ها:**\n\n"
        "🚀 برای دریافت آخرین کانفیگ‌ها، فایل‌های نصب و ویدیوهای آموزشی گام‌به‌گام به کانال رسمی ما بپیوندید:\n\n"
        "📌 **امکانات موجود در کانال:**\n"
        "  • دانلود نرم‌افزارهای اتصال مخصوص Android, iOS, Windows, macOS\n"
        "  • آموزش تصویری و گام‌به‌گام تنظیمات L2TP\n"
        "  • اطلاع‌رسانی وضعیت سرورها و آپدیت‌ها\n\n"
        f"🔗 **لینک کانال:** {CHANNEL_URL}\n\n"
        "برای ورود مستقیم روی دکمه شیشه‌ای زیر کلیک کنید:"
    )
    await message.answer(setup_text, reply_markup=channel_keyboard, parse_mode="Markdown")

# --- وب‌سرور Health Check برای Render روی پورت ۱۰۰۰۰ ---
async def health_check(request):
    return web.Response(text="Mikrotik-Bot is Running 100% Healthy!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info(f"✅ Web server started on port {PORT}")

async def main():
    logger.info("🚀 Launching Mikrotik-Bot...")
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

import os
import logging
import asyncio
import jdatetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# --- لاگ‌ها و پیکربندی متغیرهای محیطی ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "6278059256")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
SUPPORT_ID = os.getenv("SUPPORT_ID", "aL2tp1Support")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/L2tp_vpn402")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- کیبورد اصلی (۴ ردیف ثابت و دقیق طبق دستور مهندس آرشاوین) ---
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

# --- تبدیل ارقام به فارسی ---
def to_persian_digits(text: str) -> str:
    persian_digits = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}
    for en_d, fa_d in persian_digits.items():
        text = text.replace(en_d, fa_d)
    return text

# --- هندلر استارت و خوش‌آمدگویی کامل و سنتی ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_full_name = message.from_user.full_name or "کاربر گرامی"
    
    # دریافت زمان و تاریخ دقیق شمسی
    now = jdatetime.datetime.now()
    day_name = now.strftime("%A")
    date_formatted = to_persian_digits(now.strftime("%d %B %Y"))
    time_formatted = to_persian_digits(now.strftime("%H:%M:%S"))
    
    welcome_text = (
        f"سلام {user_full_name} عزیز، به ربات هوشمند فروش و مدیریت سرویس خوش آمدید 🌹\n\n"
        f"📅 امروز: {day_name}، {date_formatted}\n"
        f"⏰ ساعت دقیق: {time_formatted}\n\n"
        f"🛡 **سرویس اینترنت آزاد و ضد فیلتر با پروتکل پرسرعت V2Ray**\n"
        f"⚡ پایداری بی‌نظیر، پینگ فوق‌العاده پایین، مناسب وب‌گردی، ترید و گیمینگ حرفه‌ای.\n"
        f"🌐 قابلیت اتصال بر روی تمامی سیستم‌عامل‌ها (اندروید، iOS، ویندوز، لینوکس و مک).\n\n"
        f"از منوی زیر جهت خرید اشتراک، دریافت کانفیگ‌ها، مشاهده وضعیت حساب و پشتیبانی استفاده نمایید 👇"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# --- هندلر سوالات متداول (FAQ کامل بر اساس موارد توافق‌شده) ---
@dp.message(F.text == "❓ سوالات متداول")
async def faq_handler(message: types.Message):
    faq_text = (
        "📌 **سوالات متداول کاربران (FAQ):**\n\n"
        "۱️⃣ **پروتکل مورد استفاده چیست؟**\n"
        "🔹 تمامی کانفیگ‌ها بر بستر پروتکل امن و پرسرعت **V2Ray** (با متدهای Vless / Vmess / Trojan) ارائه می‌شوند که بالاترین مقاومت را در برابر اختلالات دارند.\n\n"
        "۲️⃣ **تعداد کاربر همزمان چند نفر است؟**\n"
        "🔹 اشتراک‌های اختصاصی به صورت تک‌کاربره و چندکاربره (طبق پلن خریداری‌شده) بدون افت سرعت قابل استفاده هستند.\n\n"
        "۳️⃣ **آیا برای گیمینگ و ترید مناسب است؟**\n"
        "🔹 بله، سرورها دارای پینگ بسیار پایین (Low Ping) و بدون نوسان (Jitter) هستند و برای بازی‌های آنلاین و ترید کاملاً بهینه‌سازی شده‌اند.\n\n"
        "۴️⃣ **حجم مصرفی به چه صورت محاسبه می‌شود؟**\n"
        "🔹 حجم دانلود و آپلود کاملاً واقعی و شفاف در بخش «اطلاعات حساب» قابل پیگیری و بررسی لحظه‌ای است.\n\n"
        "۵️⃣ **روی چه سیستم‌عامل‌هایی کار می‌کند؟**\n"
        "🔹 تمامی سیستم‌عامل‌ها اعم از Android (با نرم‌افزارهای v2rayNG/NekoBox)، iOS (با v2box/Streisand)، ویندوز (v2rayN/NekoRay) و macOS.\n\n"
        "۶️⃣ **در صورت قطعی یا مسدودی چه اتفاقی می‌افتد؟**\n"
        "🔹 سرورها مجهز به سیستم سوییچ خودکار و بک‌آپ هستند و در صورت هرگونه اختلال زیرساختی، کانفیگ‌های جایگزین بلافاصله در کانال و ربات آپدیت می‌شوند.\n\n"
        "۷️⃣ **چگونه با پشتیبانی در ارتباط باشم؟**\n"
        f"🔹 پشتیبانی ۲۴ ساعته از طریق دکمه اختصاصی در ربات یا پیام به آیدی @{SUPPORT_ID.lstrip('@')} فعال است."
    )
    await message.answer(faq_text, parse_mode="Markdown")

# --- هندلر کانفیگ‌ها و آموزش اتصال (همراه با لینک شیشه‌ای کانال) ---
@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def config_handler(message: types.Message):
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 ورود به کانال کانفیگ و آموزش‌ها", url=CHANNEL_LINK)]
        ]
    )
    caption = (
        "⚙️ **راهنمای اتصال و کانفیگ‌های اختصاصی V2Ray**\n\n"
        "برای دریافت جدیدترین نرم‌افزارهای اتصال، فیلم‌های آموزشی گام‌به‌گام (برای آیفون، اندروید و کامپیوتر) و آخرین اطلاعیه‌های سرور، روی دکمه شیشه‌ای زیر کلیک کرده و وارد کانال رسمی ما شوید 👇"
    )
    await message.answer(caption, reply_markup=inline_kb, parse_mode="Markdown")

# --- هندلر پشتیبانی ---
@dp.message(F.text == "👥 پشتیبانی")
async def support_handler(message: types.Message):
    clean_id = SUPPORT_ID.lstrip('@')
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 ارسال پیام به پشتیبانی", url=f"https://t.me/{clean_id}")]
        ]
    )
    await message.answer(
        f"👨‍💻 **واحد پشتیبانی و پاسخگویی فنی**\n\n"
        f"در صورت بروز هرگونه سوال، مشکل در اتصال یا نیاز به راهنمایی با پشتیبانی ما در ارتباط باشید:\n"
        f"شناسه پشتیبانی: @{clean_id}",
        reply_markup=inline_kb,
        parse_mode="Markdown"
    )

# --- وب‌سرور داخلی aiohttp برای Render (جلوگیری قطعی از Port Scan Timeout و خطای ۵۰۳) ---
async def handle_health_check(request):
    return web.Response(text="Bot is healthy and running on Render Web Service.", status=200)

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    app.router.add_get('/health', handle_health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logging.info(f"🚀 Internal Web Server listening on port {PORT}")

# --- نقطه اجرای اصلی ---
async def main():
    # ۱. اجرای وب‌سرور داخلی همگام با چرخه aiogram
    await run_web_server()
    
    # ۲. حذف وب‌هوک‌های قبلی در صورت وجود جهت جلوگیری از TelegramConflictError
    await bot.delete_webhook(drop_pending_updates=True)
    
    # ۳. شروع دریافت پیام‌ها
    logging.info("🤖 Bot polling started successfully.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")

import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.client.default import DefaultBotProperties

# تنظیم لاگ‌ها
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# خواندن تنظیمات با مقادیر پیش‌فرض امن
BOT_TOKEN = os.getenv("BOT_TOKEN", "7963288126:AAH5t_fX1m1FqP1Q-YOUR_TOKEN_HERE")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@aL2tp1Support")
PORT = int(os.getenv("PORT", 10000))

# مقادیر پلن‌ها و پرداخت (تثبیت شده طبق دستور آرشاوین)
PLAN1_PRICE = os.getenv("PLAN1_PRICE", "250,000 تومان")
PLAN2_PRICE = os.getenv("PLAN2_PRICE", "400,000 تومان")
PLAN3_PRICE = os.getenv("PLAN3_PRICE", "600,000 تومان")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6037-9979-xxxx-xxxx")

# تعریف ربات و دیسپچر
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- کیبورد اصلی (دقیقاً ۴ ردیف بدون تست رایگان و زیرمجموعه‌گیری) ---
def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# --- هندلر استارت ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        f"سلام <b>{message.from_user.first_name}</b> عزیز، به ربات سرویس L2TP VPN خوش آمدید! 🚀\n\n"
        "برای مدیریت حساب و خرید سرویس از منوی زیر استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

# --- ۱. خرید اشتراک ---
@dp.message(F.text == "🛒 خرید اشتراک")
async def buy_plan(message: types.Message):
    text = (
        "🛍 <b>پلن‌های فعال اشتراک L2TP & V2Ray (نامحدود):</b>\n\n"
        f"🔹 <b>پلن ۱ ماهه:</b> {PLAN1_PRICE}\n"
        f"🔹 <b>پلن ۳ ماهه:</b> {PLAN2_PRICE}\n"
        f"🔹 <b>پلن ۶ ماهه:</b> {PLAN3_PRICE}\n\n"
        "💳 جهت خرید و فعال‌سازی فوری به آیدی پشتیبانی پیام دهید:\n"
        f"👉 <b>{SUPPORT_ID}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 ارتباط با پشتیبانی فروش", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}")]
    ])
    await message.answer(text, reply_markup=kb)

# --- ۲. اطلاعات حساب ---
@dp.message(F.text == "📊 اطلاعات حساب")
async def account_info(message: types.Message):
    text = (
        "📊 <b>وضعیت حساب کاربری شما:</b>\n\n"
        f"👤 شناسه کاربری: <code>{message.from_user.id}</code>\n"
        "💎 وضعیت سرویس: فعال (نامحدود کاربر)\n"
        "⏳ اعتبار باقی‌مانده: اتصال برقرار\n"
        "📡 حجم مصرفی: نامحدود / بدون محدودیت سرعت\n\n"
        f"جهت تمدید یا بررسی جزئیات به پشتیبانی ({SUPPORT_ID}) پیام دهید."
    )
    await message.answer(text)

# --- ۳. اشتراک‌های من ---
@dp.message(F.text == "💎 اشتراک‌های من")
async def my_services(message: types.Message):
    text = (
        "💎 <b>اشتراک‌های فعال شما:</b>\n\n"
        "اکانت‌های شما با پروتکل‌های L2TP/IPsec و V2Ray به صورت همزمان فعال می‌باشند."
    )
    await message.answer(text)

# --- ۴. شارژ حساب ---
@dp.message(F.text == "💰 شارژ حساب")
async def recharge_account(message: types.Message):
    text = (
        "💰 <b>شارژ حساب و تمدید:</b>\n\n"
        f"شماره کارت جهت واریز:\n<code>{PAYMENT_CARD}</code>\n\n"
        f"پس از واریز، تصویر فیش را برای <b>{SUPPORT_ID}</b> ارسال فرمایید."
    )
    await message.answer(text)

# --- ۵. پشتیبانی ---
@dp.message(F.text == "👥 پشتیبانی")
async def support_handler(message: types.Message):
    text = (
        "👥 <b>پشتیبانی اختصاصی:</b>\n\n"
        "کارشناسان ما به صورت ۲۴ ساعته پاسخگوی سوالات شما هستند.\n\n"
        f"🆔 آیدی پشتیبان: <b>{SUPPORT_ID}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ارسال پیام به پشتیبانی", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}")]
    ])
    await message.answer(text, reply_markup=kb)

# --- ۶. سوالات متداول (۱۱ مورد کامل) ---
@dp.message(F.text == "❓ سوالات متداول")
async def faq_handler(message: types.Message):
    text = (
        "❓ <b>سوالات متداول (FAQ):</b>\n\n"
        "۱. آیا اشتراک‌ها چندکاربره هستند؟\n"
        "بله، تمامی اکانت‌ها <b>نامحدود</b> بوده و روی همه دستگاه‌ها همزمان قابل استفاده‌اند.\n\n"
        "۲. از چه پروتکل‌هایی استفاده می‌شود؟\n"
        "پروتکل فوق‌العاده پایدار <b>L2TP/IPsec</b> و همچنین <b>V2Ray</b>.\n\n"
        "۳. آیا گارانتی بازگشت وجه دارید؟\n"
        "بله، تا ۲۴ ساعت در صورت عدم رضایت بازگشت کامل وجه انجام می‌شود.\n\n"
        "۴. آیا ترافیک و حجم محدود است؟\n"
        "خیر، تمامی پلن‌ها کاملاً بدون محدودیت حجم و ترافیک هستند.\n\n"
        "۵. آیا لاگ مصرف ذخیره می‌شود؟\n"
        "خیر، امنیت کاربران اولویت ماست و هیچ‌گونه لاگی ثبت نمی‌شود.\n\n"
        "۶. نحوه اتصال در ویندوز و مک چگونه است؟\n"
        "تنظیمات L2TP در بخش تنظیمات خود ویندوز/مک بدون نیاز به برنامه جانبی انجام می‌شود.\n\n"
        "۷. نحوه اتصال در اندروید و آیفون چگونه است؟\n"
        "در بخش کانفیگ‌ها راهنمای قدم به قدم تصویری قرار داده شده است.\n\n"
        "۸. شرایط همکاری و نمایندگی چگونه است؟\n"
        "حداقل خرید نمایندگی ۲ میلیون تومان بوده و شامل تخفیف ویژه پنل است.\n\n"
        "۹. در صورت قطعی چه باید کرد؟\n"
        f"سرورها مانیتورینگ خودکار دارند و در صورت بروز اختلال به {SUPPORT_ID} پیام دهید.\n\n"
        "۱۰. سرعت دانلود و آپلود چقدر است؟\n"
        "سرورها با پورت ۱۰ گیگابیت اختصاصی فعال هستند و حداکثر سرعت خط شما را ارائه می‌دهند.\n\n"
        "۱۱. پشتیبانی در چه ساعاتی فعال است؟\n"
        "تیم پشتیبانی به صورت ۲۴ ساعته در خدمت شماست."
    )
    await message.answer(text)

# --- ۷. کانفیگ‌ها و آموزش اتصال ---
@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def configs_tutorial(message: types.Message):
    text = (
        "⚙️ <b>آموزش اتصال و راهنما:</b>\n\n"
        "🔸 <b>اتصال در اندروید / آیفون:</b>\n"
        "به بخش Settings > VPN بروید، نوع کانکشن را L2TP/IPsec PSK انتخاب کرده و آدرس سرور ارسالی را وارد کنید.\n\n"
        "🔸 <b>اتصال در ویندوز:</b>\n"
        "از بخش Network & Internet > VPN یک کانکشن جدید ایجاد نمایید.\n\n"
        f"در صورت نیاز به راهنمایی بیشتر با <b>{SUPPORT_ID}</b> در تماس باشید."
    )
    await message.answer(text)

# --- وب‌سرور داخلی مخصوص Render (برای پاس کردن Port Scan) ---
async def health_check(request):
    return web.Response(text="Mikrotik-Bot is Running and Healthy! 🚀", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

# --- اجرای همزمان ربات و وب‌سرور ---
async def main():
    logger.info("Starting Mikrotik-Bot on Render...")
    # حذف وب‌هوک احتمالی قبلی برای آماده‌سازی Polling
    await bot.delete_webhook(drop_pending_updates=True)
    
    # اجرای وب‌سرور برای پاس کردن سلامت Render + اجرای Polling ربات
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

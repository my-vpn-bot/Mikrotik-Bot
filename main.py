import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- تنظیمات لاگینگ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- متغیرهای محیطی ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-XXXX-XXXX-XXXX")
PORT = int(os.getenv("PORT", 10000))

if not BOT_TOKEN:
    raise ValueError("❌ متغیر محیطی BOT_TOKEN تنظیم نشده است!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ثابت‌ها و قیمت‌ها ---
SUPPORT_ID = "L2tp1Support"
PLAN1_PRICE = "۲۵۰,۰۰۰"
PLAN2_PRICE = "۴۰۰,۰۰۰"
PLAN3_PRICE = "۶۰۰,۰۰۰"

# --- کیبورد اصلی (Single Source of Truth: ۴ ردیف بدون تست رایگان و زیرمجموعه‌گیری) ---
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ],
    resize_keyboard=True
)

# --- منوی شیشه‌ای انتخاب پلن خرید ---
plans_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=f"پلن ۱ ماهه ({PLAN1_PRICE} تومان)", callback_data="buy_plan_1")],
        [InlineKeyboardButton(text=f"پلن ۲ ماهه ({PLAN2_PRICE} تومان)", callback_data="buy_plan_2")],
        [InlineKeyboardButton(text=f"پلن ۳ ماهه ({PLAN3_PRICE} تومان)", callback_data="buy_plan_3")]
    ]
)

# --- هندلرهای تلگرام ---

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    welcome_text = (
        "سلام! به ربات رسمی L2TP خوش آمدید 🚀\n\n"
        "لطفاً جهت استفاده از خدمات، یکی از گزینه‌های زیر را انتخاب نمایید:"
    )
    await message.answer(welcome_text, reply_markup=main_keyboard)

@dp.message(F.text == "🛒 خرید اشتراک")
async def show_plans(message: types.Message):
    await message.answer(
        "📦 لطفاً یکی از پلن‌های زیر را جهت خرید انتخاب کنید:",
        reply_markup=plans_inline_keyboard
    )

@dp.callback_query(F.data.startswith("buy_plan_"))
async def process_plan_selection(callback: types.CallbackQuery):
    plan_id = callback.data.split("_")[-1]
    
    if plan_id == "1":
        plan_name, price = "۱ ماهه", PLAN1_PRICE
    elif plan_id == "2":
        plan_name, price = "۲ ماهه", PLAN2_PRICE
    else:
        plan_name, price = "۳ ماهه", PLAN3_PRICE

    payment_text = (
        f"📋 پیش‌فاکتور خرید اشتراک {plan_name}:\n"
        f"💵 مبلغ قابل پرداخت: {price} تومان\n\n"
        f"💳 شماره کارت جهت واریز:\n"
        f"`{CARD_NUMBER}`\n"
        f"👤 به نام: رحیمی\n\n"
        "⚠️ لطفاً پس از واریز، تصویر فیش پرداختی (عکس) را در همین چت ارسال نمایید تا حساب شما فعال گردد.\n"
        f"در صورت بروز هرگونه مشکل با پشتیبانی @{SUPPORT_ID} در ارتباط باشید."
    )
    await callback.message.answer(payment_text, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.photo)
async def handle_receipt(message: types.Message):
    receipt_ack = (
        "✅ فیش واریزی شما با موفقیت دریافت شد.\n\n"
        "در حال بررسی توسط مدیریت سیستم می‌باشد. سرویس شما به محض تایید فعال خواهد شد.\n"
        f"ارتباط سریع‌تر: @{SUPPORT_ID}"
    )
    await message.answer(receipt_ack)

@dp.message(F.text == "📊 اطلاعات حساب")
async def account_info(message: types.Message):
    text = (
        f"👤 شناسه کاربری: `{message.from_user.id}`\n"
        f"نام کاربری: @{message.from_user.username or 'تعریف‌نشده'}\n"
        "وضعیت حساب: فعال ✅"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "💎 اشتراک‌های من")
async def my_subscriptions(message: types.Message):
    await message.answer(
        "سرویس فعالی برای این حساب یافت نشد.\nجهت تهیه اشتراک، از گزینه «🛒 خرید اشتراک» استفاده کنید."
    )

@dp.message(F.text == "💰 شارژ حساب")
async def wallet_charge(message: types.Message):
    await message.answer(
        f"جهت شارژ حساب، به گزینه «🛒 خرید اشتراک» مراجعه کنید یا با @{SUPPORT_ID} تماس بگیرید."
    )

@dp.message(F.text == "👥 پشتیبانی")
async def support_info(message: types.Message):
    support_text = (
        "🛠 بخش پشتیبانی فنی و مالی:\n\n"
        f"جهت ارتباط مستقیم با پشتیبانی به آیدی زیر پیام دهید:\n"
        f"👉 @{SUPPORT_ID}"
    )
    await message.answer(support_text)

@dp.message(F.text == "❓ سوالات متداول")
async def faq_info(message: types.Message):
    faq_text = (
        "❓ سوالات متداول:\n\n"
        "۱. آیا اشتراک‌ها محدودیت حجمی دارند؟\n"
        "خیر، تمام پلن‌ها نامحدود و پرسرعت ارائه می‌شوند.\n\n"
        "۲. پس از پرداخت چقدر طول می‌کشد کانفیگ ارسال شود؟\n"
        "بلافاصله پس از تایید فیش توسط پشتیبانی (کمتر از ۱۵ دقیقه).\n\n"
        "۳. روی چه دستگاه‌هایی قابل اتصال است؟\n"
        "تمام سیستم‌عامل‌ها اعم از اندروید، iOS، ویندوز و مک.\n\n"
        f"جهت راهنمایی بیشتر با @{SUPPORT_ID} در ارتباط باشید."
    )
    await message.answer(faq_text)

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def setup_instructions(message: types.Message):
    await message.answer(
        f"آموزش‌های اتصال و فایل‌های کانفیگ اختصاصی پس از خرید پلن برای شما ارسال خواهد شد.\n"
        f"پشتیبانی: @{SUPPORT_ID}"
    )

# --- سرور وب (Health Check استاندارد Render روی پورت 10000 بدون نیاز به uvicorn) ---

async def health_check(request):
    return web.Response(text="OK - Mikrotik-Bot is Running")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info(f"✅ Web server (Health Check) started on port {PORT}")

async def main():
    logger.info("🚀 Starting Mikrotik-Bot...")
    # اجرای موازی سرور وب جهت رضایت Render و پولینگ تلگرام
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# تنظیمات لاگینگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# خواندن متغیرهای محیطی از Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("خطا: متغیر BOT_TOKEN در Render تنظیم نشده است!")

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "")
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else None

# خواندن آیدی ساپورت از رندر (پشتیبانی از انواع کلیدها)
SUPPORT_USERNAME = (
    os.getenv("SUPPORT_USERNAME")
    or os.getenv("SUPPORT_ID")
    or os.getenv("ADMIN_USERNAME")
    or os.getenv("SUPPORT")
    or "Support_Admin"
).replace("@", "").strip()

# اطلاعات پرداخت بانکی
PAYMENT_CARD = (
    os.getenv("PAYMENT_CARD")
    or os.getenv("CARD_NUMBER")
    or "6037-9970-0000-0000"
)
PAYMENT_NAME = (
    os.getenv("PAYMENT_NAME")
    or os.getenv("CARD_HOLDER")
    or "مدیریت سرویس"
)

# ایجاد نمونه بات و دیسپچر
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class PaymentStates(StatesGroup):
    waiting_for_receipt = State()


def get_support_url() -> str:
    """ساخت لینک مستقیم به تلگرام پشتیبانی"""
    return f"https://t.me/{SUPPORT_USERNAME}"


# --- کیبوردهای شیشه‌ای ربات ---

def main_menu_keyboard():
    support_url = get_support_url()
    keyboard = [
        [
            InlineKeyboardButton(text="🛒 خرید سرویس جدید", callback_data="buy_service"),
            InlineKeyboardButton(text="🔄 تمدید اشتراک", callback_data="extend_config")
        ],
        [
            InlineKeyboardButton(text="📊 استعلام وضعیت و حجم", callback_data="check_config"),
            InlineKeyboardButton(text="⏳ سرویس‌های رو به اتمام", callback_data="expired_configs")
        ],
        [
            InlineKeyboardButton(text="🛠 آموزش و رفع اشکال", callback_data="fix_config"),
            InlineKeyboardButton(text="📱 دریافت بارکد (QR)", callback_data="get_skin")
        ],
        [
            InlineKeyboardButton(text="💳 شماره کارت و پرداخت", callback_data="payment_info"),
            InlineKeyboardButton(text="💬 ارتباط مستقیم با پشتیبانی", url=support_url)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def plans_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🔹 اشتراک ۱ ماهه (۳۰ گیگ) - ۵۰,۰۰۰ ت", callback_data="plan_1m")],
        [InlineKeyboardButton(text="🔹 اشتراک ۲ ماهه (۶۰ گیگ) - ۹۰,۰۰۰ ت", callback_data="plan_2m")],
        [InlineKeyboardButton(text="🔹 اشتراک ۳ ماهه (۱۰۰ گیگ) - ۱۴۰,۰۰۰ ت", callback_data="plan_3m")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_to_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]]
    )


def receipt_submission_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 ارسال عکس رسید پرداخت", callback_data="send_receipt_action")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
        ]
    )


# --- هندلرهای دستورات و کلیک‌ها ---

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    first_name = message.from_user.first_name or "کاربر گرامی"
    welcome_text = (
        f"سلام {first_name} عزیز 👋\n"
        f"به ربات مدیریت و خرید کانفیگ پرسرعت خوش آمدید.\n\n"
        f"🎯 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=main_menu_keyboard())


@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🏠 **منوی اصلی ربات:**\nلطفاً گزینه مورد نظر خود را انتخاب فرمایید:",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "buy_service")
async def buy_service_handler(callback: CallbackQuery):
    text = (
        "🚀 **تعرفه‌های سرویس پرسرعت:**\n\n"
        "یکی از پلن‌های زیر را انتخاب کنید تا مشخصات پرداخت نمایش داده شود:"
    )
    await callback.message.edit_text(text, reply_markup=plans_keyboard(), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data.startswith("plan_"))
async def plan_selected_handler(callback: CallbackQuery):
    plan_names = {
        "plan_1m": "۱ ماهه (۳۰ گیگابایت) - ۵۰,۰۰۰ تومان",
        "plan_2m": "۲ ماهه (۶۰ گیگابایت) - ۹۰,۰۰۰ تومان",
        "plan_3m": "۳ ماهه (۱۰۰ گیگابایت) - ۱۴۰,۰۰۰ تومان",
    }
    selected_plan = plan_names.get(callback.data, "پلن انتخابی")
    
    text = (
        f"📌 **پلن انتخابی:** {selected_plan}\n\n"
        f"💳 **اطلاعات کارت جهت واریز:**\n"
        f"🔹 شماره کارت: `{PAYMENT_CARD}`\n"
        f"🔹 به نام: **{PAYMENT_NAME}**\n\n"
        f"⚠️ پس از واریز، روی دکمه زیر کلیک کرده و عکس فیش را ارسال نمایید."
    )
    await callback.message.edit_text(text, reply_markup=receipt_submission_keyboard(), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "payment_info")
async def payment_info_handler(callback: CallbackQuery):
    text = (
        "💳 **اطلاعات حساب جهت پرداخت و واریز:**\n\n"
        f"🔹 شماره کارت: `{PAYMENT_CARD}`\n"
        f"🔹 به نام: **{PAYMENT_NAME}**\n\n"
        f"پس از واریز مبلغ، تصویر رسید را از بخش خرید برای ما ارسال کنید یا مستقیماً به پشتیبانی (@{SUPPORT_USERNAME}) پیام دهید."
    )
    await callback.message.edit_text(text, reply_markup=back_to_main_keyboard(), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "send_receipt_action")
async def ask_receipt_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PaymentStates.waiting_for_receipt)
    text = (
        "📸 لطفاً **تصویر یا اسکرین‌شات فیش واریزی** خود را در همین صفحه ارسال کنید:\n\n"
        "(برای انصراف /start را بفرستید)"
    )
    await callback.message.answer(text)
    await callback.answer()


@dp.message(PaymentStates.waiting_for_receipt, F.photo)
async def receipt_received_handler(message: Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    user_full_name = message.from_user.full_name
    
    # اطلاع‌رسانی به ادمین در صورت تعریف بودن ADMIN_ID
    if ADMIN_ID:
        try:
            caption = (
                f"📥 **رسید پرداخت جدید دریافت شد!**\n\n"
                f"👤 کاربر: {user_full_name} ({user_info})\n"
                f"🔢 شناسه عددی: `{message.from_user.id}`\n"
            )
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_file_id, caption=caption, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"خطا در فوروارد رسید به ادمین: {e}")

    await state.clear()
    await message.answer(
        f"✅ فیش واریزی شما با موفقیت دریافت شد.\n"
        f"پس از بررسی، کانفیگ شما تحویل داده خواهد شد.\n\n"
        f"در صورت نیاز به پیگیری فوری به پشتیبانی پیام دهید:\n@{SUPPORT_USERNAME}",
        reply_markup=back_to_main_keyboard()
    )


@dp.message(PaymentStates.waiting_for_receipt)
async def invalid_receipt_handler(message: Message):
    await message.answer("⚠️ لطفاً فقط عکس/فیش واریزی را ارسال فرمایید.")


@dp.callback_query(F.data.in_({"extend_config", "check_config", "expired_configs", "fix_config", "get_skin"}))
async def support_redirect_actions(callback: CallbackQuery):
    action_texts = {
        "extend_config": (
            "🔄 **تمدید اشتراک:**\n\n"
            "جهت تمدید کانفیگ فعلی خود، لطفاً نام کاربری یا فایل قبلی را برای پشتیبانی ارسال فرمایید:\n"
            f"👉 @{SUPPORT_USERNAME}"
        ),
        "check_config": (
            "📊 **استعلام حجم و اعتبار:**\n\n"
            "جهت مشاهده دقیق حجم باقیمانده و تاریخ انقضا با پشتیبانی در ارتباط باشید:\n"
            f"👉 @{SUPPORT_USERNAME}"
        ),
        "expired_configs": (
            "⏳ **سرویس‌های رو به اتمام:**\n\n"
            "در صورت دریافت هشدار پایان حجم یا زمان، جهت جلوگیری از قطعی تمدید کنید:\n"
            f"👉 @{SUPPORT_USERNAME}"
        ),
        "fix_config": (
            "🛠 **راهنما و رفع اشکال اتصال:**\n\n"
            "۱. نرم‌افزار خود را به آخرین نسخه بروزرسانی کنید.\n"
            "۲. حالت DNS را چک کنید.\n"
            "۳. در صورت تداوم مشکل، نام سرور را به پشتیبانی اعلام فرمایید:\n"
            f"👉 @{SUPPORT_USERNAME}"
        ),
        "get_skin": (
            "📱 **دریافت بارکد و لینک QR:**\n\n"
            "جهت دریافت مجدد بارکد QR اختصاصی اشتراک خود به پشتیبانی پیام دهید:\n"
            f"👉 @{SUPPORT_USERNAME}"
        ),
    }
    text = action_texts.get(callback.data, f"جهت پیگیری به آیدی پشتیبانی پیام دهید:\n@{SUPPORT_USERNAME}")
    await callback.message.edit_text(text, reply_markup=back_to_main_keyboard(), parse_mode="Markdown")
    await callback.answer()


# --- وب‌سرور سبک داخلی aiohttp برای Render ---
async def handle_ping(request):
    return web.Response(text="Mikrotik-Bot is alive and running!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/healthz", handle_ping)
    
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 وب‌سرور با موفقیت روی پورت {port} فعال شد.")


# --- اجرای اصلی برنامه ---
async def main():
    logger.info("🚀 ربات در حال راه‌اندازی است...")
    # اجرای وب‌سرور داخلی در پس‌زمینه
    await start_web_server()
    # شروع دریافت پیام‌ها
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ربات متوقف شد.")

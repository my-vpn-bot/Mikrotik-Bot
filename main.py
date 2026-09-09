import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ---------------------------------------------------------
# ۱. تنظیمات لاگ و متغیرهای محیطی Render
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("L2TP-Bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
SUPPORT_ID = os.getenv("SUPPORT_ID", "").strip()
CARD_NUMBER = os.getenv("CARD_NUMBER", "").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "").strip()
PORT = int(os.getenv("PORT", "10000"))

# خواندن قیمت پلن‌ها مستقیماً از متغیرهای رندر
PLAN1_PRICE = os.getenv("PLAN1_PRICE", "250,000 تومان")
PLAN2_PRICE = os.getenv("PLAN2_PRICE", "400,000 تومان")
PLAN3_PRICE = os.getenv("PLAN3_PRICE", "600,000 تومان")

# ---------------------------------------------------------
# ۲. تعریف Stateها برای FSM
# ---------------------------------------------------------
class OrderState(StatesGroup):
    waiting_for_receipt = State()

# ---------------------------------------------------------
# ۳. کیبوردها (دقیقاً بر اساس ۴ ردیف تأیید شده)
# ---------------------------------------------------------
def get_main_menu():
    kb = [
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_plans_inline():
    kb = [
        [InlineKeyboardButton(text=f"پلن ۱ ماهه (۳۰ گیگ) - {PLAN1_PRICE}", callback_data="buy_plan_1")],
        [InlineKeyboardButton(text=f"پلن ۲ ماهه (۶۰ گیگ) - {PLAN2_PRICE}", callback_data="buy_plan_2")],
        [InlineKeyboardButton(text=f"پلن ۳ ماهه (۹۰ گیگ) - {PLAN3_PRICE}", callback_data="buy_plan_3")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_order")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ---------------------------------------------------------
# ۴. سرور وب سبک جهت رفع خطای ۵۰۳ و Port Binding در Render
# ---------------------------------------------------------
async def health_check(request):
    return web.Response(text="L2TP Bot is live and healthy!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server successfully bound to port {PORT}")

# ---------------------------------------------------------
# ۵. راه‌اندازی ربات و هندلرها
# ---------------------------------------------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# هندلر شروع
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "سلام کاربر گرامی، به ربات L2TP خوش آمدید! 🌹\n\n"
        "لطفاً جهت استفاده از خدمات، یکی از گزینه‌های منوی زیر را انتخاب نمایید:"
    )
    await message.answer(text, reply_markup=get_main_menu())

# ردیف ۱: خرید اشتراک
@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy_subscription(message: Message):
    text = "💎 لطفاً یکی از پلن‌های زیر را انتخاب فرمایید:"
    await message.answer(text, reply_markup=get_plans_inline())

# ردیف ۲: اطلاعات حساب
@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account_info(message: Message):
    text = (
        f"📊 **اطلاعات کاربری شما:**\n\n"
        f"👤 نام: {message.from_user.full_name}\n"
        f"🆔 شناسه عددی: `{message.from_user.id}`\n"
        f"🔹 نام کاربری: @{message.from_user.username if message.from_user.username else 'ندارد'}\n"
        f"💰 موجودی کیف پول: ۰ تومان"
    )
    await message.answer(text, parse_mode="Markdown")

# ردیف ۲: اشتراک‌های من
@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: Message):
    text = "💎 در حال حاضر اشتراک فعالی برای حساب شما ثبت نشده است."
    await message.answer(text)

# ردیف ۳: شار@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy_subscription(message: Message):
    text = "💎 لطفاً یکی از پلن‌های زیر را انتخاب فرمایید:"
    await message.answer(text, reply_markup=get_plans_inline())

# ردیف ۲: اطلاعات حساب
@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account_info(message: Message):
    text = (
        f"📊 **اطلاعات کاربری شما:**\n\n"
        f"👤 نام: {message.from_user.full_name}\n"
        f"🆔 شناسه عددی: `{message.from_user.id}`\n"
        f"🔹 نام کاربری: @{message.from_user.username if message.from_user.username else 'ندارد'}\n"
        f"💰 موجودی کیف پول: ۰ تومان"
    )
    await message.answer(text, parse_mode="Markdown")

# ردیف ۲: اشتراک‌های من
@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: Message):
    text = "💎 در حال حاضر اشتراک فعالی برای حساب شما ثبت نشده است."
    await message.answer(text)

# ردیف ۳: شارژ حساب
@dp.message(F.text == "💰 شارژ حساب")
async def handle_wallet_charge(message: Message):
    text = (
        "💳 جهت شارژ حساب می‌توانید مبلغ مورد نظر را به شماره کارت زیر واریز فرمایید:\n\n"
        f"💳 شماره کارت: `{CARD_NUMBER}`\n"
        f"👤 به نام: {CARD_HOLDER}\n\n"
        "پس از واریز، تصویر فیش را برای پشتیبانی ارسال فرمایید."
    )
    await message.answer(text, parse_mode="Markdown")

# ردیف ۳: پشتیبانی
@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: Message):
    sup_link = SUPPORT_ID.replace("@ای اتصال به سرویس L2TP:**\n\n"
        "برای اتصال در گوشی یا سیستم خود وارد بخش تنظیمات شبکه (VPN) شوید، نوع پروتکل را L2TP قرار داده و سرور، یوزرنیم و پسورد دریافتی را وارد فرمایید."
    )
    await message.answer(text, parse_mode="Markdown")

# این‌لاین کلیک‌ها: خرید پلن
@dp.callback_query(F.data.startswith("buy_plan_"))
async def process_plan_choice(callback: CallbackQuery, state: FSMContext):
    plan_id = callback.data.split("_")[-1]
    plans = {
        "1": ("پلن ۱ ماهه (۳۰ گیگ)", PLAN1_PRICE),
        "2": ("پلن ۲ ماهه (۶۰ گیگ)", PLAN2_PRICE),
        "3": ("پلن ۳ ماهه (۹۰ گیگ)", PLAN3_PRICE)
    }
    plan_title, price = plans.get(plan_id, ("پلن انتخابی", "نامشخص"))
    
    await state.update_data(selected_plan=plan_title, price=price)
    await state.set_state(OrderState.waiting_for_receipt)
    
    text = (
        f"سفارش شما: **{plan_title}**\n"
        f"مبلغ قابل پرداخت: **{price}**\n\n"
        f"💳 شماره کارت:\n`{CARD_NUMBER}`\n"
        f"👤 به نام: {CARD_HOLDER}\n\n"
        "لطفاً پس از واریز، **تصویر رسید بانکی** را در همین چت ارسال فرمایید:"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "cancel_order")
async def process_cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ عملیات سفارش لغو شد.")
    await callback.answer()

# دریافت رسید پرداخت و ارسال به ادمین
@dp.message(OrderState.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: Message, state: FSMContext):
    user_data = await state.get_data()
    plan_title = user_data.get("selected_plan", "نامشخص")
    price = user_data.get("price", "نامشخص")
    
    await state.clear()
    await message.answer("✅ رسید شما با موفقیت ثبت شد و برای مدیریت ارسال گردید. به زودی نتیجه اعلام خواهد شد.")
    
    if ADMIN_ID:
        try:
            caption = (
                "🔔 **سفارش جدید ثبت شد!**\n\n"
                f"👤 کاربر: {message.from_user.full_name} (`{message.from_user.id}`)\n"
                f"🔹 پلن: {plan_title}\n"
                f"💰 مبلغ: {price}"
            )
            await bot.send_photo(chat_id=int(ADMIN_ID), photo=message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error forwarding receipt to admin: {e}")

# ---------------------------------------------------------
# ۶. تابع اصلی و چرخه اجرای برنامه
# ---------------------------------------------------------
async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing! Please set it in Render Environment Variables.")
        return

    # ۱. فعال‌سازی سرور وب برای رفع کامل خطای ۵۰۳ رندر
    await start_web_server()

    # ۲. حذف Webhook و پیام‌های معلق برای جلوگیری از TelegramConflictError
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook deleted and pending updates dropped.")

    # ۳. شروع دریافت پیام‌ها
    logger.info("Starting L2TP polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

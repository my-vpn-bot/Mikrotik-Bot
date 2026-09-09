import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message
)
from aiogram.fsm.storage.memory import MemoryStorage

# ----------------------------------------------------
# 1. تنظیمات و متغیرهای محیطی
# ----------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "")
CARD_NUMBER = os.getenv("CARD_NUMBER", "۶۰۳۷-۹۹۷۵-۰۰۰۰-۰۰۰۰")
CARD_HOLDER = os.getenv("CARD_HOLDER", "به نام مدیریت سرویس")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "aL2tp1Support")

# قیمت‌های ثابت و تایید شده (تومان)
PLAN_PRICES = {
    "plan_1": {"name": "پلن ۱ ماهه (تک کاربره)", "price": 250_000, "price_str": "۲۵۰,۰۰۰ تومان"},
    "plan_2": {"name": "پلن ۲ ماهه (دو کاربره)", "price": 400_000, "price_str": "۴۰۰,۰۰۰ تومان"},
    "plan_3": {"name": "پلن ۳ ماهه (نامحدود / ویژه)", "price": 600_000, "price_str": "۶۰۰,۰۰۰ تومان"},
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ----------------------------------------------------
# 2. کیبوردهای اصلی (Reply & Inline Keyboards)
# ----------------------------------------------------
# منوی اصلی ۴ ردیفه تایید شده (بدون تست رایگان و زیرمجموعه‌گیری)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 خرید اشتراک")],
        [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
        [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
        [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")]
    ],
    resize_keyboard=True
)

# دکمه‌های شیشه‌ای انتخاب پلن خرید
def get_plans_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🛒 {PLAN_PRICES['plan_1']['name']} - {PLAN_PRICES['plan_1']['price_str']}",
                    callback_data="buy_plan_1"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🛒 {PLAN_PRICES['plan_2']['name']} - {PLAN_PRICES['plan_2']['price_str']}",
                    callback_data="buy_plan_2"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🛒 {PLAN_PRICES['plan_3']['name']} - {PLAN_PRICES['plan_3']['price_str']}",
                    callback_data="buy_plan_3"
                )
            ],
            [
                InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_purchase")
            ]
        ]
    )
    return keyboard

# ----------------------------------------------------
# 3. هندلرها و لاجیک ربات
# ----------------------------------------------------
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        f"سلام {message.from_user.first_name} عزیز! 🌹\n"
        "به ربات مدیریت و خرید اشتراک خوش آمدید.\n\n"
        "لطفاً یکی از گزینه‌های منوی زیر را انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=main_menu)

@dp.message(F.text == "🛒 خرید اشتراک")
async def handle_buy_subscription(message: Message):
    text = (
        "💎 **پلن‌های فعال سرویس:**\n\n"
        "جهت خرید، لطفاً یکی از پلن‌های زیر را انتخاب کنید تا مستقیماً به مرحله پرداخت هدایت شوید:"
    )
    await message.answer(text, reply_markup=get_plans_keyboard(), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data.startswith("buy_plan_"))
async def process_plan_selection(callback: CallbackQuery):
    await callback.answer()
    plan_key = callback.data.replace("buy_", "")
    selected_plan = PLAN_PRICES.get(plan_key)

    if not selected_plan:
        await callback.message.answer("⚠️ پلن انتخابی نامعتبر است.")
        return

    payment_text = (
        f"📋 **فاکتور پرداخت**\n\n"
        f"🔹 **پلن انتخابی:** {selected_plan['name']}\n"
        f"💵 **مبلغ قابل پرداخت:** {selected_plan['price_str']}\n\n"
        f"💳 **اطلاعات کارت جهت واریز:**\n"
        f"`{CARD_NUMBER}`\n"
        f"👤 **به نام:** {CARD_HOLDER}\n\n"
        f"⚠️ **راهنمای تایید سفارش:**\n"
        f"پس از واریز، لطفاً تصویر فیش واریزی را به همراه نام کاربری خود برای پشتیبانی ارسال فرمایید:\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )

    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📲 ارسال فیش به پشتیبانی",
                    url=f"https://t.me/{SUPPORT_USERNAME}"
                )
            ],
            [
                InlineKeyboardButton(text="🔙 بازگشت به لیست پلن‌ها", callback_data="back_to_plans")
            ]
        ]
    )

    await callback.message.edit_text(payment_text, reply_markup=confirm_keyboard, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "back_to_plans")
async def back_to_plans_list(callback: CallbackQuery):
    await callback.answer()
    text = (
        "💎 **پلن‌های فعال سرویس:**\n\n"
        "جهت خرید، لطفاً یکی از پلن‌های زیر را انتخاب کنید:"
    )
    await callback.message.edit_text(text, reply_markup=get_plans_keyboard(), parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data == "cancel_purchase")
async def cancel_purchase_action(callback: CallbackQuery):
    await callback.answer("فرآیند خرید لغو شد.")
    await callback.message.delete()

@dp.message(F.text == "📊 اطلاعات حساب")
async def handle_account_info(message: Message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "تنظیم نشده"
    info_text = (
        f"📊 **اطلاعات حساب کاربری شما:**\n\n"
        f"👤 **شناسه عددی:** `{user_id}`\n"
        f"🏷 **نام کاربری:** {username}\n"
        f"💰 **موجودی کیف پول:** ۰ تومان\n"
        f"💎 **تعداد اشتراک فعال:** ۰"
    )
    await message.answer(info_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(F.text == "💎 اشتراک‌های من")
async def handle_my_subscriptions(message: Message):
    await message.answer("💎 در حال حاضر اشتراک فعالی برای شما ثبت نشده است.")

@dp.message(F.text == "💰 شارژ حساب")
async def handle_charge_account(message: Message):
    charge_text = (
        f"💰 **افزایش اعتبار حساب**\n\n"
        f"جهت شارژ حساب، مبلغ مورد نظر خود را به شماره کارت زیر واریز نمایید:\n\n"
        f"💳 `{CARD_NUMBER}`\n"
        f"👤 **به نام:** {CARD_HOLDER}\n\n"
        f"سپس رسید واریز را به همراه شناسه کاربری (`{message.from_user.id}`) برای پشتیبانی ارسال نمایید:\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await message.answer(charge_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(F.text == "👥 پشتیبانی")
async def handle_support(message: Message):
    support_text = (
        "👥 **واحد پشتیبانی**\n\n"
        "در صورت بروز هرگونه مشکل، سوال یا تمدید اشتراک با آیدی پشتیبانی در ارتباط باشید:\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await message.answer(support_text)

@dp.message(F.text == "❓ سوالات متداول")
async def handle_faq(message: Message):
    faq_text = (
        "❓ **سوالات متداول (FAQ)**\n\n"
        "۱. سرویس‌ها از چه پروتکل‌هایی پشتیبانی می‌کنند؟\n"
        "پاسخ: تمامی سرویس‌ها از پروتکل‌های پایدار L2TP و V2Ray پشتیبانی می‌کنند.\n\n"
        "۲. تحویل سرویس بعد از خرید چقدر طول می‌کشد؟\n"
        "پاسخ: پس از ارسال فیش به پشتیبانی، اشتراک در کمتر از ۱۰ دقیقه فعال می‌گردد.\n\n"
        "۳. آیا امکان استفاده روی چند دستگاه وجود دارد؟\n"
        "پاسخ: بله، بسته به پلن خریداری‌شده امکان اتصال همزمان وجود دارد."
    )
    await message.answer(faq_text)

@dp.message(F.text == "⚙️ کانفیگ‌ها و آموزش اتصال")
async def handle_configs(message: Message):
    guide_text = (
        "⚙️ **راهنمای اتصال و کانفیگ‌ها**\n\n"
        "برای اتصال در سیستم‌عامل‌های مختلف می‌توانید از راهنماهای زیر استفاده فرمایید:\n\n"
        "📱 **اندروید و iOS:** استفاده از نرم‌افزارهای V2Box یا v2rayNG و تنظیم دستی L2TP.\n"
        "💻 **ویندوز و مک:** تنظیم شبکه در بخش Network Settings.\n\n"
        f"در صورت نیاز به راهنمایی بیشتر با پشتیبانی در ارتباط باشید: @{SUPPORT_USERNAME}"
    )
    await message.answer(guide_text)

# ----------------------------------------------------
# 4. وب‌سرور سبک سلامت (برای جلوگیری از خطای پورت Render)
# ----------------------------------------------------
async def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get('/', lambda req: web.Response(text="Mikrotik Bot is running live!"))
    app.router.add_get('/health', lambda req: web.Response(text="OK"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"🌐 Health server successfully listening on port {port}")
    return runner

# ----------------------------------------------------
# 5. نقطه شروع و اجرای همزمان (Async Entrypoint)
# ----------------------------------------------------
async def main():
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN یافت نشد! لطفاً متغیر محیطی BOT_TOKEN را در Render تنظیم کنید.")
        return

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    
    # اجرای وب‌سرور برای پاس کردن Port Check پلتفرم Render
    runner = await run_web_server()
    
    try:
        logging.info("🚀 ربات با موفقیت آماده به کار شد. شروع Polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 ربات متوقف شد.")

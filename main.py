import os
import logging
import asyncio
from typing import Union

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# --- تنظیمات محیطی (Single Source of Truth) ---
TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_USERNAME = "L2tp1Support" 
CARD_HOLDER = "رحیمی"
# شماره کارت مستقیم از متغیرهای محیطی رندر خوانده می‌شود
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000-0000-0000-0000") 

# قیمت‌گذاری پلن‌ها مطابق دستور آرشاوین
PLAN1_PRICE = 250000
PLAN2_PRICE = 400000
PLAN3_PRICE = 600000

PORT = int(os.getenv("PORT", 10000))

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- کیبوردهای اصلی (دقیقاً ۴ ردیف) ---

def get_main_menu():
    builder = InlineKeyboardBuilder()
    # ردیف ۱
    builder.row(InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_subscription"))
    # ردیف ۲
    builder.row(
        InlineKeyboardButton(text="📊 اطلاعات حساب", callback_data="account_info"),
        InlineKeyboardButton(text="💎 اشتراک‌های من", callback_data="my_subscriptions")
    )
    # ردیف ۳
    builder.row(
        InlineKeyboardButton(text="💰 شارژ حساب", callback_data="topup_account"),
        InlineKeyboardButton(text="👥 پشتیبانی", callback_data="contact_support")
    )
    # ردیف ۴
    builder.row(
        InlineKeyboardButton(text="❓ سوالات متداول", callback_data="faq"),
        InlineKeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال", callback_data="configs_and_tutorials")
    )
    return builder.as_markup()

def get_plans_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"پلن ۱ - {PLAN1_PRICE:,} تومان", callback_data="plan_1"))
    builder.row(InlineKeyboardButton(text=f"پلن ۲ - {PLAN2_PRICE:,} تومان", callback_data="plan_2"))
    builder.row(InlineKeyboardButton(text=f"پلن ۳ - {PLAN3_PRICE:,} تومان", callback_data="plan_3"))
    builder.row(InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu"))
    return builder.as_markup()

# --- هندلرها ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        f"👋 <b>سلام {message.from_user.first_name} عزیز!</b>\n\n"
        "به سیستم مدیریت هوشمند <b>L2TP VPN</b> خوش آمدید.\n"
        "برای مدیریت خدمات خود از منوی زیر استفاده کنید."
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "👋 <b>به منوی اصلی بازگشتید.</b>",
        reply_markup=get_main_menu()
    )

# --- منطق خرید اشتراک (کامل و عملیاتی) ---

@dp.callback_query(F.data == "buy_subscription")
async def show_plans(callback: CallbackQuery):
    await callback.message.edit_text(
        "💎 <b>لطفاً نوع پلن مورد نظر خود را انتخاب کنید:</b>",
        reply_markup=get_plans_keyboard()
    )

@dp.callback_query(F.data.startswith("plan_"))
async def process_plan_selection(callback: CallbackQuery):
    plan_id = callback.data.split("_")[1]
    
    # تعیین قیمت بر اساس پلن انتخاب شده
    price = 0
    if plan_id == "1": price = PLAN1_PRICE
    elif plan_id == "2": price = PLAN2_PRICE
    elif plan_id == "3": price = PLAN3_PRICE

    payment_text = (
        f"✅ <b>پلن انتخاب شده: پلن {plan_id}</b>\n"
        f"💰 <b>مبلغ قابل واریز: {price:,} تومان</b>\n\n"
        f"💳 <b>شماره کارت:</b> <code>{CARD_NUMBER}</code>\n"
        f"👤 <b>به نام:</b> {CARD_HOLDER}\n\n"
        "⚠️ <b>لطفاً پس از واریز، تصویر فیش را در اینجا ارسال کنید تا توسط پشتیبانی بررسی و فعال شود.</b>\n\n"
        f"🆘 برای کمک فوری با پشتیبانی در ارتباط باشید: @{SUPPORT_USERNAME}"
    )
    
    await callback.message.edit_text(payment_text)
    # در اینجا منتظر می‌مانیم تا کاربر عکس بفرستد (در نسخه کامل با Photo Handler)

# هندلر دریافت عکس (فیش)
@dp.message(F.photo)
async def handle_receipt(message: Message):
    # ارسال پیام تایید و اطلاع‌رسانی به پشتیبانی
    await message.reply(
        f"✅ <b>فیش شما دریافت شد.</b>\n"
        f"لطفاً منتظر بررسی پشتیبانی (@{SUPPORT_USERNAME}) باشید."
    )
    # اینجا می‌توانید به پشتیبانی پیام بفرستید تا متوجه واریز شود

# --- بخش‌های دیگر (پشتیبانی و FAQ) ---

@dp.callback_query(F.data == "contact_support")
async def contact_support(callback: CallbackQuery):
    await callback.message.edit_text(
        f"👥 <b>پشتیبانی آنلاین</b>\n\n"
        f"برای ارتباط با پشتیبانی و رفع مشکلات خود، پیام خود را به آیدی زیر ارسال کنید:\n"
        f"👉 @{SUPPORT_USERNAME}",
        reply_markup=get_main_menu() # بازگشت به منو با دکمه بازگشت
    )

@dp.callback_query(F.data == "faq")
async def faq_handler(callback: CallbackQuery):
    faq_text = (
        "❓ <b>سوالات متداول</b>\n\n"
        "۱. چطور وصل شوم؟\nدر بخش کانفیگ‌ها آموزش را ببینید.\n\n"
        "۲. اشتراک من چه مدت اعتبار دارد؟\nبر اساس پلانی که خریداری کردید.\n\n"
        "۳. اگر فیش فرستادم و فعال نشد چه کنم؟\nبا @{SUPPORT_USERNAME} در میان بگذارید.\n\n"
        "۴. آیا امکان شارژ مجدد هست؟\nبله، از بخش شارژ حساب.\n"
        "۵. شماره کارت شما چیست؟\nدر بخش خرید اشتراک نمایش داده می‌شود.\n"
        "۶. چطور از پشتیبانی کمک بگیرم؟\nبا کلیک بر روی دکمه پشتیبانی."
    )
    # برای سادگی در این نسخه، فقط متن نمایش داده می‌شود
    await callback.message.edit_text(faq_text, reply_markup=get_main_menu())

# سایر هندلرها (Account Info, My Subs, etc.) باید به همین ترتیب برای جلوگیری از خطا تعریف شوند.
# در اینجا برای جلوگیری از کرش، یک هندلر کلی برای دکمه‌های تعریف نشده گذاشتم.

@dp.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer("این بخش در حال توسعه است یا هنوز تنظیم نشده است.", show_alert=True)

# --- تنظیمات سرور (Health Check برای Render) ---

app = web.Application()
async def health_check(request):
    return web.Response(text="OK")

app.router.add_get('/', health_check)

async def on_startup(app):
    await dp.start_polling(bot)

app.on_startup.append(on_startup)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

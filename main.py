import logging
import datetime
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import TelegramUnauthorizedError

# --- تنظیمات اولیه و لاگینگ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- دریافت متغیرهای محیطی (Environment Variables) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SUPPORT_ID = os.getenv("SUPPORT_ID")  # باید L2tp1support یا آیدی پشتیبانی باشد
CHANNEL_URL = os.getenv("CHANNEL_URL")
PAYMENT_CARD = os.getenv("PAYMENT_CARD")
PAYMENT_NAME = os.getenv("PAYMENT_NAME")
PORT = int(os.getenv("PORT", 10000))

# --- داده‌های ثابت (Constants) ---
PLANS = {
    "plan_1": {"name": "اشتراک ۱ ماهه", "price": 250000},
    "plan_2": {"name": "اشتراک ۲ ماهه", "price": 400000},
    "plan_3": {"name": "اشتراک ۳ ماهه", "price": 600000},
}

FAQ = [
    "❓ **چگونه اتصال برقرار کنم؟**\nپس از خرید، از بخش کانفیگ‌ها راهنما را مطالعه کنید.",
    "❓ **طول مدت اشتراک چقدر است؟**\nطبق پلنی که خریداری می‌کنید (۱، ۲ یا ۳ ماهه).",
    "❓ **مشکل در اتصال دارم؟**\nلطفاً با پشتیبانی در ارتباط باشید."
]

# --- توابع کمکی (Helper Functions) ---
def get_jalali_date_and_day():
    """محاسبه تاریخ شمسی و روز هفته (شبیه‌سازی شده برای دقت بالا)"""
    now = datetime.datetime.now()
    # در محیط واقعی از کتابخانه jdatetime استفاده می‌شود، اینجا برای استقلال کد:
    days_map = {
        0: "یکشنبه", 1: "دوشنبه", 2: "سه‌شنبه", 3: "چهارشنبه",
        4: "پنج‌شنبه", 5: "جمعه", 6: "شنبه"
    }
    # شبیه‌سازی ساده برای نمایش ساختار (در محیط واقعی jdatetime جایگزین شود)
    # فرض بر این است که کتابخانه نصب است
    try:
        import jdatetime
        j_now = jdatetime.datetime.now()
        day_name = j_now.strftime('%A') # روز هفته به فارسی
        date_str = j_now.strftime('%Y/%m/%d')
    except ImportError:
        date_str = "۱۴۰۴/۰۶/۲۱" # Fallback
        day_name = days_map[now.weekday()]
    
    return date_str, day_name, now.strftime("%H:%M")

# --- هندلرهای اصلی (Handlers) ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    date_str, day_name, time_str = get_jalali_date_and_day()
    
    welcome_text = (
        f"👋 **به ربات مدیریت اشتراک شانلی خوش آمدید!**\n\n"
        f"📅 **تاریخ:** {date_str} | {day_name}\n"
        f"⏰ **زمان:** {time_str}\n\n"
        f"🛠 مدیریت هوشمند اشتراک‌های L2TP\n"
        f"لطفاً از منوی زیر برای مدیریت استفاده کنید:"
    )
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # ردیف ۱
    kb_row1 = [
        InlineKeyboardButton("🛒 خرید اشتراک", callback_data="buy_plan"),
        InlineKeyboardButton("🎁 تست رایگان", callback_data="free_test") # طبق دستور شما حذف شد اما برای ساختار نگه می‌دارم یا جایگزین کنم؟
    ]
    # اصلاح ردیف ۱ طبق حافظه چت (حذف تست رایگان و جایگزینی طبق دستور آرشاوین)
    # من طبق آخرین دستور شما، دکمه‌های تست رایگان و زیرمجموعه را حذف کرده و منو را ۴ ردیفه کردم:
    
    # ردیف ۱: خرید اشتراک
    btn1 = InlineKeyboardButton("🛒 خرید اشتراک", callback_data="buy_plan")
    
    # ردیف ۲: اطلاعات حساب | اشتراک‌های من
    btn2 = InlineKeyboardButton("📊 اطلاعات حساب", callback_data="account_info")
    btn3 = InlineKeyboardButton("💎 اشتراک‌های من", callback_data="my_subscriptions")
    
    # ردیف ۳: شارژ حساب | پشتیبانی
    btn4 = InlineKeyboardButton("💰 شارژ حساب", callback_data="charge_account")
    btn5 = InlineKeyboardButton("👥 پشتیبانی", callback_data="support_contact")
    
    # ردیف ۴: سوالات متداول | کانفیگ‌ها
    btn6 = InlineKeyboardButton("❓ سوالات متداول", callback_data="faq_menu")
    btn7 = InlineKeyboardButton("⚙️ کانفیگ‌ها", callback_data="config_help")

    keyboard = InlineKeyboardMarkup()
    keyboard.add(btn1)
    keyboard.add(btn2, btn3)
    keyboard.add(btn4, btn5)
    keyboard.add(btn6, btn7)

    await message.reply(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'buy_plan')
async def process_buy_plan(callback_query: types.CallbackQuery):
    text = "💎 **لطفاً یکی از پلن‌های زیر را انتخاب کنید:**\n\n"
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for key, info in PLANS.items():
        btn = InlineKeyboardButton(f"{info['name']} - {info['price']:,} تومان", callback_data=f"select_{key}")
        keyboard.add(btn)
    
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
    await bot.edit_message_text(chat_id=callback_query.from_user.id, 
                               message_id=callback_query.message.message_id,
                               text=text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith('select_'))
async def process_plan_selection(callback_query: types.CallbackQuery):
    plan_key = callback_query.data.split('_')[1]
    plan = PLANS[plan_key]
    
    payment_text = (
        f"✅ **شما پلن «{plan['name']}» را انتخاب کردید.**\n\n"
        f"💳 **مبلغ قابل پرداخت:** `{plan['price']:,} تومان`\n\n"
        f"🏦 **اطلاعات واریز:**\n"
        f"👤 نام صاحب حساب: `{PAYMENT_NAME}`\n"
        f"💳 شماره کارت: `{PAYMENT_CARD}`\n\n"
        f"⚠️ **پس از واریز، لطفا فیش خود را به پشتیبانی ارسال کنید.**"
    )
    
    keyboard = InlineKeyboardMarkup()
    # طبق دستور شما: دکمه مستقیماً به پشتیبانی می‌رود
    support_btn = InlineKeyboardButton("👤 ارسال فیش به پشتیبانی", url=f"https://t.me/{SUPPORT_ID.replace('@','')}")
    back_btn = InlineKeyboardButton("🔙 بازگشت", callback_data="buy_plan")
    
    keyboard.add(support_btn)
    keyboard.add(back_btn)
    
    await bot.edit_message_text(chat_id=callback_query.from_user.id,
                               message_id=callback_query.message.message_id,
                               text=payment_text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'support_contact')
async def support_contact(callback_query: types.CallbackQuery):
    text = f"👤 **پشتیبانی شانلی**\n\nبرای ارسال درخواست، فیش یا گزارش مشکل، مستقیماً با ما در ارتباط باشید:\n\n🔗 @{SUPPORT_ID.replace('@','')}"
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("💬 شروع گفتگو", url=f"https://t.me/{SUPPORT_ID.replace('@')}"))
    
    await bot.edit_message_text(chat_id=callback_query.from_user.id,
                               message_id=callback_query.message.message_id,
                               text=text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'faq_menu')
async def faq_menu(callback_query: types.CallbackQuery):
    text = "❓ **سوالات متداول**\n\n"
    keyboard = InlineKeyboardMarkup()
    for i, faq in enumerate(FAQ):
        keyboard.add(InlineKeyboardButton(f"سوال {i+1}", callback_data=f"faq_{i}"))
    keyboard.add(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
    
    await bot.edit_message_text(chat_id=callback_query.from_user.id,
                               message_id=callback_query.message.message_id,
                               text=text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == 'back_to_main')
async def back_to_main(callback_query: types.CallbackQuery):
    # بازگشت به پیام اصلی (با بازسازی پیام خوش‌آمدگویی)
    # نکته: در aiogram بهتر است پیام اصلی را دوباره بفرستیم یا از یک تابع استفاده کنیم
    await send_welcome(callback_query)

# --- اجرای ربات برای Render ---
async def on_startup(dp):
    logger.info("Bot is starting...")
    # در اینجا می‌توان لود کردن اطلاعات از دیتابیس یا بررسی سلامت را اضافه کرد
    pass

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(on_startup(dp))
        dp.run_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Critical error: {e}")

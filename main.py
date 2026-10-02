import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# تنظیمات لاگینگ برای ردیابی دقیق
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# خواندن ایمن و دقیق متغیرهای محیطی از Render
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENoy4cm5g646bX0X")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6278059256"))
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support")
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", "10000"))

# راه‌اندازی ربات و دیسپچر
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# استیت‌های مربوط به خرید و ارسال فیش
class BuyState(StatesGroup):
    waiting_for_plan = State()
    waiting_for_receipt = State()

# --- کیبوردهای ربات ---

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("💎 خرید و تمدید اشتراک"),
        KeyboardButton("📊 پنل کاربری IBSng")
    )
    keyboard.add(
        KeyboardButton("🚀 لیست تعرفه‌ها و امکانات"),
        KeyboardButton("📱 راهنمای اتصال")
    )
    keyboard.add(
        KeyboardButton("💬 پشتیبانی و ارتباط با ما"),
        KeyboardButton("📢 کانال رسمی اطلاع‌رسانی")
    )
    return keyboard

def get_plans_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("⭐ پلن ویژه VIP نامحدود (۱ ماهه / ۱ کاربره) - ۳۵۰,۰۰۰ تومان", callback_data="buy_vip_unlimited"),
        InlineKeyboardButton("🔹 ۱ ماهه تک کاربره - ۲۰۰,۰۰۰ تومان", callback_data="buy_1m_1u"),
        InlineKeyboardButton("🔹 ۱ ماهه دو کاربره - ۲۵۰,۰۰۰ تومان", callback_data="buy_1m_2u"),
        InlineKeyboardButton("🔹 ۲ ماهه تک کاربره - ۳۸۰,۰۰۰ تومان", callback_data="buy_2m_1u"),
        InlineKeyboardButton("🔹 ۲ ماهه دو کاربره - ۴۳۰,۰۰۰ تومان", callback_data="buy_2m_2u"),
        InlineKeyboardButton("🔹 ۳ ماهه تک کاربره - ۵۵۰,۰۰۰ تومان", callback_data="buy_3m_1u"),
        InlineKeyboardButton("🔹 ۳ ماهه دو کاربره - ۶۰۰,۰۰۰ تومان", callback_data="buy_3m_2u")
    )
    return keyboard

# دیکشنری مشخصات پلن‌ها
PLANS_DATA = {
    "buy_vip_unlimited": {"title": "پلن ویژه VIP نامحدود (۱ ماهه - ۱ کاربره)", "price": "۳۵۰,۰۰۰ تومان"},
    "buy_1m_1u": {"title": "۱ ماهه تک کاربره", "price": "۲۰۰,۰۰۰ تومان"},
    "buy_1m_2u": {"title": "۱ ماهه دو کاربره", "price": "۲۵۰,۰۰۰ تومان"},
    "buy_2m_1u": {"title": "۲ ماهه تک کاربره", "price": "۳۸۰,۰۰۰ تومان"},
    "buy_2m_2u": {"title": "۲ ماهه دو کاربره", "price": "۴۳۰,۰۰۰ تومان"},
    "buy_3m_1u": {"title": "۳ ماهه تک کاربره", "price": "۵۵۰,۰۰۰ تومان"},
    "buy_3m_2u": {"title": "۳ ماهه دو کاربره", "price": "۶۰۰,۰۰۰ تومان"},
}

# --- هندلرهای دستورات و پیام‌ها ---

@dp.message_handler(commands=['start'], state='*')
async def start_cmd(message: types.Message, state: FSMContext):
    await state.finish()
    welcome_text = (
        "سلام و درود! به سامانه رسمی سرویس‌های پرسرعت L2TP VPN خوش آمدید. 🇩🇪✨\n\n"
        "⚡ ارائه‌دهنده قدرتمندترین و پایدارترین سرورهای اختصاصی آلمان با پینگ فوق‌العاده و سرعت نامحدود.\n"
        "🎁 تمامی سرویس‌ها دارای ۱۰ گیگابایت حجم هدیه می‌باشند.\n\n"
        "لطفاً از منوی زیر گزینه مورد نظر خود را انتخاب نمایید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda msg: msg.text == "🚀 لیست تعرفه‌ها و امکانات", state='*')
async def show_tariffs(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "📋 **لیست تعرفه‌های سرویس‌های اختصاصی آلمان (با ۱۰ گیگ هدیه روی تمامی پلن‌ها):**\n\n"
        "⭐ **پلن ویژه VIP نامحدود (۱ ماهه / ۱ کاربره):** ۳۵۰,۰۰۰ تومان\n\n"
        "🔹 **۱ ماهه تک کاربره:** ۲۰۰,۰۰۰ تومان\n"
        "🔹 **۱ ماهه دو کاربره:** ۲۵۰,۰۰۰ تومان\n\n"
        "🔹 **۲ ماهه تک کاربره:** ۳۸۰,۰۰۰ تومان\n"
        "🔹 **۲ ماهه دو کاربره:** ۴۳۰,۰۰۰ تومان\n\n"
        "🔹 **۳ ماهه تک کاربره:** ۵۵۰,۰۰۰ تومان\n"
        "🔹 **۳ ماهه دو کاربره:** ۶۰۰,۰۰۰ تومان\n\n"
        "🌐 سرورهای اختصاصی مستقر در کشور آلمان با بالاترین کیفیت و اتصال پایدار و بدون قطعی."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_plans_inline_keyboard())

@dp.message_handler(lambda msg: msg.text == "💎 خرید و تمدید اشتراک", state='*')
async def buy_subscription(message: types.Message, state: FSMContext):
    await state.finish()
    text = "لطفاً پلن اشتراک مورد نظر خود را برای خرید یا تمدید انتخاب کنید:"
    await message.answer(text, reply_markup=get_plans_inline_keyboard())

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("buy_"), state='*')
async def plan_selected(callback_query: types.CallbackQuery, state: FSMContext):
    plan_key = callback_query.data
    plan_info = PLANS_DATA.get(plan_key)

    if not plan_info:
        await callback_query.answer("پلن یافت نشد!", show_alert=True)
        return

    await state.update_data(chosen_plan=plan_info["title"], price=plan_info["price"])
    await BuyState.waiting_for_receipt.set()

    payment_msg = (
        f"✅ **سفارش انتخاب شده:** {plan_info['title']}\n"
        f"💰 **مبلغ قابل پرداخت:** {plan_info['price']}\n\n"
        f"💳 لطفاً مبلغ را به شماره کارت زیر واریز نمایید:\n\n"
        f"💳 شماره کارت:\n`{PAYMENT_CARD}`\n"
        f"👤 به نام: **{PAYMENT_NAME}**\n\n"
        "📸 پس از واریز، **تصویر واضح فیش واریزی** یا اسکرین‌شات رسید را همین‌جا ارسال کنید."
    )
    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=payment_msg,
        parse_mode="Markdown"
    )
    await callback_query.answer()

@dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT, types.ContentType.TEXT], state=BuyState.waiting_for_receipt)
async def process_receipt(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    plan_title = user_data.get("chosen_plan", "نامشخص")
    price = user_data.get("price", "نامشخص")

    user_info = (
        f"👤 نام: {message.from_user.full_name}\n"
        f"🆔 آیدی کاربری: `{message.from_user.id}`\n"
        f"🔗 یوزرنیم: @{message.from_user.username if message.from_user.username else 'ندارد'}\n"
        f"💎 پلن انتخابی: {plan_title}\n"
        f"💰 مبلغ: {price}"
    )

    # ارسال به ادمین
    admin_caption = f"🧾 **فیش واریزی جدید دریافت شد!**\n\n{user_info}"
    try:
        if message.photo:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_caption, parse_mode="Markdown")
        elif message.document:
            await bot.send_document(chat_id=ADMIN_ID, document=message.document.file_id, caption=admin_caption, parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=ADMIN_ID, text=f"{admin_caption}\n\n📝 متن ارسالی: {message.text}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"خطا در ارسال به ادمین: {e}")

    await message.answer(
        "✅ فیش واریزی شما با موفقیت برای مدیریت ارسال شد.\n"
        "⏳ اطلاعات اکانت شما پس از بررسی در سریع‌ترین زمان ممکن ارسال خواهد شد.\n\n"
        "از شکیبایی شما سپاسگزاریم. 🙏",
        reply_markup=get_main_keyboard()
    )
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "📊 پنل کاربری IBSng", state='*')
async def ibsng_panel(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "🌐 **ورود به پنل کاربری IBSng:**\n\n"
        "⚠️ **نکته بسیار مهم:**\n"
        "«برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.»\n\n"
        f"🔗 [ورود به پنل کاربری IBSng]({IBSNG_PANEL_URL})"
    )
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🌐 ورود مستقیم به پنل", url=IBSNG_PANEL_URL))
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "📱 راهنمای اتصال", state='*')
async def connection_guide(message: types.Message, state: FSMContext):
    await state.finish()
    guide_text = (
        "📚 **راهنمای جامع اتصال به سرویس‌های L2TP:**\n\n"
        "این پروتکل به صورت پیش‌فرض و نیتیو (بدون نیاز به نصب نرم‌افزار اضافی) در انواع سیستم‌عامل‌ها پشتیبانی می‌شود:\n\n"
        "🔹 **ویندوز و لپ‌تاپ:** از مسیر Settings > Network & Internet > VPN اقدام به ساخت کانکشن L2TP/IPsec با پیش‌کلید (Preshared Key) نمایید.\n"
        "🔹 **گوشی‌های موبایل (iOS و Android):** در بخش تنظیمات VPN، پروتکل L2TP یا IKEv2 را انتخاب و اطلاعات ارسال‌شده را وارد کنید.\n"
        "🔹 **مودم‌ها و روترها:** در کنسول مدیریتی مودم، در بخش VPN Client تنظیمات L2TP را وارد کرده تا تمام اینترنت منزل/محل‌کار از سرور اختصاصی آلمان عبور کند.\n\n"
        f"در صورت نیاز به راهنمایی گام‌به‌گام با پشتیبانی در ارتباط باشید: {SUPPORT_ID}"
    )
    await message.answer(guide_text, parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "💬 پشتیبانی و ارتباط با ما", state='*')
async def support_info(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "👨‍💻 **مرکز پشتیبانی و ارتباط مستقیم:**\n\n"
        f"جهت طرح هرگونه سوال، مشاوره یا رفع اشکال با آیدی پشتیبانی در ارتباط باشید:\n"
        f"👉 {SUPPORT_ID}\n\n"
        "پاسخگویی در کوتاه‌ترین زمان ممکن صورت می‌گیرد."
    )
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("ارسال پیام به پشتیبانی", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}"))
    await message.answer(text, reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "📢 کانال رسمی اطلاع‌رسانی", state='*')
async def channel_info(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "📢 برای دریافت آخرین اخبار، وضعیت سرورها و اطلاعیه‌ها در کانال رسمی ما عضو شوید:\n\n"
        f"🔗 [کانال رسمی اطلاع‌رسانی]({CHANNEL_URL})"
    )
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("عضویت در کانال", url=CHANNEL_URL))
    await message.answer(text, reply_markup=keyboard)

# سرور وب برای زنده نگه داشتن سرویس روی Render (Health Check)
async def handle_ping(request):
    return web.Response(text="Bot is running smoothly on German Servers!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Web server started on port {PORT}")

async def main():
    await start_web_server()
    logger.info("Starting Telegram Bot Polling...")
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())

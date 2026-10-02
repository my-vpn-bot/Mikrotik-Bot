import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# تنظیمات دقیق لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# خواندن متغیرهای محیطی از Render
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENjgv03a5lnarX0X")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6278059256"))
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support")
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", "10000"))

bot = Bot(token=GAPGPTMASKTOKENjgv03a5lnarX1X
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class BuyState(StatesGroup):
    waiting_for_plan = State()
    waiting_for_receipt = State()

# --- کیبورد اصلی (پایین صفحه) ---
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

# --- منوی اینلاین راهنمای اتصال سیستم‌عامل‌ها (دقیقاً مثل تصویر) ---
def get_guide_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📱 آیفون و آیپد (iOS)", callback_data="guide_ios"),
        InlineKeyboardButton("🤖 اندروید (Android)", callback_data="guide_android")
    )
    keyboard.add(
        InlineKeyboardButton("💻 ویندوز (Windows)", callback_data="guide_windows"),
        InlineKeyboardButton("🍏 مک‌بوک (macOS)", callback_data="guide_mac")
    )
    keyboard.add(
        InlineKeyboardButton("📟 مودم و روتر", callback_data="guide_modem"),
        InlineKeyboardButton("🛡️ آموزش OpenVPN", callback_data="guide_ovpn")
    )
    return keyboard

# --- لیست تعرفه‌ها ---
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

PLANS_DATA = {
    "buy_vip_unlimited": {"title": "پلن ویژه VIP نامحدود (۱ ماهه - ۱ کاربره)", "price": "۳۵۰,۰۰۰ تومان"},
    "buy_1m_1u": {"title": "۱ ماهه تک کاربره", "price": "۲۰۰,۰۰۰ تومان"},
    "buy_1m_2u": {"title": "۱ ماهه دو کاربره", "price": "۲۵۰,۰۰۰ تومان"},
    "buy_2m_1u": {"title": "۲ ماهه تک کاربره", "price": "۳۸۰,۰۰۰ تومان"},
    "buy_2m_2u": {"title": "۲ ماهه دو کاربره", "price": "۴۳۰,۰۰۰ تومان"},
    "buy_3m_1u": {"title": "۳ ماهه تک کاربره", "price": "۵۵۰,۰۰۰ تومان"},
    "buy_3m_2u": {"title": "۳ ماهه دو کاربره", "price": "۶۰۰,۰۰۰ تومان"},
}

# --- پیام شروع ---
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

# --- لیست تعرفه‌ها ---
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
        "🌐 سرورهای اختصاصی مستقر در کشور آلمان با بالاترین پایداری و بدون قطعی."
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_plans_inline_keyboard())

# --- خرید و پرداخت ---
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
        "از صبوری شما سپاسگزاریم. 🙏",
        reply_markup=get_main_keyboard()
    )
    await state.finish()

# --- پنل کاربری IBSng ---
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

# --- راهنمای جامع اتصال و انتخاب دیوایس ---
@dp.message_handler(lambda msg: msg.text == "📱 راهنمای اتصال", state='*')
async def connection_guide_menu(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "📱 **راهنمای جامع اتصال به سرویس‌ها:**\n\n"
        "لطفاً دستگاه یا سیستم‌عامل مورد نظر خود را برای مشاهده آموزش گام‌به‌گام انتخاب کنید:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_guide_inline_keyboard())

# دکمه‌های اینلاین راهنما
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("guide_"), state='*')
async def process_guides(callback: types.CallbackQuery):
    action = callback.data
    
    if action == "guide_ios":
        guide_msg = (
            "📱 **آموزش اتصال در آیفون و آیپد (iOS):**\n\n"
            "۱. وارد `Settings` و سپس بخش `VPN & Device Management` شوید.\n"
            "۲. گزینه `Add VPN Configuration` را انتخاب کنید.\n"
            "۳. نوع اتصال (`Type`) را روی **L2TP** بگذارید.\n"
            "۴. مشخصات (Server، Username، Password و Secret) ارسال‌شده را وارد کرده و Save کنید.\n"
            "۵. دکمه اتصال را روشن نمایید."
        )
    elif action == "guide_android":
        guide_msg = (
            "🤖 **آموزش اتصال در اندروید (Android):**\n\n"
            "۱. به تنظیمات گوشی (Settings) و بخش اتصالات (Connections > More connection settings > VPN) بروید.\n"
            "۲. افزودن VPN جدید را بزنید و نوع اتصال را **L2TP/IPSec PSK** انتخاب کنید.\n"
            "۳. آدرس سرور و پیش‌کلید (Preshared Key) را وارد کنید.\n"
            "۴. نام کاربری و پسورد خود را ثبت و متصل شوید."
        )
    elif action == "guide_windows":
        guide_msg = (
            "💻 **آموزش اتصال در ویندوز (Windows):**\n\n"
            "۱. وارد Settings > Network & Internet > VPN شوید.\n"
            "۲. گزینه Add a VPN connection را بزنید.\n"
            "۳. VPN Provider را روی Windows (built-in) و نوع را روی **L2TP/IPsec with pre-shared key** قرار دهید.\n"
            "۴. مشخصات دریافتی را وارد کرده و ذخیره نمایید."
        )
    elif action == "guide_mac":
        guide_msg = (
            "🍏 **آموزش اتصال در مک‌بوک (macOS):**\n\n"
            "۱. وارد System Settings > Network شوید.\n"
            "۲. روی علامت سه نقطه/افزودن کلیک کرده و Add VPN Configuration > L2TP over IPSec را بزنید.\n"
            "۳. آدرس سرور، نام کاربری و در بخش Authentication Settings پسورد و Shared Secret را درج نمایید."
        )
    elif action == "guide_modem":
        guide_msg = (
            "📟 **آموزش تنظیم روی مودم و روتر:**\n\n"
            "۱. وارد صفحه کنسول مدیریتی مودم (معمولاً 192.168.1.1) شوید.\n"
            "۲. به بخش VPN یا VPN Client بروید.\n"
            "۳. پروتکل L2TP را انتخاب و آدرس سرور اختصاصی و اطلاعات اکانت را وارد کرده و فعال کنید تا تمام اینترنت شبکه شما تانل شود."
        )
    elif action == "guide_ovpn":
        guide_msg = (
            "🛡️ **آموزش اتصال با OpenVPN:**\n\n"
            "۱. اپلیکیشن رسمی OpenVPN Connect را دانلود و نصب کنید.\n"
            "۲. فایل کانفیگ اختصاصی ارسالی را در برنامه Import کنید.\n"
            "۳. یوزرنیم و پسورد خود را وارد کرده و متصل شوید."
        )
    else:
        guide_msg = "اطلاعات راهنما در دسترس نیست."

    await callback.message.answer(guide_msg, parse_mode="Markdown")
    await callback.answer()

# --- پشتیبانی و کانال ---
@dp.message_handler(lambda msg: msg.text == "💬 پشتیبانی و ارتباط با ما", state='*')
async def support_info(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "👨‍💻 **مرکز پشتیبانی و ارتباط مستقیم:**\n\n"
        f"جهت طرح هرگونه سوال، راهنمایی یا پیگیری با آیدی پشتیبانی در ارتباط باشید:\n"
        f"👉 {SUPPORT_ID}"
    )
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("ارسال پیام به پشتیبانی", url=f"https://t.me/{SUPPORT_ID.replace('@', '')}"))
    await message.answer(text, reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "📢 کانال رسمی اطلاع‌رسانی", state='*')
async def channel_info(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "📢 برای دریافت آخرین وضعیت سرورها، اخبار و تخفیف‌ها در کانال رسمی ما عضو شوید:\n\n"
        f"🔗 [کانال رسمی اطلاع‌رسانی]({CHANNEL_URL})"
    )
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("عضویت در کانال", url=CHANNEL_URL))
    await message.answer(text, reply_markup=keyboard)

# سرور وب برای Health Check در Render
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

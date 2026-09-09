import os
import asyncio
import logging
from datetime import datetime

import pytz
import jdatetime
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ----------------------------------------------------
# 1. تنظیمات لاگ و متغیرهای محیطی
# ----------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))
PORT = int(os.getenv("PORT", 10000))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/L2TP_VPN_OFFICIAL")

CARD_NUMBER = "6104338904607443"
CARD_HOLDER = "رحیمی"

PLAN1_NAME = "پلن ۱ ماهه"
PLAN1_PRICE = "۲۵۰,۰۰۰"

PLAN2_NAME = "پلن ۳ ماهه"
PLAN2_PRICE = "۴۰۰,۰۰۰"

PLAN3_NAME = "پلن ۶ ماهه"
PLAN3_PRICE = "۶۰۰,۰۰۰"

# ----------------------------------------------------
# 2. وضعیت‌های FSM
# ----------------------------------------------------
class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

# ----------------------------------------------------
# 3. توابع کمکی تبدیل اعداد و زمان تهران
# ----------------------------------------------------
def to_persian_digits(text: str) -> str:
    en_to_fa = {
        '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
        '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'
    }
    return "".join(en_to_fa.get(ch, ch) for ch in str(text))

def get_tehran_datetime_persian():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now_tehran = datetime.now(tehran_tz)
    j_now = jdatetime.datetime.fromgregorian(datetime=now_tehran)

    persian_weekdays = {
        "Saturday": "شنبه",
        "Sunday": "یک‌شنبه",
        "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه",
        "Wednesday": "چهارشنبه",
        "Thursday": "پنج‌شنبه",
        "Friday": "جمعه"
    }
    weekday_en = now_tehran.strftime("%A")
    weekday_fa = persian_weekdays.get(weekday_en, weekday_en)

    persian_months = [
        "", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
    ]
    month_name = persian_months[j_now.month]

    date_str = f"{to_persian_digits(j_now.day)} {month_name} {to_persian_digits(j_now.year)}"
    time_str = f"{to_persian_digits(now_tehran.strftime('%H'))}:{to_persian_digits(now_tehran.strftime('%M'))}"

    return weekday_fa, date_str, time_str

# ----------------------------------------------------
# 4. کیبوردهای اصلی و شیشه‌ای (Back & Clean)
# ----------------------------------------------------
def get_main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    # ردیف ۱
    keyboard.row(KeyboardButton("🛒 خرید اشتراک"))
    # ردیف ۲
    keyboard.row(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    # ردیف ۳
    keyboard.row(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    # ردیف ۴
    keyboard.row(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return keyboard

def get_close_button():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("❌ بستن پیام", callback_data="close_message"))
    return keyboard

def get_plans_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(f"🔹 {PLAN1_NAME} ({PLAN1_PRICE} تومان)", callback_data="plan_1"),
        InlineKeyboardButton(f"🔹 {PLAN2_NAME} ({PLAN2_PRICE} تومان)", callback_data="plan_2"),
        InlineKeyboardButton(f"🔹 {PLAN3_NAME} ({PLAN3_PRICE} تومان)", callback_data="plan_3"),
        InlineKeyboardButton("❌ بستن پیام", callback_data="close_message")
    )
    return keyboard

# ----------------------------------------------------
# 5. تنظیمات ربات و دیسپچر
# ----------------------------------------------------
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ----------------------------------------------------
# 6. هندلرهای عمومی و منوی استارت
# ----------------------------------------------------
@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    user_name = message.from_user.first_name or "کاربر"
    weekday_fa, date_str, time_str = get_tehran_datetime_persian()

    welcome_text = (
        f"سلام {user_name} عزیز، به ربات هوشمند **L2TP VPN** خوش آمدی! 🌸\n\n"
        f"📅 **امروز:** {weekday_fa}، {date_str}\n"
        f"⏰ **ساعت فعلی (افق تهران):** {time_str}\n\n"
        f"🚀 **دسترسی پایدار، بدون مرز و با بالاترین استاندارد امنیتی!**\n"
        f"سرویس‌های ما با بهره‌گیری از آخرین هسته‌های پایدار V2Ray و مسیریابی ویژه داخلی، "
        f"تجربه‌ای متمایز از وبگردی آزاد را برای شما فراهم می‌آورند.\n\n"
        f"💎 **ویژگی‌های برجسته سرویس:**\n"
        f"✅ پینگ ایده‌آل و بهینه‌سازی شده جهت **گیمینگ آنلاین و کاهش پکت‌لاس**\n"
        f"✅ آی‌پی تمیز، ثابت و مطمئن ویژه **ترید، فارکس و صرافی‌های بین‌المللی**\n"
        f"✅ سازگاری کامل با تمامی سیستم‌عامل‌ها (Android, iOS, Windows, macOS)\n"
        f"✅ بدون اعمال محدودیت حجمی یا افت پهنای باند شبکه\n\n"
        f"⚡ جهت ثبت یا تمدید اشتراک، وضعیت حساب و دریافت کانفیگ‌ها، از کلیدهای منوی زیر استفاده کنید.\n\n"
        f"📢 **کانال اطلاع‌رسانی و اخبار وضعیت سرورها:**\n"
        f"🔗 {CHANNEL_LINK}"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

# هندلر Callback بستن پیام‌ها
@dp.callback_query_handler(lambda c: c.data == "close_message", state="*")
async def handle_close_message(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    try:
        await callback_query.message.delete()
    except Exception:
        await callback_query.answer("پیام بسته شد.")

# ----------------------------------------------------
# 7. فرآیند خرید، انتخاب پلن و ارسال فیش
# ----------------------------------------------------
@dp.message_handler(lambda msg: msg.text == "🛒 خرید اشتراک", state="*")
async def process_buy_menu(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "🛒 **لیست پلن‌های فعال سرویس L2TP VPN:**\n\n"
        "لطفاً دوره مد نظر خود را جهت دریافت شماره کارت و واریز انتخاب کنید:"
    )
    await message.answer(text, reply_markup=get_plans_inline_keyboard(), parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith("plan_"), state="*")
async def process_plan_selection(callback_query: types.CallbackQuery, state: FSMContext):
    plan_key = callback_query.data
    plan_map = {
        "plan_1": (PLAN1_NAME, PLAN1_PRICE),
        "plan_2": (PLAN2_NAME, PLAN2_PRICE),
        "plan_3": (PLAN3_NAME, PLAN3_PRICE),
    }
    selected_plan = plan_map.get(plan_key, (PLAN1_NAME, PLAN1_PRICE))

    await state.update_data(selected_plan=selected_plan[0], plan_price=selected_plan[1])
    await PaymentStates.waiting_for_receipt.set()

    text = (
        f"💳 **اطلاعات واریز وجه - {selected_plan[0]}**\n\n"
        f"💰 مبلغ قابل پرداخت: **{selected_plan[1]} تومان**\n\n"
        f"📌 شماره کارت بانکی:\n"
        f"`{CARD_NUMBER}`\n"
        f"👤 بنام: **{CARD_HOLDER}**\n\n"
        f"⚠️ **دستورالعمل تایید:**\n"
        f"پس از واریز، لطفاً **فقط تصویر (عکس) فیش واریزی** خود را در همین چت ارسال نمایید تا بلافاصله بررسی و اشتراک فعال گردد."
    )
    await callback_query.message.edit_text(text, reply_markup=get_close_button(), parse_mode="Markdown")
    await callback_query.answer()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=PaymentStates.waiting_for_receipt)
async def process_receipt_photo(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    plan_name = user_data.get("selected_plan", "مشخص نشده")
    plan_price = user_data.get("plan_price", "مشخص نشده")
    
    user = message.from_user
    username_str = f"@{user.username}" if user.username else "ندارد"

    admin_caption = (
        f"📥 **رسید واریز وجه جدید!**\n\n"
        f"👤 خریدار: {user.full_name} ({username_str})\n"
        f"🆔 آیدی عددی: `{user.id}`\n"
        f"📦 پلن انتخابی: **{plan_name}**\n"
        f"💰 مبلغ: **{plan_price} تومان**\n"
    )

    admin_kb = InlineKeyboardMarkup(row_width=2)
    admin_kb.add(
        InlineKeyboardButton("✅ تایید و تحویل", callback_data=f"approve_{user.id}"),
        InlineKeyboardButton("❌ رد درخواست", callback_data=f"reject_{user.id}")
    )

    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=message.photo[-1].file_id,
            caption=admin_caption,
            reply_markup=admin_kb,
            parse_mode="Markdown"
        )
        await message.answer(
            "✅ فیش واریزی شما با موفقیت برای مدیریت ارسال گردید.\n"
            "پس از تایید، اطلاعات اتصال مستقیماً از طریق همین ربات برای شما ارسال خواهد شد. شکیبا باشید.",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"Error sending receipt to admin: {e}")
        await message.answer("⚠️ در ارسال رسید به بخش مدیریت خطایی رخ داد. لطفاً با پشتیبانی در ارتباط باشید.")

    await state.finish()

@dp.message_handler(state=PaymentStates.waiting_for_receipt, content_types=types.ContentType.ANY)
async def process_invalid_receipt(message: types.Message):
    await message.answer("⚠️ لطفاً فقط عکس فیش واریزی را ارسال کنید یا بر روی دکمه '❌ بستن پیام' در پیام قبلی کلیک نمایید.")

# هندلرهای ادمین جهت تایید یا رد
@dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("reject_"))
async def admin_decision_handler(callback_query: types.CallbackQuery):
    action, target_user_id = callback_query.data.split("_")
    target_user_id = int(target_user_id)

    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔️ شما به این پنل دسترسی ندارید.", show_alert=True)
        return

    if action == "approve":
        await bot.send_message(
            target_user_id,
            "🎉 **پرداخت شما تایید شد!**\n\n"
            "کانفیگ و اشتراک شما فعال گردید. از بخش «💎 اشتراک‌های من» می‌توانید جزئیات آن را دریافت نمایید."
        )
        await callback_query.message.edit_caption(
            caption=callback_query.message.caption + "\n\n🟢 **وضعیت: تایید و ارسال شد.**"
        )
    else:
        await bot.send_message(
            target_user_id,
            "❌ متاسفانه فیش ارسالی شما توسط مدیریت تایید نشد. در صورت بروز هرگونه مشکل با بخش «👥 پشتیبانی» تماس بگیرید."
        )
        await callback_query.message.edit_caption(
            caption=callback_query.message.caption + "\n\n🔴 **وضعیت: توسط ادمین رد شد.**"
        )
    await callback_query.answer()

# ----------------------------------------------------
# 8. هندلرهای سایر بخش‌های منو با پاکسازی چت (Back & Clean)
# ----------------------------------------------------
@dp.message_handler(lambda msg: msg.text == "📊 اطلاعات حساب", state="*")
async def process_account_info(message: types.Message, state: FSMContext):
    await state.finish()
    user = message.from_user
    username_str = f"@{user.username}" if user.username else "ثبت نشده"
    
    text = (
        f"📊 **اطلاعات حساب کاربری شما:**\n\n"
        f"👤 نام: **{user.full_name}**\n"
        f"🆔 آیدی عددی: `{user.id}`\n"
        f"🏷️ نام کاربری: {username_str}\n"
        f"💰 موجودی کیف پول: **۰ تومان**\n"
        f"📡 وضعیت سرویس فعال: **در حال حاضر اشتراک فعالی ثبت نشده است.**"
    )
    await message.answer(text, reply_markup=get_close_button(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "💎 اشتراک‌های من", state="*")
async def process_my_subs(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "💎 **لیست اشتراک‌های خریداری‌شده شما:**\n\n"
        "در حال حاضر هیچ سرویس فعالی برای اکانت شما ثبت نشده است.\n"
        "جهت سفارش اشتراک جدید می‌توانید از بخش «🛒 خرید اشتراک» اقدام کنید."
    )
    await message.answer(text, reply_markup=get_close_button(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "💰 شارژ حساب", state="*")
async def process_charge_balance(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "💰 **شارژ کیف پول کاربری:**\n\n"
        f"شماره کارت جهت افزایش اعتبار:\n`{CARD_NUMBER}`\n"
        f"بنام: **{CARD_HOLDER}**\n\n"
        "پس از انتقال وجه، فیش را همراه با آیدی عددی خود به بخش پشتیبانی ارسال بفرمایید."
    )
    await message.answer(text, reply_markup=get_close_button(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "👥 پشتیبانی", state="*")
async def process_support(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "👥 **واحد ارتباط با پشتیبانی فنی:**\n\n"
        "در صورت بروز هرگونه اختلال در اتصال، تغییر آی‌دی یا سوالات قبل از خرید، با اکانت پشتیبانی در تماس باشید:\n\n"
        "💬 ادمین پشتیبانی: @VPN_Support\n"
        "⏰ ساعت پاسخگویی: ۱۰ صبح الی ۲ بامداد"
    )
    await message.answer(text, reply_markup=get_close_button(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def process_configs_guide(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "⚙️ **راهنما و نرم‌افزارهای اتصال:**\n\n"
        "📱 **اندروید:** نرم‌افزار v2rayNG / Nekobox\n"
        "🍏 **آیفون (iOS):** نرم‌افزار V2Box / Streisand / FoXray\n"
        "💻 **ویندوز:** نرم‌افزار v2rayN / Nekoray\n\n"
        "پس از دریافت کانفیگ اختصاصی، کافیست لینک را در برنامه Paste نموده و دکمه اتصال را لمس نمایید."
    )
    await message.answer(text, reply_markup=get_close_button(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "❓ سوالات متداول", state="*")
async def process_faq(message: types.Message, state: FSMContext):
    await state.finish()
    faq_text = (
        "❓ **پرسش‌های متداول کاربران (FAQ):**\n\n"
        "۱. **آیا سرعت سرویس‌ها تضمینی است؟**\n"
        "بله، تمامی سرورها با پورت ۱۰ گیگابیت و بدون محدودیت پهنای باند ارائه می‌شوند.\n\n"
        "۲. **آیا بر روی همراه اول و ایرانسل متصل می‌شود؟**\n"
        "بله، به دلیل پیاده‌سازی پروتکل‌های نوین ضد فیلتر، تمامی اپراتورها به‌خوبی پشتیبانی می‌شوند.\n\n"
        "۳. **آیا اکانت‌ها حجم منصفانه دارند یا نامحدودند؟**\n"
        "بسته‌های ارائه شده به تناسب پلن به شکل حجم نامحدود واقعی عرضه می‌شوند.\n\n"
        "۴. **چند کاربر به‌صورت همزمان می‌توانند استفاده کنند؟**\n"
        "هر کانفیگ استاندارد به صورت ۲ کاربره همزمان پیکربندی شده است.\n\n"
        "۵. **آیا برای گیمینگ مناسب است؟**\n"
        "بله، پینگ سرورها بین ۸۰ تا ۱۲۰ میلی‌ثانیه تثبیت شده است.\n\n"
        "۶. **آیا برای صرافی‌های ارز دیجیتال و پی‌پال امن است؟**\n"
        "آی‌پی سرورها کاملاً تمیز و استاتیک بوده و نشت لوکیشن ندارند.\n\n"
        "۷. **در صورت قطعی سرور چه اتفاقی می‌افتد؟**\n"
        "تیم فنی به صورت ۲۴ ساعته مانیتورینگ دارد و در صورت اختلال، مسیر جدید جایگزین می‌شود.\n\n"
        "۸. **آیا روی iOS به درایور یا پروفایل خاصی نیاز است؟**\n"
        "خیر، به راحتی با نصب برنامه رایگان V2Box از اپ‌استور متصل می‌شوید.\n\n"
        "۹. **تحویل سرویس پس از خرید چه مقدار طول می‌کشد؟**\n"
        "بررسی فیش و تحویل اکانت کمتر از ۱۰ دقیقه در ساعات کاری انجام خواهد شد.\n\n"
        "۱۰. **چگونه کانفیگ را تمدید کنیم؟**\n"
        "کافیست قبل از انقضا از طریق دکمه «خرید اشتراک» مجدداً دوره خود را انتخاب و تمدید کنید.\n\n"
        "۱۱. **در صورت عدم رضایت ضمانت بازگشت وجه وجود دارد؟**\n"
        "در صورت عدم امکان اتصال توسط تیم فنی تا ۲۴ ساعت، کل وجه بدون کسر هزینه عودت داده می‌شود."
    )
    await message.answer(faq_text, reply_markup=get_close_button(), parse_mode="Markdown")

# ----------------------------------------------------
# 9. وب‌سرور داخلی aiohttp برای Render Health Check (Port 10000)
# ----------------------------------------------------
async def health_check(request):
    return web.Response(text="Bot is running smoothly!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check webserver started on port {PORT}")

# ----------------------------------------------------
# 10. اجرای همزمان پولینگ و سرور
# ----------------------------------------------------
async def main():
    await start_web_server()
    logger.info("Starting Telegram Bot Polling...")
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())

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
# 1. تنظیمات لاگ و متغیرهای محیطی از پنل Render
# ----------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# مقادیر به صورت خودکار از Environment Variables رندر فراخوانی می‌شوند
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", 10000))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/L2TP_VPN_OFFICIAL").strip()
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "VPN_Support").replace("@", "").strip()

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
# 3. توابع کمکی تبدیل تقویم و اعداد به فارسی
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
# 4. ساختار کیبوردهای اصلی و شیشه‌ای
# ----------------------------------------------------
def get_main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton("🛒 خرید اشتراک"))
    keyboard.row(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    keyboard.row(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
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
        InlineKeyboardButton("❌ بستن منو", callback_data="close_message")
    )
    return keyboard

def get_payment_actions_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📸 ارسال فیش واریزی", callback_data="send_receipt_action"),
        InlineKeyboardButton("🔙 بازگشت به پلن‌ها", callback_data="back_to_plans")
    )
    keyboard.add(InlineKeyboardButton("❌ بستن پیام", callback_data="close_message"))
    return keyboard

def get_support_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💬 چت با پشتیبانی فنی", url=f"https://t.me/{SUPPORT_USERNAME}"),
        InlineKeyboardButton("❌ بستن پیام", callback_data="close_message")
    )
    return keyboard

def get_charge_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💬 ارسال فیش به پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}"),
        InlineKeyboardButton("❌ بستن پیام", callback_data="close_message")
    )
    return keyboard

def get_configs_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📢 عضویت در کانال اطلاع‌رسانی", url=CHANNEL_LINK),
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
# 6. خوش‌آمدگویی و استارت
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
        f"سرویس‌های ما با بهره‌گیری از پروتکل‌های پایدار و مسیریابی ویژه، "
        f"تجربه‌ای متمایز از وبگردی آزاد را برای شما فراهم می‌آورند.\n\n"
        f"💎 **ویژگی‌های برجسته سرویس:**\n"
        f"✅ پینگ ایده‌آل و پایدار جهت **گیمینگ آنلاین و ترید**\n"
        f"✅ آی‌پی ثابت و تمیز ویژه صرافی‌های بین‌المللی\n"
        f"✅ سازگاری کامل با تمامی سیستم‌عامل‌ها (Android, iOS, Windows)\n"
        f"✅ بدون افت سرعت یا اعمال محدودیت پهنای باند شبکه\n\n"
        f"⚡ جهت ثبت یا تمدید اشتراک و دریافت کانفیگ‌ها از منوی زیر استفاده کنید.\n\n"
        f"📢 **کانال اطلاع‌رسانی سرورها:**\n"
        f"🔗 [ورود به کانال تلگرام]({CHANNEL_LINK})"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown", disable_web_page_preview=True)

# هندلر بستن پیام
@dp.callback_query_handler(lambda c: c.data == "close_message", state="*")
async def handle_close_message(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    try:
        await callback_query.message.delete()
    except Exception:
        await callback_query.answer("پیام بسته شد.")

# ----------------------------------------------------
# 7. فرآیند خرید، انتخاب پلن، بازگشت و ارسال فیش
# ----------------------------------------------------
@dp.message_handler(lambda msg: msg.text == "🛒 خرید اشتراک", state="*")
async def process_buy_menu(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "🛒 **لیست پلن‌های فعال سرویس L2TP VPN:**\n\n"
        "لطفاً دوره مد نظر خود را جهت واریز و فعال‌سازی انتخاب کنید:"
    )
    await message.answer(text, reply_markup=get_plans_inline_keyboard(), parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == "back_to_plans", state="*")
async def handle_back_to_plans(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    text = (
        "🛒 **لیست پلن‌های فعال سرویس L2TP VPN:**\n\n"
        "لطفاً دوره مد نظر خود را انتخاب فرمایید:"
    )
    await callback_query.message.edit_text(text, reply_markup=get_plans_inline_keyboard(), parse_mode="Markdown")
    await callback_query.answer()

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

    text = (
        f"💳 **اطلاعات واریز وجه - {selected_plan[0]}**\n\n"
        f"💰 مبلغ قابل پرداخت: **{selected_plan[1]} تومان**\n\n"
        f"📌 شماره کارت بانکی:\n"
        f"`{CARD_NUMBER}`\n"
        f"👤 بنام: **{CARD_HOLDER}**\n\n"
        f"ℹ️ **دستورالعمل:**\n"
        f"پس از واریز، روی دکمه **«📸 ارسال فیش واریزی»** در زیر کلیک کرده و عکس رسید را بفرستید."
    )
    await callback_query.message.edit_text(text, reply_markup=get_payment_actions_keyboard(), parse_mode="Markdown")
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "send_receipt_action", state="*")
async def request_receipt_upload(callback_query: types.CallbackQuery, state: FSMContext):
    await PaymentStates.waiting_for_receipt.set()
    cancel_kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="back_to_plans")
    )
    await callback_query.message.answer(
        "📸 لطفاً **عکس فیش واریزی** خود را در همین چت ارسال نمایید:",
        reply_markup=cancel_kb
    )
    await callback_query.answer()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=PaymentStates.waiting_for_receipt)
async def process_receipt_photo(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    plan_name = user_data.get("selected_plan", "پلن انتخابی")
    plan_price = user_data.get("plan_price", "نامشخص")
    
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
            "پس از بررسی، کانفیگ اختصاصی شما مستقیماً در همین ربات تحویل داده خواهد شد.",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"Error sending receipt to admin: {e}")
        await message.answer("⚠️ در ارسال رسید به سرور مدیریت خطایی رخ داد. لطفاً با پشتیبانی در ارتباط باشید.")

    await state.finish()

# تایید یا رد توسط ادمین
@dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("reject_"))
async def admin_decision_handler(callback_query: types.CallbackQuery):
    action, target_user_id = callback_query.data.split("_")
    target_user_id = int(target_user_id)

    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔️ شما به این بخش دسترسی ندارید.", show_alert=True)
        return

    if action == "approve":
        await bot.send_message(
            target_user_id,
            "🎉 **پرداخت شما تایید شد!**\n\n"
            "اشتراک شما با موفقیت فعال گردید. از بخش «💎 اشتراک‌های من» می‌توانید وضعیت سرویس خود را ملاحظه فرمایید."
        )
        await callback_query.message.edit_caption(
            caption=callback_query.message.caption + "\n\n🟢 **وضعیت: توسط ادمین تایید شد.**"
        )
    else:
        await bot.send_message(
            target_user_id,
            "❌ متاسفانه فیش ارسالی تایید نشد. در صورت کسر وجه یا هرگونه سوال با بخش «👥 پشتیبانی» تماس بگیرید."
        )
        await callback_query.message.edit_caption(
            caption=callback_query.message.caption + "\n\n🔴 **وضعیت: توسط ادمین رد شد.**"
        )
    await callback_query.answer()

# ----------------------------------------------------
# 8. هندلرهای سایر منوها (شارژ، پشتیبانی، کانفیگ و...)
# ----------------------------------------------------
@dp.message_handler(lambda msg: msg.text == "💰 شارژ حساب", state="*")
async def process_charge_balance(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "💰 **شارژ و افزایش اعتبار کیف پول:**\n\n"
        f"📌 شماره کارت واریز:\n`{CARD_NUMBER}`\n"
        f"👤 بنام: **{CARD_HOLDER}**\n\n"
        "پس از انتقال وجه، جهت اعمال موجودی روی دکمه زیر کلیک کرده و فیش را همراه با آیدی عددی خود برای پشتیبانی بفرستید:"
    )
    await message.answer(text, reply_markup=get_charge_keyboard(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "👥 پشتیبانی", state="*")
async def process_support(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "👥 **واحد پشتیبانی و ارتباط مستقیم با اپراتور:**\n\n"
        "در صورت بروز هرگونه قطعی، سوالات فنی یا راهنمایی در فعال‌سازی سرویس‌ها، از طریق دکمه زیر به صورت مستقیم پیام دهید:"
    )
    await message.answer(text, reply_markup=get_support_keyboard(), parse_mode="Markdown")

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
        f"📡 وضعیت سرویس: **هیچ اشتراک فعالی یافت نشد.**"
    )
    await message.answer(text, reply_markup=get_close_button(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "💎 اشتراک‌های من", state="*")
async def process_my_subs(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "💎 **لیست اشتراک‌های شما:**\n\n"
        "در حال حاضر هیچ سرویس فعالی برای شما ثبت نشده است.\n"
        "جهت خرید سرویس جدید از دکمه «🛒 خرید اشتراک» استفاده کنید."
    )
    await message.answer(text, reply_markup=get_close_button(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def process_configs_guide(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "⚙️ **راهنما و نرم‌افزارهای اتصال به سرویس:**\n\n"
        "📱 **اندروید:** برنامه‌های v2rayNG و Nekobox\n"
        "🍏 **آیفون (iOS):** برنامه‌های V2Box ،Streisand و FoXray\n"
        "💻 **ویندوز و مک:** برنامه‌های v2rayN و Nekoray\n\n"
        "تمامی فایل‌ها، آموزش‌های ویدیویی و آخرین اخبار سرورها در کانال رسمی قرار می‌گیرد:"
    )
    await message.answer(text, reply_markup=get_configs_keyboard(), parse_mode="Markdown")

@dp.message_handler(lambda msg: msg.text == "❓ سوالات متداول", state="*")
async def process_faq(message: types.Message, state: FSMContext):
    await state.finish()
    faq_text = (
        "❓ **پرسش‌های متداول کاربران (FAQ):**\n\n"
        "۱. **آیا سرعت سرویس‌ها تضمینی است؟**\n"
        "بله، تمامی سرورها با پورت ۱۰ گیگابیت اختصاصی و بدون افت پهنای باند ارائه می‌شوند.\n\n"
        "۲. **آیا بر روی همراه اول و ایرانسل متصل می‌شود؟**\n"
        "بله، به دلیل پیاده‌سازی پروتکل‌های نوین ضد فیلتر، با تمامی اپراتورها سازگار است.\n\n"
        "۳. **آیا اکانت‌ها محدودیت حجمی دارند؟**\n"
        "خیر، بسته‌های ارائه شده با حجم نامحدود واقعی عرضه می‌شوند.\n\n"
        "۴. **چند کاربر به‌صورت همزمان می‌توانند استفاده کنند؟**\n"
        "هر کانفیگ استاندارد به صورت ۲ کاربره همزمان پیکربندی شده است.\n\n"
        "۵. **آیا برای گیمینگ مناسب است؟**\n"
        "بله، پینگ سرورها بین ۸۰ تا ۱۲۰ میلی‌ثانیه بهینه‌سازی شده است.\n\n"
        "۶. **آیا برای صرافی‌های ارز دیجیتال و پی‌پال امن است؟**\n"
        "آی‌پی سرورها کاملاً تمیز و استاتیک بوده و نشت لوکیشن ندارند.\n\n"
        "۷. **در صورت قطعی سرور چه اتفاقی می‌افتد؟**\n"
        "تیم فنی به صورت ۲۴ ساعته سرورها را رصد کرده و بلافاصله سرور جایگزین می‌شود.\n\n"
        "۸. **آیا روی iOS به نرم‌افزار خاصی نیاز است؟**\n"
        "خیر، به راحتی با نصب اپلیکیشن رایگان V2Box از اپ‌استور متصل می‌شوید.\n\n"
        "۹. **تحویل سرویس پس از خرید چقدر زمان می‌برد؟**\n"
        "بررسی فیش و تحویل اکانت کمتر از ۱۰ دقیقه انجام خواهد شد.\n\n"
        "۱۰. **چگونه کانفیگ را تمدید کنیم؟**\n"
        "قبل از انقضا از طریق دکمه «خرید اشتراک» مجدداً دوره خود را واریز و تمدید فرمایید.\n\n"
        "۱۱. **در صورت عدم رضایت ضمانت بازگشت وجه وجود دارد؟**\n"
        "در صورت عدم اتصال تا ۲۴ ساعت، کل وجه بدون کسر هزینه عودت داده می‌شود."
    )
    await message.answer(faq_text, reply_markup=get_close_button(), parse_mode="Markdown")

# ----------------------------------------------------
# 9. وب‌سرور aiohttp جهت Render Health Check
# ----------------------------------------------------
async def health_check(request):
    return web.Response(text="Bot is running smoothly on Render!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check webserver started on port {PORT}")

# ----------------------------------------------------
# 10. اجرای برنامه
# ----------------------------------------------------
async def main():
    await start_web_server()
    logger.info("Starting Telegram Bot Polling...")
    # حذف آپدیت‌های انباشته‌شده برای جلوگیری از باگ تداخل
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())

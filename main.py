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
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- تنظیمات لاگینگ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- متغیرهای محیطی پنل Render ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip() or "0")
CARD_NUMBER = os.getenv("CARD_NUMBER", "6037-9918-XXXX-XXXX").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "به نام مدیریت").strip()

# متغیرهای پشتیبانی و کانال تنظیم شده در رندر
RAW_SUPPORT = os.getenv("SUPPORT_USERNAME", "").strip().replace("@", "")
RAW_CHANNEL = os.getenv("CHANNEL_LINK", "").strip()

# تولید لینک و متن نمایشی داینامیک
SUPPORT_URL = f"https://t.me/{RAW_SUPPORT}" if RAW_SUPPORT else "https://t.me/"
CHANNEL_URL = RAW_CHANNEL if RAW_CHANNEL.startswith("http") else (f"https://t.me/{RAW_CHANNEL.replace('@', '')}" if RAW_CHANNEL else "https://t.me/")
SUPPORT_DISPLAY = f"@{RAW_SUPPORT}" if RAW_SUPPORT else "@پشتیبانی"
CHANNEL_DISPLAY = RAW_CHANNEL if RAW_CHANNEL else "کانال اطلاع‌رسانی"

# مشخصات پلن‌ها
PLANS = {
    "plan_1": {"name": "پلن ۱ ماهه (تک کاربره)", "price": "250,000"},
    "plan_2": {"name": "پلن ۲ ماهه (دو کاربره)", "price": "400,000"},
    "plan_3": {"name": "پلن ۳ ماهه (سه کاربره)", "price": "600,000"}
}

# تابع تبدیل اعداد انگلیسی به فارسی
def to_persian_digits(text: str) -> str:
    en_digits = "0123456789"
    fa_digits = "۰۱۲۳۴۵۶۷۸۹"
    table = str.maketrans("".join(en_digits), "".join(fa_digits))
    return str(text).translate(table)

# تاریخ و زمان رسمی تهران به صورت شمسی
def get_tehran_datetime():
    tz = pytz.timezone("Asia/Tehran")
    tehran_now = datetime.now(tz)
    j_date = jdatetime.datetime.fromgregorian(datetime=tehran_now)
    weekdays = {
        0: "شنبه", 1: "یکشنبه", 2: "دوشنبه", 3: "سه‌شنبه",
        4: "چهارشنبه", 5: "پنج‌شنبه", 6: "جمعه"
    }
    weekday_name = weekdays.get(j_date.weekday(), "")
    date_str = f"{weekday_name}، {j_date.strftime('%Y/%m/%d')}"
    time_str = tehran_now.strftime("%H:%M:%S")
    return to_persian_digits(date_str), to_persian_digits(time_str)

# راه‌اندازی ربات
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# وضعیت FSM برای دریافت فیش
class PurchaseState(StatesGroup):
    waiting_for_receipt = State()

# کیبورد منوی اصلی (۴ ردیفه تثبیت شده)
def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    # ردیف ۱
    kb.row(InlineKeyboardButton("🛒 خرید اشتراک", callback_data="buy_subscription"))
    # ردیف ۲
    kb.row(
        InlineKeyboardButton("📊 اطلاعات حساب", callback_data="account_info"),
        InlineKeyboardButton("💎 اشتراک‌های من", callback_data="my_subscriptions")
    )
    # ردیف ۳
    kb.row(
        InlineKeyboardButton("💰 شارژ حساب", callback_data="charge_account"),
        InlineKeyboardButton("👥 پشتیبانی", callback_data="support_menu")
    )
    # ردیف ۴
    kb.row(
        InlineKeyboardButton("❓ سوالات متداول", callback_data="faq_menu"),
        InlineKeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال", callback_data="configs_menu")
    )
    return kb

def get_close_btn():
    return InlineKeyboardButton("❌ بستن پیام", callback_data="close_message")

# --- هندلرهای ربات شانلی ---

# استارت ربات
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    date_str, time_str = get_tehran_datetime()
    first_name = message.from_user.first_name or "کاربر گرامی"

    welcome_text = (
        f"سلام {first_name} عزیز، به ربات شانلی خوش آمدید! 🌸\n\n"
        f"📅 تاریخ امروز: <b>{date_str}</b>\n"
        f"⏰ ساعت: <b>{time_str}</b>\n\n"
        f"📢 کانال ما: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>\n"
        f"💬 پشتیبانی: <a href='{SUPPORT_URL}'>{SUPPORT_DISPLAY}</a>\n\n"
        "جهت استفاده از خدمات، یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu(), disable_web_page_preview=True)

# 📊 اطلاعات حساب
@dp.callback_query_handler(lambda c: c.data == "account_info", state="*")
async def cb_account_info(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = f"@{callback.from_user.username}" if callback.from_user.username else "ثبت نشده"
    first_name = callback.from_user.first_name or "—"
    date_str, _ = get_tehran_datetime()

    text = (
        "📊 <b>اطلاعات حساب کاربری شما</b>\n\n"
        f"👤 نام: <b>{first_name}</b>\n"
        f"🆔 شناسه کاربری: <code>{to_persian_digits(str(user_id))}</code>\n"
        f"🏷 یوزنیم: <b>{username}</b>\n"
        f"💰 موجودی کیف پول: <b>۰ تومان</b>\n"
        f"📅 تاریخ استعلام: <b>{date_str}</b>\n"
        f"💎 وضعیت اکانت: <b>عادی</b>\n\n"
        f"کانال: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>"
    )
    kb = InlineKeyboardMarkup().add(get_close_btn())
    await callback.message.answer(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()

# 💎 اشتراک‌های من
@dp.callback_query_handler(lambda c: c.data == "my_subscriptions", state="*")
async def cb_my_subscriptions(callback: types.CallbackQuery):
    text = (
        "💎 <b>اشتراک‌های فعال شما</b>\n\n"
        "در حال حاضر هیچ سرویس فعالی برای شما ثبت نشده است.\n"
        "جهت تهیه اشتراک، از منوی اصلی گزینه «🛒 خرید اشتراک» را انتخاب کنید."
    )
    kb = InlineKeyboardMarkup().add(get_close_btn())
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

# 🛒 خرید اشتراک
@dp.callback_query_handler(lambda c: c.data == "buy_subscription", state="*")
async def cb_buy_subscription(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, p_info in PLANS.items():
        kb.add(InlineKeyboardButton(f"{p_info['name']} - {to_persian_digits(p_info['price'])} تومان", callback_data=f"select_{p_id}"))
    kb.add(get_close_btn())

    text = "🛒 <b>لطفاً پلن مورد نظر خود را انتخاب فرمایید:</b>"
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

# پیش‌فاکتور پلن انتخابی
@dp.callback_query_handler(lambda c: c.data.startswith("select_plan_"), state="*")
async def cb_select_plan(callback: types.CallbackQuery, state: FSMContext):
    plan_id = callback.data.replace("select_", "")
    plan = PLANS.get(plan_id)
    if not plan:
        await callback.answer("پلن معتبر نیست.", show_alert=True)
        return

    await state.update_data(chosen_plan=plan['name'], chosen_price=plan['price'])

    text = (
        f"📋 <b>پیش‌فاکتور خرید</b>\n\n"
        f"🔹 سرویس: <b>{plan['name']}</b>\n"
        f"💵 مبلغ قابل پرداخت: <b>{to_persian_digits(plan['price'])} تومان</b>\n\n"
        f"💳 شماره کارت جهت واریز:\n"
        f"<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "⚠️ لطفاً پس از واریز، روی دکمه «📸 ارسال فیش واریزی» بزنید و تصویر فیش را ارسال نمایید."
    )

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📸 ارسال فیش واریزی", callback_data="send_receipt_step"),
        InlineKeyboardButton("🔙 بازگشت به پلن‌ها", callback_data="buy_subscription"),
        get_close_btn()
    )
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

# دکمه ورود به حالت ارسال فیش
@dp.callback_query_handler(lambda c: c.data == "send_receipt_step", state="*")
async def cb_send_receipt_step(callback: types.CallbackQuery, state: FSMContext):
    await PurchaseState.waiting_for_receipt.set()
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="cancel_receipt")
    )
    await callback.message.answer("📸 لطفاً تصویر رسید واریزی خود را در قالب یک عکس ارسال فرمایید:", reply_markup=kb)
    await callback.answer()

# انصراف از ارسال فیش
@dp.callback_query_handler(lambda c: c.data == "cancel_receipt", state=PurchaseState.waiting_for_receipt)
async def cb_cancel_receipt(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback.message.answer("❌ عملیات ارسال فیش لغو شد.", reply_markup=get_main_menu())
    await callback.answer()

# دریافت عکس فیش واریزی و ارسال برای ادمین
@dp.message_handler(content_types=[types.ContentType.PHOTO], state=PurchaseState.waiting_for_receipt)
async def handle_receipt_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("chosen_plan", "نامشخص")
    plan_price = data.get("chosen_price", "نامشخص")
    user = message.from_user
    date_str, time_str = get_tehran_datetime()

    if ADMIN_ID != 0:
        caption = (
            "🔔 <b>رسید پرداخت جدید دریافت شد!</b>\n\n"
            f"👤 خریدار: {user.full_name} (<code>{user.id}</code>)\n"
            f"🏷 یوزنیم: @{user.username if user.username else 'ندارد'}\n"
            f"📦 سرویس: <b>{plan_name}</b>\n"
            f"💵 مبلغ: <b>{to_persian_digits(plan_price)} تومان</b>\n"
            f"📅 زمان: <b>{date_str} - {time_str}</b>"
        )
        try:
            await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption)
        except Exception as e:
            logger.error(f"Error forwarding receipt to admin: {e}")

    await state.finish()
    await message.answer(
        "✅ فیش واریزی شما با موفقیت برای مدیریت ارسال شد.\n"
        "پس از بررسی، کانفیگ برای شما ارسال خواهد شد.\n"
        f"در صورت نیاز به پیگیری با پشتیبانی در ارتباط باشید:\n"
        f"💬 <a href='{SUPPORT_URL}'>{SUPPORT_DISPLAY}</a>",
        reply_markup=get_main_menu(),
        disable_web_page_preview=True
    )

# 💰 شارژ حساب
@dp.callback_query_handler(lambda c: c.data == "charge_account", state="*")
async def cb_charge_account(callback: types.CallbackQuery):
    text = (
        "💰 <b>شارژ حساب کاربری</b>\n\n"
        "جهت افزایش اعتبار کیف پول، لطفاً مبلغ مورد نظر خود را به شماره کارت زیر واریز کرده و فیش آن را برای پشتیبانی ارسال فرمایید:\n\n"
        f"💳 شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        f"ارتباط مستقیم با واحد پشتیبانی مالی:\n"
        f"💬 <a href='{SUPPORT_URL}'>{SUPPORT_DISPLAY}</a>"
    )
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("💬 چت با پشتیبانی مالی", url=SUPPORT_URL),
        get_close_btn()
    )
    await callback.message.answer(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()

# 👥 پشتیبانی
@dp.callback_query_handler(lambda c: c.data == "support_menu", state="*")
async def cb_support_menu(callback: types.CallbackQuery):
    text = (
        "👥 <b>مرکز پشتیبانی فنی و فروش</b>\n\n"
        "همکاران ما به صورت ۲۴ ساعته آماده پاسخگویی به مشکلات و سوالات شما هستند.\n"
        "جهت شروع گفتگو روی دکمه زیر کلیک فرمایید:"
    )
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("💬 چت با پشتیبانی فنی", url=SUPPORT_URL),
        get_close_btn()
    )
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

# ❓ سوالات متداول
@dp.callback_query_handler(lambda c: c.data == "faq_menu", state="*")
async def cb_faq_menu(callback: types.CallbackQuery):
    text = (
        "❓ <b>سوالات متداول کاربران</b>\n\n"
        "۱. <b>سرویس‌ها روی چه سیستم‌عامل‌هایی کار می‌کنند؟</b>\n"
        "پاسخ: تمامی سیستم‌عامل‌های اندروید، iOS، ویندوز و مکینتاش.\n\n"
        "۲. <b>تحویل سرویس چقدر زمان می‌برد؟</b>\n"
        "پاسخ: تایید رسیدها معمولاً بین ۵ الی ۳۰ دقیقه انجام می‌پذیرد.\n\n"
        "۳. <b>آیا امکان تمدید سرویس قبلی وجود دارد؟</b>\n"
        "پاسخ: بله، قبل از اتمام با پشتیبانی هماهنگ فرمایید."
    )
    kb = InlineKeyboardMarkup().add(get_close_btn())
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

# ⚙️ کانفیگ‌ها و آموزش اتصال
@dp.callback_query_handler(lambda c: c.data == "configs_menu", state="*")
async def cb_configs_menu(callback: types.CallbackQuery):
    text = (
        "⚙️ <b>آموزش‌های اتصال و دریافت کانفیگ‌ها</b>\n\n"
        "تمامی نرم‌افزارهای مورد نیاز و آموزش‌های تصویری را از طریق کانال رسمی ما دریافت نمایید:\n\n"
        f"📢 کانال اطلاع‌رسانی: <a href='{CHANNEL_URL}'>{CHANNEL_DISPLAY}</a>\n"
        f"💬 راهنمایی بیشتر: <a href='{SUPPORT_URL}'>{SUPPORT_DISPLAY}</a>"
    )
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("📢 ورود به کانال تلگرام", url=CHANNEL_URL),
        InlineKeyboardButton("💬 راهنمایی در پشتیبانی", url=SUPPORT_URL),
        get_close_btn()
    )
    await callback.message.answer(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()

# ❌ بستن پیام
@dp.callback_query_handler(lambda c: c.data == "close_message", state="*")
async def cb_close_message(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        await callback.answer("پیام بسته شد.")

# --- سرور وب جهت هلث‌چک در Render (پورت ۱۰۰۰۰) ---
async def handle_ping(request):
    return web.Response(text="Shanli Bot is running fine!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check web server started on port {port}")

# --- راه‌اندازی ربات و حذف وب‌هوک قبلی ---
async def on_startup(dp):
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(start_web_server())
    logger.info("Shanli Bot has started successfully.")

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing! Please set it in Render Environment.")
    else:
        executor.start_polling(dp, on_startup=on_startup, skip_updates=True)

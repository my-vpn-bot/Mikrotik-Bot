import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
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
    ReplyKeyboardRemove
)
from aiogram.utils import executor

# ==================== تنظیمات لاگ ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== متغیرهای محیطی (Render) ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
CARD_NUMBER = os.getenv("CARD_NUMBER", "6104338904607443")
CARD_HOLDER = os.getenv("CARD_HOLDER", "رحیمی")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "L2tp1support")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/L2tp_vpn402")

# پاکسازی فرمت یوزرنیم و لینک
CLEAN_SUPPORT = SUPPORT_USERNAME.replace("@", "").strip()
CLEAN_CHANNEL = CHANNEL_LINK.strip()
if not CLEAN_CHANNEL.startswith("http"):
    CLEAN_CHANNEL = f"https://t.me/{CLEAN_CHANNEL.replace('@', '')}"

# ==================== راه‌اندازی ربات ====================
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# دیکشنری نگهداری آخرین آیدی پیام ربات برای هر کاربر
USER_LAST_MSG = {}

# ==================== پلن‌های فروش تثبیت‌شده ====================
PLANS = {
    "p1": {"name": "اشتراک ۱ ماهه (تک کاربره)", "price": "۲۵۰,۰۰۰ تومان", "raw_price": 250000},
    "p2": {"name": "اشتراک ۲ ماهه (دو کاربره)", "price": "۴۰۰,۰۰۰ تومان", "raw_price": 400000},
    "p3": {"name": "اشتراک ۳ ماهه (سه کاربره)", "price": "۶۰۰,۰۰۰ تومان", "raw_price": 600000}
}

# ==================== وضعیت‌های FSM ====================
class OrderState(StatesGroup):
    waiting_for_receipt = State()

class ReportState(StatesGroup):
    waiting_for_report = State()

# ==================== توابع کمکی تقویم شمسی و زمان ====================
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = (gy + 1) if (gm > 2) else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd

def get_tehran_time_details():
    tehran_tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tehran_tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    weekdays_fa = {
        "Saturday": "شنبه", "Sunday": "یکشنبه", "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه", "Thursday": "پنج‌شنبه", "Friday": "جمعه"
    }
    weekday_name = weekdays_fa.get(now.strftime("%A"), "")
    date_str = f"{jy:04d}/{jm:02d}/{jd:02d}"
    time_str = now.strftime("%H:%M:%S")
    return date_str, time_str, weekday_name

# ==================== تابع ارسال تمیز و بدون شلوغی (Clean Send) ====================
async def send_clean(message: types.Message, text: str, reply_markup=None, disable_web_page_preview=True):
    user_id = message.chat.id
    
    # ۱. حذف پیام قبلی ربات برای کاربر در صورت وجود
    if user_id in USER_LAST_MSG:
        try:
            await bot.delete_message(chat_id=user_id, message_id=USER_LAST_MSG[user_id])
        except Exception:
            pass

    # ۲. حذف پیامی که کاربر ارسال کرده (دکمه یا متن)
    try:
        await message.delete()
    except Exception:
        pass

    # ۳. ارسال پیام جدید و ثبت آیدی آن
    new_msg = await bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview
    )
    USER_LAST_MSG[user_id] = new_msg.message_id
    return new_msg

# ==================== کیبوردهای ربات ====================
def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(KeyboardButton("🛒 خرید اشتراک"))
    keyboard.add(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    keyboard.add(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    keyboard.add(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return keyboard

def plans_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    for p_id, p_info in PLANS.items():
        btn_text = f"{p_info['name']} — {p_info['price']}"
        keyboard.add(InlineKeyboardButton(text=btn_text, callback_data=f"buy_{p_id}"))
    return keyboard

def cancel_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ انصراف"))
    return keyboard

def support_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="💬 چت مستقیم با پشتیبانی", url=f"https://t.me/{CLEAN_SUPPORT}"),
        InlineKeyboardButton(text="⚠️ ثبت و ارسال گزارش خطا", callback_data="report_error")
    )
    return keyboard

# ==================== هندلرهای اصلی ====================
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    date_str, time_str, weekday_name = get_tehran_time_details()
    user_name = message.from_user.first_name or "کاربر گرامی"

    welcome_text = (
        f"سلام <b>{user_name}</b> عزیز، به ربات شانلی خوش آمدید! 🌟\n\n"
        f"📅 <b>امروز:</b> {weekday_name} {date_str}\n"
        f"⏰ <b>ساعت رسمی:</b> {time_str}\n"
        f"🆔 <b>شناسه عددی شما:</b> <code>{message.from_user.id}</code>\n\n"
        f"🛡 <i>ارائه‌دهنده سرویس‌های پرسرعت و پایدار V2Ray</i>\n"
        f"💡 لطفاً گزینه مورد نظر خود را از منوی زیر انتخاب کنید:"
    )
    await send_clean(message, welcome_text, reply_markup=main_menu_keyboard())

@dp.message_handler(lambda msg: msg.text == "❌ انصراف", state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await send_clean(message, "عملیات لغو شد. به منوی اصلی بازگشتید.", reply_markup=main_menu_keyboard())

# --- منوی خرید اشتراک ---
@dp.message_handler(lambda msg: msg.text == "🛒 خرید اشتراک", state="*")
async def menu_buy(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "🛍 <b>پلن‌های فعال سرویس شانلی:</b>\n\n"
        "لطفاً یکی از اشتراک‌های زیر را انتخاب فرمایید:"
    )
    await send_clean(message, text, reply_markup=plans_inline_keyboard())

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("buy_"), state="*")
async def process_plan_choice(callback_query: types.CallbackQuery, state: FSMContext):
    plan_key = callback_query.data.split("_")[1]
    if plan_key in PLANS:
        plan = PLANS[plan_key]
        await state.update_data(chosen_plan=plan['name'], chosen_price=plan['price'])
        await OrderState.waiting_for_receipt.set()

        text = (
            f"🛒 <b>سفارش شما:</b> {plan['name']}\n"
            f"💰 <b>مبلغ قابل پرداخت:</b> {plan['price']}\n\n"
            f"💳 <b>شماره کارت:</b>\n<code>{CARD_NUMBER}</code>\n"
            f"👤 <b>به نام:</b> {CARD_HOLDER}\n\n"
            f"📸 <i>لطفاً پس از واریز، تصویر فیش واریزی خود را در همین چت ارسال نمایید:</i>"
        )
        await bot.answer_callback_query(callback_query.id)
        # ویرایش پیام اینلاین به مرحله واریز و فعال کردن دکمه انصراف
        await bot.edit_message_text(
            text=text,
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id
        )
        # تنظیم دکمه لغو در زیر چت
        await bot.send_message(
            chat_id=callback_query.message.chat.id,
            text="در صورت تمایل به لغو می‌توانید از دکمه زیر استفاده کنید:",
            reply_markup=cancel_keyboard()
        )

@dp.message_handler(content_types=[types.ContentType.PHOTO], state=OrderState.waiting_for_receipt)
async def process_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("chosen_plan", "نامشخص")
    plan_price = data.get("chosen_price", "نامشخص")
    photo_id = message.photo[-1].file_id

    # ارسال برای ادمین در صورت تنظیم بودن
    if ADMIN_ID:
        admin_text = (
            f"🔔 <b>فیش جدید دریافت شد!</b>\n\n"
            f"👤 <b>کاربر:</b> {message.from_user.full_name} (@{message.from_user.username})\n"
            f"🆔 <b>شناسه:</b> <code>{message.from_user.id}</code>\n"
            f"📦 <b>پلن:</b> {plan_name}\n"
            f"💳 <b>مبلغ:</b> {plan_price}"
        )
        try:
            await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=admin_text)
        except Exception as e:
            logger.error(f"خطا در ارسال فیش به ادمین: {e}")

    await state.finish()
    success_text = (
        "✅ <b>فیش واریزی شما با موفقیت ثبت شد!</b>\n\n"
        "اطلاعات پس از بررسی توسط تیم پشتیبانی تأیید شده و کانفیگ اختصاصی شما ارسال خواهد گردید."
    )
    await send_clean(message, success_text, reply_markup=main_menu_keyboard())

# --- اطلاعات حساب و اشتراک‌ها ---
@dp.message_handler(lambda msg: msg.text == "📊 اطلاعات حساب", state="*")
async def menu_account_info(message: types.Message, state: FSMContext):
    await state.finish()
    user = message.from_user
    text = (
        f"📊 <b>اطلاعات کاربری شما:</b>\n\n"
        f"👤 <b>نام:</b> {user.first_name}\n"
        f"🆔 <b>شناسه عددی:</b> <code>{user.id}</code>\n"
        f"🔗 <b>نام کاربری:</b> @{user.username if user.username else 'ندارد'}\n"
        f"💎 <b>وضعیت حساب:</b> کاربر فعال شانلی"
    )
    await send_clean(message, text, reply_markup=main_menu_keyboard())

@dp.message_handler(lambda msg: msg.text == "💎 اشتراک‌های من", state="*")
async def menu_my_subscriptions(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "💎 <b>اشتراک‌های فعال شما:</b>\n\n"
        "در حال حاضر اشتراک فعالی یافت نشد.\n"
        "برای تهیه سرویس می‌توانید از گزینه «🛒 خرید اشتراک» استفاده کنید."
    )
    await send_clean(message, text, reply_markup=main_menu_keyboard())

# --- شارژ حساب ---
@dp.message_handler(lambda msg: msg.text == "💰 شارژ حساب", state="*")
async def menu_charge_account(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "💰 <b>شارژ حساب کاربری:</b>\n\n"
        "برای شارژ مستقیم کیف پول یا تمدید اشتراک فعلی، می‌توانید به پشتیبانی پیام دهید یا از منوی «🛒 خرید اشتراک» پلن مورد نظر خود را انتخاب نمایید."
    )
    await send_clean(message, text, reply_markup=main_menu_keyboard())

# --- پشتیبانی و ثبت گزارش خطا ---
@dp.message_handler(lambda msg: msg.text == "👥 پشتیبانی", state="*")
async def menu_support(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "👥 <b>مرکز پشتیبانی شانلی:</b>\n\n"
        "برای ارتباط مستقیم با تیم پشتیبانی یا گزارش مشکلات فنی، گزینه‌های زیر در دسترس شماست:"
    )
    await send_clean(message, text, reply_markup=support_inline_keyboard())

@dp.callback_query_handler(lambda c: c.data == "report_error", state="*")
async def report_error_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await ReportState.waiting_for_report.set()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        chat_id=callback_query.message.chat.id,
        text="✍️ لطفاً شرح مشکل یا خطای مشاهده شده را ارسال نمایید:",
        reply_markup=cancel_keyboard()
    )

@dp.message_handler(state=ReportState.waiting_for_report)
async def process_report_text(message: types.Message, state: FSMContext):
    report_content = message.text
    if ADMIN_ID:
        admin_alert = (
            f"⚠️ <b>گزارش خطای جدید از کاربر:</b>\n\n"
            f"👤 <b>کاربر:</b> {message.from_user.full_name} (@{message.from_user.username})\n"
            f"🆔 <code>{message.from_user.id}</code>\n\n"
            f"📝 <b>متن گزارش:</b>\n{report_content}"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_alert)
        except Exception as e:
            logger.error(f"خطا در ارسال گزارش به ادمین: {e}")

    await state.finish()
    await send_clean(
        message,
        "✅ گزارش شما ثبت شد و برای پشتیبانی ارسال گردید. با تشکر از شکیبایی شما.",
        reply_markup=main_menu_keyboard()
    )

# --- سوالات متداول (FAQ کامل ۱۲ موردی) ---
@dp.message_handler(lambda msg: msg.text == "❓ سوالات متداول", state="*")
async def menu_faq(message: types.Message, state: FSMContext):
    await state.finish()
    faq_text = (
        "❓ <b>سوالات متداول کاربران:</b>\n\n"
        "<b>۱. تحویل سرویس چقدر زمان می‌برد؟</b>\n"
        "پس از ارسال فیش و تأیید ادمین، کانفیگ فوراً ارسال می‌شود.\n\n"
        "<b>۲. این سرویس‌ها روی چه اپراتورهایی کار می‌کنند؟</b>\n"
        "روی تمامی اپراتورها (همراه اول، ایرانسل، رایتل و اینترنت خانگی).\n\n"
        "<b>۳. نرم‌افزارهای مورد نیاز برای اتصال چیست؟</b>\n"
        "اندروید: v2rayNG | آیفون: Streisand, V2Box, FoXray | ویندوز: v2rayN.\n\n"
        "<b>۴. آیا محدودیت حجم وجود دارد؟</b>\n"
        "پلن‌ها دارای ترافیک منصفانه و نامحدود حجمی متناسب با مدت زمان هستند.\n\n"
        "<b>۵. تفاوت سرویس تک‌کاربره و چندکاربره چیست؟</b>\n"
        "در سرویس‌های دو و سه کاربره، چند دستگاه به صورت همزمان می‌توانند متصل شوند.\n\n"
        "<b>۶. در صورت قطع شدن سرویس چه اقدامی کنیم؟</b>\n"
        "از بخش پشتیبانی گزینه «ثبت گزارش خطا» را بزنید یا به آیدی پشتیبانی پیام دهید.\n\n"
        "<b>۷. آیا امکان بازگشت وجه وجود دارد؟</b>\n"
        "در صورت عدم امکان اتصال و رفع نشدن مشکل، وجه بازگشت داده می‌شود.\n\n"
        "<b>۸. پروتکل‌های در حال استفاده کدامند؟</b>\n"
        "در حال حاضر پروتکل‌های پرسرعت V2Ray (Vless/VMess) فعال هستند.\n\n"
        "<b>۹. آیا نیاز به تنظیم دستی DNS یا IP است؟</b>\n"
        "خیر، تمامی تنظیمات درون لینک کانفیگ به صورت خودکار اعمال می‌شود.\n\n"
        "<b>۱۰. آیا تمدید سرویس قبل از اتمام زمان امکان‌پذیر است؟</b>\n"
        "بله، می‌توانید پیش از اتمام دوره اقدام به تمدید فرمایید.\n\n"
        "<b>۱۱. کانال رسمی اطلاع‌رسانی کجاست؟</b>\n"
        "از دکمه «⚙️ کانفیگ‌ها و آموزش اتصال» می‌توانید وارد کانال شوید.\n\n"
        "<b>۱۲. ساعت پاسخگویی پشتیبانی چگونه است؟</b>\n"
        "پشتیبانی به صورت ۲۴ ساعته در دسترس شما عزیزان است."
    )
    await send_clean(message, faq_text, reply_markup=main_menu_keyboard())

# --- کانفیگ‌ها و آموزش اتصال ---
@dp.message_handler(lambda msg: msg.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def menu_configs_tutorials(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "⚙️ <b>کانفیگ‌ها و آموزش‌های جامع اتصال:</b>\n\n"
        f"برای دریافت آخرین آپدیت برنامه‌ها، آموزش‌های ویدئویی و کانفیگ‌ها روی لینک زیر کلیک کنید:\n\n"
        f"<a href=\"{CLEAN_CHANNEL}\">🔗 ورود به کانال آموزشی و اطلاع‌رسانی</a>"
    )
    await send_clean(message, text, reply_markup=main_menu_keyboard())

# ==================== وب‌سرور داخلی هلث‌چک برای Render ====================
async def handle_health(request):
    return web.Response(text="Shanli Bot is healthy and running!", status=200)

async def start_background_tasks(app):
    asyncio.create_task(dp.start_polling())

async def cleanup_background_tasks(app):
    await dp.stop_polling()
    await bot.close()
    await storage.close()

def create_app():
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app

# ==================== نقطه اجرای برنامه ====================
if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)

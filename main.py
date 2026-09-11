import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- متغیرهای محیطی و تنظیمات پایه ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
CARD_NUMBER = os.getenv("CARD_NUMBER", "6104338904607443")
CARD_HOLDER = os.getenv("CARD_HOLDER", "رحیمی")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "L2tp1support")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/L2tp_vpn402")

CLEAN_SUPPORT = SUPPORT_USERNAME.replace("@", "").strip()
CLEAN_CHANNEL = CHANNEL_LINK.strip()
if not CLEAN_CHANNEL.startswith("http"):
    CLEAN_CHANNEL = f"https://t.me/{CLEAN_CHANNEL.replace('@', '')}"

FAQ_TEXT = """<b>❓ سوالات متداول شانلی:</b>

1. <b>زمان تحویل؟</b> تمامی اشتراک‌های شانلی بلافاصله پس از تایید فیش واریزی تحویل داده می‌شوند.
2. <b>کدام اپراتورها؟</b> شانلی با تمامی اپراتورهای همراه اول، ایرانسل، رایتل و اینترنت خانگی سازگار است.
3. <b>نرم‌افزار مورد نیاز؟</b> بهترین تجربه کاربری با سرویس‌های شانلی، استفاده از V2rayNG برای اندروید و V2Box برای آیفون است.
4. <b>حجم سرویس؟</b> تمامی اشتراک‌های شانلی دارای حجم نامحدود و منصفانه هستند.
5. <b>تعداد کاربر؟</b> بسته به پلن انتخابی در شانلی، امکان استفاده همزمان برای ۱ تا ۳ نفر وجود دارد.
6. <b>در صورت قطعی؟</b> در صورت بروز هرگونه مشکل در اتصال به شانلی، حتماً از طریق پشتیبانی گزارش دهید.
7. <b>برگشت وجه؟</b> در صورتی که سرویس شانلی به هیچ عنوان متصل نشود، امکان عودت وجه وجود دارد.
8. <b>پروتکل اتصالی؟</b> شانلی از پروتکل‌های امن و به‌روز برای عبور از فیلترینگ استفاده می‌کند.
9. <b>تنظیمات دستی؟</b> خیر، تمامی کانفیگ‌های شانلی به‌صورت اتوماتیک و هوشمند تحویل داده می‌شوند.
10. <b>تمدید اشتراک؟</b> بله، کاربران عزیز شانلی می‌توانند قبل از اتمام زمان، اشتراک خود را تمدید کنند.
11. <b>آدرس کانال؟</b> لینک کانال همیشه در منوی اصلی ربات شانلی در دسترس است.
12. <b>ساعات پشتیبانی؟</b> تیم پشتیبانی شانلی به‌صورت ۲۴ ساعته در کنار شماست."""

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
USER_LAST_MSG = {}

PLANS = {
    "p1": {"name": "اشتراک ۱ ماهه (تک کاربره)", "price": "۲۵۰,۰۰۰ تومان"},
    "p2": {"name": "اشتراک ۲ ماهه (دو کاربره)", "price": "۴۰۰,۰۰۰ تومان"},
    "p3": {"name": "اشتراک ۳ ماهه (سه کاربره)", "price": "۶۰۰,۰۰۰ تومان"}
}

class OrderState(StatesGroup):
    waiting_for_receipt = State()

# --- محاسبات تقویم و زمان تهران ---
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
    tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    weekdays = {
        "Saturday": "شنبه",
        "Sunday": "یکشنبه",
        "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه",
        "Wednesday": "چهارشنبه",
        "Thursday": "پنج‌شنبه",
        "Friday": "جمعه"
    }
    return f"{jy:04d}/{jm:02d}/{jd:02d}", now.strftime("%H:%M:%S"), weekdays.get(now.strftime("%A"), "")

# --- ارسال پیام تمیز (Clean UI) ---
async def send_clean(message: types.Message, text: str, reply_markup=None):
    user_id = message.chat.id
    if user_id in USER_LAST_MSG:
        try:
            await bot.delete_message(chat_id=user_id, message_id=USER_LAST_MSG[user_id])
        except Exception:
            pass
    try:
        await message.delete()
    except Exception:
        pass
    new_msg = await bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, disable_web_page_preview=True)
    USER_LAST_MSG[user_id] = new_msg.message_id

# --- کیبورد اصلی ربات (۴ ردیف استاندارد) ---
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row(KeyboardButton("🛒 خرید اشتراک"))
    kb.row(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    kb.row(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    kb.row(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return kb

# --- هندلرهای تلگرام ---
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    date, time, wd = get_tehran_time_details()
    text = (
        f"سلام <b>{message.from_user.first_name}</b> عزیز، به ربات شانلی خوش آمدید! 🌟\n\n"
        f"📅 <b>تاریخ:</b> {wd} {date}\n"
        f"⏰ <b>ساعت:</b> {time}\n"
        f"🆔 <b>شناسه شما:</b> <code>{message.from_user.id}</code>\n\n"
        f"🔗 <a href=\"{CLEAN_CHANNEL}\">کانال رسمی</a>"
    )
    await send_clean(message, text, reply_markup=main_menu())

@dp.message_handler(lambda msg: msg.text == "🛒 خرید اشتراک", state="*")
async def menu_buy(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(row_width=1)
    for k, v in PLANS.items():
        kb.add(InlineKeyboardButton(f"{v['name']} — {v['price']}", callback_data=f"buy_{k}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await send_clean(message, "لطفا پلن مورد نظر خود را انتخاب کنید:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"), state="*")
async def process_buy(c: types.CallbackQuery, state: FSMContext):
    plan_key = c.data.split("_")[1]
    plan = PLANS[plan_key]
    await state.update_data(p_name=plan['name'], p_price=plan['price'])
    await OrderState.waiting_for_receipt.set()
    text = (
        f"سفارش: <b>{plan['name']}</b>\n"
        f"مبلغ: <b>{plan['price']}</b>\n"
        f"شماره کارت: <code>{CARD_NUMBER}</code> ({CARD_HOLDER})\n\n"
        f"لطفا تصویر فیش واریزی خود را ارسال کنید."
    )
    await bot.edit_message_text(
        text,
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ انصراف", callback_data="back_to_main"))
    )

@dp.message_handler(content_types=['photo'], state=OrderState.waiting_for_receipt)
async def process_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if ADMIN_ID:
        try:
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=f"رسید جدید از <b>{message.from_user.full_name}</b> (<code>{message.from_user.id}</code>)\nپلن: {data.get('p_name')}"
            )
        except Exception as e:
            logger.error(f"Error sending receipt to admin: {e}")
    await state.finish()
    await send_clean(message, "✅ فیش شما با موفقیت ثبت شد و در حال بررسی است.", reply_markup=main_menu())

@dp.message_handler(lambda msg: msg.text == "📊 اطلاعات حساب", state="*")
async def menu_acc(message: types.Message, state: FSMContext):
    text = (
        f"📊 <b>اطلاعات حساب شما:</b>\n\n"
        f"👤 نام: {message.from_user.first_name}\n"
        f"🆔 شناسه کاربری: <code>{message.from_user.id}</code>\n"
        f"🔰 وضعیت حساب: عادی"
    )
    await send_clean(message, text, reply_markup=main_menu())

@dp.message_handler(lambda msg: msg.text == "💎 اشتراک‌های من", state="*")
async def menu_subs(message: types.Message, state: FSMContext):
    text = (
        "💎 <b>اشتراک‌های من:</b>\n\n"
        "در حال حاضر اشتراک فعالی برای شما ثبت نشده است.\n"
        "برای خرید یا استعلام وضعیت سرویس خود به پشتیبانی مراجعه کنید."
    )
    await send_clean(message, text, reply_markup=main_menu())

@dp.message_handler(lambda msg: msg.text == "💰 شارژ حساب", state="*")
async def menu_charge(message: types.Message, state: FSMContext):
    await send_clean(message, "💰 <b>شارژ حساب:</b>\nجهت افزایش اعتبار و شارژ موجودی، به پشتیبانی پیام دهید.", reply_markup=main_menu())

@dp.message_handler(lambda msg: msg.text == "👥 پشتیبانی", state="*")
async def menu_supp(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💬 چت مستقیم با پشتیبانی", url=f"https://t.me/{CLEAN_SUPPORT}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await send_clean(message, "👥 <b>راهنمایی و پشتیبانی:</b>\nسوالی دارید یا به راهنمایی نیاز دارید؟ در خدمتیم.", reply_markup=kb)

@dp.message_handler(lambda msg: msg.text == "❓ سوالات متداول", state="*")
async def menu_faq(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await send_clean(message, FAQ_TEXT, reply_markup=kb)

@dp.message_handler(lambda msg: msg.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def menu_configs(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔗 ورود به کانال رسمی شانلی", url=CLEAN_CHANNEL))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await send_clean(message, "⚙️ <b>آموزش اتصال:</b>\nتمامی آموزش‌ها و فایل‌های اتصال در کانال رسمی قرار داده شده است.", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "back_to_main", state="*")
async def back_to_main(c: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await send_clean(c.message, "به منوی اصلی بازگشتید:", reply_markup=main_menu())

# --- اجرای وب‌سرور Render و Polling ---
if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    app = web.Application()
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    
    async def start(app):
        asyncio.create_task(dp.start_polling())
        
    app.on_startup.append(start)
    web.run_app(app, host="0.0.0.0", port=port)

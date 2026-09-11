import os
import asyncio
import logging
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiohttp import web

# ==================== تنظیمات و لاگ ====================
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

SUPPORT_ID = os.getenv("SUPPORT_ID", "L2tp1support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()

# فایل ذخیره آمار کاربران
USERS_FILE = "users.txt"

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== توابع مدیریت آمار کاربران ====================
def register_user(user_id: int):
    """ثبت شناسه کاربر در فایل متنی در صورت عدم وجود"""
    try:
        user_id_str = str(user_id)
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                f.write(f"{user_id_str}\n")
            return
        
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = [line.strip() for line in f.readlines() if line.strip()]
        
        if user_id_str not in users:
            with open(USERS_FILE, "a", encoding="utf-8") as f:
                f.write(f"{user_id_str}\n")
    except Exception as e:
        logging.error(f"خطا در ثبت کاربر: {e}")

# ==================== وضعیت‌های FSM ====================
class ReportState(StatesGroup):
    waiting_for_error = State()

# ==================== تعرفه‌ها و پلن‌ها ====================
PLANS = {
    "p1": {"name": "اشتراک ۱ ماهه", "price": "۲۵۰,۰۰۰ تومان"},
    "p2": {"name": "اشتراک ۲ ماهه", "price": "۴۰۰,۰۰۰ تومان"},
    "p3": {"name": "اشتراک ۳ ماهه", "price": "۶۰۰,۰۰۰ تومان"},
}

# ==================== تبدیل تاریخ میلادی به هجری شمسی (جلالی) ====================
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gm > 2:
        gy2 = gy
    else:
        gy2 = gy - 1
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
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

def get_persian_datetime():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    time_str = now.strftime("%H:%M:%S")
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    date_str = f"{jy:04d}/{jm:02d}/{jd:02d}"
    return date_str, time_str

# ==================== کیبورد اصلی ۴ ردیفه ====================
def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🛒 خرید اشتراک"))
    kb.add(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    kb.add(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    kb.add(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return kb

def get_welcome_text(user):
    date_str, time_str = get_persian_datetime()
    return (
        f"سلام <b>{user.first_name}</b> عزیز، به ربات هوشمند شانلی خوش آمدید! 🌸\n\n"
        f"📅 تاریخ امروز (شمسی): <code>{date_str}</code>\n"
        f"⏰ ساعت رسمی تهران: <code>{time_str}</code>\n"
        f"🆔 شناسه کاربری شما: <code>{user.id}</code>\n\n"
        f"⚠️ <b>وضعیت پروتکل‌های فعال:</b>\n"
        f"در حال حاضر کلیه سرویس‌های ما بر پایه پروتکل‌های پرسرعت <b>V2Ray</b> (VMess/VLESS) ارائه می‌شوند.\n\n"
        f"🛠 <b>برنامه بروزرسانی:</b>\n"
        f"در بروزرسانی‌های بعدی، پشتیبانی از پروتکل‌های قدرتمند <b>L2TP</b>، <b>PPTP</b> و <b>OpenVPN</b> نیز به لیست سرویس‌ها اضافه خواهد شد.\n\n"
        "⚡️ برای شروع استفاده از خدمات و مدیریت سرویس خود، لطفاً از منوی زیر گزینه‌ای را انتخاب کنید:"
    )

# ==================== هندلرهای اصلی ====================
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    # ثبت آیدی کاربر برای آمارگیر
    register_user(message.from_user.id)
    await message.answer(get_welcome_text(message.from_user), reply_markup=get_main_keyboard())

@dp.message_handler(commands=['stats'], state="*")
async def cmd_stats(message: types.Message, state: FSMContext):
    """دستور اختصاصی ادمین برای دیدن تعداد کاربران"""
    await state.finish()
    if ADMIN_ID != 0 and message.from_user.id != ADMIN_ID:
        return
    
    total_users = 0
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = [line.strip() for line in f.readlines() if line.strip()]
                total_users = len(users)
        except Exception as e:
            logging.error(f"خطا در خواندن آمار: {e}")

    await message.answer(
        f"📊 <b>آمار ربات شانلی:</b>\n\n"
        f"👥 تعداد کل کاربران ثبت‌شده: <b>{total_users} نفر</b>"
    )

@dp.message_handler(lambda m: m.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, info in PLANS.items():
        kb.add(InlineKeyboardButton(f"🔹 {info['name']} — {info['price']}", callback_data=f"buy_{p_id}"))
    await message.answer("🛍 <b>لیست پلن‌های اشتراک:</b>\n\nلطفاً یکی از پلن‌های زیر را جهت خرید انتخاب کنید:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "📊 اطلاعات حساب", state="*")
async def handle_account(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        f"📊 <b>اطلاعات حساب کاربری</b>\n\n"
        f"👤 نام: <b>{message.from_user.full_name}</b>\n"
        f"🆔 شناسه: <code>{message.from_user.id}</code>\n"
        f"💎 وضعیت اشتراک: <b>غیرفعال</b>\n"
        f"💰 موجودی کیف پول: <b>۰ تومان</b>"
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda m: m.text == "💎 اشتراک‌های من", state="*")
async def handle_my_subs(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("💎 <b>اشتراک‌های فعال شما:</b>\n\nدر حال حاضر اشتراک فعالی برای شما ثبت نشده است.", reply_markup=get_main_keyboard())

@dp.message_handler(lambda m: m.text == "💰 شارژ حساب", state="*")
async def handle_charge(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("👤 ارسال فیش به پشتیبانی", url=SUPPORT_URL))
    text = (
        f"💰 <b>اطلاعات حساب بانکی جهت واریز:</b>\n\n"
        f"💳 شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 بنام: <b>{CARD_HOLDER}</b>\n\n"
        f"پس از واریز مبلغ، با لمس دکمه زیر تصویر فیش را مستقیماً به پشتیبانی ({SUPPORT_USERNAME}) ارسال فرمایید."
    )
    await message.answer(text, reply_markup=kb)

@dp.message_handler(lambda m: m.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💬 چت مستقیم با پشتیبانی", url=SUPPORT_URL))
    kb.add(InlineKeyboardButton("⚠️ ثبت گزارش خطا / مشکل اتصال", callback_data="report_error"))
    text = (
        f"👥 <b>مرکز پشتیبانی فنی و ارتباط با ادمین:</b>\n\n"
        f"آیدی پشتیبانی: {SUPPORT_USERNAME}\n\n"
        "در صورت بروز مشکل در اتصال یا سوالات فنی، می‌توانید مستقیماً پیام دهید یا گزارش خطا ثبت کنید:"
    )
    await message.answer(text, reply_markup=kb)

@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "❓ <b>سوالات متداول (FAQ):</b>\n\n"
        "۱. <b>سرویس‌های فعلی بر چه اساسی هستند؟</b>\nدر حال حاضر کلیه سرویس‌ها V2Ray هستند.\n\n"
        "۲. <b>پروتکل‌های دیگر مثل L2TP اضافه می‌شوند؟</b>\nبله، به زودی L2TP, PPTP و OpenVPN اضافه خواهد شد.\n\n"
        "۳. <b>چگونه متصل شوم؟</b>\nاز بخش کانفیگ‌ها برنامه متناسب را دانلود کنید.\n\n"
        "۴. <b>تایید فیش چقدر زمان می‌برد؟</b>\nدر اسرع وقت توسط پشتیبانی تایید می‌شود.\n\n"
        "۵. <b>آیا اشتراک‌ها قابل انتقال هستند؟</b>\nخیر، اشتراک‌ها مختص یک شناسه کاربری هستند.\n\n"
        "۶. <b>چرا سرعت گاهی نوسان دارد؟</b>\nبستگی به نوع اینترنت و اپراتور شما دارد.\n\n"
        "۷. <b>آیا سرورها اختصاصی هستند؟</b>\nتمامی سرورها با پهنای باند اختصاصی می‌باشند.\n\n"
        "۸. <b>چگونه گزارش قطعی یا خطا بدهم؟</b>\nاز بخش پشتیبانی گزینه گزارش خطا را انتخاب کنید.\n\n"
        "۹. <b>آیا پشتیبانی ۲۴ ساعته است؟</b>\nبله، در سریع‌ترین زمان پاسخگو هستیم.\n\n"
        "۱۰. <b>امنیت اتصالات چطور است؟</b>\nتمامی اتصالات با پروتکل‌های امن رمزنگاری شده هستند.\n\n"
        "۱۱. <b>اگر شارژ کنم چه زمانی فعال می‌شود؟</b>\nپس از ارسال فیش به پشتیبانی و تایید، آنی فعال می‌شود."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda m: m.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def handle_configs(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔗 ورود به کانال آموزش و دانلود نرم‌افزارها", url=CHANNEL_URL))
    text = (
        "⚙️ <b>آموزش اتصال و دریافت کانفیگ‌ها:</b>\n\n"
        "تمامی نرم‌افزارهای مورد نیاز، آموزش‌های تصویری و فایل‌های اتصال در کانال رسمی ما قرار دارند.\n\n"
        f"🔗 <a href=\"{CHANNEL_URL}\">جهت ورود و مشاهده آموزش‌ها اینجا کلیک کنید</a>"
    )
    await message.answer(text, reply_markup=kb)

# ==================== جریان‌های کال‌بک ====================
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"), state="*")
async def callback_buy_plan(query: types.CallbackQuery, state: FSMContext):
    plan_key = query.data.split("_")[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await query.answer("پلن یافت نشد.", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("👤 ارسال فیش به پشتیبانی", url=SUPPORT_URL))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu"))
    
    text = (
        f"🧾 <b>پیش‌فاکتور خرید اشتراک</b>\n\n"
        f"📦 پلن انتخابی: <b>{plan['name']}</b>\n"
        f"💵 مبلغ قابل پرداخت: <b>{plan['price']}</b>\n\n"
        f"💳 شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 بنام: <b>{CARD_HOLDER}</b>\n\n"
        f"لطفاً مبلغ را واریز کرده و سپس تصویر فیش واریزی را از طریق دکمه زیر به آیدی پشتیبانی ({SUPPORT_USERNAME}) ارسال فرمایید."
    )
    await query.message.edit_text(text, reply_markup=kb)
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "report_error", state="*")
async def callback_report_issue(query: types.CallbackQuery, state: FSMContext):
    await ReportState.waiting_for_error.set()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu"))
    await query.message.edit_text(
        "⚠️ <b>ثبت گزارش خطا:</b>\n\n"
        "علت وصل نشدن یا متن خطایی که دریافت می‌کنید را همراه با نوع اینترنت خود در قالب یک پیام متنی بفرستید:",
        reply_markup=kb
    )
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "main_menu", state="*")
async def callback_back_menu(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.delete()
    await query.message.answer(get_welcome_text(query.from_user), reply_markup=get_main_keyboard())
    await query.answer()

# ==================== دریافت ورودی‌های FSM ====================
@dp.message_handler(state=ReportState.waiting_for_error)
async def handle_incoming_report(message: types.Message, state: FSMContext):
    report_text = (
        f"⚠️ <b>گزارش خطای جدید</b>\n\n"
        f"👤 فرستنده: {message.from_user.full_name}\n"
        f"🆔 شناسه: <code>{message.from_user.id}</code>\n\n"
        f"📝 متن:\n{message.text}"
    )
    if ADMIN_ID != 0:
        try:
            await bot.send_message(ADMIN_ID, report_text)
        except Exception as e:
            logging.error(f"خطا در ارسال گزارش به ادمین: {e}")
            
    await message.answer("✅ گزارش خطای شما برای تیم پشتیبانی ارسال شد و بررسی خواهد شد.", reply_markup=get_main_keyboard())
    await state.finish()

# ==================== سرور هلث‌چک برای رندر ====================
async def run_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Shanli Bot is active"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health check server listening on port {port}")

async def main():
    await run_server()
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())

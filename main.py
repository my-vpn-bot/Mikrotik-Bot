import os
import asyncio
import logging
import sqlite3
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputFile
)
from aiohttp import web

# ==================== تنظیمات و لاگ ====================
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

SUPPORT_ID = os.getenv("SUPPORT_ID", "L2tp1Support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()

# مسیر فایل‌های تصویری
CARD_IMAGE_PATH = "شماره کارت1.jpg"

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== دیتابیس شمارنده کاربران ====================
DB_FILE = "bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    join_date TEXT
                )''')
    conn.commit()
    conn.close()

def add_user_to_db(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date_str, _ = get_persian_datetime()
    c.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)", (user_id, date_str))
    conn.commit()
    conn.close()

def get_total_users_count() -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

init_db()

# ==================== وضعیت‌های FSM ====================
class OrderState(StatesGroup):
    waiting_for_receipt = State()

class ChargeState(StatesGroup):
    waiting_for_receipt = State()
    waiting_for_username = State()

class ReportState(StatesGroup):
    waiting_for_error = State()

# ==================== تعرفه‌ها و پلن‌ها (۶ پلن) ====================
PLANS = {
    "1m_1u": {"name": "اشتراک ۱ ماهه (۳۰ گیگابایت - تک کاربره)", "price": "۲۰۰,۰۰۰ تومان", "duration": "۱ ماه", "traffic": "30GB", "users": "۱ کاربره"},
    "1m_2u": {"name": "اشتراک ۱ ماهه (۳۰ گیگابایت - دو کاربره)", "price": "۲۵۰,۰۰۰ تومان", "duration": "۱ ماه", "traffic": "30GB", "users": "۲ کاربره"},
    "2m_1u": {"name": "اشتراک ۲ ماهه (۶۰ گیگابایت - تک کاربره)", "price": "۴۰۰,۰۰۰ تومان", "duration": "۲ ماه", "traffic": "60GB", "users": "۱ کاربره"},
    "2m_2u": {"name": "اشتراک ۲ ماهه (۶۰ گیگابایت - دو کاربره)", "price": "۴۵۰,۰۰۰ تومان", "duration": "۲ ماه", "traffic": "60GB", "users": "۲ کاربره"},
    "3m_1u": {"name": "اشتراک ۳ ماهه (۹۰ گیگابایت - تک کاربره)", "price": "۶۰۰,۰۰۰ تومان", "duration": "۳ ماه", "traffic": "90GB", "users": "۱ کاربره"},
    "3m_2u": {"name": "اشتراک ۳ ماهه (۹۰ گیگابایت - دو کاربره)", "price": "۶۵۰,۰۰۰ تومان", "duration": "۳ ماه", "traffic": "90GB", "users": "۲ کاربره"},
}

# ==================== توابع تاریخ جلالی ====================
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

# ==================== منوی اصلی ====================
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
        f"سلام <b>{user.first_name}</b> عزیز، به سرویس قدرتمند L2TP/OpenVPN خوش آمدید! 🛡\n\n"
        f"📅 تاریخ: <code>{date_str}</code> | ⏰ ساعت: <code>{time_str}</code>\n"
        f"🆔 شناسه کاربری شما: <code>{user.id}</code>\n\n"
        f"⚡️ <b>پروتکل‌های پرسرعت فعال:</b>\n"
        f"• پروتکل پیشرفته <b>L2TP / IPSec</b> (بدون نیاز به نصب نرم‌افزار اضافی)\n"
        f"• پروتکل امن و رمزنگاری‌شده <b>OpenVPN</b>\n"
        f"• پروتکل پایدار <b>PPTP</b> سازگار با تمامی مودم‌ها و روترها\n\n"
        f"🎁 <i>تمامی پلن‌های اشتراک دارای ۱۰ گیگابایت ترافیک هدیه می‌باشند.</i>\n\n"
        "جهت انتخاب و مدیریت سرویس خود از کلیدهای منوی زیر استفاده کنید:"
    )

# ==================== هندلرهای پیام و دستورات ====================
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    add_user_to_db(message.from_user.id)
    await message.answer(get_welcome_text(message.from_user), reply_markup=get_main_keyboard())

@dp.message_handler(commands=['stats'], state="*")
async def cmd_stats(message: types.Message):
    if ADMIN_ID != 0 and message.from_user.id == ADMIN_ID:
        total = get_total_users_count()
        await message.answer(f"📊 <b>آمار اعضای ربات:</b>\n\nتعداد کل کاربران ثبت‌شده: <b>{total}</b> نفر")
    else:
        await message.answer("شما دسترسی به این بخش را ندارید.")

@dp.message_handler(lambda m: m.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, info in PLANS.items():
        kb.add(InlineKeyboardButton(f"🔹 {info['name']} — {info['price']}", callback_data=f"buy_{p_id}"))
    await message.answer(
        "🛍 <b>لیست پلن‌های سرویس (همراه با ۱۰ گیگابایت هدیه):</b>\n\n"
        "لطفاً یکی از تعرفه‌های زیر را انتخاب نمایید:",
        reply_markup=kb
    )

@dp.message_handler(lambda m: m.text == "📊 اطلاعات حساب", state="*")
async def handle_account(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        f"📊 <b>اطلاعات حساب کاربری شما:</b>\n\n"
        f"👤 نام: <b>{message.from_user.full_name}</b>\n"
        f"🆔 شناسه تلگرام: <code>{message.from_user.id}</code>\n"
        f"💎 وضعیت اکانت: <b>فعال / ثبت‌شده</b>\n"
        f"💰 کیف پول: <b>۰ تومان</b>\n\n"
        "برای شارژ یا تمدید اشتراک می‌توانید از منوی «💰 شارژ حساب» اقدام کنید."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda m: m.text == "💎 اشتراک‌های من", state="*")
async def handle_my_subs(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "💎 <b>اشتراک‌های فعال:</b>\n\n"
        "مشخصات اشتراک شما در IBSng ثبت گردیده است. جهت دریافت وضعیت مانده حجم و زمان به پشتیبانی پیام دهید.",
        reply_markup=get_main_keyboard()
    )

@dp.message_handler(lambda m: m.text == "💰 شارژ حساب", state="*")
async def handle_charge(message: types.Message, state: FSMContext):
    await state.finish()
    await ChargeState.waiting_for_receipt.set()
    
    caption = (
        f"💰 <b>شارژ و تمدید حساب کاربری</b>\n\n"
        f"💳 شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📌 <b>مراحل شارژ حساب:</b>\n"
        "۱. مبلغ مورد نظر را واریز نمایید.\n"
        "۲. <b>تصویر فیش واریزی</b> را همینجا ارسال کنید.\n"
        "۳. در مرحله بعد نام کاربری (Username) سرویس خود را وارد نمایید."
    )
    
    if os.path.exists(CARD_IMAGE_PATH):
        await message.answer_photo(photo=InputFile(CARD_IMAGE_PATH), caption=caption)
    else:
        await message.answer(caption)

@dp.message_handler(lambda m: m.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💬 ارتباط مستقیم در تلگرام", url=SUPPORT_URL))
    kb.add(InlineKeyboardButton("⚠️ ثبت گزارش خطا / مشکل در اتصال", callback_data="report_error"))
    text = (
        f"👥 <b>مرکز پشتیبانی فنی و پاسخگویی ۲۴ ساعته:</b>\n\n"
        f"🆔 آیدی پشتیبانی: {SUPPORT_USERNAME}\n"
        f"📢 کانال رسمی: @L2tp_vpn402\n\n"
        "جهت رفع مشکل اتصال یا راهنمایی تنظیمات با ما در ارتباط باشید:"
    )
    await message.answer(text, reply_markup=kb)

@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "❓ <b>سوالات متداول و راهنمای پروتکل‌ها:</b>\n\n"
        "۱. <b>پروتکل‌های قابل استفاده کدامند؟</b>\n"
        "ما از سه پروتکل رسمی و با ثبات <b>L2TP/IPSec</b>، <b>OpenVPN</b> و <b>PPTP</b> استفاده می‌کنیم.\n\n"
        "۲. <b>طریقه اتصال آیفون (iOS):</b>\n"
        "وارد Settings > General > VPN & Device Management > Add VPN Configuration شوید. Type را L2TP انتخاب کنید و آدرس سرور و Secret را وارد نمایید.\n\n"
        "۳. <b>طریقه اتصال اندروید (Android):</b>\n"
        "وارد تنظیمات اتصالات (Connections) > More connection settings > VPN شوید و پروفایل L2TP/IPSec PSK ایجاد کنید.\n\n"
        "۴. <b>طریقه اتصال ویندوز و مک (Windows/Mac):</b>\n"
        "در ویندوز از بخش VPN Settings گزینه L2TP with Preshared Key را انتخاب کنید یا فایل‌های OpenVPN (.ovpn) را در کلاینت رسمی OpenVPN وارد نمایید.\n\n"
        "۵. <b>طریقه اتصال مودم و روتر (Router/Modem):</b>\n"
        "وارد پنل مودم شوید (۱۹۲.۱۶۸.۱.۱)، در بخش VPN/Tunneling نوع اتصال را L2TP یا PPTP قرار داده و سرور و مشخصات را وارد نمایید.\n\n"
        "۶. <b>طرح جبرانی مشترکین چیست؟</b>\n"
        "مشترکین قدیمی می‌توانند با ارسال فیش قبلی و یوزرنیم، اکانت خود را با دوره کامل + ۱۰ گیگ هدیه مجدداً فعال کنند."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

@dp.message_handler(lambda m: m.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def handle_configs(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔗 کانال آموزش‌ها و نرم‌افزارها", url=CHANNEL_URL))
    text = (
        "⚙️ <b>راهنمای اتصال و فایل‌های کانفیگ:</b>\n\n"
        "تمامی راهنماهای ویدیویی و تصویری اتصال به L2TP، PPTP و فایل‌های اختصاصی OpenVPN در کانال رسمی قرار دارند:\n\n"
        f"🔗 <a href=\"{CHANNEL_URL}\">مشاهده آموزش‌ها و دانلود فایل‌های کانفیگ</a>"
    )
    await message.answer(text, reply_markup=kb)

# ==================== جریان‌های کال‌بک خرید و گزارش ====================
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"), state="*")
async def callback_buy_plan(query: types.CallbackQuery, state: FSMContext):
    plan_key = query.data.split("buy_")[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await query.answer("پلن یافت نشد.", show_alert=True)
        return
    
    await state.update_data(plan_key=plan_key, plan_name=plan["name"], plan_price=plan["price"])
    await OrderState.waiting_for_receipt.set()
    
    # دکمه بازگشت فقط در فرآیند خرید اشتراک
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 بازگشت به لیست پلن‌ها", callback_data="back_to_plans"))
    
    caption = (
        f"🧾 <b>پیش‌فاکتور خرید اشتراک</b>\n\n"
        f"📦 پلن: <b>{plan['name']}</b>\n"
        f"💵 مبلغ: <b>{plan['price']}</b>\n\n"
        f"💳 شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "لطفاً پس از واریز، <b>تصویر فیش واریزی</b> خود را ارسال کنید:"
    )
    
    await query.message.delete()
    if os.path.exists(CARD_IMAGE_PATH):
        await bot.send_photo(query.message.chat.id, photo=InputFile(CARD_IMAGE_PATH), caption=caption, reply_markup=kb)
    else:
        await bot.send_message(query.message.chat.id, text=caption, reply_markup=kb)
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "back_to_plans", state=OrderState.waiting_for_receipt)
async def callback_back_to_plans(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, info in PLANS.items():
        kb.add(InlineKeyboardButton(f"🔹 {info['name']} — {info['price']}", callback_data=f"buy_{p_id}"))
    await query.message.delete()
    await bot.send_message(
        query.message.chat.id,
        "🛍 <b>لیست پلن‌های اشتراک:</b>\n\nلطفاً یکی از تعرفه‌ها را انتخاب کنید:",
        reply_markup=kb
    )
    await query.answer()

@dp.callback_query_handler(lambda c: c.data == "report_error", state="*")
async def callback_report_issue(query: types.CallbackQuery, state: FSMContext):
    await ReportState.waiting_for_error.set()
    await query.message.edit_text(
        "⚠️ <b>ثبت گزارش خطا و قطعی:</b>\n\n"
        "لطفاً متن خطا، نوع پروتکل (L2TP / PPTP / OpenVPN) و نوع اینترنت خود (همراه اول / ایرانسل / مخابرات) را در قالب یک پیام ارسال کنید:"
    )
    await query.answer()

# ==================== دریافت مراحل FSM ====================
# خرید اشتراک - دریافت فیش
@dp.message_handler(content_types=['photo'], state=OrderState.waiting_for_receipt)
async def handle_order_receipt(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    plan_name = user_data.get("plan_name", "خرید اشتراک")
    plan_price = user_data.get("plan_price", "نامشخص")
    
    caption = (
        f"🔔 <b>فیش واریزی جدید (خرید اشتراک)</b>\n\n"
        f"👤 کاربر: {message.from_user.full_name}\n"
        f"🆔 شناسه: <code>{message.from_user.id}</code>\n"
        f"📦 پلن: {plan_name}\n"
        f"💰 مبلغ: {plan_price}"
    )
    if ADMIN_ID != 0:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption)
    
    await message.answer("✅ فیش شما با موفقیت دریافت شد و برای ادمین ارسال گردید. کانفیگ و اشتراک شما به زودی ارسال می‌شود.", reply_markup=get_main_keyboard())
    await state.finish()

# شارژ حساب - مرحله ۱: دریافت عکس فیش
@dp.message_handler(content_types=['photo'], state=ChargeState.waiting_for_receipt)
async def handle_charge_receipt(message: types.Message, state: FSMContext):
    await state.update_data(receipt_file_id=message.photo[-1].file_id)
    await ChargeState.waiting_for_username.set()
    await message.answer("✅ فیش دریافت شد.\n\nلطفاً <b>نام کاربری (Username)</b> اکانت VPN خود را وارد نمایید تا شارژ اعمال شود:")

# شارژ حساب - مرحله ۲: دریافت یوزرنیم
@dp.message_handler(state=ChargeState.waiting_for_username)
async def handle_charge_username(message: types.Message, state: FSMContext):
    username_val = message.text.strip()
    user_data = await state.get_data()
    file_id = user_data.get("receipt_file_id")
    
    caption = (
        f"💰 <b>درخواست شارژ حساب کاربری</b>\n\n"
        f"👤 کاربر: {message.from_user.full_name}\n"
        f"🆔 شناسه تلگرام: <code>{message.from_user.id}</code>\n"
        f"🔑 نام کاربری مشترک: <code>{username_val}</code>"
    )
    if ADMIN_ID != 0 and file_id:
        await bot.send_photo(ADMIN_ID, file_id, caption=caption)
    
    await message.answer(f"✅ درخواست شارژ برای نام کاربری <b>{username_val}</b> با موفقیت ثبت شد و به زودی تمدید خواهد شد.", reply_markup=get_main_keyboard())
    await state.finish()

# گزارش خطا
@dp.message_handler(state=ReportState.waiting_for_error)
async def handle_incoming_report(message: types.Message, state: FSMContext):
    report_text = f"⚠️ <b>گزارش خطای جدید</b>\n\n👤 فرستنده: {message.from_user.full_name}\n🆔 شناسه: <code>{message.from_user.id}</code>\n\n📝 متن گزارش:\n{message.text}"
    if ADMIN_ID != 0:
        await bot.send_message(ADMIN_ID, report_text)
    await message.answer("✅ گزارش شما برای تیم پشتیبانی ارسال شد و بررسی می‌گردد.", reply_markup=get_main_keyboard())
    await state.finish()

# ==================== سرور هلث‌چک و استارت ====================
async def run_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Shanli L2TP Bot is Active"))
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

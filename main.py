import os
import logging
import sqlite3
import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ==================== مشخصات ثابت و رسمی سرویس ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKEN56xw8aret4jX0X")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6278859256"))

CHANNEL_URL = "https://t.me/L2tp_vpn402"
CHANNEL_ID = "@L2tp_vpn402"
SUPPORT_URL = "https://t.me/L2tp1Support"
SUPPORT_ID = "@L2tp1Support"
BOT_USERNAME = "@L2TP_Arshavin_Bot"

PAYMENT_CARD = "6104338904607443"
PAYMENT_NAME = "رحیمی (بانک ملت)"
IBSNG_PANEL_URL = "http://94.184.45.58:48201/IBSng/user/"

VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "GAPGPTMASKTOKEN56xw8aret4jX1X"

IMG_TARIFF = "تعرفه.jpg"
IMG_CARD = "شماره کارت1.jpg"
IMG_MOBILE = "ایفون و اندروید.jpg"
IMG_PC_MODEM = "مودم و لب تاب.jpg"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=GAPGPTMASKTOKEN56xw8aret4jX2X
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ==================== محاسبه تاریخ شمسی و ساعت تهران ====================
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    jy = 0 if gy <= 1600 else 979
    gy -= 621 if gy <= 1600 else 1600
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    jy += (days - 1) // 365
    if days > 0:
        days = (days - 1) % 365
    jm = (days // 31) + 1 if days < 186 else 7 + ((days - 186) // 30)
    jd = 1 + (days % 31 if days < 186 else (days - 186) % 30)
    return jy, jm, jd

def get_current_jalali_datetime():
    # اختلاف ساعت با UTC برای ساعت رسمی تهران (+3:30)
    tz_tehran = datetime.timezone(datetime.timedelta(hours=3, minutes=30))
    now = datetime.datetime.now(tz_tehran)
    
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    
    days_fa = {
        5: "شنبه",
        6: "یک‌شنبه",
        0: "دوشنبه",
        1: "سه‌شنبه",
        2: "چهارشنبه",
        3: "پنج‌شنبه",
        4: "جمعه"
    }
    
    months_fa = [
        "", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
    ]
    
    day_name = days_fa[now.weekday()]
    month_name = months_fa[jm]
    time_str = now.strftime("%H:%M:%S")
    date_str = f"{jd} {month_name} {jy}"
    
    return day_name, date_str, time_str

# ==================== دیتابیس ====================
conn = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS counters (
    action_name TEXT PRIMARY KEY,
    count INTEGER DEFAULT 0
)
""")
conn.commit()

def record_user(user: types.User):
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user.id, user.username or "", user.full_name or "")
        )
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error (record_user): {e}")

def increment_counter(action_name: str):
    try:
        cursor.execute("""
            INSERT INTO counters (action_name, count) VALUES (?, 1)
            ON CONFLICT(action_name) DO UPDATE SET count = count + 1
        """, (action_name,))
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error (increment_counter): {e}")

def get_stats_data():
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT action_name, count FROM counters")
    clicks = dict(cursor.fetchall())
    return total_users, clicks

# ==================== FSM States ====================
class FormState(StatesGroup):
    waiting_for_payment = State()
    waiting_for_support = State()

# ==================== کیبوردها ====================
BTN_BACK = "🔙 برگشت به منوی اصلی"

def get_main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row("🛍 خرید اشتراک", "💳 تمدید حساب")
    kb.row("🌐 پنل کاربری IBSng", "📖 راهنمای اتصال")
    kb.row("💬 پشتیبانی آنلاین", "❓ سوالات و طرح جبرانی")
    return kb

def get_back_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_BACK)
    return kb

def get_guide_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row("📱 آموزش آیفون و اندروید", "💻 آموزش ویندوز و مودم")
    kb.row(BTN_BACK)
    return kb

def get_support_inline():
    ikb = types.InlineKeyboardMarkup(row_width=2)
    ikb.row(
        types.InlineKeyboardButton(text="💬 پیام به پشتیبان تلگرام", url=SUPPORT_URL),
        types.InlineKeyboardButton(text="📢 کانال اطلاع‌رسانی", url=CHANNEL_URL)
    )
    return ikb

# ==================== متن تعرفه‌ها ====================
PRICING_MESSAGE = (
    "📋 <b>تعرفه‌های رسمی اشتراک پرسرعت L2TP VPN 24/7</b>\n"
    "🎁 <i>(تمامی پلن‌ها شامل ۱۰ گیگابایت ترافیک هدیه می‌باشند)</i>\n\n"
    "🔹 <b>پلن‌های یک‌ماهه:</b>\n"
    "▫️ یک‌ماهه تک‌کاربره: <b>۲۰۰,۰۰۰ تومان</b>\n"
    "▫️ یک‌ماهه دو‌کاربره: <b>۲۵۰,۰۰۰ تومان</b>\n\n"
    "🔹 <b>پلن‌های دو‌ماهه:</b>\n"
    "▫️ دو‌ماهه تک‌کاربره: <b>۳۸۰,۰۰۰ تومان</b>\n"
    "▫️ دو‌ماهه دو‌کاربره: <b>۴۳۰,۰۰۰ تومان</b>\n\n"
    "🔹 <b>پلن‌های سه‌ماهه:</b>\n"
    "▫️ سه‌ماهه تک‌کاربره: <b>۵۵۰,۰۰۰ تومان</b>\n"
    "▫️ سه‌ماهه دو‌کاربره: <b>۶۰۰,۰۰۰ تومان</b>\n\n"
    "💳 <b>مشخصات حساب بانکی جهت واریز:</b>\n"
    f"▫️ شماره کارت: <code>{PAYMENT_CARD}</code>\n"
    f"▫️ به نام: <b>{PAYMENT_NAME}</b>\n\n"
    "📸 <b>لطفاً پس از واریز، عکس فیش بانکی خود را همین‌جا ارسال نمایید:</b>\n"
    f"💬 ارتباط مستقیم با پشتیبانی: {SUPPORT_ID}"
)

# ==================== هندلرها ====================
@dp.message_handler(lambda m: m.text == BTN_BACK, state="*")
async def process_back_button(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply("به منوی اصلی بازگشتید 👇", reply_markup=get_main_keyboard())

@dp.message_handler(commands=['start'], state="*")
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    record_user(message.from_user)
    increment_counter("start_total")
    
    day_name, date_str, time_str = get_current_jalali_datetime()
    user_name = message.from_user.first_name or "کاربر"
    
    welcome_text = (
        f"سلام <b>{user_name}</b> عزیز، خیلی خوش آمدید! 🌹\n\n"
        f"📅 <b>روز:</b> {day_name}\n"
        f"📆 <b>تاریخ:</b> {date_str}\n"
        f"⏰ <b>ساعت:</b> {time_str}\n\n"
        "⚡️ به ربات رسمی فروش و پشتیبانی هوشمند <b>L2TP VPN 24/7</b> خوش آمدید.\n\n"
        "🚀 <b>امکانات و ویژگی‌های سرویس ما:</b>\n"
        "▫️ بالاترین سرعت و پایداری بدون قطعی\n"
        "▫️ بدون نیاز به نصب نرم‌افزار اضافی (پروتکل امن L2TP/IPSec داخلی سیستم‌عامل)\n"
        "▫️ سازگار با تمامی اپراتورها (همراه اول، ایرانسل، رایتل، شاتل و اینترنت ثابت)\n"
        "▫️ پنل اختصاصی IBSng برای مشاهده آنلاین حجم و زمان باقیمانده\n"
        "🎁 <b>۱۰ گیگابایت ترافیک هدیه</b> روی تمامی پلن‌ها\n\n"
        f"📢 <b>کانال رسمی:</b> {CHANNEL_ID}\n"
        f"💬 <b>پشتیبانی مستقیم:</b> {SUPPORT_ID}\n"
        f"🤖 <b>آیدی ربات:</b> {BOT_USERNAME}\n\n"
        "👇 <b>جهت شروع، یکی از گزینه‌های منوی زیر را انتخاب نمایید:</b>"
    )
    
    quick_kb = types.InlineKeyboardMarkup(row_width=2)
    quick_kb.row(
        types.InlineKeyboardButton(text="📢 کانال رسمی", url=CHANNEL_URL),
        types.InlineKeyboardButton(text="💬 ارتباط با پشتیبان", url=SUPPORT_URL)
    )
    
    try:
        await message.reply(welcome_text, reply_markup=quick_kb, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Start send error: {e}")
        clean_text = welcome_text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
        await message.reply(clean_text, reply_markup=quick_kb)
        
    await message.answer("منوی خدمات:", reply_markup=get_main_keyboard())

@dp.message_handler(commands=['stats', 'counter'], state="*")
async def admin_stats_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    total_users, clicks = get_stats_data()
    stats_msg = (
        "📊 <b>آمار و عملکرد لحظه‌ای ربات:</b>\n\n"
        f"👥 <b>تعداد کاربران ثبت‌شده:</b> <code>{total_users}</code> نفر\n"
        f"🚀 <b>کل دفعات /start:</b> <code>{clicks.get('start_total', 0)}</code> بار\n\n"
        "📈 <b>تعداد کلیک‌ها و درخواست‌ها:</b>\n"
        f"▫️ خرید و تمدید: <code>{clicks.get('click_buy_renew', 0)}</code>\n"
        f"▫️ ورود به پنل IBSng: <code>{clicks.get('click_ibsng', 0)}</code>\n"
        f"▫️ راهنمای اتصال: <code>{clicks.get('click_guide', 0)}</code>\n"
        f"▫️ بخش پشتیبانی: <code>{clicks.get('click_support', 0)}</code>\n"
        f"▫️ سوالات و طرح جبرانی: <code>{clicks.get('click_faq', 0)}</code>\n"
        f"▫️ فیش‌های واریزی ارسالی: <code>{clicks.get('receipt_sent', 0)}</code>\n"
        f"▫️ پیام‌های پشتیبانی ثبت‌شده: <code>{clicks.get('tickets_received', 0)}</code>\n"
    )
    await message.reply(stats_msg, parse_mode="HTML")

@dp.message_handler(lambda m: m.text in ["🛍 خرید اشتراک", "💳 تمدید حساب"], state="*")
async def buy_subscription(message: types.Message, state: FSMContext):
    await state.finish()
    increment_counter("click_buy_renew")
    await FormState.waiting_for_payment.set()
    
    if os.path.exists(IMG_TARIFF):
        try:
            with open(IMG_TARIFF, "rb") as photo:
                await message.reply_photo(photo, caption=PRICING_MESSAGE, reply_markup=get_back_keyboard(), parse_mode="HTML")
                return
        except Exception as e:
            logging.error(f"Tariff Photo Error: {e}")
            
    await message.reply(PRICING_MESSAGE, reply_markup=get_back_keyboard(), parse_mode="HTML")

@dp.message_handler(state=FormState.waiting_for_payment, content_types=types.ContentTypes.ANY)
async def process_payment_receipt(message: types.Message, state: FSMContext):
    increment_counter("receipt_sent")
    user = message.from_user
    caption = (
        "💰 <b>فیش واریزی جدید دریافت شد!</b>\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 آیدی عددی: <code>{user.id}</code>\n"
        f"📝 پیام همراه: {message.caption or message.text or 'بدون متن'}"
    )
    
    try:
        if message.photo:
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="HTML")
        elif message.document:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, parse_mode="HTML")
        else:
            await bot.send_message(ADMIN_ID, caption, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Admin forward error: {e}")

    await message.reply(
        "✅ <b>فیش واریزی شما دریافت و برای ادمین ارسال گردید.</b>\n"
        "پس از بررسی، کانفیگ و مشخصات اکانت به سرعت تحویل داده می‌شود.\n\n"
        f"📢 کانال رسمی: {CHANNEL_URL}\n"
        f"💬 پشتیبان اختصاصی: {SUPPORT_ID}",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
    await state.finish()

@dp.message_handler(lambda m: m.text == "🌐 پنل کاربری IBSng", state="*")
async def ibsng_menu_handler(message: types.Message):
    increment_counter("click_ibsng")
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.add(types.InlineKeyboardButton(text="🔗 ورود به پنل کاربری IBSng", url=IBSNG_PANEL_URL))

    text = (
        "🌐 <b>ورود به سامانه مدیریت حساب کاربری (IBSng)</b>\n\n"
        "از این طریق می‌توانید حجم باقیمانده، تاریخ انقضا و وضعیت آنلاین بودن اکانت خود را مشاهده فرمایید.\n\n"
        "⚠️ <b>هشدار امنیتی بسیار مهم:</b>\n"
        "<b>«حتماً در اولین ورود به پنل، رمز عبور (Password) خود را تغییر دهید تا امنیت سرویس تضمین گردد.»</b>\n\n"
        "📌 <b>مراحل:</b>\n"
        "1️⃣ روی دکمه زیر کلیک کرده و وارد صفحه شوید.\n"
        "2️⃣ نام کاربری و رمز دریافتی را وارد نمایید.\n"
        "3️⃣ از منوی بالای پنل بر روی گزینه <b>Change Password</b> بزنید و رمز اختصاصی خود را وارد و ذخیره کنید.\n\n"
        f"💬 در صورت بروز هرگونه مشکل با پشتیبانی در تماس باشید: {SUPPORT_ID}"
    )
    await message.reply(text, reply_markup=inline_kb, parse_mode="HTML")
    await message.answer("جهت بازگشت به منوی قبلی:", reply_markup=get_back_keyboard())

@dp.message_handler(lambda m: m.text == "📖 راهنمای اتصال", state="*")
async def guide_menu_handler(message: types.Message):
    increment_counter("click_guide")
    text = (
        "📖 <b>راهنمای جامع راه‌اندازی و اتصال L2TP/IPSec:</b>\n\n"
        f"🌐 <b>Server IP:</b> <code>{VPN_SERVER_IP}</code>\n"
        f"🔑 <b>IPsec Pre-Shared Key:</b> <code>{IPSEC_SECRET}</code>\n\n"
        "👇 نوع دستگاه خود را انتخاب فرمایید:"
    )
    await message.reply(text, reply_markup=get_guide_keyboard(), parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "📱 آموزش آیفون و اندروید", state="*")
async def guide_mobile(message: types.Message):
    text = (
        "📱 <b>راهنمای اتصال موبایل (iOS و Android):</b>\n\n"
        "🍎 <b>آیفون (iOS):</b>\n"
        "1. به مسیر Settings > General > VPN & Device Management بروید.\n"
        "2. Add VPN Configuration را زده و Type را <b>L2TP</b> بگذارید.\n"
        f"3. در کادر Server آدرس <code>{VPN_SERVER_IP}</code> را بنویسید.\n"
        "4. نام کاربری و رمز خود را وارد کنید.\n"
        f"5. در کادر Secret مقدار <code>{IPSEC_SECRET}</code> را وارد کرده و Done را بزنید.\n\n"
        "🤖 <b>اندروید (Android):</b>\n"
        "1. به تنظیمات > اتصالات > VPN بروید.\n"
        "2. افزودن VPN را زده و نوع را <b>L2TP/IPSec PSK</b> انتخاب نمایید.\n"
        f"3. سرور: <code>{VPN_SERVER_IP}</code> | کلید پیش‌مشترک: <code>{IPSEC_SECRET}</code>\n\n"
        f"📢 کانال: {CHANNEL_ID} | 💬 پشتیبانی: {SUPPORT_ID}"
    )
    if os.path.exists(IMG_MOBILE):
        try:
            with open(IMG_MOBILE, "rb") as photo:
                await message.reply_photo(photo, caption=text, reply_markup=get_guide_keyboard(), parse_mode="HTML")
                return
        except Exception as e:
            logging.error(f"Mobile Photo Error: {e}")
            
    await message.reply(text, reply_markup=get_guide_keyboard(), parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "💻 آموزش ویندوز و مودم", state="*")
async def guide_pc_modem(message: types.Message):
    text = (
        "💻 <b>راهنمای اتصال ویندوز و مودم:</b>\n\n"
        "🖥 <b>ویندوز (Windows):</b>\n"
        "1. به Settings > Network & Internet > VPN رفته و Add VPN را انتخاب کنید.\n"
        "2. گزینه Provider را Windows (built-in) بگذارید.\n"
        f"3. در Server name مقدار <code>{VPN_SERVER_IP}</code> را بزنید.\n"
        "4. VPN type را <b>L2TP/IPsec with pre-shared key</b> قرار دهید.\n"
        f"5. در کادر Pre-shared key مقدار <code>{IPSEC_SECRET}</code> را وارد کنید و ذخیره نمایید.\n\n"
        "📶 <b>مودم و روتر (Router):</b>\n"
        "در پنل تنظیمات ۱۹۲.۱۶۸.۱.۱، در بخش VPN Client، پروتکل L2TP را با سرور و سکرت فوق ست کنید.\n\n"
        f"📢 کانال: {CHANNEL_ID} | 💬 پشتیبانی: {SUPPORT_ID}"
    )
    if os.path.exists(IMG_PC_MODEM):
        try:
            with open(IMG_PC_MODEM, "rb") as photo:
                await message.reply_photo(photo, caption=text, reply_markup=get_guide_keyboard(), parse_mode="HTML")
                return
        except Exception as e:
            logging.error(f"PC Photo Error: {e}")
            
    await message.reply(text, reply_markup=get_guide_keyboard(), parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "💬 پشتیبانی آنلاین", state="*")
async def support_handler(message: types.Message, state: FSMContext):
    await state.finish()
    increment_counter("click_support")
    await FormState.waiting_for_support.set()
    text = (
        "💬 <b>واحد پشتیبانی رسمی L2TP VPN 24/7</b>\n\n"
        "برای ثبت مستقیم تیکت، <b>نام کاربری سرویس</b> و <b>متن سوال یا مشکل</b> خود را در قالب یک پیام همین‌جا ارسال نمایید.\n\n"
        "یا می‌توانید مستقیماً از طریق دکمه‌های زیر با آیدی پشتیبان در تلگرام ارتباط برقرار کنید:"
    )
    await message.reply(text, reply_markup=get_support_inline(), parse_mode="HTML")
    await message.answer("جهت انصراف دکمه برگشت را بزنید:", reply_markup=get_back_keyboard())

@dp.message_handler(state=FormState.waiting_for_support, content_types=types.ContentTypes.ANY)
async def process_support_ticket(message: types.Message, state: FSMContext):
    increment_counter("tickets_received")
    user = message.from_user
    user_msg = message.text or message.caption or "ارسال رسانه بدون متن"

    ticket_text = (
        "🚨 <b>تیکت پشتیبانی جدید!</b>\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 آیدی عددی: <code>{user.id}</code>\n\n"
        f"📄 <b>پیام کاربر:</b>\n{user_msg}"
    )

    try:
        await bot.send_message(ADMIN_ID, ticket_text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Support forward error: {e}")

    await message.reply(
        "✅ <b>درخواست شما برای پشتیبانی ارسال شد و به زودی پاسخ داده می‌شود.</b>\n\n"
        f"💬 آیدی مستقیم تلگرام: {SUPPORT_ID}\n"
        f"📢 کانال اطلاع‌رسانی: {CHANNEL_URL}",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
    await state.finish()

@dp.message_handler(lambda m: m.text == "❓ سوالات و طرح جبرانی", state="*")
async def faq_menu_handler(message: types.Message):
    increment_counter("click_faq")
    faq_text = (
        "❓ <b>پاسخ به سوالات متداول و اطلاع‌رسانی:</b>\n\n"
        "🔄 <b>طرح جبرانی ویژه مشترکین قدیمی:</b>\n"
        "مشترکین عزیزی که طی ۲ تا ۳ سال گذشته اشتراک داشته‌اند و به علت قطعی‌ها سرویس‌شان قطع شده بود، "
        "با ارسال نام کاربری و رسید یا فیش واریزی قبلی به پشتیبانی، <b>اکانتشان با دوره کامل و ۱۰ گیگابایت حجم هدیه بدون دریافت هزینه از نو فعال می‌گردد.</b>\n\n"
        "🎁 <b>ترافیک هدیه:</b>\n"
        "تمامی پلن‌های جدید ۱، ۲ و ۳ ماهه دارای ۱۰ گیگابایت ترافیک هدیه می‌باشند.\n\n"
        "🔐 <b>چرا تغییر رمز در IBSng الزامی است؟</b>\n"
        "برای حفظ امنیت حساب شما و جلوگیری از هرگونه سوءاستفاده، حتماً در اولین اتصال رمز پنل خود را عوض کنید.\n\n"
        f"📢 کانال رسمی: {CHANNEL_URL}\n"
        f"💬 پشتیبان: {SUPPORT_ID}"
    )
    await message.reply(faq_text, reply_markup=get_back_keyboard(), parse_mode="HTML")

@dp.message_handler(state="*")
async def general_fallback(message: types.Message):
    await message.reply("لطفاً از گزینه‌های منو استفاده بفرمایید 👇", reply_markup=get_main_keyboard())

# ==================== استارت ضد تداخل ====================
async def on_startup(dispatcher):
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook cleared. Bot started cleanly.")

if __name__ == '__main__':
    print("🚀 ربات با مشخصات کامل در حال اجراست...")
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)

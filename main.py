import os
import logging
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ==================== دریافت تنظیمات دقیقا از Environment رندر ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8715195364:AAGaBoFhH5VeDYjBg1SitR1Ah4giogi103g")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6278859256"))
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338904607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی (بانک ملت)")
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/")

# مشخصات ثابت اتصال VPN
VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "12345678."

# مسیر فایل‌های عکس (در صورت وجود در مخزن پروژه)
IMG_TARIFF = "تعرفه.jpg"
IMG_CARD = "شماره کارت1.jpg"
IMG_MOBILE = "ایفون و اندروید.jpg"
IMG_PC_MODEM = "مودم و لب تاب.jpg"

# ==================== لاگینگ و راه‌اندازی ربات ====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ==================== دیتابیس آمار و شماره‌انداز ====================
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

# ==================== وضعیت‌های FSM ====================
class FormState(StatesGroup):
    waiting_for_payment = State()
    waiting_for_support = State()

# ==================== کیبوردها و دکمه‌ها ====================
BTN_BACK = "🔙 برگشت به منوی اصلی"

def get_main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row("🛍 خرید اشتراک", "💳 تمدید حساب")
    kb.row("🌐 پنل کاربری IBSng", "📖 راهنمای اتصال")
    kb.row("💬 پشتیبانی", "❓ سوالات متداول")
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

# ==================== متن تعرفه‌ها ====================
PRICING_MESSAGE = (
    "📋 **تعرفه‌های رسمی اشتراک پرسرعت L2TP VPN 24/7**\n"
    "🎁 *(تمامی پلن‌ها شامل ۱۰ گیگابایت ترافیک هدیه می‌باشند)*\n\n"
    "🔹 **پلن‌های یک‌ماهه:**\n"
    "▫️ یک‌ماهه تک‌کاربره: **۲۰۰,۰۰۰ تومان**\n"
    "▫️ یک‌ماهه دو‌کاربره: **۲۵۰,۰۰۰ تومان**\n\n"
    "🔹 **پلن‌های دو‌ماهه:**\n"
    "▫️ دو‌ماهه تک‌کاربره: **۳۸۰,۰۰۰ تومان**\n"
    "▫️ دو‌ماهه دو‌کاربره: **۴۳۰,۰۰۰ تومان**\n\n"
    "🔹 **پلن‌های سه‌ماهه:**\n"
    "▫️ سه‌ماهه تک‌کاربره: **۵۵۰,۰۰۰ تومان**\n"
    "▫️ سه‌ماهه دو‌کاربره: **۶۰۰,۰۰۰ تومان**\n\n"
    "💳 **مشخصات واریز:**\n"
    f"شماره کارت: `{PAYMENT_CARD}`\n"
    f"به نام: **{PAYMENT_NAME}**\n\n"
    "📸 **لطفاً پس از پرداخت، عکس فیش واریزی خود را ارسال فرمایید:**"
)

# ==================== دکمه بازگشت گلوبال ====================
@dp.message_handler(lambda m: m.text == BTN_BACK, state="*")
async def process_back_button(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply("به منوی اصلی برگشتید 👇", reply_markup=get_main_keyboard())

# ==================== دستور /start ====================
@dp.message_handler(commands=['start'], state="*")
async def start_handler(message: types.Message, state: FSMContext):
    await state.finish()
    record_user(message.from_user)
    increment_counter("start_total")
    
    welcome_text = (
        f"سلام {message.from_user.first_name} عزیز 👋\n"
        "به ربات رسمی فروش و پشتیبانی **L2TP VPN 24/7** خوش آمدید.\n\n"
        "⚡️ بدون قطعی، با سرعت بالا و امنیت کامل\n"
        "🌐 سازگار با همراه اول، ایرانسل، رایتل و اینترنت ثابت مخابرات و فیبر\n\n"
        f"📢 کانال رسمی ما: {CHANNEL_URL}\n"
        "جهت شروع یکی از بخش‌های زیر را لمس کنید:"
    )
    await message.reply(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# ==================== دستور شماره‌انداز و آمار /counter ====================
@dp.message_handler(commands=['stats', 'counter'], state="*")
async def admin_stats_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    total_users, clicks = get_stats_data()
    stats_msg = (
        "📊 **گزارش لحظه‌ای شماره‌انداز سیستم:**\n\n"
        f"👥 **کل اعضای یونیک ربات:** `{total_users}` نفر\n"
        f"🚀 **تعداد کل دفعات /start:** `{clicks.get('start_total', 0)}` بار\n\n"
        "📈 **آمار تفکیکی بازدیدها:**\n"
        f"▫️ کلیک منوی خرید و تمدید: `{clicks.get('click_buy_renew', 0)}`\n"
        f"▫️ کلیک ورود به پنل IBSng: `{clicks.get('click_ibsng', 0)}`\n"
        f"▫️ کلیک راهنمای اتصال: `{clicks.get('click_guide', 0)}`\n"
        f"▫️ کلیک بخش پشتیبانی: `{clicks.get('click_support', 0)}`\n"
        f"▫️ کلیک سوالات متداول: `{clicks.get('click_faq', 0)}`\n"
        f"▫️ فیش‌های واریزی ارسالی: `{clicks.get('receipt_sent', 0)}`\n"
        f"▫️ تیکت‌های پشتیبانی ثبت‌شده: `{clicks.get('tickets_received', 0)}`\n"
    )
    await message.reply(stats_msg, parse_mode="Markdown")

# ==================== خرید و تمدید اشتراک ====================
@dp.message_handler(lambda m: m.text in ["🛍 خرید اشتراک", "💳 تمدید حساب"], state="*")
async def buy_subscription(message: types.Message, state: FSMContext):
    await state.finish()
    increment_counter("click_buy_renew")
    await FormState.waiting_for_payment.set()
    
    # ارسال عکس تعرفه در صورت وجود
    if os.path.exists(IMG_TARIFF):
        try:
            with open(IMG_TARIFF, "rb") as photo:
                await message.reply_photo(photo, caption=PRICING_MESSAGE, reply_markup=get_back_keyboard(), parse_mode="Markdown")
                return
        except Exception as e:
            logging.error(f"Error sending photo: {e}")
            
    await message.reply(PRICING_MESSAGE, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@dp.message_handler(state=FormState.waiting_for_payment, content_types=types.ContentTypes.ANY)
async def process_payment_receipt(message: types.Message, state: FSMContext):
    increment_counter("receipt_sent")
    user = message.from_user
    
    caption = (
        "💰 **فیش واریزی جدید دریافت شد!**\n"
        f"👤 خریدار: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 آیدی عددی: `{user.id}`\n"
        f"📝 توضیحات: {message.caption or message.text or 'ندارد'}"
    )
    
    try:
        if message.photo:
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
        elif message.document:
            await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, parse_mode="Markdown")
        else:
            await bot.send_message(ADMIN_ID, caption, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error sending receipt to admin: {e}")

    await message.reply(
        "✅ **رسید پرداخت شما با موفقیت ثبت شد.**\n"
        "پس از بررسی، مشخصات اکانت بلافاصله برای شما ارسال می‌گردد.\n"
        f"پشتیبانی: {SUPPORT_ID}",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await state.finish()

# ==================== پنل کاربری IBSng ====================
@dp.message_handler(lambda m: m.text == "🌐 پنل کاربری IBSng", state="*")
async def ibsng_menu_handler(message: types.Message):
    increment_counter("click_ibsng")
    inline_kb = types.InlineKeyboardMarkup()
    inline_kb.add(types.InlineKeyboardButton(text="🔗 ورود مستقیم به پنل یوزر IBSng", url=IBSNG_PANEL_URL))

    text = (
        "🌐 **ورود به پنل مدیریت اکانت (IBSng)**\n\n"
        "از این بخش می‌توانید حجم مصرفی، مانده اعتبار و وضعیت آنلاین بودن حساب خود را بررسی فرمایید.\n\n"
        "⚠️ **هشدار امنیتی بسیار مهم:**\n"
        "**«حتماً در اولین ورود به پنل، رمز عبور (Password) اکانت خود را تغییر دهید تا امنیت شما تضمین گردد.»**\n\n"
        "📌 **راهنما:**\n"
        "1️⃣ روی دکمه زیر کلیک کنید.\n"
        "2️⃣ نام کاربری و رمز خود را وارد کنید.\n"
        "3️⃣ از بالای صفحه روی **Change Password** بزنید و رمز دلخواه خود را ثبت کنید."
    )
    await message.reply(text, reply_markup=inline_kb, parse_mode="Markdown")
    await message.answer("جهت برگشت دکمه زیر را لمس کنید:", reply_markup=get_back_keyboard())

# ==================== راهنمای اتصال جامع ====================
@dp.message_handler(lambda m: m.text == "📖 راهنمای اتصال", state="*")
async def guide_menu_handler(message: types.Message):
    increment_counter("click_guide")
    text = (
        "📖 **راهنمای جامع اتصال به سرورهای L2TP/IPSec:**\n\n"
        f"🌐 **Server Address:** `{VPN_SERVER_IP}`\n"
        f"🔑 **IPsec Secret (PSK):** `{IPSEC_SECRET}`\n\n"
        "👇 نوع دستگاه خود را جهت مشاهده راهنما انتخاب کنید:"
    )
    await message.reply(text, reply_markup=get_guide_keyboard(), parse_mode="Markdown")

@dp.message_handler(lambda m: m.text == "📱 آموزش آیفون و اندروید", state="*")
async def guide_mobile(message: types.Message):
    text = (
        "📱 **راهنمای اتصال آیفون و اندروید:**\n\n"
        "🍎 **آیفون (iOS):**\n"
        "1. به مسیر Settings > General > VPN & Device Management بروید.\n"
        "2. گزینه Add VPN Configuration را بزنید و Type را **L2TP** انتخاب کنید.\n"
        f"3. در کادر Server مقدار `{VPN_SERVER_IP}` را بنویسید.\n"
        "4. نام کاربری و رمز عبور دریافتی خود را وارد کنید.\n"
        f"5. در کادر Secret مقدار `{IPSEC_SECRET}` را وارد کرده و Save کنید.\n\n"
        "🤖 **اندروید (Android):**\n"
        "1. به تنظیمات > اتصالات > VPN بروید.\n"
        "2. نوع اتصال را **L2TP/IPSec PSK** قرار دهید.\n"
        f"3. سرور: `{VPN_SERVER_IP}` | سکرت: `{IPSEC_SECRET}`"
    )
    if os.path.exists(IMG_MOBILE):
        try:
            with open(IMG_MOBILE, "rb") as photo:
                await message.reply_photo(photo, caption=text, reply_markup=get_guide_keyboard(), parse_mode="Markdown")
                return
        except Exception as e:
            logging.error(f"Error sending mobile photo: {e}")
            
    await message.reply(text, reply_markup=get_guide_keyboard(), parse_mode="Markdown")

@dp.message_handler(lambda m: m.text == "💻 آموزش ویندوز و مودم", state="*")
async def guide_pc_modem(message: types.Message):
    text = (
        "💻 **راهنمای اتصال ویندوز و مودم:**\n\n"
        "🖥 **ویندوز (Windows):**\n"
        "1. وارد Settings > Network & Internet > VPN شوید و Add VPN را بزنید.\n"
        "2. VPN Provider را روی Windows (built-in) قرار دهید.\n"
        f"3. در Server name or address مقدار `{VPN_SERVER_IP}` را بگذارید.\n"
        "4. نوع VPN را روی **L2TP/IPsec with pre-shared key** بگذارید.\n"
        f"5. در Pre-shared key مقدار `{IPSEC_SECRET}` را بنویسید و ذخیره کنید.\n\n"
        "📶 **مودم و روتر (Router):**\n"
        "در پنل تنظیمات مودم بخش VPN Client را روی L2TP با مشخصات فوق فعال فرمایید."
    )
    if os.path.exists(IMG_PC_MODEM):
        try:
            with open(IMG_PC_MODEM, "rb") as photo:
                await message.reply_photo(photo, caption=text, reply_markup=get_guide_keyboard(), parse_mode="Markdown")
                return
        except Exception as e:
            logging.error(f"Error sending pc/modem photo: {e}")
            
    await message.reply(text, reply_markup=get_guide_keyboard(), parse_mode="Markdown")

# ==================== بخش پشتیبانی ====================
@dp.message_handler(lambda m: m.text == "💬 پشتیبانی", state="*")
async def support_handler(message: types.Message, state: FSMContext):
    await state.finish()
    increment_counter("click_support")
    await FormState.waiting_for_support.set()
    text = (
        "💬 **واحد پشتیبانی L2TP VPN 24/7**\n\n"
        "لطفاً در یک پیام **نام کاربری اشتراک** و **شرح دقیق سوال یا مشکل** خود را ارسال نمایید:\n\n"
        "*(جهت انصراف دکمه برگشت زیر را بزنید)*"
    )
    await message.reply(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

@dp.message_handler(state=FormState.waiting_for_support, content_types=types.ContentTypes.ANY)
async def process_support_ticket(message: types.Message, state: FSMContext):
    increment_counter("tickets_received")
    user = message.from_user
    user_msg = message.text or message.caption or "ارسال فایل بدون متن"

    ticket_text = (
        "🚨 **پیام پشتیبانی جدید!**\n"
        f"👤 کاربر: {user.full_name} (@{user.username or 'ندارد'})\n"
        f"🆔 آیدی عددی: `{user.id}`\n\n"
        f"📄 **متن تیکت:**\n{user_msg}"
    )

    try:
        await bot.send_message(ADMIN_ID, ticket_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error sending ticket to admin: {e}")

    await message.reply(
        "✅ **پیام شما با موفقیت برای پشتیبانی ارسال گردید.**\n"
        "کارشناسان ما به زودی پاسخ شما را ارسال خواهند کرد.\n\n"
        f"ارتباط مستقیم: {SUPPORT_ID}",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await state.finish()

# ==================== سوالات متداول ====================
@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def faq_menu_handler(message: types.Message):
    increment_counter("click_faq")
    faq_text = (
        "❓ **سوالات متداول کاربران:**\n\n"
        "🔐 **۱. چرا تغییر رمز پنل IBSng الزامی است؟**\n"
        "برای حفظ امنیت حساب شما و عدم سوءاستفاده افراد دیگر.\n\n"
        "🎁 **۲. حجم هدیه چیست؟**\n"
        "تمامی پلن‌های ۱، ۲ و ۳ ماهه ما دارای ۱۰ گیگابایت ترافیک هدیه می‌باشند.\n\n"
        "🔄 **۳. طرح جبرانی مشترکین قدیمی چیست؟**\n"
        "مشترکین عزیزی که در دوران قطعی سرویس داشتند، با ارسال نام کاربری و رسید قبلی، اشتراکشان بدون دریافت هزینه از امروز تمدید و فعال می‌شود.\n\n"
        f"📢 کانال اطلاع‌رسانی: {CHANNEL_URL}\n"
        f"💬 آیدی پشتیبان: {SUPPORT_ID}"
    )
    await message.reply(faq_text, reply_markup=get_back_keyboard(), parse_mode="Markdown")

# ==================== پیام‌های متفرقه ====================
@dp.message_handler(state="*")
async def general_fallback(message: types.Message):
    await message.reply("لطفاً از دکمه‌های منوی زیر استفاده فرمایید 👇", reply_markup=get_main_keyboard())

# ==================== اجرای نهایی ربات ====================
if __name__ == '__main__':
    print("🚀 ربات L2TP VPN با موفقیت اجرا شد...")
    executor.start_polling(dp, skip_updates=True)

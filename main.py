import os
import asyncio
import logging
import sqlite3
import random
import string
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

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENgjlgj2jhxvkX0X").strip()

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "02786850266").strip()
clean_admin_id = ADMIN_ID_RAW.lstrip('0')
ADMIN_ID = int(clean_admin_id) if clean_admin_id.isdigit() else 2786850266

SUPPORT اصلی دقیقاً مطابق نسخهٔ کامل خودت بازگردانی و تنظیم شد.

---

### کد کامل، بدون بخش جبرانی و با تمام سوالات و عکس‌ها (`main.py`):
```python
import os
import asyncio
import logging
import sqlite3
import random
import string
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

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENgjlgj2jhxvkX1X").strip()

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "02786850266").strip()
clean_admin_id = ADMIN_ID_RAW.lstrip('0')
ADMIN_ID = int(clean_admin_id) if clean_admin_id.isdigit() else 2786850266

SUPPORT_ID = os.getenv("SUPPORT_ID", "L2tp1Support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()
IBSNG_conn.close()

def add_user_to_db(user: types.User):
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
date_str, _, _ = get_persian_datetime()
c.execute(
"INSERT OR IGNORE INTO users (user_id, full_name, username, join_date) VALUES (?, ?, ?, ?)",
(user.id, user.full_name or "", user.username or "", date_str)
)
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

class SupportState(StatesGroup):
waiting_for_username_and_msg = State()

# ==================== تعرفه‌ها ====================
PLANS = {
"1m_1u": {"name": "اشتراک 1 ماهه (تک کاربره + 10 گیگ هدیه)", "price": "200,000 تومان"},
"1m_2u": {"name": "اشتراک 1 ماهه (دو کاربره + 10 گیگ هدیه)", "price": "250,000 تومان"},
"2m_1u": {"name": "اشتراک 2 ماهه (تک کاربره + 10 گیگ هدیه)", "price": "380,000 تومان"},
"2m_2u": {"name": "اشتراک 2 ماهه (دو کاربره + 10 گیگ هدیه)", "price": "430,000 تومان"},
"3m_1u": {"name": "اشتراک 3 ماهه (تک کاربره + 10 گیگ هدیه)", "price": "550,000 تومان"},
"3m_2u": {"name": "اشتراک 3 ماهه (دو کاربره + 10 گیگ هدیه)", "price": "600,000 تومان"},
}

# ==================== توابع کمکی تقویم و مشخصات ====================
def generate_credentials(prefix="arshavin"):
rand_num = random. = State()
waiting_for_username = State()

class SupportState(StatesGroup):
waiting_for_username_and_msg = State()

# ==================== تعرفه‌ها ====================
PLANS = {
"1m_1u": {"name": "اشتراک 1 ماهه (تک کاربره + 10 گیگ هدیه)", "price": "200,000 تومان"},
"1m_2u": {"name": "اشتراک 1 ماهه (دو کاربره + 10 گیگ هدیه)", "price": "250,000 تومان"},
"2m_1u": {"name": "اشتراک 2 ماهه (تک کاربره + 10 گیگ هدیه)", "price": "380,000 تومان"},
"2m_2u": {"name": "اشتراک 2 ماهه (دو کاربره + 10 گیگ هدیه)", "price": "430,000 تومان"},
"3m_1u": {"name": "اشتراک 3 ماهه (تک کاربره + 10 گیگ هدیه)", "price": "550,000 تومان"},
"3m_2u": {"name": "اشتراک 3 ماهه (دو کاربره + 10 گیگ هدیه)", "price": "600,000 تومان"},
}

# ==================== توابع کمکی تقویم و مشخصات ====================
def generate_credentials(prefix="arshavin"):
rand_num = random.randint(1000, 9999)
chars = string.ascii_lowercase + string.digits
rand_pass = ''.join(random.choice(chars) for _ in range(6))
return f"{prefix}{rand_num}", rand_pass

def gregorian_to_jalali(gy, gm, gd):
g_d_m =gorian_to_jalali(now.year, now.month, now.day)
days_fa = {5: "شنبه", 6: "یک‌شنبه", 0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه"}
day_name = days_fa.get(now.weekday(), "")
date_str = f"{jy:04d}/{jm:02d}/{jd:02d}"
return date_str, time_str, day_name

def get_welcome_text(user: types.User):
date_str, time_str, day_name = get_persian_datetime()
return (
f"سلام <b>{user.first_name}</b> عزیز،\n"
f"به سامانه هوشمند و رسمی <b>L2TP VPN 24/7</b> خوش آمدید.\n\n"
f"📅 امروز: <b>{day_name} {date_str}</b>\n"
f"⏰ ساعت: <b>{time_str}</b>\n\n"
"لطفاً جهت استفاده از امکانات ربات، از منوی زیر گزینه‌ای را انتخاب فرمایید:"
)

# ==================== کیبوردها ====================
BTN_BACK = "🔙 برگشت به منوی اصلی"

def get_main_keyboard():
kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
kb.add(
KeyboardButton("🛒 خرید اشتراک"),
KeyboardButton("💰 شارژ حساب")
)
kb.add(
KeyboardButton("🌐 پنل کاربری IBSng"),
KeyboardButton("📊 اطلاعات حساب")
)
kb.add(
KeyboardButton("❓ سوالات متداول"),
KeyboardButton("👥 پشتیبانی")
)
return kb

def get_back_keyboard():
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(KeyboardButton(BTN_BACK))
return kb

def get_faq_keyboard():
ikb = InlineKeyboardMarkup(row_width=1)
ikb.add(
InlineKeyboardButton("📱 راهنمای اتصال آیفون و آیپد (iOS)", callback_data="faq_ios"),
InlineKeyboardButton("🤖 راهنمای اتصال گوشی‌های اندروید (Android)", callback_data="faq_android"),
InlineKeyboardButton("💻 راهنمای اتصال ویندوز (Windows 10/11)", callback_data="faq_windows"),
InlineKeyboardButton("📡 راهنمای ست کردن روی مودم و روتر", callback_data="faq_modem"),
InlineKeyboardButton("🌐 راهنمای ورود و کار با پنل IBSng", callback_data="faq_ibsng")
)
return ikb

# ==================== دستورات اصلی ====================
@dp.message_handler(commands=['start'], state="*")
@dp.message_handler(lambda m: m.text == BTN_BACK, state="*")
async def cmd_start(message: types.Message, state: FSMContext):
await state.finish()
add_user_to_db(message.from_user)

quick_kb = InlineKeyboardMarkup(row_width=2)
quick_kb.row(
InlineKeyboardButton("📢 کانال اطلاع‌رسانی", url=CHANNEL_URL),
InlineKeyboardButton("💬 پشتیبانی", url=SUPPORT_URL)
)

await message.reply(
get_welcome_text(message.from_user),
reply_markup=get_main_keyboard()
)
await message.answer("دسترسی‌های سریع:", reply_markup=quick_kb)

@dp.message_handler(commands=['stats'], state="*")
async def cmd_stats(message: types.Message):
if message.from_user.id != ADMIN_ID:
return
total_users = get_total_users_count()
date_str, time_str, _ = get_persian_datetime()
await message.reply(
f"📊 <b>آمار زنده ربات:</b>\n\n"
f"👥 تعداد کل کاربران ثبت‌شده: <b>{total_users:,} نفر</b>\n"
f"📅 تاریخ: <code>{date_str}</code> | ساعت: <code>{time_str}</code>"
)

# ==================== خرید اشتراک ====================
@dp.message_handler(lambda m: m.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
await state.finish()
kb = InlineKeyboardMarkup(row_width=1)
for p_id, info in PLANS.items():
kb.add(InlineKeyboardButton(f"🔹 {info['name']} — {info['price']}", callback_data=f"buy_{p_id}"))

caption = (
"🛍 <b>لیست تعرفه‌های رسمی اشتراک L2TP VPN 24/7</b>\n"
"🎁 <i>(تمامی پلن‌ها شامل 10 گیگابایت ترافیک هدیه هستند)</i>\n\n"
"🔹 <b>پلن‌های یک‌ماهه:</b>\n"
"▫️ یک‌ماهه تک‌کاربره: <b>200,000 تومان</b>\n"
"▫️ یک‌ماهه دو‌کاربره: <b>250,000 تومان</b>\n\n"
"🔹 <b>پلن‌های دو‌ماهه:</b>\n"
"▫️ دو‌ماهه تک‌کاربره: <b>380,000 تومان</b>\n"
"▫️ دو‌ماهه دو‌کاربره: <b>430,000 تومان</b>\n\n"
"🔹 <b>پلن‌های سه‌ماهه:</b>\n"
"▫️ سه‌ماهه تک‌کاربره: <b>550,000 تومان</b>\n"
"▫️ سه‌ماهه دو‌کاربره: <b>600,000 تومان</b>\n\n"
"👇 پلن مورد نظر خود را برای صدور فاکتور انتخاب نمایید:"
)
if os.path.exists(TARIFF_IMAGE_PATH):
await message.reply_photo(photo=InputFile(TARIFF_IMAGE_PATH), caption=caption, reply_markup=kb)
else:
await message.reply(caption, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"), state="*")
async def process_buy_callback(callback_query: types.CallbackQuery, state: FSMContext):
plan_id = callback_query.data.replace("buy_", "")
plan = PLANS.get(plan_id)
if not plan:
await callback_query.answer("پلن یافت نشد!", show_alert=True)
return

await state.update_data(chosen_plan=plan_id)
await OrderState.waiting_for_receipt.set()

caption = (
f"🛒 <b>پیش‌فاکتور خرید اشتراک</b>\n\n"
f"📦 پلن انتخابی: <b>{plan['name']}</b>\n"
f"💰 مبلغ قابل پرداخت: <b>{plan['price']}</b>\n\n"
f"💳 <b>شماره کارت جهت واریز:</b>\n<code>{CARD_NUMBER}</code>\n"
f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
"📸 لطفاً پس از واریز، <b>تصویر فیش واریزی</b> خود را ارسال نمایید:"
)

if os.path.exists(CARD_IMAGE_PATH):
await bot.send_photo(
chat_id=callback_query.from_user.id,
photo=InputFile(CARD_IMAGE_PATH),
caption=caption,
reply_markup=get_back_keyboard()
)
else:
await bot.send_message(
chat_id=callback_query.from_user.id,
text=caption,
reply_markup=get_back_keyboard()
)
await callback_query.answer()

@dp.message_handler(state=OrderState.waiting_for_receipt, content_types=types.ContentTypes.PHOTO)
async def process_order_receipt(message: types.Message, state: FSMContext):
data = await state.get_data()
plan_id = data.get("chosen_plan")
plan = PLANS.get(plan_id, {"name": "سرویس سفارشی", "price": "نامشخص"})
user = message.from_user
date_str, time_str, _ = get_persian_datetime()

admin_caption = (
"🔔 <b>فیش واریزی جدید جهت خرید اشتراک</b>\n\n"
f"👤 خریدار: <b>{user.full_name}</b>\n"
f"🆔 شناسه: <code>{user.id}</code>\n"
f"🔗 یوزرنیم: @{user.username or 'ندارد'}\n"
f"📦 پلن: <b>{plan['name']}</b>\n"
f"💰 مبلغ: <b>{plan['price']}</b>\n"
f"📅 تاریخ: <code>{date_str}</code> | ساعت: <code>{time_str}</code>"
)

admin_kb = InlineKeyboardMarkup(row_width=2)
admin_kb.row(
InlineKeyboardButton("✅ تأیید و ارسال اکانت", callback_data=f"adm_ok_{user.id}_{plan_id}"),
InlineKeyboardButton("❌ رد فیش", callback_data=f"adm_no_{user.id}")
)

try:
await bot.send_photo(
ADMIN_ID,
photo=message.photo[-1].file_id,
caption=admin_caption,
reply_markup=admin_kb
)
except Exception as e:
logging.error(f"Error sending order receipt to admin: {e}")

await message.reply(
"✅ <b>فیش واریزی شما با موفقیت برای مدیریت ارسال شد.</b>\n\n"
"پس از بررسی، مشخصات اتصال اختصاصی مستقیماً همین‌جا برای شما ارسال خواهد شد.",
reply_markup=get_main_keyboard()
)
await state.finish()

# ==================== تأیید و رد سفارش توسط ادمین ====================
@dp.callback_query_handler(lambda c: c.data.startswith("adm_ok_"), state="*")
async def approve_order_admin(callback_query: types.CallbackQuery):
if callback_query.from_user.id != ADMIN_ID:
await callback_query.answer("⛔️ شما ادمین نیستید.", show_alert=True)
return

parts = callback_query.data.split("_")
user_id = int(parts[2])
plan_id = "_".join(parts[3:])
plan = PLANS.get(plan_id, {"name": "سرویس ویژه"})

username, password = GAPGPTMASKTOKENgjlgj2jhxvkX2X

delivery_text = (
"🎉 <b>سفارش شما با موفقیت تأیید شد و اکانت فعال گردید!</b>\n\n"
f"📦 سرویس: <b>{plan['name']}</b>\n"
f"🌐 آدرس سرور (Server IP): <code>{VPN_SERVER_IP}</code>\n"
f"🔑 کلید امنیتی (IPsec Secret): <code>{IPSEC_SECRET}</code>\n"
f"👤 نام کاربری (Username): <code>{username}</code>\n"
f"🔒 رمز عبور (Password): <code>{password}</code>\n\n"
f"🌐 <b>پنل کاربری IBSng جهت مشاهده حجم و تغییر پسورد:</b>\n{IBSNG_PANEL_URL}\n\n"
"⚠️ <b>نکته مهم:</b> برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.\n"
"⚠️ <i>لطفاً پس از اولین ورود، رمز عبور خود را در پنل IBSng تغییر دهید.</i>\n\n"
f"💬 پشتیبانی: {SUPPORT_USERNAME}\n"
f"📢 کانال: @L2tp_vpn402"
)

try:
await bot.send_message(user_id, delivery_text)
await callback_query.message.reply(f"✅ اکانت برای کاربر <code>{user_id}</code> با موفقیت ارسال شد.")
await callback_query.message.edit_reply_markup(reply_markup=None)
except Exception as e:
await callback_query.answer(f"خطا در ارسال به کاربر: {e}", show_alert=True)

await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("adm_no_"), state="*")
async def reject_order_admin(callback_query: types.CallbackQuery):
if callback_query.from_user.id != ADMIN_ID:
await callback_query.answer("⛔️ شما ادمین نیستید.", show_alert=True)
return

user_id = int(callback_query.data.split("_")[2])
reject_text = (
"❌ <b>فیش واریزی ارسالی شما مورد تأیید قرار نگرفت.</b>\n\n"
"در صورتی که وجه از حسابتان کسر گردیده، لطفاً جهت پیگیری به پشتیبانی پیام دهید:\n"
f"💬 {SUPPORT_USERNAME}"
)

try:
await bot.send_message(user_id, reject_text)
await callback_query.message.reply(f"❌ فیش کاربر <code>{user_id}</code> رد شد.")
await callback_query.message.edit_reply_markup(reply_markup=None)
except Exception as e:
await callback_query.answer(f"خطا: {e}", show_alert=True)

await callback_query.answer()

# ==================== اطلاعات حساب ====================
@dp.message_handler(lambda m: m.text == "📊 اطلاعات حساب", state="*")
async def handle_account(message: types.Message, state: FSMContext):
await state.finish()
text = (
f"📊 <b>مشخصات حساب شما در سیستم:</b>\n\n"
f"👤 نام: <b>{message.from_user.full_name}</b>\n"
f"🆔 شناسه عددی تلگرام: <code>{message.from_user.id}</code>\n"
f"💎 وضعیت عضویت: <b>کاربر ثبت‌شده</b>\n\n"
"💡 جهت مشاهده دقیق تاریخ انقضا و مانده حجم، وارد <b>«🌐 پنل کاربری IBSng»</b> شوید."
)
await message.reply(text, reply_markup=get_main_keyboard())

# ==================== پنل کاربری IBSng ====================
@dp.message_handler(lambda m: m.text == "🌐 پنل کاربری IBSng", state="*")
async def handle_ibsng_panel(message: types.Message, state: FSMContext):
await state.finish()
ikb = InlineKeyboardMarkup(row_width=1)
ikb.add(InlineKeyboardButton("🔗 ورود مستقیم به پنل کاربری IBSng", url=IBSNG_PANEL_URL))

text = (
"🌐 <b>سامانه اختصاصی مشاهده وضعیت و مدیریت اکانت IBSng</b>\n\n"
f"🔗 <b>لینک ورود به پنل:</b>\n{IBSNG_PANEL_URL}\n\n"
"⚠️ <b>نکته مهم:</b> برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از اتمام دوباره روشن کنید.\n\n"
"⚠️ <b>نکته بسیار مهم امنیتی:</b>\n"
"<b>«حتماً و الزاماً در اولین ورود به پنل کاربری، رمز عبور (پسورد) خود را تغییر دهید تا از هرگونه سوءاستفاده جلوگیری شود.»</b>\n\n"
"▫️ مشاهده مانده حجم دقیق و ترافیک مصرفی\n"
"▫️ مشاهده تاریخ انقضای دقیق اشتراک\n"
"▫️ امکان تغییر پسورد اکانت اتصال"
)
await message.reply(text, reply_markup=ikb)

# ==================== شارژ حساب ====================
@dp.message_handler(lambda m: m.text == "💰 شارژ حساب", state="*")
async def handle_charge(message: types.Message, state: FSMContext):
await state.finish()
await ChargeState.waiting_for_receipt.set()

caption = (
"💰 <b>شارژ و تمدید حساب کاربری</b>\n\n"
"📋 <b>تعرفه‌های رسمی تمدید و شارژ (شامل 10 گیگ هدیه):</b>\n"
"▫️ 1 ماهه تک کاربره: <b>200,000 تومان</b>\n"
"▫️ 1 ماهه دو کاربره: <b>250,000 تومان</b>\n"
"▫️ 2 ماهه تک کاربره: <b>380,000 تومان</b>\n"
"▫️ 2 ماهه دو کاربره: <b>430,000 تومان</b>\n"
"▫️ 3 ماهه تک کاربره: <b>550,000 تومان</b>\n"
"▫️ 3 ماهه دو کاربره: <b>600,000 تومان</b>\n\n"
f"💳 شماره کارت جهت واریز:\n<code>{CARD_NUMBER}</code>\n"
f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
"📸 لطفاً ابتدا مبلغ مورد نظر را واریز نموده و <b>تصویر فیش واریزی</b> را همین‌جا ارسال نمایید:"
)
if os.path.exists(CARD_IMAGE_PATH):
await message.reply_photo(photo=InputFile(CARD_IMAGE_PATH), caption=caption, reply_markup=get_back_keyboard())
else:
await message.reply(caption, reply_markup=get_back_keyboard())

@dp.message_handler(state=ChargeState.waiting_for_receipt, content_types=types.ContentTypes.PHOTO)
async def process_charge_receipt(message: types.Message, state: FSMContext):
await state.update_data(charge_receipt_id=message.photo[-1].file_id)
await ChargeState.waiting_for_username.set()
await message.reply(
"✍️ فیش دریافت شد. حالا لطفاً <b>نام کاربری (یوزرنیم)</b> اکانت فعلی خود را ارسال کنید تا شارژ روی همان اکانت اعمال شود:"
)

@dp.message_handler(state=ChargeState.waiting_for_username, content_types=types.ContentTypes.TEXT)
async def process_charge_username(message: types.Message, state: FSMContext):
data = await state.get_data()
receipt_file_id = data.get("charge_receipt_id")
account_username = message.text.strip()
user = message.from_user
date_str, time_str, _ = get_persian_datetime()

admin_caption = (
"🔄 <b>درخواست تمدید و شارژ اکانت</b>\n\n"
f"👤 کاربر: <b>{user.full_name}</b>\n"
f"🆔 شناسه: <code>{user.id}</code>\n"
f"🔗 یوزرنیم تلگرام: @{user.username or 'ندارد'}\n"
f"👤 <b>اکانت جهت شارژ:</b> <code>{account_username}</code>\n"
f"📅 تاریخ: <code>{date_str}</code> | ساعت: <code>{time_str}</code>"
)

try:
await bot.send_photo(ADMIN_ID, photo=receipt_file_id, caption=admin_caption)
except Exception as e:
logging.error(f"Error sending charge alert to admin: {e}")

await message.reply(
f"✅ <b>درخواست تمدید برای اکانت «{account_username}» ثبت گردید.</b>\n"
"پس از بررسی و اعمال شارژ در پنل، اکانت شما به‌صورت خودکار تمدید می‌گردد.",
reply_markup=get_main_keyboard()
)
await state.finish()

# ==================== پشتیبانی ====================
@dp.message_handler(lambda m: m.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message, state: FSMContext):
await state.finish()
await SupportState.waiting_for_username_and_msg.set()

ikb = InlineKeyboardMarkup(row_width=1)
ikb.add(InlineKeyboardButton("💬 پیام مستقیم به پشتیبان تلگرام", url=SUPPORT_URL))

text = (
"👥 <b>پشتیبانی آنلاین و هوشمند L2TP VPN 24/7</b>\n\n"
"✍️ <b>لطفاً نام کاربری (یوزرنیم) اکانت وی‌پی‌ان خود را به همراه شرح مشکل یا درخواستتان در یک پیام ارسال کنید تا برای بررسی ارجاع شود:</b>\n\n"
f"💬 آیدی مستقیم ادمین: {SUPPORT_USERNAME}\n"
f"📢 کانال رسمی: @L2tp_vpn402"
)
await message.reply(text, reply_markup=get_back_keyboard())
await message.answer("ارتباط از طریق تلگرام:", reply_markup=ikb)

@dp.message_handler(state=SupportState.waiting_for_username_and_msg, content_types=types.ContentTypes.ANY)
async def process_support_input(message: types.Message, state: FSMContext):
user = message.from_user
user_text = message.text or message.caption or "ارسال فایل/تصویر بدون متن"

admin_alert = (
"🚨 <b>درخواست پشتیبانی و بررسی اکانت</b>\n\n"
f"👤 فرستنده: <b>{user.full_name}</b>\n"
f"🆔 شناسه: <code>{user.id}</code>\n"
f"🔗 یوزرنیم تلگرام: @{user.username or 'ندارد'}\n\n"
f"📝 <b>متن / یوزرنیم ارسالی کاربر:</b>\n{user_text}"
)

if ADMIN_ID != 0:
try:
if message.photo:
await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=admin_alert)
else:
await bot.send_message(ADMIN_ID, admin_alert)
except Exception as e:
logging.error(f"Error alerting admin: {e}")

await message.reply(
"✅ <b>پشتیبانی درخواست شما را با موفقیت تحویل گرفت.</b>\n\n"
"اطلاعات اکانت و پیام شما برای اپراتور ارسال شد و در سریع‌ترین زمان ممکن بررسی و پاسخ داده خواهد شد.\n\n"
f"💬 پیگیری مستقیم: {SUPPORT_USERNAME}",
reply_markup=get_main_keyboard()
)
await state.finish()

# ==================== سوالات متداول و راهنمای جامع اتصال ====================
@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message, state: FSMContext):
await state.finish()
text = (
"❓ <b>مرکز راهنما و سوالات متداول مشترکین L2TP VPN 24/7</b>\n\n"
"⚡️ <b>مشخصات عمومی سرور:</b>\n"
f"▫️ آدرس سرور (Server Address): <code>{VPN_SERVER_IP}</code>\n"
f"▫️ کلید امنیتی (IPsec Secret / Pre-Shared Key): <code>{IPSEC_SECRET}</code>\n\n"
"👇 لطفاً دستگاه یا بخش مورد نظر خود را از دکمه‌های زیر انتخاب فرمایید تا راهنمای کامل و تصویری نمایش داده شود:"
)
await message.reply(text, reply_markup=get_faq_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("faq_"), state="*")
async def handle_faq_callbacks(callback_query: types.CallbackQuery):
action = callback_query.data

if action == "faq_ios":
caption = (
"📱 <b>راهنمای اتصال در آیفون و آیپد (Apple iOS):</b>\n\n"
"1. وارد <b>Settings</b> گوشی شوید.\n"
"2. به مسیر <b>General ⬅️ VPN & Device Management ⬅️ VPN</b> بروید.\n"
"3. گزینه <b>Add VPN Configuration</b> را لمس کنید.\n"
"4. بخش <b>Type</b> را روی <b>L2TP</b> تنظیم کنید.\n"
f"5. در کادر <b>Server</b> مقدار <code>{VPN_SERVER_IP}</code> را وارد کنید.\n"
"6. در کادر <b>Account</b> نام کاربری و در <b>Password</b> رمز عبور خود را وارد کنید.\n"
f"7. در کادر <b>Secret</b> کلید <code>{IPSEC_SECRET}</code> را وارد کرده و Done را بزنید."
)
if os.path.exists(IOS_ANDROID_IMAGE_PATH):
await bot.send_photo(callback_query.from_user.id, photo=InputFile(IOS_ANDROID_IMAGE_PATH), caption=caption)
else:
await bot.send_message(callback_query.from_user.id, text=caption)

elif action == "faq_android":
caption = (
"🤖 <b>راهنمای اتصال در گوشی‌های اندروید (Android):</b>\n\n"
"1. وارد تنظیمات (Settings) گوشی شوید.\n"
"2. به بخش <b>اتصالات (Connections) ⬅️ تنظیمات بیشتر ⬅️ VPN</b> بروید.\n"
"3. علامت + یا سه نقطه را زده و <b>Add VPN Profile</b> را انتخاب کنید.\n"
"4. بخش <b>Type</b> را روی <b>L2TP/IPSec PSK</b> قرار دهید.\n"
f"5. در کادر <b>Server address</b> مقدار <code>{VPN_SERVER_IP}</code> را بنویسید.\n"
f"6. در کادر <b>IPSec pre-shared key</b> کلید <code>{IPSEC_SECRET}</code> را وارد کنید.\n"
"7. پروفایل را ذخیره کرده و هنگام اتصال نام کاربری و پسورد خود را بزنید."
)
if os.path.exists(IOS_ANDROID_IMAGE_PATH):
await bot.send_photo(callback_query.from_user.id, photo=InputFile(IOS_ANDROID_IMAGE_PATH), caption=caption)
else:
await bot.send_message(callback_query.from_user.id, text=caption)

elif action == "faq_windows":
caption = (
"💻 <b>راهنمای اتصال در ویندوز (Windows 10 / 11):</b>\n\n"
"1. وارد <b>Settings ⬅️ Network & Internet ⬅️ VPN</b> شوید.\n"
"2. روی <b>Add a VPN connection</b> کلیک کنید.\n"
"3. VPN provider را روی Windows (built-in) بگذارید.\n"
"4. VPN type را روی <b>L2TP/IPsec with pre-shared key</b> تنظیم کنید.\n"
f"5. در Server name or address مقدار <code>{VPN_SERVER_IP}</code> را وارد کنید.\n"
f"6. در Pre-shared key مقدار <code>{IPSEC_SECRET}</code> را بنویسید.\n"
"7. یوزرنیم و پسورد اکانت را وارد کرده و Save را بزنید."
)
if os.path.exists(MODEM_LAPTOP_IMAGE_PATH):
await bot.send_photo(callback_query.from_user.id, photo=InputFile(MODEM_LAPTOP_IMAGE_PATH), caption=caption)
else:
await bot.send_message(callback_query.from_user.id, text=caption)

elif action == "faq_modem":
caption = (
"📡 <b>راهنمای تنظیم سرویس روی مودم و روتر:</b>\n\n"
"1. وارد صفحه تنظیمات مودم/روتر (192.168.1.1 یا 192.168.8.1) شوید.\n"
"2. به بخش <b>VPN</b> یا <b>VPN Client</b> مراجعه کنید.\n"
"3. پروتکل را روی <b>L2TP</b> قرار دهید.\n"
f"4. آدرس سرور (LNS / Server) را <code>{VPN_SERVER_IP}</code> وارد کنید.\n"
"5. نام کاربری و پسورد اکانت خود را درج نمایید.\n"
"6. وضعیت اتصال را روی Auto-Connect گذاشته و Apply/Save نمایید."
)
if os.path.exists(MODEM_LAPTOP_IMAGE_PATH):
await bot.send_photo(callback_query.from_user.id, photo=InputFile(MODEM_LAPTOP_IMAGE_PATH), caption=caption)
else:
await bot.send_message(callback_query.from_user.id, text=caption)

elif action == "faq_ibsng":
text = (
"🌐 <b>راهنمای پنل کاربری IBSng:</b>\n\n"
f"🔗 لینک پنل: {IBSNG_PANEL_URL}\n\n"
"⚠️ <b>نکته مهم:</b> برای ارتباط بهتر با پنل حتماً وی‌پی‌ان خود را خاموش کنید.\n"
"▫️ با نام کاربری و رمزی که بعد از خرید دریافت کرده‌اید وارد شوید.\n"
"▫️ در صفحه اول مانده حجم دقیق و اعتبار زمانی نمایش داده می‌شود.\n"
"▫️ از منوی تنظیمات می‌توانید پسورد اتصال خود را در هر لحظه تغییر دهید."
)
await bot.send_message(callback_query.from_user.id, text=text)

await callback_query.answer()

# ==================== وب‌سرور جهت زنده نگه داشتن در پنل Render ====================
async def handle_ping(request):
return web.Response(text="L2TP VPN Bot is Alive & Running 24/7!")

async def start_web_server():
port = int(os.getenv("PORT", 10000))
app = web.Application()
app.router.add_get("/", handle_ping)
app.router.add_get("/healthz", handle_ping)
runner = web.AppRunner(app)
await runner.setup()
site = web.TCPSite(runner, "0.0.0.0", port)
await site.start()
logging.info(f"Web server started on port {port}")

# ==================== نقطه ورود اصلی برنامه ====================
async def main():
await start_web_server()
await dp.start_polling()

if __name__ == "__main__":
asyncio.run(main())


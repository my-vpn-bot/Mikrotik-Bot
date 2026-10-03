import asyncio
from datetime import datetime
import logging
import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiohttp import web
import pytz

# ==================== تنظیمات و لاگ ====================
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENtd3q3cr87X0X").strip()

# مدیریت و استخراج صحیح ID ادمین
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "02786850266").strip()
clean_admin_id = ADMIN_ID_RAW.lstrip("0")
ADMIN_ID = int(clean_admin_id) if clean_admin_id.isdigit() else 2786850266

SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()
IBSNG_PANEL_URL = os.getenv(
    "IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/"
).strip()
OPENVPN_FILE_PATH = os.getenv(
    "OPENVPN_FILE_PATH", "files/openvpn/client.ovpn"
).strip()

# آدرس سرور L2TP VPN و کلید پیش‌فرض IPsec
VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "GAPGPTMASKTOKENtd3q3cr87X1X"

CARD_IMAGE_PATH = "شماره کارت1.jpg"
TARIFF_IMAGE_PATH = "تعرفه.jpg"

# ساختار ربات
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== دیتابیس SQLite ====================
DB_FILE = "bot_users.db"


def init_db():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("""CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    join_date TEXT
                )""")
  # جدول گزارش‌گیری سفارشات و خریدهای روزانه
  c.execute("""CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    plan_name TEXT,
                    amount_toman INTEGER,
                    order_date TEXT
                )""")
  conn.commit()
  conn.close()


def add_user_to_db(user: types.User):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  date_str, _, _ = get_persian_datetime()
  c.execute(
      "INSERT OR IGNORE INTO users (user_id, full_name, username, join_date)"
      " VALUES (?, ?, ?, ?)",
      (user.id, user.full_name or "", user.username or "", date_str),
  )
  conn.commit()
  conn.close()


def record_order_in_db(user_id: int, plan_name: str, price_str: str):
  """ثبت خرید کاربر جهت آمارگیری روزانه"""
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  date_str, _, _ = get_persian_datetime()

  amount = 0
  try:
    clean_price = price_str.replace("تومان", "").replace(",", "").strip()
    amount = int("".join(filter(str.isdigit, clean_price)))
  except Exception:
    amount = 0

  c.execute(
      "INSERT INTO orders (user_id, plan_name, amount_toman, order_date) VALUES"
      " (?, ?, ?, ?)",
      (user_id, plan_name, amount, date_str),
  )
  conn.commit()
  conn.close()


def get_daily_sales_report():
  """محاسبه خروجی و درآمد امروز"""
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  date_str, _, _ = get_persian_datetime()

  c.execute(
      "SELECT COUNT(*), SUM(amount_toman) FROM orders WHERE order_date = ?",
      (date_str,),
  )
  row = c.fetchone()
  conn.close()

  count = row[0] if row and row[0] else 0
  total_sum = row[1] if row and row[1] else 0
  return count, total_sum


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


# ==================== تعرفه‌های رسمی جدید (با قید حجم دقیق و هدیه) ====================
PLANS = {
    "vip_1u": {
        "name": "⭐ اشتراک VIP تک کاربره ترافیک نامحدود (پیشنهادی ما) سرور پرسرعت آلمان",
        "price": "350,000 تومان",
    },
    "1m_1u": {
        "name": "اشتراک 1 ماهه تک کاربره (30 گیگ + 10 گیگ هدیه) سرور آلمان",
        "price": "200,000 تومان",
    },
    "1m_2u": {
        "name": "اشتراک 1 ماهه دو کاربره (30 گیگ + 10 گیگ هدیه) سرور آلمان",
        "price": "250,000 تومان",
    },
    "2m_1u": {
        "name": "اشتراک 2 ماهه تک کاربره (60 گیگ + 10 گیگ هدیه) سرور آلمان",
        "price": "380,000 تومان",
    },
    "2m_2u": {
        "name": "اشتراک 2 ماهه دو کاربره (60 گیگ + 10 گیگ هدیه) سرور آلمان",
        "price": "430,000 تومان",
    },
    "3m_1u": {
        "name": "اشتراک 3 ماهه تک کاربره (90 گیگ + 10 گیگ هدیه) سرور آلمان",
        "price": "550,000 تومان",
    },
    "3m_2u": {
        "name": "اشتراک 3 ماهه دو کاربره (90 گیگ + 10 گیگ هدیه) سرور آلمان",
        "price": "600,000 تومان",
    },
}


# ==================== تاریخ شمسی ====================
def gregorian_to_jalali(gy, gm, gd):
  g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
  jy = 0 if gy <= 1600 else 979
  gy -= 621 if gy <= 1600 else 1600
  gy2 = gy + 1 if gm > 2 else gy
  days = (
      (365 * gy)
      + ((gy2 + 3) // 4)
      - ((gy2 + 99) // 100)
      + ((gy2 + 399) // 400)
      - 80
      + gd
      + g_d_m[gm - 1]
  )
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


def get_persian_datetime():
  tehran_tz = pytz.timezone("Asia/Tehran")
  now = datetime.now(tehran_tz)
  time_str = now.strftime("%H:%M:%S")
  jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
  days_fa = {
      5: "شنبه",
      6: "یک‌شنبه",
      0: "دوشنبه",
      1: "سه‌شنبه",
      2: "چهارشنبه",
      3: "پنج‌شنبه",
      4: "جمعه",
  }
  day_name = days_fa.get(now.weekday(), "")
  date_str = f"{jy}/{jm:02d}/{jd:02d}"
  return date_str, time_str, day_name


# ==================== کیبوردها ====================
BTN_BACK = "🔙 برگشت به منوی اصلی"


def get_main_keyboard():
  kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  kb.add(KeyboardButton("🛒 خرید اشتراک"))
  kb.add(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("🌐 پنل کاربری IBSng"))
  kb.add(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
  kb.add(
      KeyboardButton("❓ سوالات متداول"),
      KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"),
  )
  return kb


def get_back_keyboard():
  kb = ReplyKeyboardMarkup(resize_keyboard=True)
  kb.add(KeyboardButton(BTN_BACK))
  return kb


def get_welcome_text(user):
  date_str, time_str, day_name = get_persian_datetime()
  return (
      f"سلام <b>{user.first_name}</b> عزیز، خیلی خوش آمدید! 🌹\n\n"
      f"📅 <b>روز:</b> {day_name}\n"
      f"📆 <b>تاریخ:</b> <code>{date_str}</code> | ⏰ <b>ساعت:</b>"
      f" <code>{time_str}</code>\n"
      f"🆔 شناسه کاربری: <code>{user.id}</code>\n\n"
      "🇩🇪 <b>سرورهای اختصاصی، پرسرعت و پایدار آلمان L2TP VPN 24/7:</b>\n"
      "▫️ پروتکل امن <b>L2TP / IPSec</b> (بدون نیاز به نرم‌افزار جانبی)\n"
      "▫️ پروتکل‌های <b>OpenVPN</b> و <b>PPTP</b> سازگار با انواع سیستم‌عامل‌ها و"
      " مودم‌ها\n"
      "🎁 <b>10 گیگابایت ترافیک هدیه</b> روی تمامی پلن‌های جدید\n\n"
      "👇 جهت استفاده از امکانات، یکی از گزینه‌های منوی زیر را انتخاب نمایید:"
  )


# ==================== هندلرهای عمومی ====================
@dp.message_handler(lambda m: m.text == BTN_BACK, state="*")
async def process_global_back(message: types.Message, state: FSMContext):
  await state.finish()
  await message.reply(
      "به منوی اصلی بازگشتید 👇", reply_markup=get_main_keyboard()
  )


@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
  await state.finish()
  add_user_to_db(message.from_user)

  quick_kb = InlineKeyboardMarkup(row_width=2)
  quick_kb.row(
      InlineKeyboardButton("📢 کانال اطلاع‌رسانی", url=CHANNEL_URL),
      InlineKeyboardButton("💬 پشتیبانی", url=SUPPORT_URL),
  )

  await message.reply(
      get_welcome_text(message.from_user), reply_markup=get_main_keyboard()
  )
  await message.answer("دسترسی‌های سریع:", reply_markup=quick_kb)


# گزارش فروش روزانه برای ادمین
@dp.message_handler(commands=["report"], state="*")
async def cmd_report(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  date_str, time_str, _ = get_persian_datetime()
  count, total_sales = get_daily_sales_report()

  report_text = (
      f"📈 <b>گزارش فروش و خروجی امروز ({date_str}):</b>\n\n"
      f"🛒 تعداد سفارشات ثبت‌شده امروز: <b>{count:,} عدد</b>\n"
      f"💰 مجموع خروجی و فروش امروز: <b>{total_sales:,} تومان</b>\n\n"
      f"⏰ زمان گزارش‌گیری: <code>{time_str}</code>"
  )
  await message.reply(report_text)


@dp.message_handler(commands=["stats"], state="*")
async def cmd_stats(message: types.Message):
  if message.from_user.id != ADMIN_ID:
    return
  total_users = get_total_users_count()
  date_str, time_str, _ = get_persian_datetime()
  await message.reply(
      "📊 <b>آمار زنده ربات:</b>\n\n"
      f"👥 تعداد کل کاربران ثبت‌شده: <b>{total_users:,} نفر</b>\n"
      f"📅 تاریخ: <code>{date_str}</code> | ساعت: <code>{time_str}</code>"
  )


# ==================== خرید اشتراک ====================
@dp.message_handler(lambda m: m.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
  await state.finish()
  kb = InlineKeyboardMarkup(row_width=1)
  for p_id, info in PLANS.items():
    kb.add(
        InlineKeyboardButton(
            f"🔹 {info['name']} — {info['price']}", callback_data=f"buy_{p_id}"
        )
    )

  caption = (
      "🛒 <b>خرید اشتراک L2TP VPN 24/7 (سرور پرسرعت آلمان 🇩🇪)</b>\n\n"
      "👇 <b>لطفاً پلن مورد نظر خود را از دکمه‌های زیر انتخاب نمایید:</b>"
  )
  if os.path.exists(TARIFF_IMAGE_PATH):
    await message.reply_photo(
        photo=InputFile(TARIFF_IMAGE_PATH), caption=caption, reply_markup=kb
    )
  else:
    await message.reply(caption, reply_markup=kb)


# ==================== اطلاعات حساب ====================
@dp.message_handler(lambda m: m.text == "📊 اطلاعات حساب", state="*")
async def handle_account(message: types.Message, state: FSMContext):
  await state.finish()
  text = (
      "📊 <b>مشخصات حساب شما در سیستم:</b>\n\n"
      f"👤 نام: <b>{message.from_user.full_name}</b>\n"
      f"🆔 شناسه عددی تلگرام: <code>{message.from_user.id}</code>\n"
      "💎 وضعیت عضویت: <b>کاربر ثبت‌شده</b>\n\n"
      "💡 جهت مشاهده دقیق تاریخ انقضا و مانده حجم، وارد <b>«🌐 پنل کاربری"
      " IBSng»</b> شوید."
  )
  await message.reply(text, reply_markup=get_main_keyboard())


# ==================== پنل کاربری IBSng ====================
@dp.message_handler(lambda m: m.text == "🌐 پنل کاربری IBSng", state="*")
async def handle_ibsng_panel(message: types.Message, state: FSMContext):
  await state.finish()
  ikb = InlineKeyboardMarkup(row_width=1)
  ikb.add(
      InlineKeyboardButton(
          "🔗 ورود مستقیم به پنل کاربری IBSng", url=IBSNG_PANEL_URL
      )
  )

  text = (
      "🌐 <b>سامانه اختصاصی مشاهده وضعیت و مدیریت اکانت IBSng</b>\n\n"
      f"🔗 <b>لینک ورود به پنل:</b>\n{IBSNG_PANEL_URL}\n\n"
      "💡 <b>برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید و بعد از"
      " اتمام دوباره روشن کنید.</b>\n\n"
      "⚠️ <b>نکته مهم امنیتی:</b>\n"
      "<b>«حتماً و الزاماً در اولین ورود به پنل کاربری، کلمه عبور (پسورد) خود را"
      " تغییر دهید تا از هرگونه سوءاستفاده جلوگیری شود.»</b>\n\n"
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
      "💰 <b>شارژ و تمدید حساب کاربری (سرور پرسرعت آلمان 🇩🇪)</b>\n\n"
      f"💳 شماره کارت جهت واریز:\n<code>{CARD_NUMBER}</code>\n"
      f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
      "📸 لطفاً مبلغ اشتراک را واریز نموده و <b>تصویر فیش واریزی</b> را همین‌جا"
      " ارسال نمایید:"
  )
  if os.path.exists(CARD_IMAGE_PATH):
    await message.reply_photo(
        photo=InputFile(CARD_IMAGE_PATH),
        caption=caption,
        reply_markup=get_back_keyboard(),
    )
  else:
    await message.reply(caption, reply_markup=get_back_keyboard())


# ==================== پشتیبانی ====================
@dp.message_handler(lambda m: m.text == "👥 پشتیبانی", state="*")
async def handle_support(message: types.Message, state: FSMContext):
  await state.finish()
  await SupportState.waiting_for_username_and_msg.set()

  ikb = InlineKeyboardMarkup(row_width=1)
  ikb.add(
      InlineKeyboardButton("💬 پیام مستقیم به پشتیبان تلگرام", url=SUPPORT_URL)
  )

  text = (
      "👥 <b>پشتیبانی آنلاین و هوشمند L2TP VPN 24/7</b>\n\n"
      "✍️ <b>لطفاً نام کاربری (یوزرنیم) اکانت وی‌پی‌ان خود را به همراه شرح مشکل"
      " یا درخواستتان در یک پیام ارسال کنید تا برای بررسی ارجاع شود:</b>\n\n"
      f"💬 آیدی مستقیم ادمین: {SUPPORT_USERNAME}\n"
      "📢 کانال رسمی: @L2tp_vpn402"
  )
  await message.reply(text, reply_markup=get_back_keyboard())
  await message.answer("ارتباط از طریق تلگرام:", reply_markup=ikb)


@dp.message_handler(
    state=SupportState.waiting_for_username_and_msg,
    content_types=types.ContentTypes.ANY,
)
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
        await bot.send_photo(
            ADMIN_ID, message.photo[-1].file_id, caption=admin_alert
        )
      else:
        await bot.send_message(ADMIN_ID, admin_alert)
    except Exception as e:
      logging.error(f"Error alerting admin: {e}")

  await message.reply(
      "✅ <b>پشتیبانی درخواست شما را با موفقیت تحویل گرفت.</b>\n\n"
      "اطلاعات اکانت و پیام شما برای اپراتور ارسال شد و در سریع‌ترین زمان ممکن"
      " بررسی و پاسخ داده خواهد شد.\n\n"
      f"💬 پیگیری مستقیم: {SUPPORT_USERNAME}",
      reply_markup=get_main_keyboard(),
  )
  await state.finish()


# ==================== سوالات متداول شیشه‌ای (Inline FAQ) ====================
def get_faq_main_kb():
  ikb = InlineKeyboardMarkup(row_width=2)
  ikb.row(
      InlineKeyboardButton("📱 آیفون و آیپد (iOS)", callback_data="faq_ios"),
      InlineKeyboardButton("🤖 اندروید (Android)", callback_data="faq_android"),
  )
  ikb.row(
      InlineKeyboardButton("💻 ویندوز (Windows)", callback_data="faq_windows"),
      InlineKeyboardButton("🍏 مک‌بوک (macOS)", callback_data="faq_mac"),
  )
  ikb.row(
      InlineKeyboardButton("📶 مودم و روتر", callback_data="faq_router"),
      InlineKeyboardButton(
          "🛡 آموزش و دانلود OpenVPN", callback_data="faq_openvpn"
      ),
  )
  return ikb


def get_faq_sub_kb():
  ikb = InlineKeyboardMarkup(row_width=1)
  ikb.add(
      InlineKeyboardButton(
          "🔙 بازگشت به منوی سوالات متداول", callback_data="faq_home"
      )
  )
  return ikb


def get_openvpn_kb():
  ikb = InlineKeyboardMarkup(row_width=1)
  ikb.add(
      InlineKeyboardButton(
          "📥 دانلود مستقیم فایل کانفیگ (client.ovpn)",
          callback_data="dl_openvpn",
      )
  )
  ikb.add(
      InlineKeyboardButton(
          "🔙 بازگشت به منوی سوالات متداول", callback_data="faq_home"
      )
  )
  return ikb


FAQ_MAIN_TEXT = (
    "❓ <b>پاسخ به سوالات متداول و راهنمای جامع اتصال L2TP/IPSec</b>\n\n"
    "⚡️ <b>مشخصات عمومی سرور:</b>\n"
    f"▫️ آدرس سرور (Server Address): <code>{VPN_SERVER_IP}</code>\n"
    "▫️ کلید امنیتی (IPsec Secret / Pre-Shared Key):"
    f" <code>{IPSEC_SECRET}</code>\n\n"
    "👇 <b>سیستم‌عامل یا موضوع مورد نظر خود را انتخاب نمایید:</b>"
)


@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message, state: FSMContext):
  await state.finish()
  await message.reply(FAQ_MAIN_TEXT, reply_markup=get_faq_main_kb())


@dp.callback_query_handler(lambda c: c.data.startswith("faq_"), state="*")
async def callback_faq_navigation(query: types.CallbackQuery):
  action = query.data.replace("faq_", "")

  if action == "home":
    await query.message.edit_text(FAQ_MAIN_TEXT, reply_markup=get_faq_main_kb())
    await query.answer()
    return

  text = ""
  reply_markup = get_faq_sub_kb()

  if action == "ios":
    text = (
        "📱 <b>راهنمای اتصال در آیفون و آیپد (Apple iOS):</b>\n\n"
        "1. وارد Settings ⬅️ General ⬅️ VPN & Device Management ⬅️ VPN شوید.\n"
        "2. گزینه <b>Add VPN Configuration</b> را لمس کنید.\n"
        "3. نوع (Type) را روی <b>L2TP</b> قرار دهید.\n"
        f"4. در بخش Server آدرس <code>{VPN_SERVER_IP}</code> را وارد کنید.\n"
        "5. نام کاربری (Account) و کلمه عبور (Password) خود را وارد کنید.\n"
        f"6. در کادر Secret مقدار <code>{IPSEC_SECRET}</code> را وارد و Save را"
        " بزنید."
    )
  elif action == "android":
    text = (
        "🤖 <b>راهنمای اتصال در اندروید (Android):</b>\n\n"
        "1. وارد تنظیمات گوشی ⬅️ اتصالات (Connections) ⬅️ تنظیمات بیشتر ⬅️ VPN"
        " شوید.\n"
        "2. علامت + یا سه نقطه بالا را زده و <b>Add VPN Profile</b> را انتخاب"
        " کنید.\n"
        "3. نوع (Type) را روی <b>L2TP/IPSec PSK</b> قرار دهید.\n"
        f"4. در Server address آدرس <code>{VPN_SERVER_IP}</code> را بنویسید.\n"
        f"5. در کادر IPSec pre-shared key مقدار <code>{IPSEC_SECRET}</code> را"
        " وارد کنید.\n"
        "6. ذخیره کرده و هنگام اتصال یوزرنیم و پسورد خود را بزنید."
    )
  elif action == "windows":
    text = (
        "💻 <b>راهنمای اتصال در ویندوز (Windows 10 / 11):</b>\n\n"
        "1. وارد Settings ⬅️ Network & Internet ⬅️ VPN شده و Add VPN را"
        " بزنید.\n"
        "2. VPN Provider را روی <b>Windows (built-in)</b> بگذارید.\n"
        "3. VPN Type را روی <b>L2TP/IPsec with pre-shared key</b> تنظیم"
        " کنید.\n"
        f"4. در Server name or address مقدار <code>{VPN_SERVER_IP}</code> را"
        " وارد کنید.\n"
        f"5. در Pre-shared key مقدار <code>{IPSEC_SECRET}</code> را بنویسید.\n"
        "6. یوزرنیم و پسورد اکانت را وارد کرده و Save و Connect را بزنید."
    )
  elif action == "mac":
    text = (
        "🍏 <b>راهنمای اتصال در مک‌بوک (macOS):</b>\n\n"
        "1. وارد System Settings ⬅️ Network شوید.\n"
        "2. روی علامت سه نقطه/افزودن کلیک کرده و Add VPN Configuration ⬅️"
        " <b>L2TP over IPSec</b> را انتخاب کنید.\n"
        f"3. در Server Address مقدار <code>{VPN_SERVER_IP}</code> را وارد"
        " کنید.\n"
        "4. Account Name را یوزرنیم خود وارد کرده و در Authentication"
        " Settings:\n"
        "   - Password: کلمه عبور شما\n"
        f"   - Shared Secret: مقدار <code>{IPSEC_SECRET}</code>\n"
        "5. Apply را زده و متصل شوید."
    )
  elif action == "router":
    text = (
        "📶 <b>راهنمای تنظیم روی انواع مودم و روتر (Router / Modem):</b>\n\n"
        "1. وارد پنل وب مودم (معمولاً 192.168.1.1 یا 192.168.8.1) شوید.\n"
        "2. به منوی VPN ⬅️ L2TP Client بروید.\n"
        "3. وضعیت را Enabled کرده، Protocol را روی L2TP قرار دهید.\n"
        f"4. در فیلد LNS Address / Server آدرس <code>{VPN_SERVER_IP}</code> را"
        " وارد کنید.\n"
        "5. یوزرنیم و پسورد اکانت را وارد کرده و ذخیره نمایید."
    )
  elif action == "openvpn":
    text = (
        "🛡 <b>راهنما و فایل کانفیگ OpenVPN:</b>\n\n"
        "1. برنامه <b>OpenVPN Connect</b> را از استور گوشی یا سایت رسمی نصب"
        " کنید.\n"
        "2. روی دکمه زیر کلیک کرده و فایل کانفیگ رسمی <code>client.ovpn</code>"
        " را دانلود کنید.\n"
        "3. فایل را در برنامه OpenVPN وارد (Import) نمایید.\n"
        "4. یوزرنیم و پسورد اکانت خود را وارد کرده و متصل شوید."
    )
    reply_markup = get_openvpn_kb()

  await query.message.edit_text(text, reply_markup=reply_markup)
  await query.answer()


# ==================== ارسال فایل کانفیگ OpenVPN ====================
@dp.callback_query_handler(lambda c: c.data == "dl_openvpn", state="*")
async def callback_download_openvpn(query: types.CallbackQuery):
  if os.path.exists(OPENVPN_FILE_PATH):
    await query.answer("در حال ارسال فایل کانفیگ OpenVPN...")
    caption = (
        "📥 <b>فایل کانفیگ اختصاصی OpenVPN</b>\n\n"
        "▫️ فایل بالا را دانلود کرده و با برنامه <b>OpenVPN Connect</b> باز"
        " کنید.\n"
        "▫️ سپس یوزرنیم و پسورد اشتراک خود را وارد کرده و متصل شوید.\n\n"
        f"📢 کانال رسمی: {CHANNEL_URL}"
    )
    await bot.send_document(
        chat_id=query.message.chat.id,
        document=InputFile(OPENVPN_FILE_PATH),
        caption=caption,
    )
  else:
    await query.answer(
        "⚠️ فایل کانفیگ در سرور یافت نشد. لطفاً به پشتیبانی پیام دهید.",
        show_alert=True,
    )


# ==================== آموزش اتصال ====================
@dp.message_handler(lambda m: m.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def handle_configs(message: types.Message, state: FSMContext):
  await state.finish()
  kb = InlineKeyboardMarkup(row_width=1)
  kb.add(
      InlineKeyboardButton(
          "📥 دانلود مستقیم فایل کانفیگ OpenVPN", callback_data="dl_openvpn"
      )
  )
  kb.add(
      InlineKeyboardButton(
          "📢 ورود به کانال آموزش‌ها و کانفیگ‌ها", url=CHANNEL_URL
      )
  )

  text = (
      "⚙️ <b>مشخصات و آموزش اتصال:</b>\n\n"
      f"🌐 <b>Server Address:</b> <code>{VPN_SERVER_IP}</code>\n"
      f"🔑 <b>IPSec Secret / PSK:</b> <code>{IPSEC_SECRET}</code>\n\n"
      "📱 <b>پروتکل L2TP/IPSec:</b> بدون نیاز به نصب نرم‌افزار روی تمامی"
      " سیستم‌عامل‌ها و مودم‌ها.\n"
      "🛡 <b>پروتکل OpenVPN:</b> جهت دریافت آنی فایل تنظیمات دکمه زیر را"
      " بزنید:\n"
  )
  await message.reply(text, reply_markup=kb)


# ==================== کال‌بک خرید و دریافت فیش ====================
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"), state="*")
async def callback_buy_plan(query: types.CallbackQuery, state: FSMContext):
  plan_key = query.data.split("buy_")[1]
  plan = PLANS.get(plan_key)
  if not plan:
    await query.answer("پلن یافت نشد.", show_alert=True)
    return

  await state

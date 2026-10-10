# -*- coding: utf-8 -*-
import os, logging, sqlite3
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils import executor
from aiohttp import web

logging.basicConfig(level=logging.INFO)
# در محیط اجرا، متغیر TELEGRAM_BOT_TOKEN را با توکن ربات تنظیم کنید.
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "02786850266").strip()
_admin_digits = ADMIN_ID_RAW.lstrip("0")
ADMIN_ID = int(_admin_digits) if _admin_digits.isdigit() else 2786850266
SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CHANNEL_USERNAME = "@L2tp_vpn402"
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/").strip()
OPENVPN_FILE_PATH = os.getenv("OPENVPN_FILE_PATH", "files/openvpn/client.ovpn").strip()
VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "12345678."
CARD_IMAGE_PATH, TARIFF_IMAGE_PATH = "شماره کارت1.jpg", "تعرفه.jpg"
DB_FILE = "bot_users.db"

if not BOT_TOKEN:
    raise RuntimeError("متغیر محیطی TELEGRAM_BOT_TOKEN تنظیم نشده است.")
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

class OrderState(StatesGroup):
    waiting_for_receipt = State()
class ChargeState(StatesGroup):
    waiting_for_receipt = State()
    waiting_for_username = State()
class SupportState(StatesGroup):
    waiting_for_username_and_msg = State()

PLANS = {
    "test_1u": {"name": "⚡️ اشتراک تست 24 ساعته تک کاربره (3 گیگابایت)", "price": "30,000 تومان"},
    "vip_1u": {"name": "⭐ اشتراک 1 ماهه VIP تک کاربره ترافیک نامحدود (پیشنهادی ما)", "price": "350,000 تومان"},
    "1m_1u": {"name": "اشتراک 1 ماهه تک کاربره (30 گیگ + 10 گیگ هدیه)", "price": "200,000 تومان"},
    "1m_2u": {"name": "اشتراک 1 ماهه دو کاربره (30 گیگ + 10 گیگ هدیه)", "price": "250,000 تومان"},
    "2m_1u": {"name": "اشتراک 2 ماهه تک کاربره (60 گیگ + 10 گیگ هدیه)", "price": "380,000 تومان"},
    "2m_2u": {"name": "اشتراک 2 ماهه دو کاربره (60 گیگ + 10 گیگ هدیه)", "price": "430,000 تومان"},
    "3m_1u": {"name": "اشتراک 3 ماهه تک کاربره (90 گیگ + 10 گیگ هدیه)", "price": "550,000 تومان"},
    "3m_2u": {"name": "اشتراک 3 ماهه دو کاربره (90 گیگ + 10 گیگ هدیه)", "price": "600,000 تومان"},
}

def gregorian_to_jalali(gy, gm, gd):
    month_days = [0,31,59,90,120,151,181,212,243,273,304,334]
    jy = 0 if gy <= 1600 else 979
    gy -= 621 if gy <= 1600 else 1600
    gy2 = gy + 1 if gm > 2 else gy
    days = 365*gy + (gy2+3)//4 - (gy2+99)//100 + (gy2+399)//400 - 80 + gd + month_days[gm-1]
    jy += 33*(days//12053); days %= 12053
    jy += 4*(days//1461); days %= 1461
    jy += (days-1)//365
    if days > 0: days = (days-1)%365
    jm = days//31+1 if days < 186 else 7+(days-186)//30
    jd = 1+(days%31 if days < 186 else (days-186)%30)
    return jy, jm, jd

def get_persian_datetime():
    now = datetime.now(pytz.timezone("Asia/Tehran"))
    jy,jm,jd = gregorian_to_jalali(now.year,now.month,now.day)
    weekdays = {5:"شنبه",6:"یک‌شنبه",0:"دوشنبه",1:"سه‌شنبه",2:"چهارشنبه",3:"پنج‌شنبه",4:"جمعه"}
    return f"{jy}/{jm:02d}/{jd:02d}", now.strftime("%H:%M:%S"), weekdays[now.weekday()]

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, full_name TEXT, username TEXT, join_date TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_name TEXT, amount_toman INTEGER, order_date TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
def add_user_to_db(user):
    date_str,_,_ = get_persian_datetime()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", (user.id,user.full_name or "",user.username or "",date_str))
def record_order_in_db(user_id, plan_name, price_str):
    date_str,_,_ = get_persian_datetime()
    digits = "".join(filter(str.isdigit, price_str.replace("تومان", "").replace(",", "")))
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO orders (user_id,plan_name,amount_toman,order_date) VALUES (?,?,?,?)", (user_id,plan_name,int(digits or 0),date_str))
def get_orders_report(period="today"):
    date_str,_,_ = get_persian_datetime()
    queries = {"today":("SELECT COUNT(*),SUM(amount_toman) FROM orders WHERE order_date=?",(date_str,)), "7days":("SELECT COUNT(*),SUM(amount_toman) FROM orders WHERE created_at>=datetime('now','-7 days')",()), "30days":("SELECT COUNT(*),SUM(amount_toman) FROM orders WHERE created_at>=datetime('now','-30 days')",()), "total":("SELECT COUNT(*),SUM(amount_toman) FROM orders",())}
    sql,args = queries.get(period,queries["total"])
    with sqlite3.connect(DB_FILE) as conn: row=conn.execute(sql,args).fetchone()
    return row[0] or 0,row[1] or 0
def get_total_users_count():
    with sqlite3.connect(DB_FILE) as conn: return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
init_db()

async def check_channel_member(user_id):
    try:
        member=await bot.get_chat_member(chat_id=CHANNEL_USERNAME,user_id=user_id)
        return member.status in ("creator","administrator","member","restricted")
    except Exception:
        logging.exception("Error checking channel membership")
        return True
BTN_BACK="🔙 برگشت به منوی اصلی"
def get_main_keyboard():
    kb=ReplyKeyboardMarkup(resize_keyboard=True,row_width=2)
    kb.add(KeyboardButton("🛒 خرید اشتراک"))
    kb.add(KeyboardButton("📊 اطلاعات حساب"),KeyboardButton("🌐 پنل کاربری IBSng"))
    kb.add(KeyboardButton("🔄 تمدید اکانت"),KeyboardButton("👥 پشتیبانی"))
    kb.add(KeyboardButton("❓ سوالات متداول"),KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return kb
def get_back_keyboard():
    kb=ReplyKeyboardMarkup(resize_keyboard=True); kb.add(KeyboardButton(BTN_BACK)); return kb
def get_buy_menu_keyboard():
    kb=InlineKeyboardMarkup(row_width=1)
    for key,plan in PLANS.items(): kb.add(InlineKeyboardButton(f"🔹 {plan['name']} — {plan['price']}",callback_data="buy_"+key))
    return kb
def get_report_keyboard():
    kb=InlineKeyboardMarkup(row_width=2)
    kb.row(InlineKeyboardButton("📅 امروز",callback_data="rep_today"),InlineKeyboardButton("🗓 ۷ روز گذشته",callback_data="rep_7days"))
    kb.row(InlineKeyboardButton("📆 ۳۰ روز گذشته",callback_data="rep_30days"),InlineKeyboardButton("📊 کل فروش",callback_data="rep_total"))
    return kb
def get_welcome_text(user):
    d,t,w=get_persian_datetime()
    return f"سلام <b>{user.first_name}</b> عزیز، خوش آمدید! 🌹\n\n📅 <b>روز:</b> {w}\n📆 <b>تاریخ:</b> <code>{d}</code> | ⏰ <code>{t}</code>\n🆔 شناسه: <code>{user.id}</code>\n\n🇩🇪 <b>سرورهای L2TP VPN 24/7:</b>\n▫️ پروتکل L2TP/IPSec\n▫️ OpenVPN و PPTP\n🎁 10 گیگابایت ترافیک هدیه\n\n👇 یکی از گزینه‌های منو را انتخاب کنید:"

@dp.message_handler(lambda m:m.text==BTN_BACK,state="*")
async def process_global_back(message,state):
    await state.finish(); await message.reply("به منوی اصلی بازگشتید 👇",reply_markup=get_main_keyboard())
@dp.message_handler(commands=["start"],state="*")
async def cmd_start(message,state):
    await state.finish(); add_user_to_db(message.from_user)
    kb=InlineKeyboardMarkup(row_width=2).row(InlineKeyboardButton("📢 کانال اطلاع‌رسانی",url=CHANNEL_URL),InlineKeyboardButton("💬 پشتیبانی",url=SUPPORT_URL))
    await message.reply(get_welcome_text(message.from_user),reply_markup=get_main_keyboard()); await message.answer("دسترسی‌های سریع:",reply_markup=kb)
@dp.message_handler(commands=["report"],state="*")
async def cmd_report(message):
    if message.from_user.id!=ADMIN_ID:return
    d,t,_=get_persian_datetime(); count,total=get_orders_report("today")
    await message.reply(f"📈 <b>گزارش فروش</b>\n📅 امروز: <code>{d}</code> ساعت <code>{t}</code>\n🛒 سفارش‌ها: <b>{count:,}</b>\n💰 فروش: <b>{total:,} تومان</b>",reply_markup=get_report_keyboard())
@dp.callback_query_handler(lambda c:c.data.startswith("rep_"),state="*")
async def callback_report_period(query):
    if query.from_user.id!=ADMIN_ID: await query.answer("دسترسی غیرمجاز!",show_alert=True); return
    period=query.data[4:]; count,total=get_orders_report(period); _,tm,_=get_persian_datetime()
    names={"today":"امروز","7days":"۷ روز گذشته","30days":"۳۰ روز گذشته","total":"کل دوره"}
    await query.message.edit_text(f"📈 <b>گزارش فروش ({names.get(period,'')}):</b>\n🛒 تعداد: <b>{count:,}</b>\n💰 درآمد: <b>{total:,} تومان</b>\n⏰ <code>{tm}</code>",reply_markup=get_report_keyboard()); await query.answer()
@dp.message_handler(commands=["stats"],state="*")
async def cmd_stats(message):
    if message.from_user.id!=ADMIN_ID:return
    d,t,_=get_persian_datetime(); await message.reply(f"📊 <b>آمار ربات</b>\n👥 کاربران: <b>{get_total_users_count():,}</b>\n📅 <code>{d}</code> | <code>{t}</code>")

@dp.message_handler(lambda m:m.text=="🛒 خرید اشتراک",state="*")
async def handle_buy(message,state):
    await state.finish()
    if not await check_channel_member(message.from_user.id):
        kb=InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("📢 عضویت در کانال",url=CHANNEL_URL),InlineKeyboardButton("✅ بررسی مجدد",callback_data="check_join_buy"))
        await message.reply("⚠️ برای خرید ابتدا عضو کانال شوید.",reply_markup=kb); return
    caption="🛒 <b>خرید اشتراک L2TP VPN</b>\n\nپلن مورد نظر را انتخاب کنید:"
    if os.path.exists(TARIFF_IMAGE_PATH): await message.reply_photo(InputFile(TARIFF_IMAGE_PATH),caption=caption,reply_markup=get_buy_menu_keyboard())
    else: await message.reply(caption,reply_markup=get_buy_menu_keyboard())
@dp.callback_query_handler(lambda c:c.data=="check_join_buy",state="*")
async def callback_check_join_buy(query,state):
    if await check_channel_member(query.from_user.id):
        await query.message.delete(); caption="🛒 <b>خرید اشتراک</b>\nپلن مورد نظر را انتخاب کنید:"
        if os.path.exists(TARIFF_IMAGE_PATH): await bot.send_photo(query.message.chat.id,InputFile(TARIFF_IMAGE_PATH),caption=caption,reply_markup=get_buy_menu_keyboard())
        else: await bot.send_message(query.message.chat.id,caption,reply_markup=get_buy_menu_keyboard())
        await query.answer("عضویت تایید شد ✅")
    else: await query.answer("هنوز عضو کانال نشده‌اید.",show_alert=True)
@dp.message_handler(lambda m:m.text=="📊 اطلاعات حساب",state="*")
async def handle_account(message,state):
    await state.finish(); u=message.from_user
    await message.reply(f"📊 <b>مشخصات حساب</b>\n👤 {u.full_name}\n🆔 <code>{u.id}</code>\n💎 کاربر ثبت‌شده\n\nبرای مشاهده انقضا و حجم وارد پنل IBSng شوید.",reply_markup=get_main_keyboard())
@dp.message_handler(lambda m:m.text=="🌐 پنل کاربری IBSng",state="*")
async def handle_ibsng_panel(message,state):
    await state.finish(); kb=InlineKeyboardMarkup().add(InlineKeyboardButton("🔗 ورود به پنل IBSng",url=IBSNG_PANEL_URL))
    await message.reply(f"🌐 <b>پنل کاربری IBSng</b>\n{IBSNG_PANEL_URL}\n\n⚠️ در اولین ورود حتماً رمز عبور را تغییر دهید.\n▫️ مشاهده حجم و تاریخ انقضا",reply_markup=kb)
@dp.message_handler(lambda m:m.text in ["🔄 تمدید اکانت","💰 شارژ حساب"],state="*")
async def handle_charge(message,state):
    await state.finish(); await ChargeState.waiting_for_receipt.set()
    caption=f"🔄 <b>تمدید اکانت</b>\n💳 کارت: <code>{CARD_NUMBER}</code>\n👤 به نام: <b>{CARD_HOLDER}</b>\n📸 تصویر فیش را ارسال کنید:"
    if os.path.exists(CARD_IMAGE_PATH): await message.reply_photo(InputFile(CARD_IMAGE_PATH),caption=caption,reply_markup=get_back_keyboard())
    else: await message.reply(caption,reply_markup=get_back_keyboard())
@dp.message_handler(lambda m:m.text=="👥 پشتیبانی",state="*")
async def handle_support(message,state):
    await state.finish(); await SupportState.waiting_for_username_and_msg.set()
    kb=InlineKeyboardMarkup().add(InlineKeyboardButton("💬 پیام مستقیم به پشتیبان",url=SUPPORT_URL))
    await message.reply(f"👥 <b>پشتیبانی</b>\nنام کاربری VPN و شرح درخواست را در یک پیام ارسال کنید.\n💬 {SUPPORT_USERNAME}",reply_markup=get_back_keyboard()); await message.answer("راه ارتباط مستقیم:",reply_markup=kb)
@dp.message_handler(state=SupportState.waiting_for_username_and_msg,content_types=types.ContentTypes.ANY)
async def process_support_input(message,state):
    u=message.from_user; text=message.text or message.caption or "ارسال فایل/تصویر بدون متن"
    alert=f"🚨 <b>درخواست پشتیبانی</b>\n👤 {u.full_name}\n🆔 <code>{u.id}</code>\n🔗 @{u.username or 'ندارد'}\n📝 {text}"
    if ADMIN_ID:
        try:
            if message.photo: await bot.send_photo(ADMIN_ID,message.photo[-1].file_id,caption=alert)
            else: await bot.send_message(ADMIN_ID,alert)
        except Exception: logging.exception("Error alerting admin")
    await message.reply(f"✅ درخواست برای اپراتور ارسال شد.\n💬 {SUPPORT_USERNAME}",reply_markup=get_main_keyboard()); await state.finish()

FAQ_MAIN_TEXT=f"❓ <b>راهنمای اتصال L2TP/IPSec</b>\n🌐 سرور: <code>{VPN_SERVER_IP}</code>\n🔑 کلید IPSec: <code>{IPSEC_SECRET}</code>\nسیستم‌عامل یا موضوع را انتخاب کنید:"
def get_faq_main_kb():
    kb=InlineKeyboardMarkup(row_width=2)
    for title,key in [("📱 iOS","ios"),("🤖 Android","android"),("💻 Windows","windows"),("🍏 macOS","mac"),("📶 مودم/روتر","router"),("🛡 OpenVPN","openvpn")]: kb.insert(InlineKeyboardButton(title,callback_data="faq_"+key))
    return kb
def get_faq_sub_kb(): return InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به سوالات",callback_data="faq_home"))
def get_openvpn_kb(): return InlineKeyboardMarkup().add(InlineKeyboardButton("📥 دانلود client.ovpn",callback_data="dl_openvpn"),InlineKeyboardButton("🔙 بازگشت",callback_data="faq_home"))
@dp.message_handler(lambda m:m.text=="❓ سوالات متداول",state="*")
async def handle_faq(message,state):
    await state.finish(); await message.reply(FAQ_MAIN_TEXT,reply_markup=get_faq_main_kb())
@dp.callback_query_handler(lambda c:c.data.startswith("faq_"),state="*")
async def callback_faq_navigation(query):
    action=query.data[4:]
    if action=="home": await query.message.edit_text(FAQ_MAIN_TEXT,reply_markup=get_faq_main_kb()); await query.answer(); return
    labels={"ios":"آیفون و آیپد","android":"اندروید","windows":"ویندوز","mac":"مک‌بوک","router":"مودم و روتر","openvpn":"OpenVPN"}
    text=f"📘 <b>راهنمای {labels.get(action,'اتصال')}</b>\n\nسرور: <code>{VPN_SERVER_IP}</code>\nIPSec PSK: <code>{IPSEC_SECRET}</code>\nنام کاربری و رمز اکانت خود را وارد کنید."
    await query.message.edit_text(text,reply_markup=get_openvpn_kb() if action=="openvpn" else get_faq_sub_kb()); await query.answer()
@dp.callback_query_handler(lambda c:c.data=="dl_openvpn",state="*")
async def callback_download_openvpn(query):
    if os.path.exists(OPENVPN_FILE_PATH):
        await query.answer("در حال ارسال فایل..."); await bot.send_document(query.message.chat.id,InputFile(OPENVPN_FILE_PATH),caption="📥 فایل کانفیگ OpenVPN")
    else: await query.answer("⚠️ فایل کانفیگ یافت نشد.",show_alert=True)
@dp.message_handler(lambda m:m.text=="⚙️ کانفیگ‌ها و آموزش اتصال",state="*")
async def handle_configs(message,state):
    await state.finish(); kb=InlineKeyboardMarkup().add(InlineKeyboardButton("📥 دانلود OpenVPN",callback_data="dl_openvpn"),InlineKeyboardButton("📢 کانال",url=CHANNEL_URL))
    await message.reply(f"⚙️ <b>مشخصات اتصال</b>\n🌐 Server: <code>{VPN_SERVER_IP}</code>\n🔑 IPSec Secret: <code>{IPSEC_SECRET}</code>",reply_markup=kb)

async def send_plan_invoice(chat_id,plan,state):
    await state.update_data(plan_name=plan["name"],plan_price=plan["price"]); await OrderState.waiting_for_receipt.set()
    caption=f"🧾 <b>پیش‌فاکتور</b>\n📦 پلن: <b>{plan['name']}</b>\n💵 مبلغ: <b>{plan['price']}</b>\n💳 کارت: <code>{CARD_NUMBER}</code>\n👤 به نام: <b>{CARD_HOLDER}</b>\n\nتصویر فیش را ارسال کنید:"
    if os.path.exists(TARIFF_IMAGE_PATH): await bot.send_photo(chat_id,InputFile(TARIFF_IMAGE_PATH),caption=caption,reply_markup=get_back_keyboard())
    else: await bot.send_message(chat_id,caption,reply_markup=get_back_keyboard())
@dp.callback_query_handler(lambda c:c.data.startswith("buy_"),state="*")
async def callback_buy_plan(query,state):
    plan=PLANS.get(query.data.split("buy_",1)[1])
    if not plan: await query.answer("پلن یافت نشد.",show_alert=True); return
    await query.message.delete(); await send_plan_invoice(query.message.chat.id,plan,state); await query.answer()
@dp.message_handler(content_types=types.ContentTypes.PHOTO,state=OrderState.waiting_for_receipt)
async def process_order_receipt(message,state):
    data=await state.get_data(); plan_name=data.get("plan_name","اشتراک"); plan_price=data.get("plan_price","نامشخص")
    user=message.from_user; d,t,_=get_persian_datetime(); record_order_in_db(user.id,plan_name,plan_price)
    caption=f"🛒 <b>سفارش جدید</b>\n📦 {plan_name}\n💰 {plan_price}\n👤 {user.full_name}\n🆔 <code>{user.id}</code>\n🔗 @{user.username or 'ندارد'}\n📅 {d} {t}"
    if ADMIN_ID:
        try: await bot.send_photo(ADMIN_ID,message.photo[-1].file_id,caption=caption)
        except Exception: logging.exception("Error sending receipt to admin")
    await message.reply("✅ فیش دریافت شد و سفارش برای بررسی اپراتور ارسال شد.",reply_markup=get_main_keyboard()); await state.finish()
@dp.message_handler(content_types=types.ContentTypes.PHOTO,state=ChargeState.waiting_for_receipt)
async def process_charge_receipt(message,state):
    await state.update_data(receipt_file_id=message.photo[-1].file_id); await ChargeState.waiting_for_username.set()
    await message.reply("✅ فیش دریافت شد. اکنون نام کاربری اکانت برای تمدید را بفرستید:",reply_markup=get_back_keyboard())
@dp.message_handler(state=ChargeState.waiting_for_username,content_types=types.ContentTypes.TEXT)
async def process_charge_username(message,state):
    data=await state.get_data(); file_id=data.get("receipt_file_id"); username=message.text.strip(); user=message.from_user; d,t,_=get_persian_datetime()
    caption=f"🔄 <b>درخواست تمدید</b>\n👤 اکانت: <code>{username}</code>\n👤 {user.full_name}\n🆔 <code>{user.id}</code>\n🔗 @{user.username or 'ندارد'}\n📅 {d} {t}"
    if ADMIN_ID and file_id:
        try: await bot.send_photo(ADMIN_ID,file_id,caption=caption)
        except Exception: logging.exception("Error sending renewal request")
    await message.reply(f"✅ درخواست تمدید <code>{username}</code> ثبت شد.",reply_markup=get_main_keyboard()); await state.finish()

async def handle_health_check(request): return web.Response(text="Mikrotik-Bot is running smoothly!",status=200)
async def on_startup(dispatcher):
    port=int(os.getenv("PORT",10000)); app=web.Application(); app.router.add_get("/",handle_health_check)
    runner=web.AppRunner(app); await runner.setup(); site=web.TCPSite(runner,"0.0.0.0",port); await site.start()
    logging.info("Health check web server running on port %s",port)
if __name__=="__main__": executor.start_polling(dp,on_startup=on_startup,skip_updates=True)

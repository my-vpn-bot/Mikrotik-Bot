import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# ۱. تنظیمات مرجع و متغیرهای محیطی
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUPPORT_USERNAME = "L2tp1support"
CHANNEL_LINK = "https://t.me/L2tp_vpn402"
PORT = int(os.getenv("PORT", 10000))

# تعرفه‌های استاندارد مصوب
PLANS = {
    "p1": {"name": "اشتراک ۱ ماهه (تک کاربره)", "price": "۲۵۰,۰۰۰ تومان"},
    "p2": {"name": "اشتراک ۲ ماهه (دو کاربره)", "price": "۴۰۰,۰۰۰ تومان"},
    "p3": {"name": "اشتراک ۳ ماهه (سه کاربره)", "price": "۶۰۰,۰۰۰ تومان"}
}

# لاگ و ساخت کلاینت ربات
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# شمارنده بازدیدکنندگان یکتا
UNIQUE_VISITORS = set()

# ==========================================
# ۲. توابع تبدیل تاریخ شمسی و ساعت تهران
# ==========================================
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

WEEKDAYS_FA = {
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنج‌شنبه",
    4: "جمعه",
    5: "شنبه",
    6: "یکشنبه"
}

def get_tehran_datetime_info():
    tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tz)
    jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
    weekday = WEEKDAYS_FA[now.weekday()]
    date_str = f"{jy:04d}/{jm:02d}/{jd:02d}"
    time_str = now.strftime("%H:%M:%S")
    return date_str, weekday, time_str

# ==========================================
# ۳. کیبوردهای منوی اصلی (۴ ردیف اختصاصی)
# ==========================================
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🛒 خرید اشتراک", callback_data="buy_menu"))
    kb.add(
        InlineKeyboardButton("📊 اطلاعات حساب", callback_data="acc_info"),
        InlineKeyboardButton("💎 اشتراک‌های من", callback_data="my_subs")
    )
    kb.add(
        InlineKeyboardButton("💰 شارژ حساب", callback_data="charge"),
        InlineKeyboardButton("👥 پشتیبانی", callback_data="support")
    )
    kb.add(
        InlineKeyboardButton("❓ سوالات متداول", callback_data="faq"),
        InlineKeyboardButton("⚙️ کانفیگ‌ها و آموزش", callback_data="configs")
    )
    return kb

def get_welcome_text(user_id, name):
    date_str, weekday, time_str = get_tehran_datetime_info()
    return (
        f"🌟 <b>به ربات شانلی خوش آمدید، {name} عزیز!</b>\n\n"
        f"ارائه دهنده قدرتمندترین سرویس‌های عبور از محدودیت با پروتکل‌های V2Ray, L2TP, OpenVPN, PPTP.\n\n"
        f"📅 <b>تاریخ امروز:</b> {date_str} ({weekday})\n"
        f"⏰ <b>ساعت رسمی تهران:</b> {time_str}\n"
        f"🆔 <b>شناسه عددی شما:</b> <code>{user_id}</code>\n"
        f"👤 <b>تعداد کل بازدیدکنندگان یکتا:</b> {len(UNIQUE_VISITORS)}\n\n"
        f"لطفاً از منوی زیر گزینه مورد نظرتان را انتخاب کنید:"
    )

# ==========================================
# ۴. هندلرهای دستور /start و منوی اصلی
# ==========================================
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    UNIQUE_VISITORS.add(message.from_user.id)
    await message.answer(
        get_welcome_text(message.from_user.id, message.from_user.first_name or "کاربر"),
        reply_markup=main_menu()
    )

@dp.callback_query_handler(lambda c: c.data == "back_to_main", state="*")
async def back_to_main(c: types.CallbackQuery, state: FSMContext):
    await state.finish()
    UNIQUE_VISITORS.add(c.from_user.id)
    text = get_welcome_text(c.from_user.id, c.from_user.first_name or "کاربر")
    await bot.edit_message_text(
        text,
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=main_menu()
    )

# ==========================================
# ۵. ردیف اول: منوی خرید و ارسال مستقیم فیش
# ==========================================
@dp.callback_query_handler(lambda c: c.data == "buy_menu", state="*")
async def menu_buy(c: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(row_width=1)
    for k, v in PLANS.items():
        kb.add(InlineKeyboardButton(f"{v['name']} — {v['price']}", callback_data=f"plan_{k}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    
    await bot.edit_message_text(
        "🛒 <b>لطفاً پلن اشتراک مورد نظر خود را انتخاب کنید:</b>",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data.startswith("plan_"), state="*")
async def process_plan(c: types.CallbackQuery, state: FSMContext):
    plan_key = c.data.split("_")[1]
    plan = PLANS.get(plan_key, {"name": "اشتراک ویژه", "price": "تعرفه مصوب"})
    text = (
        f"🛒 <b>پلن انتخابی:</b> {plan['name']}\n"
        f"💰 <b>مبلغ قابل پرداخت:</b> {plan['price']}\n\n"
        f"💳 برای تکمیل سفارش و دریافت سرویس، مبلغ را به شماره کارت پشتیبانی واریز کرده و تصویر فیش واریزی را مستقیماً به پی‌وی پشتیبانی ارسال فرمایید.\n\n"
        f"👇 جهت ارسال مستقیم فیش، روی دکمه زیر کلیک کنید:"
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("ارسال فیش به پشتیبانی 👤", url=f"https://t.me/{SUPPORT_USERNAME}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منوی خرید", callback_data="buy_menu"))
    kb.add(InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_main"))
    
    await bot.edit_message_text(
        text,
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=kb
    )

# ==========================================
# ۶. ردیف دوم: اطلاعات حساب و اشتراک‌ها
# ==========================================
@dp.callback_query_handler(lambda c: c.data == "acc_info", state="*")
async def menu_acc_info(c: types.CallbackQuery, state: FSMContext):
    text = (
        f"📊 <b>اطلاعات حساب کاربری شما:</b>\n\n"
        f"👤 <b>نام:</b> {c.from_user.first_name}\n"
        f"🆔 <b>شناسه عددی:</b> <code>{c.from_user.id}</code>\n"
        f"💰 <b>موجودی کیف پول:</b> ۰ تومان\n"
        f"💎 <b>تعداد سرویس‌های فعال:</b> ۰\n"
    )
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await bot.edit_message_text(text, chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "my_subs", state="*")
async def menu_my_subs(c: types.CallbackQuery, state: FSMContext):
    text = (
        "💎 <b>اشتراک‌های فعال شما:</b>\n\n"
        "در حال حاضر هیچ اشتراک فعالی برای حساب شما ثبت نشده است.\n"
        "جهت خرید یا فعال‌سازی سرویس از بخش «خرید اشتراک» اقدام کنید."
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🛒 خرید اشتراک", callback_data="buy_menu"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await bot.edit_message_text(text, chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=kb)

# ==========================================
# ۷. ردیف سوم: شارژ حساب و پشتیبانی
# ==========================================
@dp.callback_query_handler(lambda c: c.data == "charge", state="*")
async def menu_charge(c: types.CallbackQuery, state: FSMContext):
    text = (
        "💰 <b>شارژ حساب کاربری:</b>\n\n"
        "جهت افزایش موجودی کیف پول و شارژ حساب، لطفاً مبلغ مورد نظر خود را به شماره کارت اعلامی توسط پشتیبانی واریز کرده و فیش را برای ادمین ارسال کنید."
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("ارسال فیش به پشتیبانی 👤", url=f"https://t.me/{SUPPORT_USERNAME}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await bot.edit_message_text(text, chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "support", state="*")
async def menu_support(c: types.CallbackQuery, state: FSMContext):
    text = (
        "👥 <b>مرکز پشتیبانی ۲۴/۷ شانلی:</b>\n\n"
        "برای پاسخ به سوالات، دریافت راهنمایی، پیگیری اشتراک و ارسال فیش واریزی، روی دکمه زیر کلیک کرده و با کارشناسان ما گفتگو کنید."
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💬 ارتباط مستقیم با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await bot.edit_message_text(text, chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=kb)

# ==========================================
# ۸. ردیف چهارم: سوالات متداول و کانفیگ‌ها
# ==========================================
@dp.callback_query_handler(lambda c: c.data == "faq", state="*")
async def menu_faq(c: types.CallbackQuery, state: FSMContext):
    faq_text = (
        "<b>❓ سوالات متداول کاربران شانلی (FAQ):</b>\n\n"
        "1️⃣ <b>پروتکل‌ها:</b> پشتیبانی کامل از پروتکل‌های V2Ray (Vless/Vmess/Trojan)، L2TP، OpenVPN و PPTP.\n"
        "2️⃣ <b>زمان تحویل:</b> بلافاصله و آنی پس از ارسال و تایید فیش توسط پشتیبانی.\n"
        "3️⃣ <b>سازگاری دستگاه‌ها:</b> قابل استفاده در اندروید، iOS (آیفون/آیپد)، ویندوز و مک‌بوک.\n"
        "4️⃣ <b>سازگاری اپراتورها:</b> بهینه‌شده برای همراه اول، ایرانسل، رایتل و اینترنت‌های ثابت (شاتل، مخابرات و...).\n"
        "5️⃣ <b>محدودیت حجم:</b> تمامی پلن‌ها دارای ترافیک نامحدود و بدون افت کیفیت هستند.\n"
        "6️⃣ <b>تعداد کاربر:</b> اتصال همزمان ۱ تا ۳ کاربر/دستگاه متناسب با پلن خریداری‌شده.\n"
        "7️⃣ <b>گارانتی سرویس:</b> تضمین اتصال پایدار و بدون قطعی در تمامی ساعات شبانه‌روز.\n"
        "8️⃣ <b>عودت وجه:</b> در صورت بروز هرگونه مشکل فنی لاینحل، بازگشت کامل وجه انجام می‌شود.\n"
        "9️⃣ <b>ساعات پشتیبانی:</b> پشتیبانی به صورت ۲۴ ساعته در ۷ روز هفته فعال و پاسخگو است.\n"
        "🔟 <b>شرایط استفاده:</b> استفاده صرفاً قانونی و شخصی بر روی دستگاه‌های تعریف‌شده.\n"
        "1️⃣1️⃣ <b>آموزش اتصال:</b> برنامه‌ها و ویدیوهای آموزشی گام‌به‌گام در کانال ربات قرار دارد.\n"
        "1️⃣2️⃣ <b>امنیت و حریم خصوصی:</b> رمزنگاری چندلایه سرتاسری و عدم ذخیره‌سازی هیچ‌گونه لاگ مصرفی.\n"
        "1️⃣3️⃣ <b>تمدید اشتراک:</b> امکان تمدید سرویس قبل از اتمام زمان با حفظ همان کانفیگ و اطلاعات."
    )
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await bot.edit_message_text(faq_text, chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "configs", state="*")
async def menu_configs(c: types.CallbackQuery, state: FSMContext):
    text = (
        "⚙️ <b>کانفیگ‌ها، نرم‌افزارها و آموزش اتصال:</b>\n\n"
        "برای دانلود آخرین نسخه نرم‌افزارهای V2RayNG، v2rayN، Streisand، Clash و مشاهده آموزش‌های ویدیویی، وارد کانال رسمی ما شوید:"
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📢 ورود به کانال آموزش و نرم‌افزارها", url=CHANNEL_LINK))
    kb.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    await bot.edit_message_text(text, chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=kb)

# ==========================================
# ۹. وب‌سرور داخلی هلث‌چک برای Render
# ==========================================
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Shanli Bot is Healthy & Live!"))
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

# ==========================================
# ۱۰. نقطه ورود و اجرای اصلی ربات
# ==========================================
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)

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

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ==================== وضعیت‌های FSM ====================
class OrderState(StatesGroup):
    waiting_for_receipt = State()

class ReportState(StatesGroup):
    waiting_for_error = State()

# ==================== تعرفه‌ها و پلن‌ها ====================
PLANS = {
    "p1": {"name": "اشتراک ۱ ماهه (تک کاربره)", "price": "۲۵۰,۰۰۰ تومان"},
    "p2": {"name": "اشتراک ۲ ماهه (دو کاربره)", "price": "۴۰۰,۰۰۰ تومان"},
    "p3": {"name": "اشتراک ۳ ماهه (سه کاربره)", "price": "۶۰۰,۰۰۰ تومان"},
}

# ==================== توابع کمکی رابط کاربری ====================
def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🛒 خرید اشتراک"))
    kb.add(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    kb.add(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    kb.add(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return kb

def get_persian_datetime():
    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%Y/%m/%d")
    return date_str, time_str

def get_welcome_text(user):
    date_str, time_str = get_persian_datetime()
    return (
        f"سلام <b>{user.first_name}</b> عزیز، به ربات هوشمند شانلی خوش آمدید! 🌸\n\n"
        f"📅 تاریخ: <code>{date_str}</code>\n"
        f"⏰ ساعت رسمی تهران: <code>{time_str}</code>\n"
        f"🆔 شناسه کاربری: <code>{user.id}</code>\n\n"
        "⚡️ برای استفاده از خدمات و مدیریت سرویس، لطفاً از منوی زیر گزینه‌ای را انتخاب کنید:"
    )

# ==================== هندلرهای اصلی منو ====================
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(get_welcome_text(message.from_user), reply_markup=get_main_keyboard())

# ۱. خرید اشتراک و نمایش تعرفه‌ها
@dp.message_handler(lambda m: m.text == "🛒 خرید اشتراک", state="*")
async def handle_buy(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    for p_id, info in PLANS.items():
        kb.add(InlineKeyboardButton(f"🔹 {info['name']} — {info['price']}", callback_data=f"buy_{p_id}"))
    await message.answer("🛍 <b>لیست پلن‌های اشتراک:</b>\n\nلطفاً یکی از پلن‌های زیر را جهت خرید انتخاب کنید:", reply_markup=kb)

# ۲. اطلاعات حساب
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

# ۳. اشتراک‌های من
@dp.message_handler(lambda m: m.text == "💎 اشتراک‌های من", state="*")
async def handle_my_subs(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("💎 <b>اشتراک‌های فعال شما:</b>\n\nدر حال حاضر اشتراک فعالی برای شما ثبت نشده است.", reply_markup=get_main_keyboard())

# ۴. شارژ حساب
@dp.message_handler(lambda m: m.text == "💰 شارژ حساب", state="*")
async def handle_charge(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🧾 ارسال فیش واریزی", callback_data="send_receipt_charge"))
    text = (
        f"💰 <b>اطلاعات حساب بانکی جهت واریز:</b>\n\n"
        f"💳 شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 بنام: <b>{CARD_HOLDER}</b>\n\n"
        "پس از انتقال وجه، دکمه زیر را لمس کرده و تصویر فیش واریزی را ارسال کنید."
    )
    await message.answer(text, reply_markup=kb)

# ۵. پشتیبانی
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

# ۶. سوالات متداول
@dp.message_handler(lambda m: m.text == "❓ سوالات متداول", state="*")
async def handle_faq(message: types.Message, state: FSMContext):
    await state.finish()
    text = (
        "❓ <b>سوالات متداول کاربران:</b>\n\n"
        "۱. <b>چگونه متصل شوم؟</b>\n"
        "از بخش کانفیگ‌ها برنامه متناسب با سیستم‌عامل خود را دانلود و اطلاعات سرویس را وارد کنید.\n\n"
        "۲. <b>آیا اشتراک‌ها محدودیت دارند؟</b>\n"
        "پلن‌ها بر اساس تعداد کاربر مجاز مشخص شده‌اند و کیفیت اتصال به طور دائم پایش می‌شود.\n\n"
        "۳. <b>تایید فیش چه مدت طول می‌کشد؟</b>\n"
        "فیش‌های ارسالی توسط پشتیبانی در اسرع وقت بررسی و حساب فعال می‌شود."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

# ۷. کانفیگ‌ها و آموزش اتصال
@dp.message_handler(lambda m: m.text == "⚙️ کانفیگ‌ها و آموزش اتصال", state="*")
async def handle_configs(message: types.Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📢 ورود به کانال آموزش و اتصالات", url=CHANNEL_URL))
    text = (
        "⚙️ <b>آموزش اتصال و فایل‌های کانفیگ:</b>\n\n"
        "تمامی نرم‌افزارهای مورد نیاز و راهنماهای قدم‌به‌قدم در کانال اطلاع‌رسانی قرار دارند."
    )
    await message.answer(text, reply_markup=kb)

# ==================== جریان‌های کال‌بک اینلاین ====================
# انتخاب پلن خرید
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"), state="*")
async def callback_buy_plan(query: types.CallbackQuery, state: FSMContext):
    plan_key = query.data.split("_")[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await query.answer("پلن یافت نشد.", show_alert=True)
        return
    
    await state.update_data(plan_key=plan_key, plan_name=plan["name"], plan_price=plan["price"])
    await OrderState.waiting_for_receipt.set()

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu"))

    text = (
        f"🧾 <b>پیش‌فاکتور خرید اشتراک</b>\n\n"
        f"📦 پلن انتخابی: <b>{plan['name']}</b>\n"
        f"💵 مبلغ قابل پرداخت: <b>{plan['price']}</b>\n\n"
        f"💳 شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 بنام: <b>{CARD_HOLDER}</b>\n\n"
        "لطفاً پس از واریز مبلغ، تصویر فیش واریزی خود را در همین صفحه ارسال کنید:"
    )
    await query.message.edit_text(text, reply_markup=kb)
    await query.answer()

# ارسال فیش از بخش شارژ حساب
@dp.callback_query_handler(lambda c: c.data == "send_receipt_charge", state="*")
async def callback_charge_receipt(query: types.CallbackQuery, state: FSMContext):
    await OrderState.waiting_for_receipt.set()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu"))
    await query.message.edit_text("لطفاً تصویر فیش واریزی خود را ارسال کنید:", reply_markup=kb)
    await query.answer()

# ثبت گزارش خطا
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

# دکمه بازگشت عمومی
@dp.callback_query_handler(lambda c: c.data == "main_menu", state="*")
async def callback_back_menu(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await query.message.edit_text(get_welcome_text(query.from_user), reply_markup=None)
    await query.message.answer("منوی اصلی در دسترس است:", reply_markup=get_main_keyboard())
    await query.answer()

# ==================== دریافت ورودی‌های FSM ====================
# دریافت عکس فیش
@dp.message_handler(content_types=['photo'], state=OrderState.waiting_for_receipt)
async def handle_incoming_receipt(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    plan_name = user_data.get("plan_name", "شارژ حساب")
    plan_price = user_data.get("plan_price", "نامشخص")
    
    caption = (
        f"🔔 <b>فیش واریزی جدید!</b>\n\n"
        f"👤 کاربر: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 شناسه: <code>{message.from_user.id}</code>\n"
        f"📦 مورد: {plan_name}\n"
        f"💰 مبلغ: {plan_price}"
    )
    
    if ADMIN_ID != 0:
        try:
            await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption)
        except Exception as e:
            logging.error(f"Error forwarding receipt to admin: {e}")
            
    await message.answer("✅ فیش شما با موفقیت ثبت شد و جهت تایید برای مدیریت ارسال گردید.", reply_markup=get_main_keyboard())
    await state.finish()

# دریافت متن گزارش خطا
@dp.message_handler(state=ReportState.waiting_for_error)
async def handle_incoming_report(message: types.Message, state: FSMContext):
    report_text = (
        f"⚠️ <b>گزارش خطای جدید از کاربر</b>\n\n"
        f"👤 فرستنده: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 شناسه: <code>{message.from_user.id}</code>\n\n"
        f"📝 متن گزارش:\n{message.text}"
    )
    
    if ADMIN_ID != 0:
        try:
            await bot.send_message(ADMIN_ID, report_text)
        except Exception as e:
            logging.error(f"Error forwarding report to admin: {e}")
            
    await message.answer("✅ گزارش خطای شما برای تیم پشتیبانی ارسال شد و بررسی خواهد شد.", reply_markup=get_main_keyboard())
    await state.finish()

# ==================== سرور هلث‌چک برای Render ====================
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

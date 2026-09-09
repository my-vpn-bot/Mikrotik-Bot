import logging
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramConflictError
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message,
)
from aiogram.client.default import DefaultBotProperties
from aiohttp import web
import jdatetime
from zoneinfo import ZoneInfo

# ================= تنظیمات (Environment Variables) =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env not set")

SUPPORT_ID = os.getenv("SUPPORT_ID", "al2tpiSupport")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338994607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
HOSTING = os.getenv("HOSTING", "MikroTik V2Ray")
PORT = int(os.getenv("PORT", "10000"))

# ================= Bot & Dispatcher =================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ================= تعرفه‌ها (قیمت‌ها دست‌نخورده) =================
PLANS = {
    "plan1m": ("اشتراک یک‌ماهه", "30 گیگابایت", "350,000 تومان"),
    "plan2m": ("اشتراک دوماهه", "60 گیگابایت", "650,000 تومان"),
    "plan3m": ("اشتراک سهماهه", "90 گیگابایت", "900,000 تومان"),
}

# ================= ابزارهای کمکی =================
def to_fa_digits(num_str: str) -> str:
    fa = "۰۱۲۳۴۵۶۷۸۹"
    return "".join(fa[int(c)] if c.isdigit() else c for c in num_str)

def get_time_header() -> str:
    """تاریخ و ساعت شمسی منطقه تهران."""
    now = jdatetime.datetime.now(ZoneInfo("Asia/Tehran"))
    date_fa = to_fa_digits(now.strftime("%Y/%m/%d"))
    time_fa = to_fa_digits(now.strftime("%H:%M"))
    return f"📅 {date_fa} — ⏰ {time_fa}"

def hb(header: str, sub: str, cdata: str) -> InlineKeyboardButton:
    """دکمهٔ دوخطی حرفه‌ای: عنوان بزرگ + زیرعنوان با ✦."""
    return InlineKeyboardButton(text=f"{header}\n✦ {sub}", callback_data=cdata)

def plain(text: str, cdata: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=cdata)

# ================= کیبوردها =================
def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [hb("🛒 خرید اشتراک", "مشاهده و انتخاب پلن", "buy_sub")],
        [hb("🔮 سرویس‌های آینده", "به‌زودی در دسترس", "future_services")],
        [hb("👤 حساب کاربری", "وضعیت و مشخصات شما", "my_account")],
        [hb("🆘 پشتیبانی", "ارتباط با پشتیبان", "support")],
    ])

def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [plain("🔙 بازگشت به منوی اصلی", "main_menu")]
    ])

def plans_kb() -> InlineKeyboardMarkup:
    kb = []
    for key, (name, cap, price) in PLANS.items():
        kb.append([hb(f"📦 {name}", f"{cap} • {price}", key)])
    kb.append([plain("🔙 بازگشت به منوی اصلی", "main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def payment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [plain("💸 تایید و ارسال رسید", "pay_send")],
        [plain("💳 کپی شماره کارت", "pay_copy")],
        [plain("🔙 بازگشت به تعرفه‌ها", "buy_sub")],
    ])

# ================= هندلر: دستور شروع =================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"{get_time_header()}\n\n"
        f"👋 سلام <b>{message.from_user.first_name}</b> عزیز! 🌟\n"
        f"خوش اومدی به ربات <b>{HOSTING}</b>.\n"
        f"از منوی زیر انتخاب کن:",
        reply_markup=main_kb(),
    )

# ================= هندلر: منوی اصلی =================
@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🏠 <b>منوی اصلی</b>\nاز منوی زیر انتخاب کن:",
        reply_markup=main_kb(),
    )

# ================= هندلر: خرید اشتراک =================
@dp.callback_query(F.data == "buy_sub")
async def cb_buy_sub(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🛒 <b>تعرفه‌های V2Ray</b>\nپلن مورد نظرت رو انتخاب کن:",
        reply_markup=plans_kb(),
    )

# ================= هندلر: سرویس‌های آینده =================
@dp.callback_query(F.data == "future_services")
async def cb_future(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🔮 <b>سرویس‌های آینده</b>\n\n"
        f"✅ L2TP/IPsec\n✅ OpenVPN\n✅ WireGuard",
        reply_markup=back_kb(),
    )

# ================= هندلر: حساب کاربری =================
@dp.callback_query(F.data == "my_account")
async def cb_account(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n👤 <b>حساب کاربری</b>\nشناسه: <code>{cb.from_user.id}</code>",
        reply_markup=back_kb(),
    )

# ================= هندلر: پشتیبانی =================
@dp.callback_query(F.data == "support")
async def cb_support(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🆘 <b>پشتیبانی</b>\n"
        f"<a href='https://t.me/{SUPPORT_ID}'>ارتباط با پشتیبان</a>",
        reply_markup=back_kb(),
    )

# ================= هندلر: انتخاب پلن (حلقه) =================
for key in PLANS:
    @dp.callback_query(F.data == key)
    async def cb_plan_select(cb: CallbackQuery, key=key):
        name, cap, price = PLANS[key]
        await cb.answer()
        await cb.message.edit_text(
            f"{get_time_header()}\n\n"
            f"📦 <b>{name}</b>\n"
            f"💾 حجم: {cap}\n"
            f"💰 قیمت: <b>{price}</b>\n\n"
            f"برای پرداخت، روش مورد نظرت رو انتخاب کن:",
            reply_markup=payment_kb(),
        )

# ================= هندلر: ارسال رسید =================
@dp.callback_query(F.data == "pay_send")
async def cb_pay_send(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n"
        f"💳 شماره کارت:\n<code>{PAYMENT_CARD}</code>\n"
        f"به نام: {PAYMENT_NAME}\n\n"
        f"بعد از پرداخت، رسید رو برای پشتیبان بفرست.",
        reply_markup=back_kb(),
    )

# ================= هندلر: کپی شماره کارت =================
@dp.callback_query(F.data == "pay_copy")
async def cb_pay_copy(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(
        f"💳 <code>{PAYMENT_CARD}</code>\nبه نام: {PAYMENT_NAME}"
    )

# =ه کارت =================
@dp.callback_query(F.data == "pay_copy")
async def cb_pay_copy(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(
        f"💳 <code>{PAYMENT_CARD}</code>\nبه نام: {PAYMENT_NAME}"
    )

# ================= وب‌سرور (برای Render) =================
async def start_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response.INFO)
    await start_server()
    while True:
        try:
            await dp.start_polling(bot)
        except TelegramConflictError:
            logging.warning("Conflict detected — another instance is running. Retrying in 5s...")
            await asyncio.sleep(5)
        except Exception as exc:  # هر خطا و مدیریت بازدید
            logging.exception("Unexpected error: %s", exc)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())

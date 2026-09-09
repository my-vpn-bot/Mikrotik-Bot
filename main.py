import logging
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.client.default import DefaultBotProperties
from aiohttp import web
import jdatetime
from zoneinfo import ZoneInfo

# تنظیمات
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env not set")

SUPPORT_ID = os.getenv("SUPPORT_ID", "al2tpiSupport")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338994607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", "10000"))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

PLANS = {
    "plan1m": ("اشتراک یک‌ماهه", "30 گیگابایت | 350,000 تومان", "350,000 تومان"),
    "plan2m": ("اشتراک دوماهه", "60 گیگابایت | 650,000 تومان", "650,000 تومان"),
    "plan3m": ("اشتراک سهماهه", "90 گیگابایت | 900,000 تومان", "900,000 تومان"),
}

def to_fa_digits(num_str):
    fa = "۰۱۲۳۴۵۶۷۸۹"
    return "".join(fa[int(c)] if c.isdigit() else c for c in num_str)

def get_time_header():
    now = jdatetime.datetime.now(ZoneInfo("Asia/Tehran"))
    date_fa = now.strftime("%Y/%m/%d")
    time_fa = now.strftime("%H:%M")
    return f"📅 {to_fa_digits(date_fa)} — ⏰ {to_fa_digits(time_fa)}"

def btn(text, callback_data):
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("🛒 خرید اشتراک", "buy_sub")],
        [btn("🔮 سرویس‌های آینده", "future_services")],
        [btn("👤 حساب من", "my_account")],
        [btn("🆘 پشتیبانی", "support")]
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("🔙 بازگشت به منوی اصلی", "main_menu")]])

def plans_kb():
    kb = []
    for key, (name, desc, _) in PLANS.items():
        kb.append([btn(f"📦 {name} | {desc}", key)])
    kb.append([btn("🔙 بازگشت", "main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def payment_kb(plan_key):
    _, desc, price = PLANS[plan_key]
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn(f"💸 پرداخت {price}", "pay_send")],
        [btn("💳 کپی شماره کارت", "pay_copy")],
        [btn("🔙 بازگشت به لیست پلن‌ها", "buy_sub")]
    ])

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"{get_time_header()}\n\nسلام {message.from_user.first_name} عزیز! 🙌\n"
        f"به ربات فروش اشتراک **V2Ray** خوش آمدی.",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(f"{get_time_header()}\n\n🏠 منوی اصلی:", reply_markup=main_kb())

@dp.callback_query(F.data == "buy_sub")
async def cb_buy_sub(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(f"{get_time_header()}\n\n📋 **تعرفه‌های V2Ray:**", reply_markup=plans_kb())

@dp.callback_query(F.data == "future_services")
async def cb_future(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🔮 **سرویس‌های آینده**:\n\n"
        f"✅ L2TP/IPsec\n✅ OpenVPN\n✅ WireGuard",
        reply_markup=back_kb()
    )

@dp.callback_query(F.data == "my_account")
async def cb_account(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(f"{get_time_header()}\n\n👤 شناسه کاربری: `{cb.from_user.id}`", reply_markup=back_kb())

@dp.callback_query(F.data == "support")
async def cb_support(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🆘 **پشتیبانی**:\n[ارتباط با پشتیبان](https://t.me/{SUPPORT_ID})",
        reply_markup=back_kb()
    )

@dp.callback_query(F.data == "pay_send")
async def cb_pay_send(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n💳 شماره کارت:\n`{PAYMENT_CARD}`\nبه نام: {PAYMENT_NAME}\n\nرسید را برای پشتیبان بفرست.",
        reply_markup=back_kb()
    )

@dp.callback_query(F.data == "pay_copy")
async def cb_pay_copy(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(f"💳 `{PAYMENT_CARD}`\nبه نام: {PAYMENT_NAME}")

for key in PLANS:
    @dp.callback_query(F.data == key)
    async def cb_plan_select(cb: CallbackQuery, key=key):
        await cb.answer()
        await cb.message.edit_text(f"{get_time_header()}\n\n📦 {PLANS[key][0]}\n{PLANS[key][1]}", reply_markup=payment_kb(key))

async def start_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    await start_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

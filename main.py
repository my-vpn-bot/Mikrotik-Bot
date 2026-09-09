import logging
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramConflictError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.client.default import DefaultBotProperties
from aiohttp import web
import jdatetime
from zoneinfo import ZoneInfo

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env not set")

SUPPORT_ID = os.getenv("SUPPORT_ID", "al2tpiSupport")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338994607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
HOSTING = os.getenv("HOSTING", "MikroTik V2Ray")
PORT = int(os.getenv("PORT", "10000"))

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

PLANS = {
    "plan1m": ("اشتراک یک‌ماهه", "30 گیگابایت", "250,000 تومان"),
    "plan2m": ("اشتراک دوماهه", "60 گیگابایت", "400,000 تومان"),
    "plan3m": ("اشتراک سهماهه", "90 گیگابایت", "600,000 تومان"),
}

def to_fa_digits(num_str):
    fa = "۰۱۲۳۴۵۶۷۸۹"
    return "".join(fa[int(c)] if c.isdigit() else c for c in num_str)

def get_time_header():
    now = jdatetime.datetime.now(ZoneInfo("Asia/Tehran"))
    return f"📅 {to_fa_digits(now.strftime('%Y/%m/%d'))} — ⏰ {to_fa_digits(now.strftime('%H:%M'))}"

def hb(header, sub, cdata):
    return InlineKeyboardButton(text=f"{header}\n✦ {sub}", callback_data=c.isdigit() else c for c in num_str)

def get_time_header():
    now = jdatetime.datetime.now(ZoneInfo("Asia/Tehran"))
    return f"📅 {to_fa_digits(now.strftime('%Y/%m/%d'))} — ⏰ {to_fa_digits(now.strftime('%H:%M'))}"

def hb(header, sub, cdata):
    return InlineKeyboardButton(text=f"{header}\n✦ {sub}", callback_data=c[hb("🆘 پشتیبانی", "ارتباط با پشتیبان", "support")],
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])

def plans_kb():
    kb = []
    for key, (name, cap, price) in PLANS.items():
        kb.append([hb(f"📦 {name}", f"{cap} • {price}", key)])
    kb.append([InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def payment_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 تایید و ارسال رسید", callback_data="pay_send")],
        [InlineKeyboardButton(text="💳 کپی شماره کارت", callback_data="pay_copy")],
        [InlineKeyboardButton(text="🔙 بازگشت به تعرفه‌ها", callback_data="buy_sub")],
    ])

line_keyboard=kb)

def payment_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 تایید و ارسال رسید", callback_data="pay_send")],
        [InlineKeyboardButton(text="💳 کپی شماره کارت", callback_data="pay_copy")],
        [InlineKeyboardButton(text="🔙 بازگشت به تعرفه‌ها", callback_data="buy_sub")],
    ])

@dp.message(CommandStart())
async def cmd_start def cb_main_menu(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🏠 <b>منوی اصلی</b>\nاز منوی زیر انتخاب کن:", reply_markup=main_kb()
    )

@dp.callback_query(F.data == "buy_sub")
async def cb_buy_sub(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🛒 <b>تعرفه‌های V2Ray</b>\nپلن مورد نظرت رو انتخاب کن:", reply_markup=plans_kb()
    )

@dp.callback_query(F.data == "future_services")
async def cb_future(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🔮 <b>سرویس‌های آینده</b>\n\n"
        f"✅ L2TP/IPsec\n✅ OpenVPN\n✅ WireGuard",
        reply_markup=back_kb()
    )

@dp.callback_query(F.data == "my_account")
async def cb_account(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n👤 <b>حساب کاربری</b>\nشناسه: <code>{cb.from_user.id}</code>",
        reply_markup=back_kb()
    )

@dp.callback_query(F.data == "support")
async def cb_support(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n🆘 <b>پشتیبانی</b>\n"
        f"<a href='https://t.me/{SUPPORT_ID}'>ارتباط با پشتیبان</a>",
        reply_markup=back_kb()
    )

@dp.callback_query(F.data.in_(set(PLANS)))
async def cb_plan_select(cb: CallbackQuery):
    name, cap, price = PLANS[cb.data]
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n📦 <b>{name}</b>\n"
        f"💾 حجم: {cap}\n💰 قیمت: <b>{price}</b>\n\n"
        f"برای پرداخت، روش مورد نظرت رو انتخاب کن:",
        reply_markup=payment_kb()
    )

@dp.callback_query(F.data == "pay_send")
async def cb_pay_send(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        f"{get_time_header()}\n\n💳 شماره کارت:\n<code>{PAYMENT_CARD}</code>\n"
        f"به نام: {PAYMENT_NAME}\n\n"
        f"بعد از پرداخت، رسید رو برای پشتیبان بفرست.",
        reply_markup=back_kb()
    )

@dp.callback_query(F.data == "pay_copy")
async def cb_pay_copy(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(f"💳 <code>{PAYMENT_CARD}</code>\nبه نام: {PAYMENT_NAME}")

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
    try:
        await dp.start_polling(bot)
    except TelegramConflictError:
        logging.warning("Conflict detected — restarting cleanly.")
        await asyncio.sleep(2)
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

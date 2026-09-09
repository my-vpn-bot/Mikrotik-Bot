# -*- coding: utf-8 -*-
import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ---------------- تنظیمات ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CARD_NUMBER = os.environ.get("CARD_NUMBER", "6104-XXXX-XXXX-XXXX")
CARD_HOLDER = os.environ.get("CARD_HOLDER", "نام صاحب کارت")
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "admin")

# ---------------- تعرفه‌ها ----------------
PLANS = {
    "plan_1m": {"title": "پلن ۱ ماهه", "gb": 30, "days": 30, "price": 250000},
    "plan_2m": {"title": "پلن ۲ ماهه", "gb": 60, "days": 60, "price": 400000},
    "plan_3m": {"title": "پلن ۳ ماهه", "gb": 90, "days": 90, "price": 600000},
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

class BuyState(StatesGroup):
    waiting_receipt = State()

def header():
    return "📅 وضعیت فعلی ربات\n━━━━━━━━━━━━━━━\n"

# ---------------- کیبوردها ----------------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy")],
        [InlineKeyboardButton(text="🎁 تست رایگان", callback_data="trial")],
        [InlineKeyboardButton(text="👤 پروفایل من", callback_data="profile")],
        [InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="support")],
    ])

def plans_menu():
    rows = []
    for key, p in PLANS.items():
        rows.append([InlineKeyboardButton(
            text=f"{p['title']} | {p['gb']} گیگ | {p['price']:,} تومان",
            callback_data=f"plan:{key}",
        )])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu")]])

# ---------------- هندلرها ----------------
async def safe_edit(call: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)
    await call.answer()

async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(header() + "سلام! خوش آمدید.\nیکی از موارد زیر را انتخاب کنید:", reply_markup=main_menu())

async def cb_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, header() + "منوی اصلی:", main_menu())

async def cb_buy(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, header() + "تعرفه‌های ما:", plans_menu())

async def cb_plan(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":", 1)[1]
    plan = PLANS.get(key)
    await state.update_data(plan_key=key)
    await state.set_state(BuyState.waiting_receipt)
    text = (f"خرید {plan['title']}\n"
            f"مبلغ: {plan['price']:,} تومان\n"
            f"شماره کارت: {CARD_NUMBER}\n"
            f"به نام: {CARD_HOLDER}\n\n"
            "لطفاً عکس فیش پرداختی را ارسال کنید.")
    await safe_edit(call, text, back_menu())

async def on_receipt(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("لطفاً فقط عکس رسید را بفرستید.")
        return
    await state.clear()
    await message.answer("رسید شما دریافت شد و در انتظار تایید ادمین است.")

async def cb_trial(call: CallbackQuery, state: FSMContext):
    await safe_edit(call, "سرویس تست رایگان فعلاً در دسترس نیست.", back_menu())

async def cb_profile(call: CallbackQuery, state: FSMContext):
    await safe_edit(call, "شما اشتراک فعالی ندارید.", back_menu())

async def cb_support(call: CallbackQuery, state: FSMContext):
    await safe_edit(call, f"پشتیبانی: {SUPPORT_USERNAME}", back_menu())

# ---------------- اجرا ----------------
def build_dp():
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(on_receipt, BuyState.waiting_receipt)
    dp.callback_query.register(cb_menu, F.data == "menu")
    dp.callback_query.register(cb_buy, F.data == "buy")
    dp.callback_query.register(cb_plan, F.data.startswith("plan:"))
    dp.callback_query.register(cb_trial, F.data == "trial")
    dp.callback_query.register(cb_profile, F.data == "profile")
    dp.callback_query.register(cb_support, F.data == "support")
    return dp

async def run_webhook(dp, bot):
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    from aiohttp import web
    base_url = os.environ.get("RENDER_EXTERNAL_URL")
    webhook_path = "/webhook"
    await bot.set_webhook(f"{base_url.rstrip('/')}{webhook_path}")
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)
    port = int(os.environ.get("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=port).start()
    await asyncio.Event().wait()

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dp()
    if os.environ.get("RENDER_EXTERNAL_URL"):
        await run_webhook(dp, bot)
    else:
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

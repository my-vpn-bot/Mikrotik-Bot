# -*- coding: utf-8 -*-
import os
import asyncio
import logging
from datetime import datetime

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

# ---------------- تنظیمات اصلی ----------------
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

# ---------------- ابزارهای کمکی ----------------
def get_header():
    try:
        import jdatetime
        now = jdatetime.datetime.now()
        date_str = now.strftime("%Y/%m/%d")
    except ImportError:
        date_str = datetime.now().strftime("%Y/%m/%d")
    
    time_str = datetime.now().strftime("%H:%M:%S")
    return f"📅 <b>{date_str}</b> | 🕒 <b>{time_str}</b>\n━━━━━━━━━━━━━━━\n"

async def safe_edit(call: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await call.message.answer(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    await call.answer()

# ---------------- کیبوردها ----------------
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒  خرید اشتراک  🛍", callback_data="buy")],
        [InlineKeyboardButton(text="👤  پروفایل من  📊", callback_data="profile")],
        [InlineKeyboardButton(text="👨‍💼  پنل مدیریت  🛠", callback_data="admin_panel")],
        [InlineKeyboardButton(text="🚀  سرویس‌های آینده  🔜", callback_data="future")],
        [InlineKeyboardButton(text="🎧  ارتباط با پشتیبانی  💬", callback_data="support")],
    ])

def plans_menu_kb():
    rows = []
    for key, p in PLANS.items():
        rows.append([InlineKeyboardButton(text=f"🔹 {p['title']} ({p['gb']}GB) — {p['price']:,} تومان", callback_data=f"plan:{key}")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_to_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="menu")]])

# ---------------- هندلرها ----------------
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = get_header() + "👋 <b>خوش آمدید، آرشاوین!</b>\n\n🛡 <b>به سرویس اختصاصی VPN خوش آمدید.</b>\n✨ سرعت بی‌نظیر | امنیت تضمین شده | آی‌پی ثابت\n\n👇 از منوی زیر اقدام کنید:"
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode=ParseMode.HTML)

async def cb_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, get_header() + "🏠 <b>منوی اصلی</b>\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:", main_menu_kb())

async def cb_buy(call: CallbackQuery, state: FSMContext):
    await state.clear()
    text = get_header() + "🛒 <b>لیست قیمت‌ها و پلن‌ها:</b>\n\n"
    for p in PLANS.values():
        text += f"• {p['title']}: {p['gb']} گیگ | <b>{p['price']:,} تومان</b>\n"
    text += "\n👇 پلن مورد نظر را انتخاب کنید:"
    await safe_edit(call, text, plans_menu_kb())

async def cb_plan_select(call: CallbackQuery, state: FSMContext):
    plan_key = call.data.split(":", 1)[1]
    plan = PLANS.get(plan_key)
    if not plan: return await call.answer("⚠️ خطا!", show_alert=True)
    await state.update_data(selected_plan=plan_key)
    await state.set_state(BuyState.waiting_receipt)
    text = get_header() + f"💳 <b>تایید خرید پلن: {plan['title']}</b>\n\n📦 حجم: <b>{plan['gb']} گیگابایت</b>\n💰 مبلغ: <b>{plan['price']:,} تومان</b>\n\n📍 <b>لطفاً مبلغ را به شماره زیر واریز کنید:</b>\n<code>{CARD_NUMBER}</code>\n\n👤 به نام: <b>{CARD_HOLDER}</b>\n\n📸 <b>پس از واریز، تصویر رسید را همین‌جا ارسال کنید.</b>"
    await safe_edit(call, text, back_to_menu_kb())

async def handle_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_key = data.get("selected_plan")
    plan = PLANS.get(plan_key)
    if not message.photo: return await message.answer(get_header() + "⚠️ لطفاً <b>فقط تصویر رسید</b> را ارسال کنید.")
    await state.clear()
    await message.answer_photo(photo=message.photo[-1].file_id, caption=get_header() + f"✅ <b>رسید شما با موفقیت دریافت شد!</b>\n⏳ ادمین در حال بررسی رسید است.\n\n🛒 خرید شما: <b>{plan['title']}</b>\n💰 مبلغ: <b>{plan['price']:,} تومان</b>", reply_markup=back_to_menu_kb())

async def cb_profile(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, get_header() + f"👤 <b>پروفایل کاربری</b>\n\n🆔 آیدی شما: <code>{call.from_user.id}</code>\n📛 نام: {call.from_user.full_name}\n\n📊 وضعیت اشتراک: <i>هنوز اشتراکی خریداری نشده است.</i>", back_to_menu_kb())

async def cb_admin_panel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, get_header() + "👨‍💼 <b>پنل مدیریت</b>\n\nبخش اختصاصی جهت تایید تراکنش‌ها (در حال توسعه).", back_to_menu_kb())

async def cb_future(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, get_header() + "🚀 <b>سرویس‌های آینده</b>\n\nبه زودی امکانات زیر اضافه می‌شود:\n• پروتکل‌های جدید\n• پنل اختصاصی کاربری\n• سیستم تمدید خودکار", back_to_menu_kb())

async def cb_support(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, get_header() + f"🎧 <b>پشتیبانی مستقیم</b>\n\nبرای راهنمایی با آیدی زیر در ارتباط باشید:\n💬 <b>{SUPPORT_USERNAME}</b>", back_to_menu_kb())

# ---------------- اجرا ----------------
async def run_polling(dp: Dispatcher, bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def run_webhook(dp: Dispatcher, bot: Bot):
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    from aiohttp import web
    base_url = os.environ.get("RENDER_EXTERNAL_URL")
    webhook_path = "/webhook"
    await bot.set_webhook(f"{base_url.rstrip('/')}{webhook_path}")
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)
    port = int(os.environ.get("PORT", "8000"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=port).start()
    await asyncio.Event().wait()

def build_dp():
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(handle_receipt, BuyState.waiting_receipt)
    dp.callback_query.register(cb_menu, F.data == "menu")
    dp.callback_query.register(cb_buy, F.data == "buy")
    dp.callback_query.register(cb_plan_select, F.data.startswith("plan:"))
    dp.callback_query.register(cb_profile, F.data == "profile")
    dp.callback_query.register(cb_admin_panel, F.data == "admin_panel")
    dp.callback_query.register(cb_future, F.data == "future")
    dp.callback_query.register(cb_support, F.data == "support")
    return dp

async def main():
    if not BOT_TOKEN: return
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dp()
    if os.environ.get("RENDER_EXTERNAL_URL"): await run_webhook(dp, bot)
    else: await run_polling(dp, bot)

if __name__ == "__main__":
    asyncio.run(main())

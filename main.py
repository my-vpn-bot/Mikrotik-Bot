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
    "plan_1m": {"title": "پلن ۱ ماهه", "gb": 30, "days": 30, "price": 250_000},
    "plan_2m": {"title": "پلن ۲ ماهه", "gb": 60, "days": 60, "price": 400_000},
    "plan_3m": {"title": "پلن ۳ ماهه", "gb": 90, "days": 90, "price": 600_000},
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


class BuyState(StatesGroup):
90, "days": 90, "price": 600_000},
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


class BuyState(StatesGroup):
    waiting_receipt = State()


def fa_date():
    try:
        import jdatetime
        return jdatetime.datetime.now().strftime("%Y/%m/%d return ""


# ---------------- کیبوردها (دکمه‌های دوخطی) ----------------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک\n✨ لینک اختصاصی بگیرید", callback_data="buy")],
        [InlineKeyboardButton(text="🎁 تست رایگان\n⚡ ۱ گیگ برای ۲۴ ساعت", callback_data="trial")],
        [InlineKeyboardButton(text="👤 پروفایل من\n📊 وضعیت اشتراک", callback_data="profile")],
        [InlineKeyboardButton(text="🎧 پشتیبانی\n💬 ارتباط با ادمین", callback_data="support")],
    ])


def plans_menu():
    rows = []
    for key, p in PLANS.items():
        rows.append([InlineKeyboardButton(
            text=f"🏷 {p['title']}\n💾 {p['gb']} گیگ | 💰 {p['price']:,} تومان",
            callback_data=f"plan:{key}",
        )])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت\n🏠 منوی اصلی", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت\n🏠 منوی اصلی", callback_data="menu")],
    ])


async def safe_edit(call: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)
    await call.answer()


# ---------------- هندلرها ----------------
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = (
        header()
        + "👋 <b>سلام، خوش آمدید!</b>\n\n"
        "🔒 <i>ربات فروش اشتراک اختصاصی VPN</i>\n"
        "⚡ سرعت بالا | 🛡 امنیت کامل | 🌍 IP ثابت\n\n"
        "👇 از منوی زیر انتخاب کنید:"
    )
    await message.answer(text, reply_markup=main_menu())


async def cb_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, header() + "🏠 <b>منوی اصلی</b>\n\n👇 انتخاب کنید:", main_menu())


async def cb_buy(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lines = "\n".join(
        f"• {p['title']} — {p['gb']} گیگ — <b>{p['price']:,} تومان</b>"
        for p in PLANS.values()
    )
    await safe_edit(
        call,
        header() + "🛒 <b>تعرفه‌های اشتراک</b>\n\n" + lines + "\n\n👇 پلن مورد نظر را انتخاب کنید:",
        plans_menu(),
    )


async def cb_plan(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":", 1)[1]
    plan = PLANS.get(key)
    if not plan:
        await call.answer("⚠️ پلن نامعتبر است!", show_alert=True)
        return
    await state.update_data(plan_key=key)
    await state.set_state(BuyState.waiting_receipt)
    text = (
        header()
        + f"🛒 <b>{plan['title']}</b>\n\n"
        f"💾 حجم: <b>{plan['gb']} گیگابایت</b>\n"
        f"⏳ مدت: <b>{plan['days']} روز</b>\n"
        f"💰 قیمت: <b>{plan['price']:,} تومان</b>\n\n"
        "💳 کارت به کارت:\n"
        f"<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 پس از پرداخت، <b>عکس رسید</b> را در همین چت ارسال کنید."
    )
    await safe_edit(call, text, back_menu())


async def on_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    plan = PLANS.get(data.get("plan_key", ""))
    if not plan:
        await state.clear()
        await message.answer(
            header() + "⚠️ خطا در پلن. دوباره از منوی اصلی شروع کنید.",
            reply_markup=main_menu(),
        )
        return
    if not message.photo:
        await message.answer(header() + "📸 لطفاً فقط <b>عکس رسید پرداخت</b> را ارسال کنید.")
        return
    await state.clear()
    await message.answer(
        header()
        + "✅ <b>رسید شما دریافت شد!</b>\n\n"
        f"🛒 پلن: <b>{plan['title']}</b>\n"
        f"💰 مبلغ: <b>{plan['price']:,} تومان</b>\n\n"
        "⏳ ادمین تا چند دقیقه بررسی و لینک اختصاصی را ارسال می‌کند.",
        reply_markup=back_menu(),
    )


async def cb_trial(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(
        call,
        header() + "🎁 <b>تست رایگان</b>\n\n⚡ اشتراک آزمایشی: <b>۱ گیگ — ۲۴ ساعت</b>\n\nبرای دریافت، با پشتیبانی در تماس باشید.",
        back_menu(),
    )


async def cb_profile(call: CallbackQuery, state: FSMContext):
    await state.clear()
    u = call.from_user
    username = f"@{u.username}" if u.username else "—"
    text = (
        header()
        + "👤 <b>پروفایل من</b>\n\n"
        f"🆔 آیدی: <code>{u.id}</code>\n"
        f"📛 نام: <b>{u.full_name()}</b>\n"
        f"🔗 یوزرنیم: {username}\n\n"
        "📊 اشتراک فعال: <i>ندارید</i>"
    )
    await safe_edit(call, text, back_menu())


async def cb_support(call: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 ارتباط با پشتیبانی\n🎧 چت با ادمین",
            url=f"https://t.me/{SUPPORT_USERNAME}",
        )],
        [InlineKeyboardButton(text="🔙 بازگشت\n🏠 منوی اصلی", callback_data="menu")],
    ])
    await safe_edit(call, header() + "🎧 <b>پشتیبانی</b>\n\n💬 برای ارتباط با ادمین، روی دکمه زیر بزنید.", kb)


# ---------------- اجرا ----------------
async def run_polling(dp: Dispatcher, bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_webhook(dp: Dispatcher, bot: Bot):
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    from aiohttp import web

    base = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")
    path = "/webhook"
    await bot.set_webhook(f"{base}{path}", drop_pending_updates=True)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=path)
    setup_application(app, dp, bot=bot)

    port = int(os.environ.get("PORT", "8000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    await asyncio.Event().wait()


def build_dp() -> Dispatcher:
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


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN در متغیرهای محیطی تنظیم نشده است.")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dp()
    if os.environ.get("RENDER_EXTERNAL_URL"):
        logging.info("Webhook mode (Render)")
        await run_webhook(dp, bot)
    else:
        logging.info("Polling mode")
        await run_polling(dp, bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")

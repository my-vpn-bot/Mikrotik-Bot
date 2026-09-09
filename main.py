# -*- coding: utf-8 -*-

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

# ---------------- تنظیمات اصلی ----------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

CARD_NUMBER = os.environ.get("CARD_NUMBER", "6104-XXXX-XXXX-XXXX")
CARD_HOLDER = os.environ.get("CARD_HOLDER", "نام صاحب کارت")
PAYMENT_URL = os.environ.get("PAYMENT_URL", "")
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "admin")
SUPPORT_CHAT_ID = os.environ.get("SUPPORT_CHAT_ID", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

# ---------------- تعرفه‌ها ----------------

PLANS = {
    "plan_1m": {
        "title": "پلن ۱ ماهه",
        "protocol": "V2Ray",
        "users": "نامحدود",
        "gb": 30,
        "days": 30,
        "price": 250000,
    },
    "plan_2m": {
        "title": "پلن ۲ ماهه",
        "protocol": "V2Ray",
        "users": "نامحدود",
        "gb": 60,
        "days": 60,
        "price": 400000,
    },
    "plan_3m": {
        "title": "پلن ۳ ماهه",
        "protocol": "V2Ray",
        "users": "نامحدود",
        "gb": 90,
        "days": 90,
        "price": 600000,
    },
}

PLAN_TITLES = {p["title"]: k for k, p in PLANS.items()}

MIN_TOPUP = 2_000_000
MAX_TOPUP = 5_000_000

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ---------------- وضعیت‌ها ----------------


class BuyState(StatesGroup):
    waiting_receipt = State()


class TopUpState(StatesGroup):
    waiting_amount = State()
    waiting_receipt = State()


# ---------------- ابزارهای کمکی ----------------


def jalali_date(gy: int, gm: int, gd: int) -> tuple:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    is_leap = gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)
    gy2 = gy + 1 if gm > 2 and is_leap else gy
    days = (
        355666 + 365 * gy
        + (gy2 + 3) // 4 - (gy2 - 1) // 100 + (gy2 - 1) // 400
        + gd + g_d_m[gm - 1]
    )
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def get_header() -> str:
    now = datetime.now(TEHRAN_TZ)
    jy, jm, jd = jalali_date(now.year, now.month, now.day)
    return (
        f"🕐 امروز: <b>{jy:04d}/{jm:02d}/{jd:02d}</b>"
        f" — ساعت <b>{now:%H:%M:%S}</b>\n"
        "━━━━━━━━━━━━━━━\n"
    )


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 خرید اشتراک")],
            [
                KeyboardButton(text="📊 اطلاعات حساب"),
                KeyboardButton(text="💎 اشتراک‌های من"),
            ],
            [
                KeyboardButton(text="💰 شارژ حساب"),
                KeyboardButton(text="👥 پشتیبانی"),
            ],
            [
                KeyboardButton(text="❓ سوالات متداول"),
                KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def payment_keyboard():
    if not PAYMENT_URL:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 مشاهده شماره کارت و پرداخت",
                    url=PAYMENT_URL,
                )
            ]
        ]
    )


def normalize_digits(value: str) -> str:
    translation = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )
    return (
        value.translate(translation)
        .replace(",", "")
        .replace("٬", "")
        .replace(" ", "")
    )


def support_targets() -> list:
    targets = []
    for raw_id in (SUPPORT_CHAT_ID, ADMIN_CHAT_ID):
        try:
            if raw_id:
                chat_id = int(raw_id)
                if chat_id not in targets:
                    targets.append(chat_id)
        except ValueError:
            logging.warning("Invalid support chat id: %s", raw_id)
    return targets


async def notify_support(bot: Bot, message: Message, caption: str) -> None:
    for chat_id in support_targets():
        try:
            if message.photo:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=message.photo[-1].file_id,
                    caption=caption,
                )
            else:
                await bot.send_message(chat_id=chat_id, text=caption)
        except Exception as e:
            logging.error("Failed to notify %s: %s", chat_id, e)


# ---------------- شروع ----------------


async def send_welcome(message: Message) -> None:
    first_name = (
        message.from_user.first_name
        if message.from_user and message.from_user.first_name
        else "دوست"
    )
    text = (
        f"سلام 👋 <b>{first_name}</b> عزیز، به ربات اینترنت نیم‌بها خوش اومدی.\n\n"
        "با این ربات می‌تونی اشتراک اینترنت نیم‌بها تهیه کنی و وضعیت "
        "حساب و اشتراک‌هات رو ببینی.\n\n"
        "برای ادامه یک بخش را انتخاب کنید:\n\n"
        f"{get_header()}"
    )
    await message.answer(text, reply_markup=main_menu_kb())


async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_welcome(message)


# ---------------- منوی اصلی ----------------


async def handle_main_menu(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    await state.clear()

    if text == "🛒 خرید اشتراک":
        await show_plans(message)
    elif text == "📊 اطلاعات حساب":
        await account_info(message)
    elif text == "💎 اشتراک‌های من":
        await my_subscriptions(message)
    elif text == "💰 شارژ حساب":
        await start_topup(message, state)
    elif text == "👥 پشتیبانی":
        await support_info(message)
    elif text == "❓ سوالات متداول":
        await faq(message)
    elif text == "⚙️ کانفیگ‌ها و آموزش اتصال":
        await configs_guide(message)


# ---------------- خرید اشتراک ----------------


async def show_plans(message: Message) -> None:
    lines = [get_header(), "🛒 <b>پلن‌های اشتراک V2Ray:</b>\n"]
    for plan in PLANS.values():
        lines.append(
            f"• <b>{plan['title']}</b>\n"
            f"  📊 حجم: <b>{plan['gb']} گیگابایت</b>\n"
            f"  ⏳ مدت: <b>{plan['days']} روز</b>\n"
            f"  🔐 پروتکل: <b>{plan['protocol']}</b>\n"
            f"  👤 تعداد کاربر: <b>{plan['users']}</b>\n"
            f"  💰 مبلغ: <b>{plan['price']:,} تومان</b>\n"
        )
    lines.append(
        "👇 برای خرید، نام پلن موردنظر را ارسال کنید:\n"
        "<code>پلن ۱ ماهه</code> / <code>پلن ۲ ماهه</code> / <code>پلن ۳ ماهه</code>"
    )
    await message.answer("\n".join(lines), reply_markup=main_menu_kb())


async def plan_message(message: Message, state: FSMContext) -> None:
    plan_key = PLAN_TITLES.get(message.text or "")
    if not plan_key:
        return

    plan = PLANS[plan_key]
    await state.update_data(selected_plan=plan_key)
    await state.set_state(BuyState.waiting_receipt)

    text = (
        f"{get_header()}\n"
        f"💳 <b>تایید خرید {plan['title']}</b>\n\n"
        f"📦 حجم: <b>{plan['gb']} گیگابایت</b>\n"
        f"⏳ مدت: <b>{plan['days']} روز</b>\n"
        f"🔐 پروتکل: <b>{plan['protocol']}</b>\n"
        f"👤 تعداد کاربر: <b>{plan['users']}</b>\n"
        f"💰 مبلغ: <b>{plan['price']:,} تومان</b>\n\n"
        f"📍 شماره کارت:\n<code>{CARD_NUMBER}</code>\n\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 <b>پس از واریز، تصویر رسید را ارسال کنید.</b>"
    )

    await message.answer(text, reply_markup=payment_keyboard())
    await message.answer(
        "برای بازگشت به منوی اصلی از دکمه‌های زیر استفاده کنید.",
        reply_markup=main_menu_kb(),
    )


async def handle_purchase_receipt(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    plan = PLANS.get(data.get("selected_plan"))

    if not plan:
        await state.clear()
        await message.answer(
            "اطلاعات خرید منقضی شده است. لطفاً مجدداً از منوی "
            "«🛒 خرید اشتراک» اقدام کنید.",
            reply_markup=main_menu_kb(),
        )
        return

    if not message.photo:
        await message.answer(
            "⚠️ لطفاً تصویر رسید خرید را ارسال کنید.",
            reply_markup=main_menu_kb(),
        )
        return

    caption = (
        "🧾 <b>رسید خرید اشتراک جدید</b>\n"
        f"👤 کاربر: {message.from_user.full_name} "
        f"(<code>{message.from_user.id}</code>)\n"
        f"📦 پلن: {plan['title']}\n"
        f"🔐 پروتکل: {plan['protocol']}\n"
        f"👤 تعداد کاربر: {plan['users']}\n"
        f"📊 حجم: {plan['gb']} گیگابایت\n"
        f"⏳ مدت: {plan['days']} روز\n"
        f"💰 مبلغ: {plan['price']:,} تومان"
    )

    await notify_support(message.bot, message, caption)
    await state.clear()

    await message.answer(
        "✅ <b>رسید شما دریافت شد و برای بررسی به پشتیبانی ارسال گردید.</b>",
        reply_markup=main_menu_kb(),
    )


# ---------------- اطلاعات حساب ----------------


async def account_info(message: Message) -> None:
    user = message.from_user
    await message.answer(
        f"{get_header()}\n"
        "📊 <b>اطلاعات حساب</b>\n\n"
        f"🆔 شناسه کاربری: <code>{user.id}</code>\n"
        f"📛 نام: {user.full_name}\n\n"
        "وضعیت کیف پول و اشتراک در حال حاضر ثبت نشده است.",
        reply_markup=main_menu_kb(),
    )


async def my_subscriptions(message: Message) -> None:
    await message.answer(
        f"{get_header()}\n"
        "💎 <b>اشتراک‌های من</b>\n\n"
        "در حال حاضر اشتراک فعالی برای حساب شما یافت نشد.",
        reply_markup=main_menu_kb(),
    )


# ---------------- شارژ حساب ----------------


async def start_topup(message: Message, state: FSMContext) -> None:
    await state.set_state(TopUpState.waiting_amount)
    await message.answer(
        f"{get_header()}\n"
        "💰 <b>شارژ حساب</b>\n\n"
        "مبلغ موردنظر را به تومان وارد کنید.\n"
        f"▫️ حداقل شارژ: <b>{MIN_TOPUP:,}</b> تومان\n"
        f"▫️ حداکثر شارژ: <b>{MAX_TOPUP:,}</b> تومان",
        reply_markup=main_menu_kb(),
    )


async def topup_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = int(normalize_digits(message.text or ""))
    except ValueError:
        await message.answer(
            "⚠️ لطفاً مبلغ را فقط به‌صورت عددی و به تومان وارد کنید.",
            reply_markup=main_menu_kb(),
        )
        return

    if not MIN_TOPUP <= amount <= MAX_TOPUP:
        await message.answer(
            f"⚠️ مبلغ شارژ باید بین {MIN_TOPUP:,} تا {MAX_TOPUP:,} تومان باشد.",
            reply_markup=main_menu_kb(),
        )
        return

    await state.update_data(topup_amount=amount)
    await state.set_state(TopUpState.waiting_receipt)

    await message.answer(
        f"مبلغ اعلامی: <b>{amount:,} تومان</b>\n\n"
        f"📍 شماره کارت:\n<code>{CARD_NUMBER}</code>\n\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 پس از واریز، لطفاً تصویر فیش واریزی را ارسال نمایید.",
        reply_markup=payment_keyboard(),
    )
    await message.answer(
        "برای بازگشت به منوی اصلی از دکمه‌های زیر استفاده کنید.",
        reply_markup=main_menu_kb(),
    )


async def topup_receipt(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer(
            "⚠️ لطفاً تصویر رسید واریز را ارسال کنید.",
            reply_markup=main_menu_kb(),
        )
        return

    data = await state.get_data()
    amount = data.get("topup_amount", 0)

    caption = (
        "🧾 <b>رسید شارژ حساب کاربری</b>\n"
        f"👤 کاربر: {message.from_user.full_name} "
        f"(<code>{message.from_user.id}</code>)\n"
        f"💰 مبلغ اعلامی: {amount:,} تومان"
    )

    await notify_support(message.bot, message, caption)
    await state.clear()

    await message.answer(
        "✅ <b>رسید شارژ حساب دریافت شد و جهت تأیید به پشتیبانی ارسال گردید.</b>",
        reply_markup=main_menu_kb(),
    )


# ---------------- پشتیبانی و راهنما ----------------


async def support_info(message: Message) -> None:
    username = SUPPORT_USERNAME.lstrip("@")
    await message.answer(
        f"{get_header()}\n"
        "👥 <b>پشتیبانی</b>\n\n"
        "جهت ارتباط مستقیم با پشتیبانی از آیدی زیر استفاده کنید:\n"
        f"💬 <b>@{username}</b>",
        reply_markup=main_menu_kb(),
    )


async def faq(message: Message) -> None:
    text = (
        f"{get_header()}\n"
        "❓ <b>سوالات متداول</b>\n\n"
        "🔹 <b>چگونه اشتراک تهیه کنم؟</b>\n"
        "از گزینه «🛒 خرید اشتراک» پلن موردنظر را انتخاب و پس از واریز، "
        "فیش را بفرستید.\n\n"
        "🔹 <b>شارژ حساب چقدر زمان می‌برد؟</b>\n"
        "پس از ارسال فیش، ادمین در اسرع وقت مبلغ را تأیید و حسابتان را "
        "شارژ می‌کند.\n\n"
        "🔹 <b>پروتکل اتصال چیست؟</b>\n"
        "سرویس‌ها با پروتکل V2Ray ارائه می‌شوند."
    )
    await message.answer(text, reply_markup=main_menu_kb())


async def configs_guide(message: Message) -> None:
    text = (
        f"{get_header()}\n"
        "⚙️ <b>کانفیگ‌ها و آموزش اتصال</b>\n\n"
        "📱 <b>اندروید:</b> نرم‌افزار v2rayNG\n"
        "🍏 <b>آیفون:</b> Streisand یا FoXray / V2Box\n"
        "💻 <b>ویندوز:</b> v2rayN یا Nekoray\n\n"
        "پس از فعال‌سازی اشتراک، لینک اتصال اختصاصی برای شما ارسال خواهد شد."
    )
    await message.answer(text, reply_markup=main_menu_kb())


# ---------------- اجرا ----------------


async def run_polling(dp: Dispatcher, bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_webhook(dp: Dispatcher, bot: Bot) -> None:
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import (
        SimpleRequestHandler,
        setup_application,
    )

    base_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not base_url:
        raise RuntimeError("RENDER_EXTERNAL_URL is not set")

    webhook_path = "/webhook"
    webhook_url = f"{base_url.rstrip('/')}{webhook_path}"
    await bot.set_webhook(webhook_url)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)

    port = int(os.environ.get("PORT", "8000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logging.info("Webhook server started on port %s", port)
    await asyncio.Event().wait()


def build_dp() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(handle_purchase_receipt, BuyState.waiting_receipt)
    dp.message.register(topup_amount, TopUpState.waiting_amount)
    dp.message.register(topup_receipt, TopUpState.waiting_receipt)
    dp.message.register(plan_message, F.text.in_(set(PLAN_TITLES.keys())))
    dp.message.register(handle_main_menu, F.text)

    return dp


async def main() -> None:
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dp()

    if os.environ.get("RENDER_EXTERNAL_URL"):
        await run_webhook(dp, bot)
    else:
        await run_polling(dp, bot)


if __name__ == "__main__":
    asyncio.run(main())

"""Mikrotik-Bot — Telegram bot for V2Ray subscription sales."""
import asyncio
import logging
import os
import re
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ---------------- Config ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CARD_NUMBER = os.getenv("CARD_NUMBER", "")
CARD_HOLDER = os.getenv("CARD_HOLDER", "")
PAYMENT_URL = os.getenv("PAYMENT_URL", "")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "")
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# ---------------- Plans ----------------
PLANS = {
    "1m": {"title": "پلن ۱ ماهه", "gb": 30, "days": 30, "protocol": "V2Ray", "users": 1, "price": 100000},
    "2m": {"title": "پلن ۲ ماهه", "gb": 60, "days": 60, "protocol": "V2Ray", "users": 1, "price": 180000},
    "3m": {"title": "پلن ۳ ماهه", "gb": 100, "days": 90, "protocol": "V2Ray", "users": 1, "price": 250000},
}

PLAN_TITLES = {plan["title"]: key for key, plan in PLANS.items()}


# ---------------- States ----------------
class BuyState(StatesGroup):
    waiting_receipt = State()


class TopUpState(StatesGroup):
    waiting_amount = State()
    waiting_receipt = State()


# ---------------- Helpers ----------------
def get_header() -> str:
    return "🛡️ <b>ربات Mikrotik-Bot</b>\n"


def main_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy")],
        [
            InlineKeyboardButton(text="📊 اطلاعات حساب", callback_data="account"),
            InlineKeyboardButton(text="💎 اشتراک‌های من", callback_data="my_subs"),
        ],
        [
            InlineKeyboardButton(text="💰 شارژ حساب", callback_data="topup"),
            InlineKeyboardButton(text="👥 پشتیبانی", callback_data="support"),
        ],
        [
            InlineKeyboardButton(text="❓ سوالات متداول", callback_data="faq"),
            InlineKeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال", callback_data="configs"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    if PAYMENT_URL:
        buttons.append(
            [InlineKeyboardButton(text="🌐 مشاهده صفحه پرداخت", url=PAYMENT_URL)]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------------- Start ----------------
async def cmd_start(message: Message) -> None:
    text = (
        f"{get_header()}\n"
        "👋 سلام آرشاوین جان! به ربات خوش آمدید.\n"
        "از منوی زیر انتخاب کنید:"
    )
    await message.answer(text, reply_markup=main_menu_kb())


# ---------------- Plans ----------------
async def show_plans(message: Message) -> None:
    lines = [
        get_header(),
        "🛒 <b>پلن‌های اشتراک V2Ray:</b>\n",
    ]

    buttons = []

    for plan_key, plan in PLANS.items():
        lines.append(
            f"• <b>{plan['title']}</b>\n"
            f"  📊 حجم: <b>{plan['gb']} گیگابایت</b>\n"
            f"  ⏳ مدت: <b>{plan['days']} روز</b>\n"
            f"  🔐 پروتکل: <b>{plan['protocol']}</b>\n"
            f"  👤 تعداد کاربر: <b>{plan['users']}</b>\n"
            f"  💰 مبلغ: <b>{plan['price']:,} تومان</b>\n"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"✅ خرید {plan['title']}",
                    callback_data=f"buy:{plan_key}",
                )
            ]
        )

    lines.append("👇 پلن موردنظر را از دکمه‌های زیر انتخاب کنید:")

    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


async def plan_callback(callback, state: FSMContext) -> None:
    await callback.answer()

    plan_key = callback.data.split(":", 1)[1]
    plan = PLANS.get(plan_key)

    if not plan:
        await callback.message.answer(
            "⚠️ این پلن دیگر معتبر نیست.",
            reply_markup=main_menu_kb(),
        )
        return

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

    await callback.message.answer(
        text,
        reply_markup=payment_keyboard(),
    )

    await callback.message.answer(
        "برای بازگشت به منوی اصلی از دکمه‌های زیر استفاده کنید.",
        reply_markup=main_menu_kb(),
    )


# ---------------- Main menu handler ----------------
async def handle_main_menu(message: Message) -> None:
    text = message.text or ""

    if text == "🛒 خرید اشتراک":
        await show_plans(message)
        return

    elif text == "☰ منو":
        await message.answer(
            f"{get_header()}\nمنوی اصلی:",
            reply_markup=main_menu_kb(),
        )
        return

    await message.answer(
        f"{get_header()}\n"
        "⚠️ گزینه معتبر نیست. لطفاً از منوی زیر انتخاب کنید:",
        reply_markup=main_menu_kb(),
    )


# ---------------- Placeholder handlers for text menu items ----------------
async def plan_message(message: Message) -> None:
    plan_key = PLAN_TITLES.get(message.text)
    if plan_key:
        plan = PLANS[plan_key]
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


async def handle_purchase_receipt(message: Message, state: FSMContext) -> None:
    await message.answer("رسید شما دریافت شد. به‌زودی تأیید می‌شود. ✅")
    await state.clear()


async def topup_amount(message: Message, state: FSMContext) -> None:
    await message.answer("مبلغ شارژ را وارد کنید:")
    await state.set_state(TopUpState.waiting_amount)


async def topup_receipt(message: Message, state: FSMContext) -> None:
    await message.answer("رسید شارژ دریافت شد. به‌زودی تأیید می‌شود. ✅")
    await state.clear()


# ---------------- Dispatcher ----------------
def build_dp() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start, CommandStart())

    dp.callback_query.register(
        plan_callback,
        F.data.startswith("buy:"),
    )

    dp.message.register(
        handle_purchase_receipt,
        BuyState.waiting_receipt,
    )

    dp.message.register(
        topup_amount,
        TopUpState.waiting_amount,
    )

    dp.message.register(
        topup_receipt,
        TopUpState.waiting_receipt,
    )

    dp.message.register(
        plan_message,
        F.text.in_(set(PLAN_TITLES.keys())),
    )

    dp.message.register(
        handle_main_menu,
        F.text,
    )

    return dp


# ---------------- Main ----------------
async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dp()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

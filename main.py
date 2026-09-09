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
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

# ---------------- تنظیمات اصلی ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CARD_NUMBER = os.environ.get("CARD_NUMBER", "6104-XXXX-XXXX-XXXX")
CARD_HOLDER = os.environ.get("CARD_HOLDER", "نام صاحب کارت")
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "admin")
SUPPORT_CHAT_ID = os.environ.get("SUPPORT_CHAT_ID", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "")

# ---------------- تعرفه‌ها ----------------
PLANS = {
    "plan_1m": {"title": "پلن ۱ ماهه", "gb": 30, "days": 30, "price": 250000},
    "plan_2m": {"title": "پلن ۲ ماهه", "gb": 60, "days": 60, "price": 400000},
    "plan_3m": {"title": "پلن ۳ ماهه", "gb": 90, "days": 90, "price": 600000},
}

MIN_TOPUP = 2_000_000
MAX_TOPUP = 5_000_000
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


class BuyState(StatesGroup):
    waiting_receipt = State()


class TopUpState(StatesGroup):
    waiting_amount = State()
    waiting_receipt = State()


# ---------------- ابزارهای کمکی ----------------
def jalali_date(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """تبدیل تاریخ میلادی به شمسی بدون نیاز به کتابخانه جانبی"""
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    gy -= 1600
    gm -= 1
    gd -= 1
    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for month in range(gm):
        g_day_no += g_days_in_month[month]
    if gm > 1 and (gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)):
        g_day_no += 1
    g_day_no += gd
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    for month in range(11):
        if j_day_no < j_days_in_month[month]:
            jm = month + 1
            jd = j_day_no + 1
            return jy, jm, jd
        j_day_no -= j_days_in_month[month]
    return jy, 12, j_day_no + 1


def get_header() -> str:
    now = datetime.now(TEHRAN_TZ)
    jy, jm, jd = jalali_date(now.year, now.month, now.day)
    return f"🕐 امروز: <b>{jy:04d}/{jm:02d}/{jd:02d}</b> — ساعت <b>{now:%H:%M:%S}</b>\n━━━━━━━━━━━━━━━\n"


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 خرید اشتراک")],
            [KeyboardButton(text="📊 اطلاعات حساب"), KeyboardButton(text="💎 اشتراک‌های من")],
            [KeyboardButton(text="💰 شارژ حساب"), KeyboardButton(text="👥 پشتیبانی")],
            [KeyboardButton(text="❓ سوالات متداول"), KeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def normalize_digits(value: str) -> str:
    translation = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return value.translate(translation).replace(",", "").replace("٬", "").replace(" ", "")


def support_targets() -> list[int]:
    targets = []
    for raw_id in (SUPPORT_CHAT_ID, ADMIN_CHAT_ID):
        try:
            if raw_id and int(raw_id) not in targets:
                targets.append(int(raw_id))
        except ValueError:
            logging.warning("Invalid support chat id: %s", raw_id)
    return targets


async def notify_support(bot: Bot, message: Message, caption: str) -> None:
    for chat_id in support_targets():
        if message.photo:
            await bot.send_photo(chat_id, message.photo[-1].file_id, caption=caption)
        else:
            await bot.send_message(chat_id, caption)


# ---------------- هندلرهای پیام و منو ----------------
async def send_welcome(message: Message) -> None:
    first_name = message.from_user.first_name or "دوست"
    text = (
        f"سلام 👋 <b>{first_name}</b> عزیز به ربات اینترنت نیم‌بها خوش اومدی.\n\n"
        "با این ربات می‌تونی اشتراک اینترنت نیم‌بها تهیه کنی و وضعیت حساب و اشتراک‌هات رو ببینی.\n\n"
        "برای ادامه یک بخش را انتخاب کنید:\n\n"
        f"{get_header()}"
    )
    await message.answer(text, reply_markup=main_menu_kb())


async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await send_welcome(message)


async def handle_main_menu(message: Message, state: FSMContext):
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


async def show_plans(message: Message):
    lines = [get_header(), "🛒 <b>پلن‌های اشتراک:</b>\n"]
    for plan in PLANS.values():
        lines.append(f"• <b>{plan['title']}</b>: {plan['gb']} گیگ، {plan['days']} روز — <b>{plan['price']:,} تومان</b>")
    lines += ["\n👇 برای خرید، نام پلن موردنظر را ارسال کنید:\n<code>پلن ۱ ماهه</code> / <code>پلن ۲ ماهه</code> / <code>پلن ۳ ماهه</code>"]
    await message.answer("\n".join(lines), reply_markup=main_menu_kb())


async def plan_message(message: Message, state: FSMContext):
    mapping = {"پلن ۱ ماهه": "plan_1m", "پلن ۲ ماهه": "plan_2m", "پلن ۳ ماهه": "plan_3m"}
    plan_key = mapping.get(message.text or "")
    if not plan_key:
        return
    plan = PLANS[plan_key]
    await state.update_data(selected_plan=plan_key)
    await state.set_state(BuyState.waiting_receipt)
    text = (
        f"{get_header()}💳 <b>تایید خرید {plan['title']}</b>\n\n"
        f"📦 حجم: <b>{plan['gb']} گیگابایت</b>\n"
        f"⏳ مدت: <b>{plan['days']} روز</b>\n"
        f"💰 مبلغ: <b>{plan['price']:,} تومان</b>\n\n"
        f"📍 شماره کارت:\n<code>{CARD_NUMBER}</code>\n\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 <b>پس از واریز، تصویر رسید را ارسال کنید.</b>"
    )
    await message.answer(text, reply_markup=main_menu_kb())


async def handle_purchase_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    plan = PLANS.get(data.get("selected_plan"))
    if not plan:
        await state.clear()
        return await message.answer("اطلاعات خرید منقضی شده است. لطفاً مجدداً از منوی «🛒 خرید اشتراک» اقدام کنید.", reply_markup=main_menu_kb())
    if not message.photo:
        return await message.answer("⚠️ لطفاً تصویر رسید خرید را ارسال کنید.", reply_markup=main_menu_kb())
    caption = (
        "🧾 <b>رسید خرید اشتراک جدید</b>\n"
        f"👤 کاربر: {message.from_user.full_name} (<code>{message.from_user.id}</code>)\n"
        f"📦 پلن: {plan['title']} | {plan['gb']}GB | {plan['price']:,} تومان"
    )
    await notify_support(message.bot, message, caption)
    await state.clear()
    await message.answer("✅ <b>رسید شما دریافت شد و برای بررسی پشتیبانی ارسال گردید.</b>", reply_markup=main_menu_kb())


async def account_info(message: Message):
    user = message.from_user
    await message.answer(
        f"{get_header()}📊 <b>اطلاعات حساب</b>\n\n🆔 شناسه کاربری: <code>{user.id}</code>\n📛 نام: {user.full_name}\n\nوضعیت کیف پول و اشتراک در حال حاضر ثبت نشده است.",
        reply_markup=main_menu_kb(),
    )


async def my_subscriptions(message: Message):
    await message.answer(f"{get_header()}💎 <b>اشتراک‌های من</b>\n\nدر حال حاضر اشتراک فعالی برای حساب شما یافت نشد.", reply_markup=main_menu_kb())


async def start_topup(message: Message, state: FSMContext):
    await state.set_state(TopUpState.waiting_amount)
    await message.answer(
        f"{get_header()}💰 <b>شارژ حساب</b>\n\nمبلغ موردنظر را به تومان وارد کنید.\n"
        f"▫️ حداقل شارژ: <b>{MIN_TOPUP:,}</b> تومان\n"
        f"▫️ حداکثر شارژ: <b>{MAX_TOPUP:,}</b> تومان",
        reply_markup=main_menu_kb(),
    )


async def topup_amount(message: Message, state: FSMContext):
    try:
        amount = int(normalize_digits(message.text or ""))
    except ValueError:
        return await message.answer("⚠️ لطفاً مبلغ را فقط به‌صورت عددی و به تومان وارد کنید.", reply_markup=main_menu_kb())
    if not MIN_TOPUP <= amount <= MAX_TOPUP:
        return await message.answer(f"⚠️ مبلغ شارژ باید بین {MIN_TOPUP:,} تا {MAX_TOPUP:,} تومان باشد.", reply_markup=main_menu_kb())
    
    await state.update_data(topup_amount=amount)
    await state.set_state(TopUpState.waiting_receipt)
    await message.answer(
        f"مبلغ اعلامی: <b>{amount:,} تومان</b>\n\n"
        f"📍 شماره کارت:\n<code>{CARD_NUMBER}</code>\n\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 پس از واریز، لطفاً تصویر فیش واریزی را ارسال نمایید.",
        reply_markup=main_menu_kb(),
    )


async def topup_receipt(message: Message, state: FSMContext):
    if not message.photo:
        return await message.answer("⚠️ لطفاً تصویر رسید واریز را ارسال کنید.", reply_markup=main_menu_kb())
    data = await state.get_data()
    amount = data.get("topup_amount", 0)
    caption = (
        "🧾 <b>رسید شارژ حساب کاربری</b>\n"
        f"👤 کاربر: {message.from_user.full_name} (<code>{message.from_user.id}</code>)\n"
        f"💰 مبلغ اعلامی: {amount:,} تومان"
    )
    await notify_support(message.bot, message, caption)
    await state.clear()
    await message.answer("✅ <b>رسید شارژ حساب دریافت شد و جهت تایید به پشتیبانی ارسال گردید.</b>", reply_markup=main_menu_kb())


async def support_info(message: Message):
    await message.answer(f"{get_header()}👥 <b>پشتیبانی</b>\n\nجهت ارتباط مستقیم با پشتیبانی از آیدی زیر استفاده کنید:\n💬 <b>@{SUPPORT_USERNAME.lstrip('@')}</b>", reply_markup=main_menu_kb())


async def faq(message: Message):
    text = (
        f"{get_header()}❓ <b>سوالات متداول</b>\n\n"
        "🔹 <b>چگونه اشتراک تهیه کنم؟</b>\n"
        "از گزینه «🛒 خرید اشتراک» پلن مورد نظر را انتخاب و پس از واریز، فیش را بفرستید.\n\n"
        "🔹 <b>شارژ حساب چقدر زمان می‌برد؟</b>\n"
        "پس از ارسال فیش، ادمین در اسرع وقت مبلغ را تایید و حسابتان را شارژ می‌کند.\n\n"
        "🔹 <b>پروتکل اتصال چیست؟</b>\n"
        "سرویس‌ها با پروتکل‌های V2Ray و آی‌پی پایدار ارائه می‌شوند."
    )
    await message.answer(text, reply_markup=main_menu_kb())


async def configs_guide(message: Message):
    text = (
        f"{get_header()}⚙️ <b>کانفیگ‌ها و آموزش اتصال</b>\n\n"
        "📱 <b>اندروید:</b> نرم‌افزار v2rayNG\n"
        "🍏 <b>آیفون (iOS):</b> نرم‌افزارهای Streisand یا FoXray / V2Box\n"
        "💻 <b>ویندوز:</b> نرم‌افزار v2rayN یا Nekoray\n\n"
        "پس از فعال‌سازی اشتراک، لینک اتصال اختصاصی برای شما ارسال خواهد شد."
    )
    await message.answer(text, reply_markup=main_menu_kb())


# ---------------- اجرا ----------------
async def run_polling(dp: Dispatcher, bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_webhook(dp: Dispatcher, bot: Bot):
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

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
    dp.message.register(handle_purchase_receipt, BuyState.waiting_receipt)
    dp.message.register(topup_amount, TopUpState.waiting_amount)
    dp.message.register(topup_receipt, TopUpState.waiting_receipt)
    dp.message.register(plan_message, F.text.in_({"پلن ۱ ماهه", "پلن ۲ ماهه", "پلن ۳ ماهه"}))
    dp.message.register(handle_main_menu, F.text)
    return dp


async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set")
        return
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dp()
    if os.environ.get("RENDER_EXTERNAL_URL"):
        await run_webhook(dp, bot)
    else:
        await run_polling(dp, bot)


if __name__ == "__main__":
    asyncio.run(main())

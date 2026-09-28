import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from magic_filter import F


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# Configuration
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "GAPGPTMASKTOKENa714892oaX0X")

ADMIN_ID = int(os.getenv("ADMIN_ID", "2786850266"))
PORT = int(os.getenv("PORT", "10000"))

CHANNEL_URL = os.getenv(
    "CHANNEL_URL",
    "https://t.me/L2tp_vpn402",
)

SUPPORT_ID = os.getenv(
    "SUPPORT_ID",
    "@L2tp1Support",
)

SUPPORT_URL = (
    SUPPORT_ID
    if SUPPORT_ID.startswith("http")
    else f"https://t.me/{SUPPORT_ID.lstrip('@')}"
)

BOT_URL = "https://t.me/L2TP_Arshavin_Bot"

IBSNG_PANEL_URL = os.getenv(
    "IBSNG_PANEL_URL",
    "http://94.184.45.58:48201/IBSng/user/",
)

PAYMENT_CARD = os.getenv(
    "PAYMENT_CARD",
    "6104338904607443",
)

PAYMENT_NAME = os.getenv(
    "PAYMENT_NAME",
    "رحیمی",
)

VPN_SERVER_IP = "94.184.43.106"
IBSNG_SERVER_IP = "94.184.45.58"
IPSEC_SECRET = "GAPGPTMASKTOKENa714892oaX1X"

DB_FILE = "bot_database.db"


# ============================================================
# Date and text helpers
# ============================================================

PERSIAN_DIGITS = str.maketrans(
    "0123456789",
    "۰۱۲۳۴۵۶۷۸۹",
)

PERSIAN_WEEKDAYS = [
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
    "شنبه",
    "یکشنبه",
]

PERSIAN_MONTHS = [
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
]


def to_persian_digits(value) -> str:
    return str(value).translate(PERSIAN_DIGITS)


def gregorian_to_jalali(year: int, month: int, day: int):
    """
    تبدیل تاریخ میلادی به شمسی بدون نیاز به کتابخانه جانبی.
    """
    g_days_in_month = [
        31,
        28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]

    gy = year - 1600
    gm = month - 1
    gd = day - 1

    g_day_no = 365 * gy
    g_day_no += (gy + 3) // 4
    g_day_no -= (gy + 99) // 100
    g_day_no += (gy + 399) // 400

    for index in range(gm):
        g_day_no +=        g_day_no +=]

    if gm > 1 and (
        year % 4 == 0
        and (year % 100 != 0 or year % 400 == 0)
    ):
        g_day_no += 1

    g_day_no += gd
    j_day_no = g_day_no - 79

    j_np = j_day_no // 12053
    j_day_no %= 12053

    jy = 979 + 33 * j_np
    jy += 4 * (j_day_no // 1461)
    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    if j_day_no < 186:
        jm = 1 + j_day_no // 31
        jd = 1 + j_day_no % 31
    else:
        jm = 7 + (j_day_no - 186) // 30
        jd = 1 + (j_day_no - 186) % 30

    return jy, jm, jd


def get_tehran_now() -> datetime:
    try:
        return datetime.now(ZoneInfo("Asia/Tehran"))
    except Exception:
        return datetime.now(
            timezone(timedelta(hours=3, minutes=30))
        )


def get_full_date_text() -> str:
    now = get_tehran_now()
    jalali_year, jalali_month, jalali_day = gregorian_to_jalali(
        now.year,
        now.month,
        now.day,
    )

    weekday = PERSIAN_WEEKDAYS[now.weekday()]
    month_name = PERSIAN_MONTHS[jalali_month - 1]

    return (
        f"{weekday}، "
        f"{to_persian_digits(jalali_day)} "
        f"{month_name} "
        f"{to_persian_digits(jalali_year)}"
    )


def get_time_text() -> str:
    now = get_tehran_now()
    return to_persian_digits(now.strftime("%H:%M:%S"))


def clean_text(value: str, default: str = "نامشخص") -> str:
    if not value:
        return default
    return escape(str(value).strip())


async def safe_delete(message: Message | None):
    if message is None:
        return

    try:
        await message.delete()
    except Exception:
        pass


# ============================================================
# Database
# ============================================================

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_name TEXT,
                amount TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()


def add_user(
    user_id: int,
    username: str,
    first_name: str,
):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users
            (user_id, username, first_name)
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                username,
                first_name,
            ),
        )
        conn.commit()


def record_payment(
    user_id: int,
    plan_name: str,
    amount: str,
) -> int:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO payments
            (user_id, plan_name, amount, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (
                user_id,
                plan_name,
                amount,
            ),
        )

        conn.commit()
        return int(cursor.lastrowid)


def update_payment_status(
    payment_id: int,
    status: str,
) -> bool:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE payments
            SET status = ?
            WHERE id = ?
            """,
            (
                status,
                payment_id,
            ),
        )

        conn.commit()
        return cursor.rowcount > 0


def get_stats():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM users
            WHERE DATE(joined_at) = DATE('now')
            """
        )
        today_users = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM payments
            WHERE status = 'approved'
            """
        )
        approved_payments = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM payments
            WHERE status = 'pending'
            """
        )
        pending_payments = cursor.fetchone()[0]

        return (
            total_users,
            today_users,
            approved_payments,
            pending_payments,
        )


init_db()


# ============================================================
# FSM states
# ============================================================

class OrderStates(StatesGroup):
    choosing_plan = State()
    waiting_for_receipt = State()


class RenewalStates(StatesGroup):
    waiting_for_username = State()
    choosing_plan = State()
    waiting_for_receipt = State()


class SupportStates(StatesGroup):
    waiting_for_vpn_username = State()
    waiting_for_message = State()


# ============================================================
# Keyboards
# ============================================================

def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="🛍 خرید اشتراک"),
        ],
        [
            KeyboardButton(text="🔄 تمدید اشتراک"),
        ],
        [
            KeyboardButton(text="📊 ورود به پنل کاربری"),
        ],
        [
            KeyboardButton(text="📚 راهنمای اتصال"),
            KeyboardButton(text="💬 پشتیبانی"),
        ],
        [
            KeyboardButton(text="📢 کانال اطلاع‌رسانی"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )


def get_plans_inline_keyboard(
    prefix: str = "buy",
) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="۱ ماهه تک‌کاربره (۲۰۰ ت)",
                callback_data=f"{prefix}_1m_1u",
            ),
            InlineKeyboardButton(
                text="۱ ماهه دوکاربره (۲۵۰ ت)",
                callback_data=f"{prefix}_1m_2u",
            ),
        ],
        [
            InlineKeyboardButton(
                text="۲ ماهه تک‌کاربره (۳۸۰ ت)",
                callback_data=f"{prefix}_2m_1u",
            ),
            InlineKeyboardButton(
                text="۲ ماهه دوکاربره (۴۳۰ ت)",
                callback_data=f"{prefix}_2m_2u",
            ),
        ],
        [
            InlineKeyboardButton(
                text="۳ ماهه تک‌کاربره (۵۵۰ ت)",
                callback_data=f"{prefix}_3m_1u",
            ),
            InlineKeyboardButton(
                text="۳ ماهه دوکاربره (۶۰۰ ت)",
                callback_data=f"{prefix}_3m_2u",
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ انصراف",
                callback_data="cancel_action",
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_guides_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text="📱 آیفون و آیپد",
                callback_data="guide_ios",
            ),
            InlineKeyboardButton(
                text="🤖 اندروید",
                callback_data="guide_android",
            ),
        ],
        [
            InlineKeyboardButton(
                text="💻 ویندوز",
                callback_data="guide_windows",
            ),
            InlineKeyboardButton(
                text="🍏 مک‌او‌اس",
                callback_data="guide_mac",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🌐 مودم و روتر",
                callback_data="guide_general",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🏠 منوی اصلی",
                callback_data="back_main",
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ============================================================
# Bot and dispatcher
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
    ),
)

dp = Dispatcher(storage=MemoryStorage())


PLANS_DATA = {
    "1m_1u": (
        "۱ ماهه - ۱ کاربره",
        "۲۰۰,۰۰۰ تومان",
    ),
    "1m_2u": (
        "۱ ماهه - ۲ کاربره",
        "۲۵۰,۰۰۰ تومان",
    ),
    "2m_1u": (
        "۲ ماهه - ۱ کاربره",
        "۳۸۰,۰۰۰ تومان",
    ),
    "2m_2u": (
        "۲ ماهه - ۲ کاربره",
        "۴۳۰,۰۰۰ تومان",
    ),
    "3m_1u": (
        "۳ ماهه - ۱ کاربره",
        "۵۵۰,۰۰۰ تومان",
    ),
    "3m_2u": (
        "۳ ماهه - ۲ کاربره",
        "۶۰۰,۰۰۰ تومان",
    ),
}


# ============================================================
# Welcome message
# ============================================================

def build_welcome_text(user: Message) -> str:
    telegram_user = user.from_user

    first_name = clean_text(
        telegram_user.first_name if telegram_user else "",
        "دوست عزیز",
    )

    return (
        f"سلام <b>{first_name}</b> عزیز! 🌹\n\n"
        "به ربات رسمی مدیریت اشتراک و پشتیبانی "
        "<b>L2TP VPN 24/7</b> خوش آمدید.\n\n"
        f"📅 <b>امروز:</b> {get_full_date_text()}\n"
        f"🕒 <b>ساعت تهران:</b> {get_time_text()}\n\n"
        "🔗 <b>لینک‌های رسمی:</b>\n"
        f"🤖 ربات: <a href=\"{BOT_URL}\">@L2TP_Arshavin_Bot</a>\n"
        f"📢 کانال: <a href=\"{CHANNEL_URL}\">@L2tp_vpn402</a>\n"
        f"💬 پشتیبانی: <a href=\"{SUPPORT_URL}\">@L2tp1Support</a>\n\n"
        "🌐 <b>پنل کاربری:</b>\n"
        f"{IBSNG_PANEL_URL}\n\n"
        "⚠️ <b>توجه:</b>\n"
        "برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید "
        "و بعد از اتمام دوباره روشن کنید.\n\n"
        "لطفاً گزینه موردنظر خود را از منوی زیر انتخاب کنید:"
    )


# ============================================================
# General commands
# ============================================================

@dp.message(CommandStart())
async def cmd commands
# ============================================================

@dp.message(CommandStart())
async def cmd await state.clear()

    user = message.from_user

    if user:
        add_user(
            user_id=user.id,
            username=user.username or "",
            first_name=user.first_name or "",
        )

    await message.answer(
        build_welcome_text(message),
        reply_markup=get_main_keyboard(),
        disable_web_page_preview=True,
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not message.from_user:
        return

    if message.from_user.id != ADMIN_ID:
        return

    (
        total_users,
        today_users,
        approved_payments,
        pending_payments,
    ) = get_stats()

    text = (
        "📊 <b>آمار ربات</b>\n\n"
        f"👥 کاربران یکتای ثبت‌شده: "
        f"<code>{to_persian_digits(total_users)}</code> نفر\n"
        f"🗓 کاربران ثبت‌شده امروز: "
        f"<code>{to_persian_digits(today_users)}</code> نفر\n"
        f"✅ پرداخت‌های تأییدشده: "
        f"<code>{to_persian_digits(approved_payments)}</code>\n"
        f"⏳ رسیدهای در انتظار بررسی: "
        f"<code>{to_persian_digits(pending_payments)}</code>"
    )

    await message.answer(text)


@dp.callback_query(F.data == "back_main")
async def back_main(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()
    await state.clear()
    await safe_delete(callback.message)

    await callback.message.answer(
        "🏠 به منوی اصلی بازگشتید.",
        reply_markup=get_main_keyboard(),
    )


# ============================================================
# New subscription
# ============================================================

@dp.message(F.text == "🛍 خرید اشتراک")
async def process_buy(
    message: Message,
    state: FSMContext,
):
    await state.clear()
    await state.set_state(OrderStates.choosing_plan)

    text = (
        "💎 <b>تعرفه‌های اشتراک L2TP VPN L2TP 24/7</b>\n\n"
        "<i>تمامی پلن‌ها شامل ۱۰ گیگابایت ترافیک هدیه هستند.</i>\n\n"
        "🔹 <b>۱ ماهه تک‌کاربره:</b> ۲۰۰,۰۰۰ تومان\n"
        "🔹 <b>۱ ماهه دوکاربره:</b> ۲۵۰,۰۰۰ تومان\n\n"
        "🔹 <b>۲ ماهه تک‌کاربره:</b> ۳۸۰,۰۰۰ تومان\n"
        "🔹 <b>۲ ماهه دوکاربره:</b> ۴۳۰,۰۰۰ تومان\n\n"
        "🔹 <b>۳ ماهه تک‌کاربره:</b> ۵۵۰,۰۰۰ تومان\n"
        "🔹 <b>۳ ماهه دوکاربره:</b> ۶۰۰,۰۰۰ تومان\n\n"
        "👇 لطفاً پلن موردنظر خود را انتخاب کنید:"
    )

    await message.answer(
        text,
        reply_markup=get_plans_inline_keyboard("buy"),
    )


# ============================================================
# Renewal
# ============================================================

@dp.message(F.text == "🔄 تمدید اشتراک")
async def process_renewal(
    message: Message,
    state: FSMContext,
):
    await state.clear()
    await state.set_state(
        RenewalStates.waiting_for_username
    )

    text = (
        "🔄 <b>تمدید اشتراک سرویس</b>\n\n"
        "لطفاً <b>نام کاربری فعلی</b> خود در پنل را ارسال کنید:"
    )

    await message.answer(
        text,
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(RenewalStates.waiting_for_username)
async def process_renewal_username(
    message: Message,
    state: FSMContext,
):
    username = (message.text or "").strip()

    if not username:
        await message.answer(
 )
        return

    نام کاربری را به‌صورت متنی ارسال کنید."
        )
        return

    await state.update_data(vpn_username=username)
    await state.set_state(RenewalStates.choosing_plan)

    text = (
        f"نام کاربری دریافت شد: "
        f"<code>{clean_text(username)}</code>\n\n"
        "لطفاً مدت‌زمان تمدید اشتراک را انتخاب کنید:"
    )

    await message.answer(
        text,
        reply_markup=get_plans_inline_keyboard("renew"),
    )


# ============================================================
# Plan selection
# ============================================================

@dp.callback_query(
    F.data.startswith("buy_") | F.data.startswith("renew_")
)
async def process_plan_selection(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    if not callback.data:
        return

    parts = callback.data.split("_", 1)

    if len(parts) != 2:
        await callback.answer(
            "پلن نامعتبر است.",
            show_alert=True,
        )
        return

    action_type, plan_key = parts

    if plan_key not in PLANS_DATA:
        await callback.answer(
            "پلن نامعتبر است.",
            show_alert=True,
        )
        return

    plan_name, price = PLANS_DATA[plan_key]

    await state.update_data(
        plan_name=plan_name,
        price=price,
        action_type=action_type,
    )

    if action_type == "buy":
        await state.set_state(
            OrderStates.waiting_for_receipt
        )
    else:
        await state.set_state(
            RenewalStates.waiting_for_receipt
        )

    await safe_delete(callback.message)

    text = (
        "📋 <b>جزئیات سفارش</b>\n\n"
        f"📦 پلن انتخابی: <b>{plan_name}</b>\n"
        f"💰 مبلغ قابل پرداخت: <b>{price}</b>\n\n"
        "💳 <b>اطلاعات کارت جهت واریز</b>\n"
        f"شماره کارت: <code>{PAYMENT_CARD}</code>\n"
        f"به نام: <b>{PAYMENT_NAME}</b>\n\n"
        "📸 پس از واریز، عکس یا اسکرین‌شات فیش را ارسال کنید."
    )

    await callback.message.answer(text)


# ============================================================
# Receipt handling
# ============================================================

@dp.message(OrderStates.waiting_for_receipt, F.photo)
@dp.message(RenewalStates.waiting_for_receipt, F.photo)
async def process_receipt_photo(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()
    user = message.from_user

    if not user:
        return

    plan_name = data.get("plan_name", "نامشخص")
    price = data.get("price", "نامشخص")
    action_type = data.get("action_type", "buy")
    vpn_username = data.get(
        "vpn_username",
        "سفارش جدید",
    )

    payment_id = record_payment(
        user_id=user.id,
        plan_name=plan_name,
        amount=price,
    )

    photo_id = message.photo[-1].file_id

    request_type = (
        "خرید جدید"
        if action_type == "buy"
        else "تمدید اشتراک"
    )

    admin_caption = (
        "🔔 <b>رسید پرداخت جدید دریافت شد</b>\n\n"
        f"🧾 شماره درخواست: "
        f"<code>{payment_id}</code>\n"
        f"👤 کاربر: "
        f"{clean_text(user.full_name)} "
        f"(@{clean_text(user.username, 'ندارد')})\n"
        f"🆔 آیدی عددی: <code>{user.id}</code>\n"
        f"📌 نوع درخواست: <b>{request_type}</b>\n"
        f"🔑 نام کاربری: "
        f"<code>{clean_text(vpn_username)}</code>\n"
        f"📦 پلن: <b>{clean_text(plan_name)}</b>\n"
        f"💰 مبلغ: <b>{clean_text(price)}</b>"
    )

    admin_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید رسید",
                    callback_data=(
                        f"adm_ok_{payment_id}_{user.id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="❌ رد رسید",
                    callback_data=(
                        f"adm_reject_{payment_id}_{user.id}"
                    ),
                ),
            ]
        ]
    )

    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=admin_caption,
            reply_markup=admin_keyboard,
        )
    except Exception:
        logger.exception(
            "Could not send payment receipt to admin"
        )

 await state.clear()

    await message.answer(
        " "✅ فیش واریزی شما با موفقیت برای مدیریت ارسال شد.\n\n"
        "پس از بررسی، نتیجه درخواست برای شما ارسال خواهد شد.",
        reply_markup=get_main_keyboard(),
    )


@dp.message(OrderStates.waiting_for_receipt)
@dp.message(RenewalStates.waiting_for_receipt)
async def receipt_must_be_photo(message: Message):
    await message.answer(
        "لطفاً فقط تصویر یا اسکرین‌شات فیش واریزی را ارسال کنید."
    )


# ============================================================
# Admin payment actions
# ============================================================

@dp.callback_query(
    F.data.startswith("adm_ok_")
    | F.data.startswith("adm_reject_")
)
async def admin_payment_action(
    callback: CallbackQuery,
):
    if not callback.from_user:
        return

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "شما دسترسی لازم را ندارید.",
            show_alert=True,
        )
        return

    if not callback.data:
        return

    parts = callback.data.split("_")

    if len(parts) != 4:
        await callback.answer(
            "اطلاعات درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    action = parts[1]

    try:
        payment_id = int(parts[2])
        user_id = int(parts[3])
    except ValueError:
        await callback.answer(
            "شناسه درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    status = "approved" if action == "ok" else "rejected"
    updated = update_payment_status(
        payment_id,
        status,
    )

    if not updated:
        await callback.answer(
            "این درخواست پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.answer(
        "وضعیت درخواست ثبت شد."
    )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass

    if status == "approved":
        user_text = (
            "✅ رسید پرداخت شما تأیید شد.\n\n"
            "درخواست شما در حال بررسی نهایی است و "
            "مشخصات اکانت از طریق همین ربات برایتان ارسال می‌شود."
        )
    else:
        user_text = (
            "❌ رسید پرداخت شما تأیید نشد.\n\n"
            "لطفاً برای بررسی بیشتر با پشتیبانی تماس بگیرید."
        )

    try:
        await bot.send_message(
            chat_id=user_id,
            text=user_text,
            reply_markup=get_main_keyboard(),
        )
    except Exception        logger.exception(
            "Could not notify user about payment status"
        )


 )


# ============================================================
# Cancel
# ============================================================

@dp.callback_query(F.data == "cancel_action")
async def cancel_action(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()
    await state.clear()
    await safe_delete(callback.message)

    await callback.message.answer(
        "عملیات لغو شد.",
        reply_markup=get_main_keyboard(),
    )


# ============================================================
# IBSng panel
# ============================================================

@dp.message(F.text == "📊 ورود به پنل کاربری")
async def ibsng_panel_info(message: Message):
    text = (
        "🌐 <b>پنل مشاهده مصرف و وضعیت اشتراک</b>\n\n"
        "⚠️ <b>توجه مهم:</b>\n"
        "برای ارتباط بهتر با پنل لطفاً وی‌پی‌ان خود را خاموش کنید "
        "و بعد از اتمام دوباره روشن کنید.\n\n"
        f"🔗 <b>آدرس پنل IBSng:</b>\n"
        f"{IBSNG_PANEL_URL}\n\n"
        "نام کاربری و رمز عبور خود را در صفحه بالا وارد کنید."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 ورود به پنل کاربری",
                    url=IBSNG_PANEL_URL,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 منوی اصلی",
                    callback_data="back_main",
                )
            ],
        ]
    )

    await message.answer(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


# ============================================================
# Connection guides
# ============================================================

@dp.message(F.text == "📚 راهنمای اتصال")
async def show_guides_menu(message: Message):
    text = (
        "📚 <b>راهنمای اتصال به سرویس VPN</b>\n\n"
        f"🌐 <b>آدرس سرور VPN:</b> "
        f"<code>{VPN_SERVER_IP}</code>\n"
        f"🔑 <b>کلید اشتراکی:</b> "
        f"<code>{IPSEC_SECRET}</code>\n\n"
        "دستگاه موردنظر خود را انتخاب کنید:"
    )

    await message.answer(
        text,
        reply_markup=get_guides_keyboard(),
    )


@dp.callback_query(F.data.startswith("guide_"))
async def guide_details(callback: CallbackQuery):
    await callback.answer()

    if not callback.data:
        return

    guide_type = callback.data.split("_", 1)[1]

    if guide_type == "ios":
        text = (
            "📱 <b>راهنمای آیفون و آیپد</b>\n\n"
            "۱. وارد Settings شوید.\n"
            "۲. به بخش VPN بروید.\n"
            "۳. گزینه Add VPN Configuration را انتخاب کنید.\n"
            "۴. نوع اتصال را روی L2TP قرار دهید.\n"
            f"۵. Server: <code>{VPN_SERVER_IP}</code>\n"
            "۶. Account و Password را وارد کنید.\n"
            f"۷. Secret: <code>{IPSEC_SECRET}</code>\n"
            "۸. تنظیمات را ذخیره و متصل شوید."
        )

    elif guide_type == "android":
        text = (
            "🤖 <b>راهنمای اندروید</b>\n\n"
            "۱. وارد Settings و بخش VPN            "۳. نوع اتصال را. گزینه افزودن اتصال جدید را بزنید.\n"
            "۳. نوع اتصال را L2TP/IPSec PSK انتخاب کنید.\n"
            f"۴. Server address: <code>{VPN_SERVER_IP}</code>\n"
            f"۵. IPSec pre-shared key: "
            f"<code>{IPSEC_SECRET}</code>\n"
            "۶. نام کاربری و رمز را وارد و ذخیره کنید."
        )

    elif guide_type == "windows":
        text = (
            "💻 <b>راهنمای ویندوز</b>\n\n"
            "۱. وارد Settings > Network & Internet > VPN شوید.\n"
            "۲. روی Add a VPN connection کلیک کنید.\n"
            f"۳. Server address: <code>{VPN_SERVER_IP}</code>\n"
            "۴. VPN type را روی "
            "L2TP/IPsec with pre-shared key قرار دهید.\n"
            f"۵. Pre-shared key: <code>{IPSEC_SECRET}</code>\n"
            "۶. نام کاربری و رمز را وارد و ذخیره کنید."
        )

    elif guide_type == "mac":
        text = (
            "🍏 <b>راهنمای مک‌او‌اس</b>\n\n"
            "۱. وارد System Settings > Network شوید.\n"
            "۲. Add VPN Configuration را انتخاب کنید.\n"
            "۳. نوع L2TP over IPSec را انتخاب کنید.\n"
            f"۴. Server Address: <code>{VPN_SERVER_IP}</code>\n"
            "۵. نام کاربری و رمز را وارد کنید.\n"
            f"۶. Shared Secret: <code>{IPSEC_SECRET}</code>"
        )

    else:
        text = (
            "🌐 <b>تنظیمات عمومی مودم و روتر</b>\n\n"
            "🔹 پروتکل: L2TP/IPsec PSK\n"
            f"🔹 سرور VPN: <code>{VPN_SERVER_IP}</code>\n"
            f"🔹 IPsec Secret: <code>{IPSEC_SECRET}</code>\n"
            f"🔹 سرور اکانتینگ IBSng: "
            f"<code>{IBSNG_SERVER_IP}</code>"
        )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_guides_keyboa

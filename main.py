import asyncio
import hashlib
import html
import logging
import os
import sqlite3
import time
from urllib.parse import urljoin

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)


# =========================================================
# تنظیمات
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()

MARZBAN_URL = os.getenv("MARZBAN_URL", "").strip()
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "").strip()
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "").strip()

PAYMENT_CARD = os.getenv(
    "PAYMENT_CARD",
    "6037-9918-XXXX-XXXX",
).strip()

# آیدی صحیح پشتیبانی
SUPPORT_ID = os.getenv(
    "SUPPORT_ID",
    "@L2tp1Support",
).strip()

DB_FILE = os.getenv("DB_FILE", "bot_database.db")

PLANS = {
    "plan_1m": {
        "fa": "۱ ماهه",
        "az": "1 aylıq",
        "price": 100_000,
    },
    "plan_3m": {
        "fa": "۳ ماهه",
        "az": "3 aylıq",
        "price": 250_000,
    },
    "plan_6m": {
        "fa": "۶ ماهه",
        "az": "6 aylıq",
        "price": 450_000,
    },
}

DISCOUNT_CODES = {
    "ARSHAVIN100": 100,
    "VIP50": 50,
    "OFF20": 20,
}


# =========================================================
# دیتابیس
# =========================================================

def get_connection():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT NOT NULL DEFAULT 'fa',
                applied_discount INTEGER NOT NULL DEFAULT 0,
                discount_code TEXT
            )
            """
        )
        connection.commit()


def ensure_user(user_id):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (user_id)
            VALUES (?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )
        connection.commit()


def get_user(user_id):
    ensure_user(user_id)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT user_id, lang, applied_discount, discount_code
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return dict(row)


def get_user_lang(user_id):
    return get_user(user_id)["lang"]


def set_user_lang(user_id, lang):
    if lang not in ("fa", "az"):
        return

    ensure_user(user_id)

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET lang = ?
            WHERE user_id = ?
            """,
            (lang, user_id),
        )
        connection.commit()


def set_user_discount(user_id, code, percent):
    ensure_user(user_id)

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET applied_discount = ?, discount_code = ?
            WHERE user_id = ?
            """,
            (percent, code, user_id),
        )
        connection.commit()


init_db()


# =========================================================
# وضعیت دریافت کد تخفیف
# =========================================================

class BotStates(StatesGroup):
    waiting_for_discount = State()


# =========================================================
# متن‌های فارسی و آذربایجانی
# =========================================================

TEXTS = {
    "fa": {
        "welcome": (
            "👋 <b>به ربات فروش اشتراک VPN خوش آمدید.</b>\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
        ),
        "buy_btn": "🛒 خرید اشتراک",
        "trial_btn": "🎁 تست رایگان",
        "discount_btn": "🏷 ثبت کد تخفیف",
        "profile_btn": "👤 پروفایل و وضعیت",
        "lang_btn": "🌐 تغییر زبان",
        "support_btn": "👨‍💻 پشتیبانی",
        "back_btn": "⬅️ بازگشت به منوی اصلی",
        "choose_plan": (
            "📦 <b>پلن‌های اشتراک</b>\n\n"
            "لطفاً دوره موردنظر را انتخاب کنید:"
        ),
        "plan_1m": "🔹 ۱ ماهه نامحدود - ۱۰۰,۰۰۰ تومان",
        "plan_3m": "🔹 ۳ ماهه نامحدود - ۲۵۰,۰۰۰ تومان",
        "plan_6m": "🔹 ۶ ماهه نامحدود - ۴۵۰,۰۰۰ تومان",
        "pay_info": (
            "💳 <b>اطلاعات پرداخت</b>\n\n"
            "پلن انتخابی: {plan}\n"
            "تخفیف: {discount}٪\n"
            "مبلغ قابل پرداخت: <b>{price} تومان</b>\n\n"
            "شماره کارت:\n"
            "<code>{card}</code>\n\n"
            "پس از واریز، تصویر رسید را برای پشتیبانی ارسال کنید:\n"
            "{support}"
        ),
        "discount_prompt": (
            "🏷 کد تخفیف خود را ارسال کنید.\n\n"
            "برای انصراف، دکمه بازگشت را بزنید."
        ),
        "discount_valid": (
            "✅ کد <code>{code}</code> با موفقیت ثبت شد.\n"
            "مقدار تخفیف: <b>{percent}٪</b>"
        ),
        "discount_invalid": "❌ کد تخفیف نامعتبر یا منقضی شده است.",
        "discount_text_only": "❌ لطفاً کد تخفیف را به‌صورت متن ارسال کنید.",
        "lang_question": "🌐 زبان موردنظر را انتخاب کنید:",
        "lang_selected": "🇮🇷 زبان ربات به فارسی تغییر کرد.",
        "support_text": (
            "👨‍💻 <b>پشتیبانی</b>\n\n"
            "برای دریافت راهنمایی، پیگیری سفارش یا ارسال رسید:\n"
            "{support}"
        ),
        "profile_text": (
            "👤 <b>پروفایل کاربری</b>\n\n"
            "شناسه کاربری: <code>{user_id}</code>\n"
            "زبان: فارسی\n"
            "تخفیف فعال: {discount}٪\n"
            "کد تخفیف: <code>{discount_code}</code>"
        ),
        "trial_loading": "⏳ در حال ساخت اشتراک تست...",
        "trial_success": (
            "✅ <b>اشتراک تست رایگان ساخته شد.</b>\n\n"
            "نام کاربری:\n"
            "<code>{username}</code>\n\n"
            "لینک اشتراک:\n"
            "<code>{sub_url}</code>\n\n"
            "اعتبار: ۲۴ ساعت\n"
            "حجم: ۱ گیگابایت"
        ),
        "trial_fail": (
            "❌ ایجاد اشتراک تست انجام نشد.\n\n"
            "ممکن است قبلاً تست دریافت کرده باشید یا ارتباط با پنل "
            "مرزبان برقرار نباشد.\n\n"
            "پشتیبانی: {support}"
        ),
    },
    "az": {
        "welcome": (
            "👋 <b>VPN satış botuna xoş gəlmisiniz.</b>\n\n"
            "Zəhmət olmasa seçimlərdən birini seçin:"
        ),
        "buy_btn": "🛒 Abunəlik al",
        "trial_btn": "🎁 Pulsuz test",
        "discount_btn": "🏷 Endirim kodu",
        "profile_btn": "👤 Profil və vəziyyət",
        "lang_btn": "🌐 Dili dəyiş",
        "support_btn": "👨‍💻 Dəstək",
        "back_btn": "⬅️ Əsas menyuya qayıt",
        "choose_plan": (
            "📦 <b>Abunəlik planları</b>\n\n"
            "İstədiyiniz müddəti seçin:"
        ),
        "plan_1m": "🔹 1 aylıq limitsiz - 100,000 tümən",
        "plan_3m": "🔹 3 aylıq limitsiz - 250,000 tümən",
        "plan_6m": "🔹 6 aylıq limitsiz - 450,000 tümən",
        "pay_info": (
            "💳 <b>Ödəniş məlumatı</b>\n\n"
            "Seçilmiş plan: {plan}\n"
            "Endirim: {discount}%\n"
            "Ödəniləcək məbləğ: <b>{price} tümən</b>\n\n"
            "Kart nömrəsi:\n"
            "<code>{card}</code>\n\n"
            "Ödənişdən sonra qəbzi dəstəyə göndərin:\n"
            "{support}"
        ),
        "discount_prompt": (
            "🏷 Endirim kodunu göndərin.\n\n"
            "Ləğv etmək üçün geri düyməsini seçin."
        ),
        "discount_valid": (
            "✅ <code>{code}</code> kodu uğurla əlavə edildi.\n"
            "Endirim: <b>{percent}%</b>"
        ),
        "discount_invalid": "❌ Endirim kodu yanlışdır və ya vaxtı bitib.",
        "discount_text_only": "❌ Endirim kodunu mətn kimi göndərin.",
        "lang_question": "🌐 İstədiyiniz dili seçin:",
        "lang_selected": "🇦🇿 Botun dili Azərbaycancaya dəyişdirildi.",
        "support_text": (
            "👨‍💻 <b>Dəstək</b>\n\n"
            "Sifariş, ödəniş qəbzi və suallar üçün:\n"
            "{support}"
        ),
        "profile_text": (
            "👤 <b>İstifadəçi profili</b>\n\n"
            "İstifadəçi ID-si: <code>{user_id}</code>\n"
            "Dil: Azərbaycanca\n"
            "Aktiv endirim: {discount}%\n"
            "Endirim kodu: <code>{discount_code}</code>"
        ),
        "trial_loading": "⏳ Test abunəliyi yaradılır...",
        "trial_success": (
            "✅ <b>Pulsuz test abunəliyi yaradıldı.</b>\n\n"
            "İstifadəçi adı:\n"
            "<code>{username}</code>\n\n"
            "Abunəlik linki:\n"
            "<code>{sub_url}</code>\n\n"
            "Müddət: 24 saat\n"
            "Həcm: 1 GB"
        ),
        "trial_fail": (
            "❌ Test abunəliyi yaradıla bilmədi.\n\n"
            "Daha əvvəl test almış ola bilərsiniz və ya Marzban "
            "paneli ilə əlaqə yoxdur.\n\n"
            "Dəstək: {support}"
        ),
    },
}


# =========================================================
# کیبوردها
# =========================================================

def main_menu(user_id):
    lang = get_user_lang(user_id)
    text = TEXTS[lang]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text["buy_btn"],
                    callback_data="menu_buy",
                ),
                InlineKeyboardButton(
                    text=text["trial_btn"],
                    callback_data="menu_trial",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=text["discount_btn"],
                    callback_data="menu_discount",
                ),
                InlineKeyboardButton(
                    text=text["profile_btn"],
                    callback_data="menu_profile",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=text["lang_btn"],
                    callback_data="menu_lang",
                ),
                InlineKeyboardButton(
                    text=text["support_btn"],
                    callback_data="menu_support",
                ),
            ],
        ]
    )


def back_keyboard(user_id):
    lang = get_user_lang(user_id)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=TEXTS[lang]["back_btn"],
                    callback_data="main_menu",
                )
            ]
        ]
    )


def plans_keyboard(user_id):
    lang = get_user_lang(user_id)
    text = TEXTS[lang]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text["plan_1m"],
                    callback_data="plan_1m",
                )
            ],
            [
                InlineKeyboardButton(
                    text=text["plan_3m"],
                    callback_data="plan_3m",
                )
            ],
            [
                InlineKeyboardButton(
                    text=text["plan_6m"],
                    callback_data="plan_6m",
                )
            ],
            [
                InlineKeyboardButton(
                    text=text["back_btn"],
                    callback_data="main_menu",
                )
            ],
        ]
    )


# =========================================================
# ارتباط با Marzban
# =========================================================

class MarzbanAPI:
    def __init__(self):
        self.access_token = None

    async def authenticate(self):
        if not all(
            [
                MARZBAN_URL,
                MARZBAN_USERNAME,
                MARZBAN_PASSWORD,
            ]
        ):
            logging.error("Marzban environment variables are incomplete.")
            return False

        url = f"{MARZBAN_URL.rstrip('/')}/api/admin/token"

        form_data = {
            "username": MARZBAN_USERNAME,
            "password": MARZBAN_PASSWORD,
        }

        try:
            timeout = aiohttp.ClientTimeout(total=20)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, data=form_data) as response:
                    if response.status != 200:
                        body = await response.text()
                        logging.error(
                            "Marzban authentication failed: %s %s",
                            response.status,
                            body,
                        )
                        return False

                    result = await response.json()
                    self.access_token = result.get("access_token")
                    return bool(self.access_token)

        except Exception:
            logging.exception("Marzban authentication request failed.")
            return False

    async def request(self, method, path, **kwargs):
        if not self.access_token:
            authenticated = await self.authenticate()
            if not authenticated:
                return None, None

        url = f"{MARZBAN_URL.rstrip('/')}{path}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"

        timeout = aiohttp.ClientTimeout(total=25)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    **kwargs,
                ) as response:
                    body = await response.text()

                    if response.status == 401:
                        self.access_token = None
                        return await self.request(method, path, **kwargs)

                    try:
                        data = await response.json()
                    except Exception:
                        data = body

                    return response.status, data

        except Exception:
            logging.exception("Marzban request failed: %s", path)
            return None, None

    async def create_trial(self, telegram_user_id):
        username = f"Arshavin_test_{telegram_user_id}"

        payload = {
            "username": username,
            "proxies": {
                "vless": {},
            },
            "data_limit": 1_073_741_824,
            "expire": int(time.time()) + 86_400,
        }

        status, result = await self.request(
            "POST",
            "/api/user",
            json=payload,
        )

        if status in (200, 201) and isinstance(result, dict):
            return self.extract_subscription(username, result)

        # اگر کاربر قبلاً ساخته شده باشد، اطلاعاتش را می‌خوانیم.
        if status in (400, 409):
            status, result = await self.request(
                "GET",
                f"/api/user/{username}",
            )

            if status == 200 and isinstance(result, dict):
                return self.extract_subscription(username, result)

        logging.error(
            "Trial creation failed. Status: %s, Result: %s",
            status,
            result,
        )
        return None, None

    @staticmethod
    def extract_subscription(username, result):
        subscription_url = result.get("subscription_url")

        if not subscription_url:
            return None, None

        if subscription_url.startswith("/"):
            subscription_url = urljoin(
                f"{MARZBAN_URL.rstrip('/')}/",
                subscription_url.lstrip("/"),
            )

        return username, subscription_url


marzban = MarzbanAPI()


# =========================================================
# راه‌اندازی Aiogram
# =========================================================

dp = Dispatcher(storage=MemoryStorage())


@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    await message.answer(
        TEXTS[lang]["welcome"],
        reply_markup=main_menu(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "main_menu")
async def main_menu_handler(
    callback: types.CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    user_id = callback.from_user.id
    lang = get_user_lang(user_id)

    await callback.answer()
    await callback.message.edit_text(
        TEXTS[lang]["welcome"],
        reply_markup=main_menu(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "menu_buy")
async def buy_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)

    await callback.answer()
    await callback.message.edit_text(
        TEXTS[lang]["choose_plan"],
        reply_markup=plans_keyboard(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.in_(PLANS.keys()))
async def plan_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    lang = user["lang"]

    plan = PLANS[callback.data]
    discount = max(0, min(100, user["applied_discount"]))
    original_price = plan["price"]
    final_price = int(original_price * (100 - discount) / 100)

    message_text = TEXTS[lang]["pay_info"].format(
        plan=html.escape(plan[lang]),
        discount=discount,
        price=f"{final_price:,}",
        card=html.escape(PAYMENT_CARD),
        support=html.escape(SUPPORT_ID),
    )

    await callback.answer()
    await callback.message.edit_text(
        message_text,
        reply_markup=back_keyboard(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "menu_discount")
async def discount_handler(
    callback: types.CallbackQuery,
    state: FSMContext,
):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)

    await state.set_state(BotStates.waiting_for_discount)
    await callback.answer()
    await callback.message.edit_text(
        TEXTS[lang]["discount_prompt"],
        reply_markup=back_keyboard(user_id),
        parse_mode="HTML",
    )


@dp.message(BotStates.waiting_for_discount)
async def receive_discount_handler(
    message: types.Message,
    state: FSMContext,
):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    text = TEXTS[lang]

    if not message.text:
        await message.answer(
            text["discount_text_only"],
            reply_markup=back_keyboard(user_id),
        )
        return

    code = message.text.strip().upper()
    percent = DISCOUNT_CODES.get(code)

    if percent is None:
        await state.clear()
        await message.answer(
            text["discount_invalid"],
            reply_markup=main_menu(user_id),
            parse_mode="HTML",
        )
        return

    set_user_discount(user_id, code, percent)
    await state.clear()

    await message.answer(
        text["discount_valid"].format(
            code=html.escape(code),
            percent=percent,
        ),
        reply_markup=main_menu(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "menu_lang")
async def language_handler(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇮🇷 فارسی",
                    callback_data="set_lang_fa",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇦🇿 Azərbaycanca",
                    callback_data="set_lang_az",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ بازگشت / Geri",
                    callback_data="main_menu",
                )
            ],
        ]
    )

    await callback.answer()
    await callback.message.edit_text(
        TEXTS[lang]["lang_question"],
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@dp.callback_query(F.data.in_({"set_lang_fa", "set_lang_az"}))
async def set_language_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = "fa" if callback.data == "set_lang_fa" else "az"

    set_user_lang(user_id, lang)

    await callback.answer(
        TEXTS[lang]["lang_selected"],
        show_alert=True,
    )

    await callback.message.edit_text(
        TEXTS[lang]["welcome"],
        reply_markup=main_menu(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "menu_profile")
async def profile_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    lang = user["lang"]

    discount_code = user["discount_code"] or "-"

    profile_text = TEXTS[lang]["profile_text"].format(
        user_id=user_id,
        discount=user["applied_discount"],
        discount_code=html.escape(discount_code),
    )

    await callback.answer()
    await callback.message.edit_text(
        profile_text,
        reply_markup=back_keyboard(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "menu_support")
async def support_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)

    support_text = TEXTS[lang]["support_text"].format(
        support=html.escape(SUPPORT_ID),
    )

    await callback.answer()
    await callback.message.edit_text(
        support_text,
        reply_markup=back_keyboard(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "menu_trial")
async def trial_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    text = TEXTS[lang]

    await callback.answer(text["trial_loading"])

    username, subscription_url = await marzban.create_trial(user_id)

    if username and subscription_url:
        result_text = text["trial_success"].format(
            username=html.escape(username),
            sub_url=html.escape(subscription_url),
        )
    else:
        result_text = text["trial_fail"].format(
            support=html.escape(SUPPORT_ID),
        )

    await callback.message.edit_text(
        result_text,
        reply_markup=back_keyboard(user_id),
        parse_mode="HTML",
    )


# =========================================================
# وب‌هوک Render
# =========================================================

async def health_handler(request):
    return web.json_response(
        {
            "status": "ok",
            "service": "Mikrotik-Bot",
        }
    )


async def webhook_handler(request):
    bot = request.app["bot"]
    expected_secret = request.app["webhook_secret"]

    received_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token",
        "",
    )

    if received_secret != expected_secret:
        return web.Response(status=403, text="Forbidden")

    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return web.Response(status=200, text="OK")

    except Exception:
        logging.exception("Webhook processing failed.")
        return web.Response(status=500, text="Error")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing in Render Environment Variables."
        )

    if not RENDER_URL:
        raise RuntimeError(
            "RENDER_EXTERNAL_URL is missing in Render."
        )

    bot = Bot(token=BOT_TOKEN)

    webhook_secret = hashlib.sha256(
        BOT_TOKEN.encode("utf-8")
    ).hexdigest()

    webhook_path = "/telegram-webhook"
    webhook_url = (
        f"{RENDER_URL.rstrip('/')}{webhook_path}"
    )

    app = web.Application()
    app["bot"] = bot
    app["webhook_secret"] = webhook_secret

    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_post(webhook_path, webhook_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=port,
    )
    await site.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(
        url=webhook_url,
        secret_token=webhook_secret,
        allowed_updates=dp.resolve_used_update_types(),
    )

    logging.info("Bot webhook is active: %s", webhook_url)
    logging.info("Support ID: %s", SUPPORT_ID)
    logging.info("Service port: %s", port)

    try:
        await asyncio.Event().wait()
    finally:
        await bot.delete_webhook()
        await bot.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

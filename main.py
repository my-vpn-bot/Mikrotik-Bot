import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import jdatetime
from aiohttp import web

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)

# =========================================================
# تنظیمات لاگ
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("vpn_bot")

# =========================================================
# دریافت متغیرها از رندر (Environment Variables)
# =========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MARZBAN_URL = os.getenv("MARZBAN_URL", "").strip().rstrip("/")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "").strip()
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "").strip()

CARD_NUMBER = os.getenv("CARD_NUMBER", "شماره کارت در رندر ثبت نشده").strip()
CARD_HOLDER = os.getenv("CARD_HOLDER", "نام دارنده کارت ثبت نشده").strip()
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@YourSupportID").strip()

# =========================================================
# اطلاعات پلن‌ها
# =========================================================
PLANS = {
    "plan_1": {
        "title": "۱ ماهه",
        "days": 30,
        "volume_gb": 30,
        "price": "۵۰٬۰۰۰ تومان",
    },
    "plan_2": {
        "title": "۲ ماهه",
        "days": 60,
        "volume_gb": 60,
        "price": "۹۰٬۰۰۰ تومان",
    },
    "plan_3": {
        "title": "۳ ماهه",
        "days": 90,
        "volume_gb": 100,
        "price": "۱۳۰٬۰۰۰ تومان",
    },
}

# =========================================================
# کلاس ارتباط با مرزبان (Marzban API)
# =========================================================
class MarzbanAPI:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.access_token = None

    async def get_token(self) -> str | None:
        if not self.base_url or not self.username or not self.password:
            logger.error("❌ اطلاعات اتصال به مرزبان در متغیرهای محیطی کامل نیست.")
            return None

        url = f"{self.base_url}/api/admin/token"
        data = {"username": self.username, "password": self.password}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as response:
                    if response.status != 200:
                        logger.error(f"❌ خطا در لاگین به مرزبان. کد: {response.status}")
                        return None

                    result = await response.json()
                    self.access_token = result.get("access_token")
                    logger.info("✅ توکن مرزبان با موفقیت دریافت شد.")
                    return self.access_token
        except Exception as error:
            logger.exception(f"❌ استثنا در دریافت توکن مرزبان: {error}")
            return None

    async def create_user(self, username: str, expire_days: int, limit_gb: int) -> dict | None:
        if not self.access_token:
            token = await self.get_token()
            if not token:
                return None

        url = f"{self.base_url}/api/user"
        data_limit_bytes = limit_gb * 1024 * 1024 * 1024
        expire_timestamp = int((datetime.now(timezone.utc) + timedelta(days=expire_days)).timestamp())

        payload = {
            "username": username,
            "proxies": {"vless": {}},
            "inbounds": {},
            "expire": expire_timestamp,
            "data_limit": data_limit_bytes,
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status not in (200, 201):
                        logger.error(f"❌ خطا در ساخت کاربر مرزبان. کد: {response.status}")
                        return None
                    return await response.json()
        except Exception as error:
            logger.exception(f"❌ خطا در ساخت کاربر مرزبان: {error}")
            return None

    async def get_user(self, username: str) -> dict | None:
        if not self.access_token:
            token = await self.get_token()
            if not token:
                return None

        url = f"{self.base_url}/api/user/{username}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as response:
                    if response.status != 200:
                        return None
                    return await response.json()
        except Exception as error:
            logger.exception(f"❌ خطا در استعلام کاربر: {error}")
            return None

marzban = MarzbanAPI(
    base_url=MARZBAN_URL,
    username=MARZBAN_USERNAME,
    password=MARZBAN_PASSWORD,
)

# =========================================================
# وب‌سرور ساختگی جهت راضی نگه‌داشتن پورت رندر (Dummy Server)
# =========================================================
async def dummy_health(request: web.Request) -> web.Response:
    return web.Response(text="VPN Telegram Bot is running perfectly!", content_type="text/plain")

async def start_dummy_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", dummy_health)
    app.router.add_get("/health", dummy_health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    logger.info(f"🚀 وب‌سرور روی پورت {port} با موفقیت روشن شد.")
    return runner

# =========================================================
# توابع کیبورد شیشه‌ای
# =========================================================
def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_plans")],
            [
                InlineKeyboardButton(text="🎁 تست رایگان", callback_data="plus_test"),
                InlineKeyboardButton(text="🛠 پشتیبانی", callback_data="support"),
            ],
            [
                InlineKeyboardButton(text="🤝 همکاری در فروش", callback_data="affiliate"),
                InlineKeyboardButton(text="ℹ️ اطلاعات سرویس", callback_data="info"),
            ],
        ]
    )

def plans_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔹 پلن ۱ ماهه | ۳۰ گیگ", callback_data="plan_1")],
            [InlineKeyboardButton(text="🔹 پلن ۲ ماهه | ۶۰ گیگ", callback_data="plan_2")],
            [InlineKeyboardButton(text="🔹 پلن ۳ ماهه | ۱۰۰ گیگ", callback_data="plan_3")],
            [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")],
        ]
    )

def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
        ]
    )

def payment_keyboard(plan_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ پرداخت کردم", callback_data=f"paid_{plan_id}")],
            [InlineKeyboardButton(text="🔙 بازگشت به پلن‌ها", callback_data="buy_plans")],
        ]
    )

def get_shamsi_datetime() -> str:
    now = jdatetime.datetime.now()
    return now.strftime("%Y/%m/%d - %H:%M")

# =========================================================
# روتر و هندلرهای ربات
# =========================================================
router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    full_name = message.from_user.full_name if message.from_user else "کاربر"
    text = (
        f"👋 سلام {full_name} عزیز!\n\n"
        f"📅 تاریخ: {get_shamsi_datetime()}\n\n"
        "به ربات فروش و مدیریت اشتراک VPN خوش آمدید.\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(Fmenu_keyboard(),
        parse_mode=ParseMode.HTML,
    )

@router.callback_query(F.data == "buy_plans")
async def buy_plans_handler(callback: CallbackQueryn\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML,
    )

@router.callback_query(F.data == "buy_plans")
async def buy_plans_handler(callback: CallbackQuery):
    await callback.answer()
    text = (
        "💎 <b>پلن‌های اشتراک پرسرعت:</b>\n\n"
        "پلن موردنظر خود را انتخاب کنید:"
    )
    await callback.message.edit_text(text, reply_markup=plans_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("plan_"))
async def plan_handler(callback: CallbackQuery):
    await callback.answer()
    plan_id = callback.data
    plan = PLANS.get(plan_id)

    if not plan:
        await callback.message.answer("❌ این پلن یافت نشد.", reply_markup=back_keyboard())
        return

    text = (
        f"✅ <b>سفارش پلن {plan['title']}</b>\n\n"
        f"📦 حجم: <b>{plan['volume_gb']} گیگابایت</b>\n"
        f"⏳ اعتبار: <b>{plan['days']} روز</b>\n"
        f"💰 مبلغ: <b>{plan['price']}</b>\n\n"
        "💳 <b>اطلاعات پرداخت:</b>\n"
        f"شماره کارت:\n<code>{CARD_NUMBER}</code>\n"
        f"به نام: <b>{CARD_HOLDER}</b>\n\n"
        "⚠️ پس از واریز، روی دکمه «پرداخت کردم» کلیک کنید و رسید را بفرستید."
    )
    await callback.message.edit_text(text, reply_markup=payment_keyboard(plan_id), parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("paid_"))
async def paid_handler(callback: CallbackQuery):
    await callback.answer()
    plan_id = callback.data.replace("paid_", "")
    plan = PLANS.get(plan_id, {})
    title = plan.get("title", "نامشخص")
    price = plan.get("price", "نامشخص")

    user = callback.from_user
    username = f"@{user.username}" if user and user.username else f"ID: {user.id}"

    text = (
        "📨 <b>اعلام پرداخت شما ثبت شد!</b>\n\n"
        f"پلن انتخابی: <b>{title}</b>\n"
        f"مبلغ: <b>{price}</b>\n\n"
        "لطفاً تصویر فیش واریزی خود را همراه با نام کاربری به پشتیبانی ارسال کنید:\n"
        f"👉 <b>{SUPPORT_USERNAME}</b>\n\n"
        f"شناسه شما: <code>{username}</code>"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "plus_test")
async def free_test_handler(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🎁 <b>دریافت تست رایگان</b>\n\n"
        "جهت دریافت کانفیگ تست رایگان به آیدی پشتیبانی پیام دهید:\n\n"
        f"👉 <b>{SUPPORT_USERNAME}</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🛠 <b>پشتیبانی و ارتباط با ما</b>\n\n"
        "جهت ارسال رسید، تمدید اشتراک یا حل مشکلات اتصال پیام دهید:\n\n"
        f"👉 <b>{SUPPORT_USERNAME}</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "affiliate")
async def affiliate_handler(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🤝 <b>همکاری در فروش</b>\n\n"
        "برای دریافت پنل نمایندگی یا پورسانت فروش اشتراک، با پشتیبانی در ارتباط باشید:\n\n"
        f"👉 <b>{SUPPORT_USERNAME}</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "info")
async def info_handler(callback: CallbackQuery):
    await callback.answer()
    text = (
        "ℹ️ <b>درباره سرویس‌های ما</b>\n\n"
        "⚡️ بالاترین سرعت و کمترین پینگ\n"
        "🔒 رمزنگاری امن و بدون قطعی\n"
        "📱 قابل استفاده در اندروید، iOS، ویندوز و مک\n"
        " پشتیبانی ۲۴ ساعته"
    )
    await callback.message.edit_text(text, reply_markup=back_keyboard(), parse_mode=ParseMode.HTML)

# =========================================================
# اجرای اصلی (Main Entrypoint)
# =========================================================
async def main():
    if not BOT_TOKEN:
        logger.critical("❌ توکن ربات (BOT_TOKEN) در متغیرهای محیطی رندر پیدا نشد!")
        return

    # تنظیمات ربات
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # راه‌اندازی سرور جهت جلوگیری از بسته شدن توسط رندر
    await start_dummy_server()

    # حذف پیام‌های قبلی و شروع Polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🚀 ربات با موفقیت در رندر روشن شد...")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ خطا حین اجرای ربات: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 ربات متوقف شد.")

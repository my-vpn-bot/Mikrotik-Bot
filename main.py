import asyncio
import logging
import os
import sys

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
import jdatetime

# ==================== تنظیمات لاگ ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== متغیرهای محیطی ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MARZBAN_URL = os.getenv("MARZBAN_URL", "").rstrip("/")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "Support_Admin")
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000-0000-0000-0000")
CARD_HOLDER = os.getenv("CARD_HOLDER", "پشتیبانی")
PORT = int(os.environ.get("PORT", 10000))

# ==================== پلن‌های فروش ====================
PLANS = {
    "plan_1m_30g": {"title": "یک‌ماهه - ۳۰ گیگابایت", "price": "۶۰,۰۰۰ تومان", "days": 30, "traffic": 30},
    "plan_1m_50g": {"title": "یک‌ماهه - ۵۰ گیگابایت", "price": "۹۰,۰۰۰ تومان", "days": 30, "traffic": 50},
    "plan_1m_100g": {"title": "یک‌ماهه - ۱۰۰ گیگابایت", "price": "۱۶۰,۰۰۰ تومان", "days": 30, "traffic": 100},
    "plan_3m_150g": {"title": "سه‌ماهه - ۱۵۰ گیگابایت", "price": "۲۴۰,۰۰۰ تومان", "days": 90, "traffic": 150},
}

def get_shamsi_datetime() -> str:
    now = jdatetime.datetime.now()
    return now.strftime("%Y/%m/%d - %H:%M")

# ==================== مرزبان API ====================
class MarzbanAPI:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None

    async def get_token(self) -> str | None:
        if not self.base_url or not self.username or not self.password:
            return None
        url = f"{self.base_url}/api/admin/token"
        data = {"username": self.username, "password": self.password}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, timeout=10) as resp:
                    if resp.status == 200:
                        res_data = await resp.json()
                        self.token = res_data.get("access_token")
                        return self.token
                    else:
                        logger.error(f"Marzban Auth Error: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Marzban Connection Error: {e}")
            return None

    async def create_user(self, username: str, expire_days: int, traffic_gb: int) -> dict | None:
        token = await self.get_token()
        if not token:
            return None
        url = f"{self.base_url}/api/user"
        headers = {"Authorization": f"Bearer {token}"}
        expire_timestamp = int((jdatetime.datetime.now() + jdatetime.timedelta(days=expire_days)).timestamp())
        payload = {
            "username": username,
            "proxies": {"vless": {}, "vmess": {}},
            "inbounds": {},
            "expire": expire_timestamp,
            "data_limit": traffic_gb * 1024 * 1024 * 1024,
            "data_limit_reset_strategy": "no_reset",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        logger.error(f"Marzban Create User Error: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Create User Exception: {e}")
            return None

marzban_client = MarzbanAPI(MARZBAN_URL, MARZBAN_USERNAME, MARZBAN_PASSWORD)

# ==================== استیت‌ها ====================
class UserState(StatesGroup):
    waiting_for_receipt = State()

# ==================== کیبوردها ====================
def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="💳 خرید کانفیگ", callback_data="buy_plans"),
            InlineKeyboardButton(text="⏳ تمدید کانفیگ", callback_data="extend_config"),
        ],
        [
            InlineKeyboardButton(text="✨ تمدید کانفیگ رایگان", callback_data="free_test"),
        ],
        [
            InlineKeyboardButton(text="🔧 رفع نقص کانفیگ", callback_data="fix_config"),
        ],
        [
            InlineKeyboardButton(text="🔍 بررسی کانفیگ", callback_data="check_config"),
            InlineKeyboardButton(text="📷 دریافت اسکین", callback_data="get_skin"),
        ],
        [
            InlineKeyboardButton(text="✍️ تغییر نام کانفیگ", callback_data="rename_config"),
        ],
        [
            InlineKeyboardButton(text="🗑 حذف کانفیگ", callback_data="delete_config"),
        ],
        [
            InlineKeyboardButton(text="🔥 کانفیگ‌های در حال انقضا", callback_data="expired_configs"),
        ],
        [
            InlineKeyboardButton(text=" پشتیبانی و راهنما", callback_data="support"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def plans_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for plan_id, info in PLANS.items():
        buttons.append([InlineKeyboardButton(text=f"⚡ {info['title']} - {info['price']}", callback_data=f"select_{plan_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_keyboard(plan_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ پرداخت و ارسال فیش", callback_data=f"pay_{plan_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به لیست پلن‌ها", callback_data="buy_plans")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]])

# ==================== روتر و پردازش پیام‌ها ====================
router = Router()

async def render_screen(target, text: str, reply_markup: InlineKeyboardMarkup):
    try:
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            await target.answer(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    except Exception:
        if isinstance(target, CallbackQuery):
            await target.message.answer(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        else:
            await target.answer(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    full_name = message.from_user.full_name if message.from_user else "کاربر"
    text = (
        f"سلام <b>{full_name}</b> عزیز! 👋\n"
        "به ربات رسمی فروش و پشتیبانی سرویس‌های <b>L2TP / Marzban VPN</b> خوش آمدید.\n\n"
        f"📅 تاریخ: <code>{get_shamsi_datetime()}</code>\n\n"
        "برای استفاده از خدمات ربات، از منوی زیر استفاده کنید:"
    )
    await render_screen(message, text, main_menu_keyboard())

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    full_name = callback.from_user.full_name if callback.from_user else "کاربر"
    text = (
        f"سلام <b>{full_name}</b> عزیز! 👋\n"
        "به منوی اصلی بازگشتید.\n\n"
        f"📅 تاریخ: <code>{get_shamsi_datetime()}</code>\n\n"
        "برای استفاده از خدمات ربات، از منوی زیر استفاده کنید:"
    )
    await render_screen(callback, text, main_menu_keyboard())

@router.callback_query(F.data == "buy_plans")
async def buy_plans_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "💳 <b>خرید اشتراک جدید</b>\n\n"
        "⚡ سرورهای اختصاصی با بالاترین سرعت و پینگ پایین\n"
        "👇 لطفاً پلن مد نظر خود را انتخاب کنید:"
    )
    await render_screen(callback, text, plans_keyboard())

@router.callback_query(F.data.startswith("select_"))
async def select_plan_callback(callback: CallbackQuery):
    await callback.answer()
    plan_id = callback.data.replace("select_", "")
    plan = PLANS.get(plan_id)
    if not plan:
        await callback.answer("پلن یافت نشد!", show_alert=True)
        return

    text = (
        f"🧾 <b>پیش‌فاکتور خرید</b>\n\n"
        f"🔹 <b>پلن:</b> {plan['title']}\n"
        f"💰 <b>مبلغ:</b> {plan['price']}\n\n"
        f"💳 <b>شماره کارت:</b>\n<code>{CARD_NUMBER}</code>\n"
        f"👤 <b>به نام:</b> {CARD_HOLDER}\n\n"
        "⚠️ پس از پرداخت، دکمه «پرداخت و ارسال فیش» را بزنید و عکس رسید را ارسال کنید."
    )
    await render_screen(callback, text, payment_keyboard(plan_id))

@router.callback_query(F.data.startswith("pay_"))
async def pay_plan_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    plan_id = callback.data.replace("pay_", "")
    await state.update_data(selected_plan=plan_id)
    await state.set_state(UserState.waiting_for_receipt)

    text = (
        "📸 لطفاً <b>عکس فیش واریزی</b> را در همین گفتگو ارسال نمایید.\n\n"
        "⏳ بلافاصله پس از تایید توسط پشتیبانی، کانفیگ اختصاصی شما صادر خواهد شد."
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.message(UserState.waiting_for_receipt, F.photo)
async def receipt_photo_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_id = data.get("selected_plan", "نامشخص")
    plan_info = PLANS.get(plan_id, {}).get("title", plan_id)
    await state.clear()

    await message.reply(
        "✅ <b>فیش واریزی با موفقیت دریافت شد.</b>\n\n"
        f"📌 پلن انتخابی: {plan_info}\n"
        "درخواست شما به صف تایید منتقل شد.",
        reply_markup=back_to_main_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "free_test")
async def free_test_callback(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    username = f"test_{user_id}"
    res = await marzban_client.create_user(username=username, expire_days=1, traffic_gb=1)
    
    if res and "subscription_url" in res:
        text = (
            "✨ <b>کانفیگ تست رایگان شما آماده شد:</b>\n\n"
            f"🔗 لینک اتصال:\n<code>{res['subscription_url']}</code>\n\n"
            "لینک بالا را کپی کرده و در نرم‌افزار متصل کنید."
        )
    else:
        text = (
            "✨ <b>تمدید / دریافت تست رایگان</b>\n\n"
            "جهت دریافت تست رایگان با پشتیبانی ارتباط بگیرید:\n"
            f"🆔 @{SUPPORT_USERNAME}"
        )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "extend_config")
async def extend_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "⏳ <b>تمدید کانفیگ</b>\n\n"
        "جهت تمدید، نام کاربری یا لینک کانفیگ خود را به آیدی زیر ارسال کنید:\n\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "fix_config")
async def fix_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🔧 <b>رفع نقص و عیب‌یابی</b>\n\n"
        "۱. اینترنت گوشی را خاموش و روشن کنید.\n"
        "۲. لینک سابسکریپشن را در برنامه Update کنید.\n"
        "۳. در صورت رفع نشدن با پشتیبانی هماهنگ کنید:\n\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "check_config")
async def check_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🔍 <b>بررسی وضعیت کانفیگ</b>\n\n"
        "برای استعلام حجم و زمان باقی‌مانده اشتراک با پشتیبانی در ارتباط باشید:\n\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "get_skin")
async def skin_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "📷 <b>دریافت QR Code</b>\n\n"
        "جهت دریافت بارکد اتصال به پشتیبانی پیام دهید:\n\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "rename_config")
async def rename_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "✍️ <b>تغییر نام کانفیگ</b>\n\n"
        "جهت تغییر نام اشتراک به پشتیبانی اطلاع دهید:\n\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "delete_config")
async def delete_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🗑 <b>حذف کانفیگ</b>\n\n"
        "جهت ابطال و حذف کانفیگ با پشتیبانی در ارتباط باشید:\n\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "expired_configs")
async def expired_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🔥 <b>کانفیگ‌های در حال انقضا</b>\n\n"
        "جهت تمدید پیش از موعد و دریافت آفر ویژه به پشتیبانی پیام دهید:\n\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        " <b>پشتیبانی اختصاصی</b>\n\n"
        "پاسخگویی سریع ۲۴ ساعته:\n\n"
        f"🆔 @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

# ==================== وب‌سرور Render ====================
async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is online and healthy!"))
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Render Dummy Server bound immediately to port {PORT}")

# ==================== اجرای اصلی ====================
async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing!")
        return

    # استارت سرور قبل از تلگرام تا پورت آنی توسط رندر شناسایی شود
    await start_dummy_server()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Bot is starting polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

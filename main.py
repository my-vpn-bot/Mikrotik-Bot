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
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

MARZBAN_URL = os.getenv("MARZBAN_URL", "").rstrip("/")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "").strip()
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "").strip()

SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "Support_Admin").replace("@", "").strip()

# خواندن شماره کارت و نام صاحب کارت با پشتیبانی از هر دو نام متغیر در Render
CARD_NUMBER = (os.getenv("PAYMENT_CARD") or os.getenv("CARD_NUMBER") or "0000-0000-0000-0000").strip()
CARD_HOLDER = (os.getenv("PAYMENT_NAME") or os.getenv("CARD_HOLDER") or "پشتیبانی").strip()

PORT = int(os.environ.get("PORT", 10000))

# ==================== پلن‌های فروش ====================
PLANS = {
    "plan_1m_30g": {"title": "🚀 یک‌ماهه | ۳۰ گیگابایت", "price": "۶۰,۰۰۰ تومان", "days": 30, "traffic": 30},
    "plan_1m_50g": {"title": "⚡ یک‌ماهه | ۵۰ گیگابایت", "price": "۹۰,۰۰۰ تومان", "days": 30, "traffic": 50},
    "plan_1m_100g": {"title": "🔥 یک‌ماهه | ۱۰۰ گیگابایت", "price": "۱۶۰,۰۰۰ تومان", "days": 30, "traffic": 100},
    "plan_3m_150g": {"title": "💎 سه‌ماهه | ۱۵۰ گیگابایت", "price": "۲۴۰,۰۰۰ تومان", "days": 90, "traffic": 150},
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

# ==================== کیبوردهای بازطراحی‌شده ====================
def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🛍 خرید اشتراک جدید", callback_data="buy_plans"),
            InlineKeyboardButton(text="🔄 تمدید اشتراک فعلی", callback_data="extend_config"),
        ],
        [
            InlineKeyboardButton(text="🔍 استعلام وضعیت و حجم", callback_data="check_config"),
            InlineKeyboardButton(text="🛠 رفع اشکال و اتصال", callback_data="fix_config"),
        ],
        [
            InlineKeyboardButton(text="📱 دریافت QR Code", callback_data="get_skin"),
            InlineKeyboardButton(text="✏️ تغییر نام کانفیگ", callback_data="rename_config"),
        ],
        [
            InlineKeyboardButton(text="⏳ سرویس‌های رو به اتمام", callback_data="expired_configs"),
            InlineKeyboardButton(text="🗑 حذف یا ابطال سرویس", callback_data="delete_config"),
        ],
        [
            InlineKeyboardButton(text="💬 پشتیبانی و ارتباط با ادمین", callback_data="support"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def plans_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for plan_id, info in PLANS.items():
        buttons.append([InlineKeyboardButton(text=f"{info['title']} ▫️ {info['price']}", callback_data=f"select_{plan_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_keyboard(plan_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💳 پرداخت کردم (ارسال فیش واریز)", callback_data=f"pay_{plan_id}")],
        [InlineKeyboardButton(text="📋 انتخاب پلن دیگر", callback_data="buy_plans")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]])

# ==================== روتر و مدیریت پیام‌ها ====================
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
        f"سلام <b>{full_name}</b> عزیز، خوش آمدید 🌹\n\n"
        "⚡ <b>سامانه مدیریت و خرید سرویس‌های پرسرعت و پایدار</b>\n"
        f"📅 تاریخ: <code>{get_shamsi_datetime()}</code>\n\n"
        "👇 لطفاً خدمت مورد نظر خود را از منوی زیر انتخاب کنید:"
    )
    await render_screen(message, text, main_menu_keyboard())

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    full_name = callback.from_user.full_name if callback.from_user else "کاربر"
    text = (
        f"<b>منوی اصلی ربات</b> 🏠\n\n"
        f"کاربر گرامی: <b>{full_name}</b>\n"
        f"📅 تاریخ: <code>{get_shamsi_datetime()}</code>\n\n"
        "یکی از گزینه‌های زیر را انتخاب نمایید:"
    )
    await render_screen(callback, text, main_menu_keyboard())

@router.callback_query(F.data == "buy_plans")
async def buy_plans_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🛍 <b>خرید اشتراک اختصاصی</b>\n\n"
        "🔹 سرعت فوق‌العاده با پروتکل‌های ضد فیلتر\n"
        "🔹 پینگ بسیار پایین مناسب وب‌گردی و گیمینگ\n"
        "🔹 پشتیبانی ۲۴ ساعته و اتصال پایدار\n\n"
        "👇 <b>پلن مورد نظرتان را انتخاب کنید:</b>"
    )
    await render_screen(callback, text, plans_keyboard())

@router.callback_query(F.data.startswith("select_"))
async def select_plan_callback(callback: CallbackQuery):
    await callback.answer()
    plan_id = callback.data.replace("select_", "")
    plan = PLANS.get(plan_id)
    if not plan:
        await callback.answer("پلن مورد نظر یافت نشد!", show_alert=True)
        return

    text = (
        "🧾 <b>پیش‌فاکتور سفارش</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>سرویس انتخابی:</b> {plan['title']}\n"
        f"💰 <b>مبلغ قابل پرداخت:</b> {plan['price']}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "💳 <b>اطلاعات پرداخت:</b>\n\n"
        f"🔢 شماره کارت (لمس کنید تا کپی شود):\n"
        f"<code>{CARD_NUMBER}</code>\n\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <i>پس از واریز مبلغ، دکمه «پرداخت کردم» را زده و تصویر فیش واریزی را ارسال نمایید.</i>"
    )
    await render_screen(callback, text, payment_keyboard(plan_id))

@router.callback_query(F.data.startswith("pay_"))
async def pay_plan_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    plan_id = callback.data.replace("pay_", "")
    await state.update_data(selected_plan=plan_id)
    await state.set_state(UserState.waiting_for_receipt)

    text = (
        "📸 <b>ارسال فیش واریزی</b>\n\n"
        "لطفاً تصویر خوانا از فیش یا رسید انتقال وجه را در همین صفحه ارسال فرمایید.\n\n"
        "⏳ <i>به‌محض ارسال، درخواست شما بررسی شده و کانفیگ تحویل داده می‌شود.</i>"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.message(UserState.waiting_for_receipt, F.photo)
async def receipt_photo_handler(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    plan_id = data.get("selected_plan", "نامشخص")
    plan_info = PLANS.get(plan_id, {}).get("title", plan_id)
    plan_price = PLANS.get(plan_id, {}).get("price", "نامشخص")
    user = message.from_user
    await state.clear()

    await message.reply(
        "✅ <b>رسید شما با موفقیت دریافت شد!</b>\n\n"
        f"📌 سرویس: <b>{plan_info}</b>\n"
        f"💰 مبلغ: <b>{plan_price}</b>\n\n"
        "🕒 درخواست شما در صف تایید قرار گرفت و سرویس به‌زودی تحویل داده خواهد شد.",
        reply_markup=back_to_main_keyboard(),
        parse_mode=ParseMode.HTML
    )

    if ADMIN_ID and ADMIN_ID.isdigit():
        try:
            admin_text = (
                "🔔 <b>فیش واریزی جدید دریافت شد!</b>\n\n"
                f"👤 <b>کاربر:</b> {user.full_name} (@{user.username if user.username else 'بدون نام کاربری'})\n"
                f"🆔 <b>شناسه عددی:</b> <code>{user.id}</code>\n"
                f"📦 <b>پلن انتخابی:</b> {plan_info}\n"
                f"💰 <b>مبلغ:</b> {plan_price}\n"
                f"📅 <b>زمان:</b> {get_shamsi_datetime()}"
            )
            await bot.send_photo(
                chat_id=int(ADMIN_ID),
                photo=message.photo[-1].file_id,
                caption=admin_text,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error forwarding receipt to admin: {e}")

@router.callback_query(F.data == "extend_config")
async def extend_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🔄 <b>تمدید اشتراک</b>\n\n"
        "برای تمدید سرویس، نام کاربری اشتراک یا لینک اتصال فعلی خود را برای پشتیبانی ارسال فرمایید:\n\n"
        f"👨‍💻 <b>آیدی پشتیبانی:</b> @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "fix_config")
async def fix_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🛠 <b>راهنمای رفع مشکل و عیب‌یابی</b>\n\n"
        "۱. حالت پرواز (Airplane Mode) گوشی را ۵ ثانیه روشن و خاموش کنید.\n"
        "۲. در نرم‌افزار خود گزینه <b>Update Subscription</b> را بزنید.\n"
        "۳. در صورت برطرف نشدن مشکل، به پشتیبانی پیام دهید:\n\n"
        f"👨‍💻 <b>آیدی پشتیبانی:</b> @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "check_config")
async def check_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🔍 <b>استعلام وضعیت سرویس</b>\n\n"
        "جهت اطلاع از ترافیک مصرفی و تاریخ انقضای سرویس، به پشتیبانی پیام دهید:\n\n"
        f"👨‍💻 <b>آیدی پشتیبانی:</b> @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "get_skin")
async def skin_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "📱 <b>دریافت بارکد (QR Code)</b>\n\n"
        "برای دریافت بارکد اتصال سریع به پشتیبانی پیام دهید:\n\n"
        f"👨‍💻 <b>آیدی پشتیبانی:</b> @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "rename_config")
async def rename_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "✏️ <b>تغییر نام اشتراک</b>\n\n"
        "جهت تغییر نام کاربری کانفیگ خود با پشتیبانی هماهنگ کنید:\n\n"
        f"👨‍💻 <b>آیدی پشتیبانی:</b> @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "delete_config")
async def delete_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🗑 <b>حذف یا ابطال سرویس</b>\n\n"
        "برای حذف کامل اکانت و بستن دسترسی‌ها با ادمین در ارتباط باشید:\n\n"
        f"👨‍💻 <b>آیدی پشتیبانی:</b> @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "expired_configs")
async def expired_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "⏳ <b>سرویس‌های رو به اتمام</b>\n\n"
        "جهت تمدید پیش از موعد و بهره‌مندی از تخفیف ویژه به پشتیبانی پیام دهید:\n\n"
        f"👨‍💻 <b>ارتباط با پشتیبانی:</b> @{SUPPORT_USERNAME}"
    )
    await render_screen(callback, text, back_to_main_keyboard())

@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery):
    await callback.answer()
    text = (
        "💬 <b>مرکز پشتیبانی و راهنمایی</b>\n\n"
        "▫️ پاسخگویی سریع به مشکلات فنی و مالی\n"
        "▫️ ارسال راهنما و لینک‌های دانلود نرم‌افزار\n\n"
        f"👨‍💻 <b>ارتباط مستقیم:</b> @{SUPPORT_USERNAME}"
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
    logger.info(f"Render Server bound immediately to port {PORT}")

# ==================== اجرای اصلی ====================
async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing!")
        return

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

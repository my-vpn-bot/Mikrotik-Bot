import os
import asyncio
import logging
import sqlite3
import jdatetime
import aiohttp
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- تنظیمات لاگینگ ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- دریافت متغیرهای محیطی (Environment Variables) ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MARZBAN_URL = os.getenv("MARZBAN_URL", "").rstrip("/")
MARZBAN_USER = os.getenv("MARZBAN_USERNAME", "")
MARZBAN_PASS = os.getenv("MARZBAN_PASSWORD", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "Admin")
CARD_NUMBER = os.getenv("CARD_NUMBER", "XXXX-XXXX-XXXX-XXXX")
CARD_HOLDER = os.getenv("CARD_HOLDER", "مدیریت")

# --- کلاس مدیریت API مرزبان ---
class MarzbanAPI:
    def __init__(self):
        self.token = None

    async def get_token(self):
        if self.token:
            return self.token
        async with aiohttp.ClientSession() as s:
            payload = {"username": MARZBAN_USER, "password": MARZBAN_PASS}
            async with s.post(f"{MARZBAN_URL}/api/admin/token", data=payload) as r:
                if r.status == 200:
                    data = await r.json()
                    self.token = data["access_token"]
                    return self.token
        return None

    async def get_user(self, username):
        token = await self.get_token()
        if not token: return None
        async with aiohttp.ClientSession() as s:
            headers = {"Authorization": f"Bearer {token}"}
            async with s.get(f"{MARZBAN_URL}/api/user/{username}", headers=headers) as r:
                if r.status == 200:
                    return await r.json()
        return None

    async def create_user(self, username, plan_gb, duration_days):
        token = await self.get_token()
        if not token: return False
        # تبدیل گیگابایت به بایت
        data_limit_bytes = plan_gb * 1024**3
        # محاسبه تاریخ انقضا (به صورت Timestamp)
        expire_timestamp = int(jdatetime.datetime.now().timestamp() + (duration_days * 86400))
        
        payload = {
            "username": username,
            "data_limit": data_limit_bytes,
            "expire": expire_timestamp,
            "proxies": {"vless": {}}, # ساختار پیش‌فرض برای VLESS
            "status": "active"
        }
        async with aiohttp.ClientSession() as s:
            headers = {"Authorization": f"Bearer {token}"}
            async with s.post(f"{MARZBAN_URL}/api/user", json=payload, headers=headers) as r:
                return r.status in [200, 201]

marzban = MarzbanAPI()

# --- ماشین حالات (FSM) ---
class OrderProcess(StatesGroup):
    waiting_for_plan = State()
    waiting_for_username = State()
    waiting_for_receipt = State()

class CheckStatus(StatesGroup):
    waiting_for_username = State()

# --- کیبوردها (Keyboards) ---
def main_menu_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛍 خرید اشتراک"), KeyboardButton(text="📊 بررسی کانفیگ")],
        [KeyboardButton(text="💎 درخواست اختصاصی"), KeyboardButton(text="🤝 همکاری در فروش")],
        [KeyboardButton(text="🛠 پشتیبانی")]
    ], resize_keyboard=True)

def back_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 بازگشت")]], resize_keyboard=True)

# --- روتر و هندلرها ---
router = Router()

@router.message(CommandStart())
async def cmd_start(msg: Message):
    user_name = msg.from_user.full_name
    now = jdatetime.datetime.now()
    date_shamsi = now.strftime('%Y/%m/%d')
    
    welcome_text = (
        f"✨ <b>خوش آمدید، {user_name} عزیز!</b>\n\n"
        f"📅 <b>تاریخ:</b> <code>{date_shamsi}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 به سیستم هوشمند مدیریت <b>L2TP VPN</b> خوش آمدید.\n\n"
        f"🛠 <b>خدمات ما:</b>\n"
        f"✅ اتصال فوق‌سریع و پایدار\n"
        f"✅ پشتیبانی ۲۴ ساعته\n"
        f"✅ پلن‌های متنوع و اقتصادی\n\n"
        f"لطفاً از منوی زیر انتخاب کنید 👇"
    )
    await msg.answer(welcome_text, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb())

@router.message(F.text == "🔙 بازگشت")
async def cmd_back(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("به منوی اصلی برگشتید.", reply_markup=main_menu_kb())

# --- منطق خرید ---
@router.message(F.text == "🛍 خرید اشتراک")
async def start_purchase(msg: Message, state: FSMContext):
    text = (
        "<b>💎 پلن‌های موجود:</b>\n\n"
        "1️⃣ <b>پلن یک ماهه</b> (30GB) ➔ 70,000 تومان\n"
        "2️⃣ <b>پلن دو ماهه</b> (60GB) ➔ 130,000 تومان\n"
        "3️⃣ <b>پلن سه ماهه</b> (100GB) ➔ 180,000 تومان\n\n"
        "<i>لطفاً شماره پلن خود را ارسال کنید (مثلاً 1)</i>"
    )
    await state.set_state(OrderProcess.waiting_for_plan)
    await msg.answer(text, parse_mode=ParseMode.HTML, reply_markup=back_kb())

@router.message(OrderProcess.waiting_for_plan)
async def process_plan(msg: Message, state: FSMContext):
    plans = {"1": (30, 30), "2": (60, 60), "3": (100, 90)} # (GB, Days)
    if msg.text not in plans:
        await msg.answer("❌ شماره پلن نامعتبر است. لطفاً از 1 تا 3 انتخاب کنید.")
        return

    await state.update_data(plan_info=plans[msg.text])
    await state.set_state(OrderProcess.waiting_for_username)
    await msg.answer("👤 <b>نام کاربری (Username) دلخواه خود را وارد کنید:</b>\n(مثلاً: user_test)", parse_mode=ParseMode.HTML)

@router.message(OrderProcess.waiting_for_username)
async def process_username(msg: Message, state: FSMContext):
    username = msg.text.strip()
    if len(username) < 3:
        await msg.answer("❌ نام کاربری باید حداقل ۳ کاراکتر باشد.")
        return
    
    await state.update_data(username=username)
    await state.set_state(OrderProcess.waiting_for_receipt)
    
    payment_text = (
        "💳 <b>اطلاعات پرداخت:</b>\n\n"
        f"🏦 <b>شماره کارت:</b> <code>{CARD_NUMBER}</code>\n"
        f"👤 <b>صاحب حساب:</b> {CARD_HOLDER}\n\n"
        "✅ پس از واریز، لطفا <b>عکس فیش</b> را همین‌جا ارسال کنید."
    )
    await msg.answer(payment_text, parse_mode=ParseMode.HTML)

@router.message(OrderProcess.waiting_for_receipt, F.photo)
async def process_receipt(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    username = data.get("username")
    plan_gb = data.get("plan_info")[0]
    duration = data.get("plan_info")[1]

    # ارسال به ادمین
    admin_msg = (
        f"🔔 <b>درخواست خرید جدید!</b>\n\n"
        f"👤 از: {msg.from_user.full_name} (@{msg.from_user.username})\n"
        f"🆔 نام کاربری درخواستی: <code>{username}</code>\n"
        f"📦 پلن: {plan_gb} گیگابایت\n"
        f"⏳ مدت: {duration} روز"
    )
    await bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption=admin_msg, parse_mode=ParseMode.HTML)
    
    await msg.answer("✅ فیش شما دریافت شد. پس از تایید ادمین، اکانت شما ساخته خواهد شد.", reply_markup=main_menu_kb())
    await state.clear()

# --- منطق استعلام ---
@router.message(F.text == "📊 بررسی کانفیگ")
async def start_check(msg: Message, state: FSMContext):
    await state.set_state(CheckStatus.waiting_for_username)
    await msg.answer("🔍 <b>لطفاً نام کاربری خود را برای استعلام وارد کنید:</b>", parse_mode=ParseMode.HTML, reply_markup=back_kb())

@router.message(CheckStatus.waiting_for_username)
async def check_user_status(msg: Message, state: FSMContext):
    username = msg.text.strip()
    user_data = await marzban.get_user(username)
    
    if not user_data:
        await msg.answer("❌ کاربری با این مشخصات یافت نشد.", reply_markup=main_menu_kb())
    else:
        status = "🟢 فعال" if user_data.get("status") == "active" else "🔴 غیرفعال"
        used = user_data.get("used_traffic", 0) / (1024**3)
        limit = user_data.get("data_limit", 0) / (1024**3)
        
        # تاریخ انقضا به شمسی
        expire_ts = user_data.get("expire")
        if expire_ts:
            expire_date = jdatetime.datetime.fromtimestamp(expire_ts).strftime('%Y/%m/%d')
        else:
            expire_date = "نامحدود"

        res_text = (
            f"📊 <b>گزارش وضعیت اکانت:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>نام کاربری:</b> <code>{username}</code>\n"
            f"🚦 <b>وضعیت:</b> {status}\n"
            f"📊 <b>مصرف:</b> <code>{used:.2f}</code> / <code>{limit:.2f}</code> GB\n"
            f"📅 <b>تاریخ انقضا:</b> <code>{expire_date}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        await msg.answer(res_text, parse_mode=ParseMode.HTML, reply_markup=main_menu_kb())
    await state.clear()

# --- سایر دکمه‌ها ---
@router.message(F.text == "💎 درخواست اختصاصی")
async def custom_req(msg: Message):
    await msg.answer(f"👨‍💻 برای دریافت پلن‌های خاص و اختصاصی، با پشتیبان در ارتباط باشید: @{SUPPORT_USERNAME}")

@router.message(F.text == "🤝 همکاری در فروش")
async def reseller_info(msg: Message):
    await msg.answer("💰 با خرید پنل نمایندگی، از هر فروش درصد مشخصی سود خواهید برد. جهت دریافت اطلاعات به @"+SUPPORT_USERNAME+" پیام دهید.")

@router.message(F.text == "🛠 پشتیبانی")
async def support_msg(msg: Message):
    await msg.answer(f"👨‍💻 ادمین و پشتیبانی: @{SUPPORT_USERNAME}")

# --- اجرای اصلی ---
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    # بسیار مهم برای Render: حذف آپدیت‌های قدیمی برای جلوگیری از TelegramConflictError
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

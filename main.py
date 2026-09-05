import os
import re
import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web, ClientSession

# ==============================================================================
# 1. تنظیمات و متغیرهای محیطی (CONFIG)
# ==============================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0").strip()
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.isdigit() else 0

MARZBAN_URL = os.getenv("MARZBAN_URL", "").rstrip("/")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "")

PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6037-9999-9999-9999 (به نام مدیریت)")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "Support").lstrip("@")

PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()

if RENDER_EXTERNAL_URL and not RENDER_EXTERNAL_URL.startswith("http"):
    RENDER_EXTERNAL_URL = "https://" + RENDER_EXTERNAL_URL
RENDER_EXTERNAL_URL = RENDER_EXTERNAL_URL.rstrip("/")

masked_token = BOT_TOKEN[:6] + "..." if len(BOT_TOKEN) > 6 else "NOT_SET"
logger.info(f"شروع تنظیمات: BOT_TOKEN={masked_token}, ADMIN_ID={ADMIN_ID}, RENDER_URL={RENDER_EXTERNAL_URL}")

# ==============================================================================
# 2. پایگاه داده (SQLITE)
# ==============================================================================
DB_PATH = "bot_database.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                marzban_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                plan_name TEXT,
                amount TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_db()

def db_add_user(user_id: int, username: Optional[str]):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        conn.commit()

def db_update_marzban_user(user_id: int, marzban_user: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET marzban_username = ? WHERE telegram_id = ?",
            (marzban_user, user_id)
        )
        conn.commit()

def db_get_marzban_user(user_id: int) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT marzban_username FROM users WHERE telegram_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def db_get_stats():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM receipts WHERE DATE(created_at) = DATE('now')")
        today_receipts = cursor.fetchone()[0]
        return total_users, today_receipts

def db_get_all_user_ids():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM users")
        return [r[0] for r in cursor.fetchall()]

# ==============================================================================
# 3. کیبوردها (KEYBOARDS)
# ==============================================================================
def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="💳 خرید کانفیگ"), KeyboardButton(text="⏳ تمدید کانفیگ")],
        [KeyboardButton(text="✨ تمدید کانفیگ رایگان")],
        [KeyboardButton(text="🔧 رفع نقص کانفیگ")],
        [KeyboardButton(text="🔍 بررسی کانفیگ"), KeyboardButton(text="📷 دریافت اسکین")],
        [KeyboardButton(text="✍️ تغییر نام کانفیگ")],
        [KeyboardButton(text="🗑 حذف کانفیگ")],
        [KeyboardButton(text="🧯 کانفیگ‌های در سد انقضا")],
        [KeyboardButton(text="☎️ تماس با ما")]
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="👨‍💼 پنل مدیر")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_plans_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ 1 ماهه (30 روزه - 50 گیگ) - 100,000 تومان", callback_query_data="plan_1m")],
        [InlineKeyboardButton(text="🚀 2 ماهه (45 روزه - 90 گیگ) - 180,000 تومان", callback_query_data="plan_2m")],
        [InlineKeyboardButton(text="💎 3 ماهه (60 روزه - 130 گیگ) - 250,000 تومان", callback_query_data="plan_3m")],
        [InlineKeyboardButton(text="🎁 اکانت تست رایگان (24 ساعت)", callback_query_data="plan_test")]
    ])

# ==============================================================================
# 4. ارتباط با API مرزبان (MARZBAN API)
# ==============================================================================
class MarzbanAPI:
    def __init__(self):
        self.access_token: Optional[str] = None

    async def login(self) -> bool:
        if not MARZBAN_URL or not MARZBAN_USERNAME or not MARZBAN_PASSWORD:
            logger.error("اطلاعات اتصال به مرزبان در ENV ست نشده است.")
            return False
        
        url = f"{MARZBAN_URL}/api/admin/token"
        data = {"username": MARZBAN_USERNAME, "password": MARZBAN_PASSWORD}
        
        try:
            async with ClientSession() as session:
                async with session.post(url, data=data, timeout=10) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        self.access_token = res.get("access_token")
                        return True
                    else:
                        logger.error(f"خطای ورود به مرزبان: status {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"خطای استثنا در لاگین مرزبان: {e}")
            return False

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        if not self.access_token:
            if not await self.login():
                return None
        
        url = f"{MARZBAN_URL}/api/user/{username}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            async with ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 401:
                        # توکن منقضی شده، تلاش مجدد
                        if await self.login():
                            headers["Authorization"] = f"Bearer {self.access_token}"
                            async with session.get(url, headers=headers, timeout=10) as resp2:
                                if resp2.status == 200:
                                    return await resp2.json()
                    logger.error(f"استعلام کاربر مرزبان موفق نبود: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"خطای ارتباط با مرزبان: {e}")
            return None

marzban_api = MarzbanAPI()

# ==============================================================================
# 5. ماشین حالات (FSM STATES)
# ==============================================================================
class UserStates(StatesGroup):
    waiting_marzban_username = State()
    waiting_receipt = State()
    waiting_support_msg = State()
    waiting_action_username = State()
    waiting_new_name = State()
    admin_broadcast = State()

# ==============================================================================
# 6. هندلرها (ROUTERS & HANDLERS)
# ==============================================================================
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    db_add_user(user_id, username)
    
    is_admin = (user_id == ADMIN_ID)
    welcome_text = (
        f"سلام {message.from_user.first_name} عزیز! 👋\n"
        "به ربات رسمی فروش و پشتیبانی سرویس‌های **L2TP / Marzban VPN** خوش آمدید.\n\n"
        "برای استفاده از خدمات ربات، از منوی زیر استفاده کنید:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(is_admin), parse_mode=ParseMode.MARKDOWN)

# ------------------------------------------------------------------------------
# خرید و تمدید
# ------------------------------------------------------------------------------
@router.message(F.text == "💳 خرید کانفیگ")
async def process_buy(message: Message):
    await message.answer("لطفاً پلن مورد نظر خود را انتخاب کنید:", reply_markup=get_plans_inline_keyboard())

@router.callback_query(F.data.startswith("plan_"))
async def process_plan_choice(callback: CallbackQuery, state: FSMContext):
    plan_key = callback.data
    plans = {
        "plan_1m": ("1 ماهه (50 گیگ)", "100,000 تومان"),
        "plan_2m": ("2 ماهه (90 گیگ)", "180,000 تومان"),
        "plan_3m": ("3 ماهه (130 گیگ)", "250,000 تومان"),
        "plan_test": ("تست رایگان (24 ساعت)", "0 تومان"),
    }
    
    plan_name, price = plans.get(plan_key, ("نامشخص", "0"))
    
    if plan_key == "plan_test":
        await callback.message.edit_text("🎁 درخواست اکانت تست شما برای مدیر ارسال شد. بزودی کانفیگ برای شما ارسال می‌شود.")
        if ADMIN_ID:
            await callback.bot.send_message(
                ADMIN_ID,
                f"📥 **درخواست اکانت تست**\nاز طرف: @{callback.from_user.username or 'بدون آیدی'} (`{callback.from_user.id}`)"
            )
        await callback.answer()
        return

    await state.update_data(selected_plan=plan_name, plan_price=price)
    await state.set_state(UserStates.waiting_receipt)
    
    msg_text = (
        f"📋 **پلن انتخابی:** {plan_name}\n"
        f"💵 **مبلغ قابل پرداخت:** {price}\n\n"
        f"💳 **شماره کارت جهت واریز:**\n`{PAYMENT_CARD}`\n\n"
        "لطفاً پس از واریز، **عکس فیش واریزی** خود را در همین چت ارسال کنید."
    )
    await callback.message.edit_text(msg_text, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@router.message(StateFilter(UserStates.waiting_receipt), F.photo)
async def process_receipt_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("selected_plan", "تمدید / خرید")
    price = data.get("plan_price", "نامشخص")
    
    photo_id = message.photo[-1].file_id
    
    await message.answer("✅ فیش شما با موفقیت دریافت شد و برای مدیریت ارسال گردید. پس از بررسی، سرویس شما فعال/تمدید می‌شود.")
    
    if ADMIN_ID:
        caption = (
            f"🧾 **فیش واریزی جدید**\n"
            f"👤 کاربر: @{message.from_user.username or 'بدون آیدی'} (`{message.from_user.id}`)\n"
            f"📦 پلن: {plan_name}\n"
            f"💰 مبلغ: {price}"
        )
        await message.bot.send_photo(ADMIN_ID, photo_id, caption=caption, parse_mode=ParseMode.MARKDOWN)
    
    await state.clear()

# ------------------------------------------------------------------------------
# بررسی کانفیگ (Azki Style Status Card)
# ------------------------------------------------------------------------------
@router.message(F.text == "🔍 بررسی کانفیگ")
async def process_check_config(message: Message, state: FSMContext):
    marzban_user = db_get_marzban_user(message.from_user.id)
    if not marzban_user:
        await state.set_state(UserStates.waiting_marzban_username)
        await message.answer("🔑 لطفاً نام کاربری کانفیگ (Marzban Username) خود را ارسال کنید:")
        return

    await show_user_status(message, marzban_user)

@router.message(StateFilter(UserStates.waiting_marzban_username))
async def process_save_marzban_username(message: Message, state: FSMContext):
    username_input = message.text.strip().lstrip("@")
    db_update_marzban_user(message.from_user.id, username_input)
    await state.clear()
    await message.answer(f"✅ نام کاربری `{username_input}` ثبت شد.", parse_mode=ParseMode.MARKDOWN)
    await show_user_status(message, username_input)

async def show_user_status(message: Message, marzban_username: str):
    wait_msg = await message.answer("⏳ در حال دریافت اطلاعات از سرور...")
    data = await marzban_api.get_user(marzban_username)
    await wait_msg.delete()
    
    if not data:
        await message.answer("❌ اطلاعاتی برای این نام کاربری یافت نشد یا سرور در دسترس نیست.")
        return

    status = data.get("status", "unknown")
    status_emoji = "✅ فعال" if status == "active" else "❌ غیرفعال / منقضی"
    
    used_bytes = data.get("used_traffic", 0)
    data_limit = data.get("data_limit", 0)
    expire_timestamp = data.get("expire", 0)

    used_gb = round(used_bytes / (1024**3), 2)
    limit_gb = round(data_limit / (1024**3), 2) if data_limit else "نامحدود"
    rem_gb = round((data_limit - used_bytes) / (1024**3), 2) if data_limit else "نامحدود"

    time_rem_str = "نامحدود"
    expire_date_str = "بدون انقضا"
    if expire_timestamp:
        exp_dt = datetime.fromtimestamp(expire_timestamp, tz=timezone.utc)
        now_dt = datetime.now(timezone.utc)
        expire_date_str = exp_dt.strftime("%Y-%m-%d %H:%M")
        
        diff = exp_dt - now_dt
        if diff.total_seconds() > 0:
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            time_rem_str = f"{days} روز و {hours} ساعت و {minutes} دقیقه"
        else:
            time_rem_str = "منقضی شده"

    card_text = (
        f"📊 **کارت وضعیت حساب کاربری**\n\n"
        f"👤 **نام کاربری:** `{marzban_username}`\n"
        f"🔘 **وضعیت:** {status_emoji}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📈 **میزان مصرف:** `{used_gb} GB` از `{limit_gb} GB`\n"
        f"📉 **حجم باقی‌مانده:** `{rem_gb} GB`\n"
        f"⏳ **زمان باقی‌مانده:** {time_rem_str}\n"
        f"📅 **تاریخ انقضا:** `{expire_date_str}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🕒 آخرین بروزرسانی: {datetime.now().strftime('%H:%M:%S')}"
    )
    await message.answer(card_text, parse_mode=ParseMode.MARKDOWN)

# ------------------------------------------------------------------------------
# سایر منوها (تمدید، رفع نقص، تغییر نام، حذف)
# ------------------------------------------------------------------------------
@router.message(F.text.in_({"⏳ تمدید کانفیگ", "✨ تمدید کانفیگ رایگان", "🔧 رفع نقص کانفیگ", "✍️ تغییر نام کانفیگ", "🗑 حذف کانفیگ"}))
async def process_service_requests(message: Message, state: FSMContext):
    action = message.text
    await state.update_data(current_action=action)
    await state.set_state(UserStates.waiting_action_username)
    await message.answer(f"لطفاً نام کاربری (کانفیگ) مربوط به **{action}** را ارسال کنید:")

@router.message(StateFilter(UserStates.waiting_action_username))
async def process_action_username_received(message: Message, state: FSMContext):
    data = await state.get_data()
    action = data.get("current_action", "درخواست")
    cfg_user = message.text.strip()
    
    if action == "✍️ تغییر نام کانفیگ":
        await state.update_data(target_cfg_user=cfg_user)
        await state.set_state(UserStates.waiting_new_name)
        await message.answer("لطفاً نام جدید درخواستی را وارد کنید:")
        return

    await message.answer(f"✅ درخواست **{action}** برای نام کاربری `{cfg_user}` به مدیریت ارسال شد.", parse_mode=ParseMode.MARKDOWN)
    
    if ADMIN_ID:
        await message.bot.send_message(
            ADMIN_ID,
            f"🔔 **درخواست جدید:** {action}\n"
            f"👤 کاربر: @{message.from_user.username or 'بدون آیدی'} (`{message.from_user.id}`)\n"
            f"🔑 نام کانفیگ: `{cfg_user}`",
            parse_mode=ParseMode.MARKDOWN
        )
    await state.clear()

@router.message(StateFilter(UserStates.waiting_new_name))
async def process_new_name_received(message: Message, state: FSMContext):
    data = await state.get_data()
    cfg_user = data.get("target_cfg_user")
    new_name = message.text.strip()
    
    await message.answer(f"✅ درخواست تغییر نام کانفیگ `{cfg_user}` به `{new_name}` به مدیریت ارسال شد.", parse_mode=ParseMode.MARKDOWN)
    if ADMIN_ID:
        await message.bot.send_message(
            ADMIN_ID,
            f"🔔 **درخواست تغییر نام کانفیگ**\n"
            f"👤 کاربر: @{message.from_user.username or 'بدون آیدی'}\n"
            f"🔑 نام قدیمی: `{cfg_user}`\n"
            f"✏️ نام جدید: `{new_name}`",
            parse_mode=ParseMode.MARKDOWN
        )
    await state.clear()

@router.message(F.text == "🧯 کانفیگ‌های در سد انقضا")
async def process_expired_blocked_info(message: Message):
    text = (
        "🧯 **کانفیگ‌های در سد انقضا چیست؟**\n\n"
        "اگر حجم یا زمان اشتراک شما به پایان رسیده اما هنوز اتصال شما قطع نشده یا در وضعیت رزرو قرار دارد، "
        "کانفیگ شما در وضعیت 'سد انقضا' می‌باشد.\n\n"
        "جهت تمدید سریع و جلوگیری از قطع کامل، از منوی '⏳ تمدید کانفیگ' اقدام کنید یا با پشتیبانی در تماس باشید."
    )
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@router.message(F.text == "📷 دریافت اسکین")
async def process_get_skin(message: Message):
    await message.answer("🎨 اسکین‌ها و فایل‌های راهنمای اتصال به‌زودی در این بخش قرار خواهند گرفت.")

@router.message(F.text == "☎️ تماس با ما")
async def process_contact_support(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_support_msg)
    await message.answer(f"👨‍💻 جهت ارتباط با پشتیبانی، پیام خود را بنویسید یا مستقیماً به آیدی @{SUPPORT_USERNAME} پیام دهید:")

@router.message(StateFilter(UserStates.waiting_support_msg))
async def process_forward_support(message: Message, state: FSMContext):
    await message.answer("✅ پیام شما برای پشتیبانی ارسال شد. به زودی پاسخ شما داده خواهد شد.")
    if ADMIN_ID:
        await message.bot.send_message(
            ADMIN_ID,
            f"📩 **پیام پشتیبانی از طرف:** @{message.from_user.username or 'بدون آیدی'} (`{message.from_user.id}`)\n\n"
            f"{message.text}"
        )
    await state.clear()

# ------------------------------------------------------------------------------
# پنل مدیریت (ADMIN PANEL)
# ------------------------------------------------------------------------------
@router.message(F.text == "👨‍💼 پنل مدیر")
async def process_admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ این دستور فقط برای مدیر ربات مجاز است.")
        return

    total_users, today_receipts = db_get_stats()
    admin_text = (
        "👨‍💼 **پنل مدیریت ربات**\n\n"
        f"👥 **تعداد کل کاربران:** {total_users}\n"
        f"🧾 **فیش‌های ثبت‌شده امروز:** {today_receipts}\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 پیام همگانی (Broadcast)", callback_query_data="admin_broadcast_start")]
    ])
    await message.answer(admin_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

@router.callback_query(F.data == "admin_broadcast_start")
async def process_admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("دسترسی غیرمجاز", show_alert=True)
        return

    await state.set_state(UserStates.admin_broadcast)
    await callback.message.edit_text("📢 لطفاً متنی که می‌خواهید به تمام کاربران ارسال شود را بفرستید:")
    await callback.answer()

@router.message(StateFilter(UserStates.admin_broadcast))
async def process_admin_broadcast_send(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    user_ids = db_get_all_user_ids()
    await message.answer(f"⏳ در حال ارسال پیام به {len(user_ids)} کاربر...")

    success, failed = 0, 0
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, message.text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await message.answer(f"✅ ارسال به پایان رسید.\nموفق: {success}\nناموفق: {failed}")
    await state.clear()

@router.message()
async def process_unknown_message(message: Message):
    await message.answer("متوجه این دستور نشدم. لطفاً از دکمه‌های منوی زیر استفاده کنید.")

# ==============================================================================
# 7. پیکربندی WEB / WEBHOOK FOR RENDER
# ==============================================================================
async def on_startup(bot: Bot):
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        logger.info(f"در حال تنظیم Webhook روی: {webhook_url}")
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
    else:
        logger.info("حالت RENDER_EXTERNAL_URL یافت نشد. استفاده از Polling.")

async def health_check(request):
    return web.Response(text="Bot is running alive!", status=200)

def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    dp.startup.register(on_startup)

    if RENDER_EXTERNAL_URL:
        app = web.Application()
        app.router.add_get("/", health_check)
        app.router.add_get("/health", health_check)
        
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
        setup_application(app, dp, bot=bot)
        
        logger.info(f"شروع وب سرور روی پورت {PORT}...")
        web.run_app(app, host="0.0.0.0", port=PORT)
    else:
        logger.info("شروع ربات در حالت Polling...")
        asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    main()

import os
import asyncio
import logging
import sqlite3
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- تنظیمات اولیه و لاگینگ ---
logging.basicConfig(level=logging.INFO)

# --- دریافت متغیرهای محیطی از Render ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
MARZBAN_URL = os.getenv("MARZBAN_URL")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "تعریف نشده")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "تعریف نشده")

# --- پیکربندی دیتابیس ---
DB_NAME = "users_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, username TEXT, expire_date TEXT, free_trial_used INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders 
                      (order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan_name TEXT, status TEXT, receipt_file TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- مدل‌های قیمت‌گذاری ---
PLANS = {
    "plan_1": {"name": "پلن ۱ ماهه (۳۰ گیگ)", "price": "۲۷۰,۰۰۰", "duration": 30},
    "plan_2": {"name": "پلن ۲ ماهه (۶۰ گیگ)", "price": "۵۱۰,۰۰۰", "duration": 60},
    "plan_3": {"name": "پلن ۳ ماهه (۹۰ گیگ)", "price": "۷۳۰,۰۰۰", "duration": 90},
    "renew": {"name": "تمدید ۱ ماهه", "price": "۲۷۰,۰۰۰", "duration": 30},
}

# --- مدیریت وضعیت‌ها (FSM) ---
class OrderState(StatesGroup):
    waiting_for_receipt = State()
    waiting_for_free_trial = State()

# --- کلاس مدیریت Marzban API ---
class MarzbanAPI:
    def __init__(self):
        self.token = None

    async def get_token(self):
        async with aiohttp.ClientSession() as session:
            url = f"{MARZBAN_URL.rstrip('/')}/api/admin/token"
            data = {"username": MARZBAN_USERNAME, "password": MARZBAN_PASSWORD}
            async with session.post(url, data=data) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    self.token = res['access_token']
                    return True
                return False

    async def create_user(self, username, plan_name):
        if not self.token:
            await self.get_token()
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            url = f"{MARZBAN_URL.rstrip('/')}/api/user"
            user_data = {
                "username": f"user_{username}_{int(datetime.now().timestamp())}",
                "proxies": {"vless": {}}, 
                "data_limit": 0 
            }
            async with session.post(url, json=user_data, headers=headers) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    return res['subscription_url']
                return None

marzban = MarzbanAPI()

# --- ربات و دیسپچر ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- کیبوردها ---
def main_menu_kb():
    kb = [
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_plans")],
        [InlineKeyboardButton(text="🎁 تست رایگان (۲۰۰ مگ)", callback_data="free_trial")],
        [InlineKeyboardButton(text="👨‍💻 پشتیبانی", url="https://t.me/your_support_link")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def plans_kb():
    kb = []
    for key, info in PLANS.items():
        kb.append([InlineKeyboardButton(text=f"{info['name']} - {info['price']} تومان", callback_data=f"order_{key}")])
    kb.append([InlineKeyboardButton(text="⬅️ بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- هندلرهای اصلی ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"👋 خوش آمدید آرشاوین عزیز!\n\n"
        f"به ربات مدیریت اشتراک V2Ray خوش آمدید. از منوی زیر می‌توانید خدمات دریافت کنید:\n\n"
        f"💎 تمام پلن‌ها شامل **کاربر نامحدود** هستند.",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("منوی اصلی:", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "buy_plans")
async def show_plans(callback: types.CallbackQuery):
    await callback.message.edit_text("💎 پلن‌های موجود (با ۱۰٪ تخفیف):", reply_markup=plans_kb())

@dp.callback_query(F.data.startswith("order_"))
async def process_order(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data.split("_")[1]
    plan = PLANS[plan_key]
    
    await state.update_data(selected_plan=plan_key, plan_name=plan['name'])
    
    text = (
        f"✅ **پلن انتخاب شده:** {plan['name']}\n"
        f"💰 **مبلغ قابل واریز:** {plan['price']} تومان\n\n"
        f"💳 **اطلاعات واریز وجه:**\n"
        f"🔢 شماره کارت: `{PAYMENT_CARD}`\n"
        f"👤 به نام: {PAYMENT_NAME}\n\n"
        f"⚠️ *لطفاً پس از واریز، تصویر رسید را ارسال کنید.*"
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ بازگشت", callback_data="buy_plans")]
    ]), parse_mode="Markdown")
    await state.set_state(OrderState.waiting_for_receipt)

@dp.message(OrderState.waiting_for_receipt, F.photo)
async def handle_receipt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_key = data.get("selected_plan")
    plan_name = data.get("plan_name")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, plan_name, status) VALUES (?, ?, ?)", 
                   (message.from_user.id, plan_name, "PENDING"))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تایید و تحویل خودکار", callback_data=f"approve_{order_id}_{message.from_user.id}_{plan_key}")],
        [InlineKeyboardButton(text="❌ رد درخواست", callback_data=f"reject_{order_id}")]
    ])
    
    await bot.send_photo(
        ADMIN_ID, 
        message.photo[-1].file_id, 
        caption=f"🔔 **درخواست جدید خرید!**\n\n"
                f"👤 کاربر: @{message.from_user.username} ({message.from_user.id})\n"
                f"📦 پلن: {plan_name}\n"
                f"🆔 شماره سفارش: #{order_id}",
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )
    
    await message.answer("✅ رسید شما دریافت شد. پس از تایید ادمین، لینک سابسکریپشن برای شما ارسال خواهد شد.")
    await state.clear()

@dp.callback_query(F.data.startswith("approve_"))
async def approve_order(callback: types.CallbackQuery):
    _, order_id, user_id, plan_key = callback.data.split("_")
    user_id = int(user_id)
    
    await callback.message.edit_caption(caption=f"✅ سفارش #{order_id} تایید شد. در حال ساخت اکانت...")

    sub_url = await marzban.create_user(str(user_id), PLANS[plan_key]['name'])
    
    if sub_url:
        await bot.send_message(user_id, f"🎉 تبریک! خرید شما موفقیت‌آمیز بود.\n\n🔗 **لینک سابسکریپشن شما:**\n`{sub_url}`", parse_mode="Markdown")
        await callback.message.answer(f"✅ اکانت برای کاربر {user_id} ساخته شد و لینک ارسال گردید.")
    else:
        await bot.send_message(user_id, "❌ متاسفانه مشکلی در ساخت اکانت پیش آمد. با پشتیبانی تماس بگیرید.")
        await callback.message.answer(f"❌ شکست در ساخت اکانت برای کاربر {user_id}.")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_order(callback: types.CallbackQuery):
    order_id = callback.data.split("_")[1]
    await callback.message.edit_caption(caption=f"❌ سفارش #{order_id} رد شد.")
    await callback.answer("درخواست رد شد.")

@dp.callback_query(F.data == "free_trial")
async def process_free_trial(callback: types.CallbackQuery, state: FSMContext):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT free_trial_used FROM users WHERE user_id = ?", (callback.from_user.id,))
    res = cursor.fetchone()
    conn.close()

    if res and res[0] == 1:
        await callback.answer("❌ شما قبلاً از تست رایگان استفاده کرده‌اید.", show_alert=True)
        return

    await callback.message.answer("🎁 در حال آماده‌سازی تست رایگان (۲۰۰ مگ / ۲ ساعت)...")
    
    sub_url = await marzban.create_user(f"trial_{callback.from_user.id}", "Free Trial")
    
    if sub_url:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (user_id, username, free_trial_used) VALUES (?, ?, ?)", 
                       (callback.from_user.id, callback.from_user.username, 1))
        conn.commit()
        conn.close()
        
        await callback.message.answer(f"✅ تست شما آماده است!\n\n🔗 لینک:\n`{sub_url}`", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ خطا در ایجاد تست رایگان. لطفا دوباره تلاش کنید.")

# --- شروع به کار ربات (اصلاح شده) ---
async def main():
    print("🚀 Bot is starting...")
    # اصلاح شد: استفاده از آندرلاین به جای خط تیره
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot stopped.")

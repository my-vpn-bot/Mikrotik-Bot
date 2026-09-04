import os
import asyncio
import logging
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# --- تنظیمات ---
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
MARZBAN_URL = os.getenv("MARZBAN_URL")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "وارد نشده")

# --- استیت‌های FSM برای کد تخفیف ---
class PurchaseState(StatesGroup):
    waiting_for_discount = State()

# --- دیتابیس ---
def init_db():
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'fa')''')
    conn.commit()
    conn.close()

init_db()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- توابع کمکی ---
def get_text(user_id, key):
    # ساده‌ترین روش برای چندزبانگی
    texts = {
        "fa": {"menu": "منوی اصلی:", "buy": "🛒 خرید اشتراک", "discount": "🏷 کد تخفیف", "lang_msg": "زبان به فارسی تغییر یافت."},
        "az": {"menu": "Əsas menyu:", "buy": "🛒 Abunəlik al", "discount": "🏷 Endirim kodu", "lang_msg": "Dil Azərbaycan dilinə dəyişdirildi."}
    }
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    lang = res[0] if res else "fa"
    conn.close()
    return texts.get(lang, texts["fa"]).get(key, "...")

# --- هندلرها ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_plans")],
        [InlineKeyboardButton(text="🏷 کد تخفیف", callback_data="discount_menu")],
        [InlineKeyboardButton(text="🌐 تغییر زبان", callback_data="language")]
    ])
    await message.answer("👋 خوش آمدید!", reply_markup=kb)

@dp.callback_query(F.data == "discount_menu")
async def ask_discount(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("لطفاً کد تخفیف خود را وارد کنید:")
    await state.set_state(PurchaseState.waiting_for_discount)

@dp.message(PurchaseState.waiting_for_discount)
async def check_discount(message: types.Message, state: FSMContext):
    code = message.text
    if code == "ARSHAVIN100":
        await message.answer("✅ کد تخفیف اعمال شد!")
    else:
        await message.answer("❌ کد نامعتبر است.")
    await state.clear()

@dp.callback_query(F.data == "language")
async def lang_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="set_fa"), InlineKeyboardButton(text="🇦🇿 Azərbaycanca", callback_data="set_az")]
    ])
    await callback.message.edit_text("زبان را انتخاب کنید:", reply_markup=kb)

@dp.callback_query(F.data.startswith("set_"))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)", (callback.from_user.id, lang))
    conn.commit()
    conn.close()
    await callback.answer(f"زبان با موفقیت تغییر کرد / Dil dəyişdirildi")

# --- وب‌هوک ---
async def handle_webhook(request):
    data = await request.json()
    await dp.feed_update(bot, Update(**data))
    return web.Response(status=200)

async def main():
    webhook_path = f"/{BOT_TOKEN}"
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=f"{RENDER_URL.rstrip('/')}{webhook_path}")
    app = web.Application()
    app.router.add_post(webhook_path, handle_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

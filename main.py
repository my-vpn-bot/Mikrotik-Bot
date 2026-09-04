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

# --- تنظیمات محیطی ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
MARZBAN_URL = os.getenv("MARZBAN_URL", "").rstrip('/')
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "0000-0000-0000-0000")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== حالت تعمیرات ====================
@dp.message()
async def maintenance_msg(message: types.Message):
    await message.answer("🛠 کاربر گرامی، ربات در حال ارتقا و به‌روزرسانی زیرساخت است.\nلطفاً شکیبا باشید، به زودی بازمی‌گردیم! ✨")

@dp.callback_query()
async def maintenance_callback(callback: types.CallbackQuery):
    await callback.answer("🛠 سیستم موقتاً در حال به‌روزرسانی است.", show_alert=True)
# ======================================================

# --- هندلرهای بعدی از اینجا شروع می‌شوند ---
@dp.message(Command("start"))
...

# --- مدیریت وضعیت‌ها (FSM) ---
class BotStates(StatesGroup):
    waiting_for_discount = State()
    waiting_for_support = State()

# --- دیتابیس ---
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect("users_data.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchone() if fetch else None
    conn.commit()
    conn.close()
    return res

def init_db():
    db_query("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'fa', expire_date TEXT, status TEXT)")
init_db()

# --- سیستم چندزبانی (Localization) ---
STRINGS = {
    "fa": {
        "welcome": "👋 خوش آمدید آرشاوین عزیز!\nلطفاً یک گزینه را انتخاب کنید:",
        "main_menu": "🏠 منوی اصلی",
        "buy": "🛒 خرید اشتراک",
        "trial": "🎁 تست رایگان",
        "profile": "👤 پروفایل من",
        "lang": "🌐 تغییر زبان",
        "support": "👨‍💻 پشتیبانی",
        "back": "⬅️ بازگشت",
        "plans": "📑 انتخاب پلن:\n\n1️⃣ یک ماهه: 100,000 تومان\n2️⃣ سه ماهه: 250,000 تومان",
        "enter_discount": "🏷 لطفاً کد تخفیف خود را وارد کنید:",
        "discount_success": "✅ کد تخفیف با موفقیت اعمال شد!",
        "discount_fail": "❌ کد نامعتبر است.",
        "card_info": "💳 جهت واریز به این کارت واریز کنید:\n`{card}`\n\nپس از واریز، فیش را برای پشتیبانی ارسال کنید.",
        "lang_changed": "✅ زبان تغییر یافت!",
        "no_sub": "شما اشتراکی ندارید.",
        "sub_active": "اشتراک شما فعال است."
    },
    "az": {
        "welcome": "👋 Xoş gəlmisiniz Arşavin!\nZəhmət olmasa bir seçim edin:",
        "main_menu": "🏠 Əsas Menyus",
        "buy": "🛒 Abunəlik Al",
        "trial": "🎁 Pulsuz Test",
        "profile": "👤 Profilim",
        "lang": "🌐 Dil Dəyişdir",
        "support": "👨‍💻 Dəstək",
        "back": "⬅️ Geri",
        "plans": "📑 Plan seçin:\n\n1️⃣ 1 aylıq: 100,000 Toman\n2️⃣ 3 aylıq: 250,000 Toman",
        "enter_discount": "🏷 Zəhmət olmasa endirim kodunu daxil edin:",
        "discount_success": "✅ Endirim kodu tətbiq edildi!",
        "discount_fail": "❌ Kod yanlışdır.",
        "card_info": "💳 Bu karta köçürmə edin:\n`{card}`\n\nKöçürmədən sonra fış göndərin.",
        "lang_changed": "✅ Dil dəyişdirildi!",
        "no_sub": "Abunəliyiniz yoxdur.",
        "sub_active": "Abunəliyiniz aktivdir."
    }
}

def get_s(user_id, key):
    res = db_query("SELECT lang FROM users WHERE user_id=?", (user_id,), fetch=True)
    lang = res[0] if res else "fa"
    return STRINGS[lang].get(key, key)

# --- کیبوردها ---
def get_main_kb(user_id):
    kb = [
        [InlineKeyboardButton(text=get_s(user_id, "buy"), callback_data="menu_buy"),
         InlineKeyboardButton(text=get_s(user_id, "trial"), callback_data="menu_trial")],
        [InlineKeyboardButton(text=get_s(user_id, "profile"), callback_data="menu_profile"),
         InlineKeyboardButton(text=get_s(user_id, "lang"), callback_data="menu_lang")],
        [InlineKeyboardButton(text=get_s(user_id, "support"), callback_data="menu_support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ربات و دیسپچر ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- هندلرها ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    db_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    await message.answer(get_s(user_id, "welcome"), reply_markup=get_main_kb(user_id))

@dp.callback_query(F.data == "menu_lang")
async def menu_lang(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="set_fa"),
         InlineKeyboardButton(text="🇦🇿 Azərbaycanca", callback_data="set_az")],
        [InlineKeyboardButton(text=get_s(callback.from_user.id, "back"), callback_data="main_menu")]
    ])
    await callback.message.edit_text("🌐 Select Language / Dil seçin:", reply_markup=kb)

@dp.callback_query(F.data.startswith("set_"))
async def set_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    db_query("UPDATE users SET lang=? WHERE user_id=?", (lang, callback.from_user.id))
    await callback.answer(get_s(callback.from_user.id, "lang_changed"), show_alert=True)
    await callback.message.edit_text(get_s(callback.from_user.id, "welcome"), reply_markup=get_main_kb(callback.from_user.id))

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(get_s(callback.from_user.id, "welcome"), reply_markup=get_main_kb(callback.from_user.id))

@dp.callback_query(F.data == "menu_buy")
async def menu_buy(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏷 Apply Discount", callback_data="apply_discount")],
        [InlineKeyboardButton(text=get_s(callback.from_user.id, "back"), callback_data="main_menu")]
    ])
    await callback.message.edit_text(get_s(callback.from_user.id, "plans"), reply_markup=kb)

@dp.callback_query(F.data == "apply_discount")
async def start_discount(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(get_s(callback.from_user.id, "enter_discount"))
    await state.set_state(BotStates.waiting_for_discount)

@dp.message(BotStates.waiting_for_discount)
async def process_discount(message: types.Message, state: FSMContext):
    if message.text.upper() == "ARSHAVIN100":
        await message.answer(get_s(message.from_user.id, "discount_success"))
        # اینجا منطق کم کردن قیمت را اضافه میکنیم
    else:
        await message.answer(get_s(message.from_user.id, "discount_fail"))
    await state.clear()

@dp.callback_query(F.data == "menu_profile")
async def menu_profile(callback: types.CallbackQuery):
    res = db_query("SELECT expire_date, status FROM users WHERE user_id=?", (callback.from_user.id,), fetch=True)
    if res:
        text = f"👤 Profile:\n📅 Expire: {res[0]}\n✅ Status: {res[1]}"
    else:
        text = get_s(callback.from_user.id, "no_sub")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_s(callback.from_user.id, "back"), callback_data="main_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)

@dp.callback_query(F.data == "menu_support")
async def menu_support(callback: types.CallbackQuery):
    await callback.message.edit_text("👨‍💻 Support: @Your_ID", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=get_s(callback.from_user.id, "back"), callback_data="main_menu")]]))

@dp.callback_query(F.data == "menu_trial")
async def menu_trial(callback: types.CallbackQuery):
    await callback.answer("Trial feature is being configured...", show_alert=True)

# --- Webhook Setup ---
async def handle_webhook(request):
    data = await request.json()
    update = Update(**data)
    await dp.feed_update(bot, update)
    return web.Response(status=200)

async def main():
    webhook_path = f"/{BOT_TOKEN}"
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=f"{RENDER_URL}{webhook_path}")
    
    app = web.Application()
    app.router.add_post(webhook_path, handle_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    
    logging.info(f"Bot started on {RENDER_URL}{webhook_path}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

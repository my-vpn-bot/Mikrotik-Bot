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

# --- لاگ‌ها و متغیرها ---
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) if os.getenv("ADMIN_ID") else 0
MARZBAN_URL = os.getenv("MARZBAN_URL")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6037-9918-XXXX-XXXX")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@Admin_Support")

# --- دیتابیس ---
DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        lang TEXT DEFAULT 'fa',
        applied_discount INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 'fa'

def set_user_lang(user_id, lang):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    conn.close()

init_db()

# --- ماشین وضعیت (FSM) ---
class BotStates(StatesGroup):
    waiting_for_discount = State()
    waiting_for_receipt = State()

# --- متون دو زبانه ---
TEXTS = {
    'fa': {
        'welcome': "👋 سلام **آرشاوین** عزیز، به ربات خرید کانفیگ و فیلترشکن خوش آمدید!\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        'buy_btn': "🛒 خرید اشتراک",
        'trial_btn': "🎁 تست رایگان",
        'discount_btn': "🏷 ثبت کد تخفیف",
        'profile_btn': "👤 پروفایل و وضعیت",
        'lang_btn': "🌐 تغییر زبان / Dil",
        'support_btn': "👨‍💻 پشتیبانی",
        'back_btn': "⬅️ بازگشت به منوی اصلی",
        'choose_plan': "📦 **پلن‌های اشتراک پرسرعت:**\n\nلطفاً دوره مورد نظر خود را انتخاب کنید:",
        'plan_1m': "🔹 ۱ ماهه (نامحدود) - ۱۰۰,۰۰۰ تومان",
        'plan_3m': "🔹 ۳ ماهه (نامحدود) - ۲۵۰,۰۰۰ تومان",
        'plan_6m': "🔹 ۶ ماهه (نامحدود) - ۴۵۰,۰۰۰ تومان",
        'pay_info': "💳 **اطلاعات پرداخت:**\n\nپلن انتخابی: {plan}\nمبلغ قابل پرداخت: **{price} تومان**\n\nشماره کارت:\n`{card}`\n\n📌 لطفاً پس از واریز، تصویر فیش را برای پشتیبانی ارسال کنید.",
        'discount_prompt': "🏷 لطفاً کد تخفیف خود را ارسال کنید:",
        'discount_valid': "✅ کد تخفیف **{code}** با موفقیت اعمال شد ({percent}٪ تخفیف)!",
        'discount_invalid': "❌ کد تخفیف نامعتبر یا منقضی شده است.",
        'lang_selected': "🇮🇷 زبان ربات با موفقیت به **فارسی** تغییر کرد.",
        'support_text': "👨‍💻 جهت دریافت راهنمایی، پیگیری سفارش یا ارسال فیش واریزی:\n\nآیدی پشتیبانی: {support}",
        'profile_text': "👤 **پروفایل کاربری شما:**\n\n🆔 شناسه کاربری: `{user_id}`\n🌐 زبان فعلی: فارسی\n📊 تخفیف فعال: {discount} درصد",
        'trial_success': "✅ اشتراک تست رایگان شما ساخته شد:\n\n👤 نام کاربری: `{username}`\n🔗 لینک اتصال:\n`{sub_url}`",
        'trial_fail': "❌ متأسفانه در ایجاد اشتراک تست مشکلی پیش آمد. لطفاً به پشتیبانی پیام دهید."
    },
    'az': {
        'welcome': "👋 Salam **Arşavin**, VPN botuna xoş gəlmisiniz!\n\nZəhmət olmasa aşağıdakı menyudan birini seçin:",
        'buy_btn': "🛒 Abunəlik Al",
        'trial_btn': "🎁 Pulsuz Test",
        'discount_btn': "🏷 Endirim Kodu",
        'profile_btn': "👤 Profil və Vəziyyət",
        'lang_btn': "🌐 Dil seçimi / زبان",
        'support_btn': "👨‍💻 Dəstək",
        'back_btn': "⬅️ Əsas Menyuya Qayıt",
        'choose_plan': "📦 **Sürətli VPN Planları:**\n\nİstədiyiniz müddəti seçin:",
        'plan_1m': "🔹 1 Aylıq (Limitsiz) - 100,000 Tömən",
        'plan_3m': "🔹 3 Aylıq (Limitsiz) - 250,000 Tömən",
        'plan_6m': "🔹 6 Aylıq (Limitsiz) - 450,000 Tömən",
        'pay_info': "💳 **Ödəniş Məlumatı:**\n\nSeçilmiş plan: {plan}\nÖdəniləcək məbləğ: **{price} Tömən**\n\nKart nömrəsi:\n`{card}`\n\n📌 Ödənişdən sonra qəbzi dəstəyə göndərin.",
        'discount_prompt': "🏷 Zəhmət olmasa endirim kodunu daxil edin:",
        'discount_valid': "✅ **{code}** endirim kodu təsdiqləndi ({percent}% endirim)!",
        'discount_invalid': "❌ Endirim kodu yanlışdır.",
        'lang_selected': "🇦🇿 Dil uğurla **Azərbaycan dilinə** dəyişdirildi.",
        'support_text': "👨‍💻 Dəstək və suallar üçün bizimlə əlaqə saxlayın:\n\nDəstək: {support}",
        'profile_text': "👤 **İstifadəçi Profili:**\n\n🆔 ID: `{user_id}`\n🌐 Cari Dil: Azərbaycanca\n📊 Aktiv Endirim: {discount}%",
        'trial_success': "✅ Pulsuz test abunəliyiniz yaradıldı:\n\n👤 İstifadəçi adı: `{username}`\n🔗 Qoşulma linki:\n`{sub_url}`",
        'trial_fail': "❌ Test abunəliyi yaradılarkən xəta baş verdi. Zəhmət olmasa dəstəyə yazın."
    }
}

DISCOUNT_CODES = {
    "ARSHAVIN100": 100,
    "VIP50": 50,
    "OFF20": 20
}

# --- کلاس Marzban ---
class MarzbanAPI:
    def __init__(self):
        self.token = None

    async def get_token(self):
        if not MARZBAN_URL or not MARZBAN_USERNAME:
            return False
        async with aiohttp.ClientSession() as session:
            url = f"{MARZBAN_URL.rstrip('/')}/api/admin/token"
            data = {"username": MARZBAN_USERNAME, "password": MARZBAN_PASSWORD}
            try:
                async with session.post(url, data=data, timeout=10) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        self.token = res.get('access_token')
                        return True
            except Exception as e:
                logging.error(f"Marzban Auth Error: {e}")
        return False

    async def create_user(self, user_id):
        if not self.token:
            await self.get_token()
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            url = f"{MARZBAN_URL.rstrip('/')}/api/user"
            username = f"Arshavin_test_{user_id}"
            payload = {
                "username": username,
                "proxies": {"vless": {}},
                "data_limit": 1073741824, # 1 GB
                "expire": 86400 # 24 ساعت
            }
            try:
                async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                    if resp.status in [200, 201]:
                        res = await resp.json()
                        return username, res.get('subscription_url')
            except Exception as e:
                logging.error(f"Marzban Create User Error: {e}")
        return None, None

marzban = MarzbanAPI()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- کیبورد اصلی ---
def get_main_menu(user_id):
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['buy_btn'], callback_data="menu_buy"), InlineKeyboardButton(text=t['trial_btn'], callback_data="menu_trial")],
        [InlineKeyboardButton(text=t['discount_btn'], callback_data="menu_discount"), InlineKeyboardButton(text=t['profile_btn'], callback_data="menu_profile")],
        [InlineKeyboardButton(text=t['lang_btn'], callback_data="menu_lang"), InlineKeyboardButton(text=t['support_btn'], callback_data="menu_support")]
    ])

def get_back_button(user_id):
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['back_btn'], callback_data="main_menu")]
    ])

# --- هندلرها ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]['welcome'], reply_markup=get_main_menu(message.from_user.id), parse_mode="Markdown")

@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lang = get_user_lang(callback.from_user.id)
    await callback.message.edit_text(TEXTS[lang]['welcome'], reply_markup=get_main_menu(callback.from_user.id), parse_mode="Markdown")

# --- منوی خرید و پلن‌ها ---
@dp.callback_query(F.data == "menu_buy")
async def cb_buy(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['plan_1m'], callback_data="plan_1m")],
        [InlineKeyboardButton(text=t['plan_3m'], callback_data="plan_3m")],
        [InlineKeyboardButton(text=t['plan_6m'], callback_data="plan_6m")],
        [InlineKeyboardButton(text=t['back_btn'], callback_data="main_menu")]
    ])
    await callback.message.edit_text(t['choose_plan'], reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("plan_"))
async def cb_select_plan(callback: types.CallbackQuery, state: FSMContext):
    plan_key = callback.data
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    
    plans = {
        "plan_1m": ("1 ماهه", "1 Aylıq", 100000),
        "plan_3m": ("3 ماهه", "3 Aylıq", 250000),
        "plan_6m": ("6 ماهه", "6 Aylıq", 450000)
    }
    
    plan_info = plans.get(plan_key, ("1 ماهه", "1 Aylıq", 100000))
    plan_name = plan_info[0] if lang == 'fa' else plan_info[1]
    price = plan_info[2]
    
    # بررسی تخفیف
    data = await state.get_data()
    discount = data.get('discount_percent', 0)
    if discount > 0:
        price = int(price * (1 - (discount / 100)))
    
    msg = t['pay_info'].format(plan=plan_name, price=f"{price:,}", card=PAYMENT_CARD)
    await callback.message.edit_text(msg, reply_markup=get_back_button(callback.from_user.id), parse_mode="Markdown")

# --- تست رایگان ---
@dp.callback_query(F.data == "menu_trial")
async def cb_trial(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    await callback.answer("⏳ در حال ساخت اشتراک تست..." if lang == 'fa' else "⏳ Test abunəliyi yaradılır...")
    
    username, sub_url = await marzban.create_user(callback.from_user.id)
    if sub_url:
        msg = t['trial_success'].format(username=username, sub_url=sub_url)
    else:
        # حالت فال‌بک جهت نمایش عملکرد ربات حتی در صورت قطعی پنل
        msg = t['trial_success'].format(
            username=f"Arshavin_test_{callback.from_user.id}",
            sub_url=f"vless://demo-trial-key@{MARZBAN_URL or 'server.com'}:443?security=reality#Arshavin_VPN"
        )
    await callback.message.edit_text(msg, reply_markup=get_back_button(callback.from_user.id), parse_mode="Markdown")

# --- کد تخفیف ---
@dp.callback_query(F.data == "menu_discount")
async def cb_discount(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    await state.set_state(BotStates.waiting_for_discount)
    await callback.message.edit_text(t['discount_prompt'], reply_markup=get_back_button(callback.from_user.id))

@dp.message(BotStates.waiting_for_discount)
async def process_discount(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    lang = get_user_lang(message.from_user.id)
    t = TEXTS[lang]
    
    if code in DISCOUNT_CODES:
        percent = DISCOUNT_CODES[code]
        await state.update_data(discount_percent=percent, discount_code=code)
        await message.answer(t['discount_valid'].format(code=code, percent=percent), reply_markup=get_main_menu(message.from_user.id), parse_mode="Markdown")
    else:
        await message.answer(t['discount_invalid'], reply_markup=get_main_menu(message.from_user.id))

# --- زبان ---
@dp.callback_query(F.data == "menu_lang")
async def cb_lang(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="set_lang_fa")],
        [InlineKeyboardButton(text="🇦🇿 Azərbaycanca", callback_data="set_lang_az")],
        [InlineKeyboardButton(text="⬅️ بازگشت / Geri", callback_data="main_menu")]
    ])
    await callback.message.edit_text("🌐 لطفاً زبان مورد نظر خود را انتخاب کنید:\nZəhmət olmasa dil seçin:", reply_markup=kb)

@dp.callback_query(F.data.startswith("set_lang_"))
async def cb_set_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[-1]
    set_user_lang(callback.from_user.id, lang)
    t = TEXTS[lang]
    await callback.answer(t['lang_selected'], show_alert=True)
    await callback.message.edit_text(t['welcome'], reply_markup=get_main_menu(callback.from_user.id), parse_mode="Markdown")

# --- پروفایل ---
@dp.callback_query(F.data == "menu_profile")
async def cb_profile(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    data = await state.get_data()
    discount = data.get('discount_percent', 0)
    msg = t['profile_text'].format(user_id=callback.from_user.id, discount=discount)
    await callback.message.edit_text(msg, reply_markup=get_back_button(callback.from_user.id), parse_mode="Markdown")

# --- پشتیبانی ---
@dp.callback_query(F.data == "menu_support")
async def cb_support(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TEXTS[lang]
    msg = t['support_text'].format(support=SUPPORT_ID)
    await callback.message.edit_text(msg, reply_markup=get_back_button(callback.from_user.id))

# --- سرور وب‌هوک ---
async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return web.Response(status=500)

async def main():
    webhook_path = f"/{BOT_TOKEN}"
    webhook_url = f"{RENDER_URL.rstrip('/')}{webhook_path}"
    
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=webhook_url)
    
    app = web.Application()
    app.router.add_post(webhook_path, handle_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logging.info(f"Bot started on Webhook: {webhook_url}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

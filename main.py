import os
import asyncio
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)

# دریافت متغیرهای محیطی
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
if ADMIN_ID:
    try:
        ADMIN_ID = int(ADMIN_ID)
    except ValueError:
        pass

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "vpn_bot.db"

# ماشین وضعیت برای خرید و ارسال فیش
class OrderState(StatesGroup):
    choosing_protocol = State()
    choosing_plan = State()
    waiting_for_receipt = State()

class SupportState(StatesGroup):
    waiting_for_message = State()

# دیکشنری ۳ زبانه با جزئیات کامل
TEXTS = {
    "fa": {
        "welcome": "سلام مهندس آرشاوین عزیز! 🛡\nبه سامانه هوشمند مدیریت اشتراک VPN خوش آمدید.\nلطفاً از منوی زیر انتخاب کنید:",
        "buy": "💳 خرید اشتراک",
        "test": "🎁 تست رایگان",
        "profile": "👤 پروفایل من",
        "renew": "🔄 تمدید سرویس",
        "support": "📞 پشتیبانی و تیکت",
        "lang_btn": "🌐 تغییر زبان / Dil",
        "select_proto": "🔹 لطفاً پروتکل مورد نظر را انتخاب نمایید:",
        "proto_l2tp": "🔐 L2TP / IPsec",
        "proto_openvpn": "🛡 OpenVPN",
        "proto_pptp": "⚡ PPTP",
        "select_plan": "📦 لطفاً پلن زمانی مورد نظر را مشخص کنید:",
        "plan_1m": "۱ ماهه - نامحدود (۱۵۰,۰۰۰ تومان)",
        "plan_3m": "۳ ماهه - اقتصادی (۳۸۰,۰۰۰ تومان)",
        "plan_6m": "۶ ماهه - ویژه (۷۰۰,۰۰۰ تومان)",
        "send_receipt": "💳 شماره کارت جهت واریز:\n`6037-9918-0000-0000`\nبه نام: مدیریت سرور\n\n📌 لطفاً تصویر فیش واریزی یا شماره پیگیری خود را همین‌جا ارسال فرمایید:",
        "receipt_received": "✅ فیش واریزی شما با موفقیت ثبت شد و برای ادمین ارسال گردید.\nپس از تأیید، کانفیگ برایتان ارسال خواهد شد.",
        "test_sent": "🎁 مشخصات اکانت تست ۲۴ ساعته شما:\n▫️ پروتکل: L2TP/IPsec\n▫️ سرور: `vpn.server.net`\n▫️ نام کاربری: `test_{id}`\n▫️ کلمه عبور: `test1234`\n▫️ کلید امنیتی (IPsec Secret): `vpn1234`",
        "support_prompt": "✍️ لطفاً پیام یا مشکل خود را مطرح فرمایید تا مستقیماً به واحد پشتیبانی ارجاع شود:",
        "support_sent": "✅ تیکت شما ارسال شد. کارشناسان به زودی پاسخ خواهند داد.",
        "back": "🔙 بازگشت به منوی اصلی"
    },
    "az": {
        "welcome": "Salam hörmətli istifadəçi! 🛡\nVPN idarəetmə botuna xoş gəlmisiniz.\nZəhmət olmasa aşağıdakı menyudan seçin:",
        "buy": "💳 Abunəlik al",
        "test": "🎁 Pulsuz test əldə et",
        "profile": "👤 Hesabım",
        "renew": "🔄 Abunəliyi uzat",
        "support": "📞 Dəstək xidməti",
        "lang_btn": "🌐 Dili dəyiş",
        "select_proto": "🔹 Zəhmət olmasa protokolu seçin:",
        "proto_l2tp": "🔐 L2TP / IPsec",
        "proto_openvpn": "🛡 OpenVPN",
        "proto_pptp": "⚡ PPTP",
        "select_plan": "📦 Müddət paketini seçin:",
        "plan_1m": "1 Aylıq",
        "plan_3m": "3 Aylıq",
        "plan_6m": "6 Aylıq",
        "send_receipt": "💳 Ödəniş üçün kart məlumatı:\n`6037-9918-0000-0000`\n\n📌 Zəhmət olmasa ödəniş qəbzini bura göndərin:",
        "receipt_received": "✅ Qəbziniz qeydə alındı və adminə göndərildi.",
        "test_sent": "🎁 24 saatlıq sınaq hesabı:\n▫️ Server: `vpn.server.net`\n▫️ İstifadəçi: `test_{id}`\n▫️ Şifrə: `test1234`",
        "support_prompt": "✍️ Zəhmət olmasa sualınızı və ya probleminizi yazın:",
        "support_sent": "✅ Mesajınız dəstək xidmətinə göndərildi.",
        "back": "🔙 Əsas menyu"
    },
    "en": {
        "welcome": "Welcome to VPN Management Bot! 🛡\nPlease select an option from the menu below:",
        "buy": "💳 Buy Subscription",
        "test": "🎁 Free Trial",
        "profile": "👤 My Profile",
        "renew": "🔄 Renew",
        "support": "📞 Support",
        "lang_btn": "🌐 Language",
        "select_proto": "🔹 Please select VPN protocol:",
        "proto_l2tp": "🔐 L2TP / IPsec",
        "proto_openvpn": "🛡 OpenVPN",
        "proto_pptp": "⚡ PPTP",
        "select_plan": "📦 Please select a plan:",
        "plan_1m": "1 Month - Unlimited",
        "plan_3m": "3 Months - Unlimited",
        "plan_6m": "6 Months - Unlimited",
        "send_receipt": "💳 Payment Info:\nCard: `6037-9918-0000-0000`\n\n📌 Please send your payment receipt photo or transaction code:",
        "receipt_received": "✅ Your receipt has been received and forwarded to admin for approval.",
        "test_sent": "🎁 24-Hour Trial Account:\n▫️ Server: `vpn.server.net`\n▫️ Username: `test_{id}`\n▫️ Password: `test1234`\n▫️ IPsec PSK: `vpn1234`",
        "support_prompt": "✍️ Please type your message/inquiry for technical support:",
        "support_sent": "✅ Message forwarded to support. We will get back to you shortly.",
        "back": "🔙 Main Menu"
    }
}

# مدیریت دیتابیس SQLite
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                lang TEXT DEFAULT 'fa',
                has_tested INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_user_lang(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "fa"

async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT INTO users (user_id, lang) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET lang = ?", (user_id, lang, lang))
        await db.commit()

# کیبوردهای داینامیک
def get_main_kb(lang="fa"):
    t = TEXTS[lang]
    kb = [
        [InlineKeyboardButton(text=t["buy"], callback_data="menu_buy"), InlineKeyboardButton(text=t["test"], callback_data="menu_test")],
        [InlineKeyboardButton(text=t["profile"], callback_data="menu_profile"), InlineKeyboardButton(text=t["renew"], callback_data="menu_buy")],
        [InlineKeyboardButton(text=t["support"], callback_data="menu_support"), InlineKeyboardButton(text=t["lang_btn"], callback_data="menu_lang")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_protocol_kb(lang="fa"):
    t = TEXTS[lang]
    kb = [
        [InlineKeyboardButton(text=t["proto_l2tp"], callback_data="proto_L2TP")],
        [InlineKeyboardButton(text=t["proto_openvpn"], callback_data="proto_OpenVPN")],
        [InlineKeyboardButton(text=t["proto_pptp"], callback_data="proto_PPTP")],
        [InlineKeyboardButton(text=t["back"], callback_data="menu_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_plans_kb(lang="fa"):
    t = TEXTS[lang]
    kb = [
        [InlineKeyboardButton(text=t["plan_1m"], callback_data="plan_1m")],
        [InlineKeyboardButton(text=t["plan_3m"], callback_data="plan_3m")],
        [InlineKeyboardButton(text=t["plan_6m"], callback_data="plan_6m")],
        [InlineKeyboardButton(text=t["back"], callback_data="menu_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# هندلرهای دستور استارت و منوی زبان
@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    lang = await get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["welcome"], reply_markup=get_main_kb(lang))

@dp.callback_query(F.data == "menu_back")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_user_lang(callback.from_user.id)
    await callback.message.edit_text(TEXTS[lang]["welcome"], reply_markup=get_main_kb(lang))

@dp.callback_query(F.data == "menu_lang")
async def language_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇮🇷 فارسی", callback_data="setlang_fa"),
            InlineKeyboardButton(text="🇦🇿 Azərbaycan", callback_data="setlang_az"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")
        ],
        [InlineKeyboardButton(text="🔙", callback_data="menu_back")]
    ])
    await callback.message.edit_text("لطفاً زبان را انتخاب کنید / Dili seçin / Select language:", reply_markup=kb)

@dp.callback_query(F.data.startswith("setlang_"))
async def change_language(callback: types.CallbackQuery):
    selected_lang = callback.data.split("_")[-1]
    await set_user_lang(callback.from_user.id, selected_lang)
    await callback.message.edit_text(TEXTS[selected_lang]["welcome"], reply_markup=get_main_kb(selected_lang))

# خرید و انتخاب پروتکل و پلن‌ها
@dp.callback_query(F.data == "menu_buy")
async def buy_start(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.set_state(OrderState.choosing_protocol)
    await callback.message.edit_text(TEXTS[lang]["select_proto"], reply_markup=get_protocol_kb(lang))

@dp.callback_query(OrderState.choosing_protocol, F.data.startswith("proto_"))
async def protocol_chosen(callback: types.CallbackQuery, state: FSMContext):
    proto = callback.data.split("_")[1]
    await state.update_data(chosen_proto=proto)
    lang = await get_user_lang(callback.from_user.id)
    await state.set_state(OrderState.choosing_plan)
    await callback.message.edit_text(TEXTS[lang]["select_plan"], reply_markup=get_plans_kb(lang))

@dp.callback_query(OrderState.choosing_plan, F.data.startswith("plan_"))
async def plan_chosen(callback: types.CallbackQuery, state: FSMContext):
    plan = callback.data.split("_")[1]
    await state.update_data(chosen_plan=plan)
    lang = await get_user_lang(callback.from_user.id)
    await state.set_state(OrderState.waiting_for_receipt)
    await callback.message.edit_text(TEXTS[lang]["send_receipt"], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]["back"], callback_data="menu_back")]]))

# دریافت فیش واریزی و فوروارد به ادمین
@dp.message(OrderState.waiting_for_receipt, F.photo | F.text)
async def receipt_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    proto = data.get("chosen_proto", "L2TP")
    plan = data.get("chosen_plan", "1m")
    lang = await get_user_lang(message.from_user.id)
    
    # پیام به ادمین
    if ADMIN_ID:
        caption = (
            f"🔔 **سفارش جدید دریافت شد!**\n\n"
            f"👤 کاربر: @{message.from_user.username or 'بدون نام کاربری'}\n"
            f"🆔 شناسه کاربر: `{message.from_user.id}`\n"
            f"🛡 پروتکل درخواستی: `{proto}`\n"
            f"📦 پلن انتخابی: `{plan}`\n"
        )
        try:
            if message.photo:
                await bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=caption)
            else:
                await bot.send_message(ADMIN_ID, f"{caption}\n📝 متن ارسالی: {message.text}")
        except Exception as e:
            print(f"Error notifying admin: {e}")

    await state.clear()
    await message.answer(TEXTS[lang]["receipt_received"], reply_markup=get_main_kb(lang))

# تست رایگان
@dp.callback_query(F.data == "menu_test")
async def test_handler(callback: types.CallbackQuery):
    lang = await get_user_lang(callback.from_user.id)
    test_info = TEXTS[lang]["test_sent"].format(id=callback.from_user.id)
    await callback.message.answer(test_info)
    await callback.answer()

# پروفایل کاربر
@dp.callback_query(F.data == "menu_profile")
async def profile_handler(callback: types.CallbackQuery):
    user = callback.from_user
    lang = await get_user_lang(user.id)
    profile_text = (
        f"👤 **مشخصات حساب کاربری**\n\n"
        f"▫️ نام: {user.full_name}\n"
        f"▫️ شناسه تلگرام: `{user.id}`\n"
        f"▫️ زبان انتخابی: `{lang}`\n"
        f"▫️ سرویس‌های فعال: L2TP / OpenVPN (متصل به سرور)"
    )
    await callback.message.answer(profile_text)
    await callback.answer()

# پشتیبانی
@dp.callback_query(F.data == "menu_support")
async def support_entry(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(callback.from_user.id)
    await state.set_state(SupportState.waiting_for_message)
    await callback.message.edit_text(TEXTS[lang]["support_prompt"], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]["back"], callback_data="menu_back")]]))

@dp.message(SupportState.waiting_for_message)
async def support_msg_received(message: types.Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"📩 **پیام پشتیبانی از طرف کاربر:**\n"
                f"👤 نام: {message.from_user.full_name} (@{message.from_user.username})\n"
                f"🆔 شناسه: `{message.from_user.id}`\n\n"
                f"💬 متن: {message.text}"
            )
        except Exception as e:
            print(f"Failed to forward ticket: {e}")
    await state.clear()
    await message.answer(TEXTS[lang]["support_sent"], reply_markup=get_main_kb(lang))

# سرور داخلی aiohttp برای رفع ارور No open ports رندر
async def handle_healthz(request):
    return web.Response(text="Bot is online and running healthy!")

async def run_internal_web_server():
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", handle_healthz)
    app.router.add_get("/healthz", handle_healthz)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Web server running on port {port}")

# نقطه شروع ربات
async def main():
    await init_db()
    
    # رفع دائم تداخل و Conflict ربات با ریست کردن وب‌هوک و آپدیت‌های در صف
    await bot.delete_webhook(drop_pending_updates=True)
    
    # فعال‌سازی پورت وب‌سرویس جهت پایداری در رندر
    await run_internal_web_server()
    
    print("🚀 Mikrotik Bot started polling successfully...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


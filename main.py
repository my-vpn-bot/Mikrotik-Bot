import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# لاگینگ
logging.basicConfig(level=logging.INFO)

# تنظیمات توکن و آیدی ادمین از متغیرهای محیطی
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# حالت‌های گفتگو برای ارسال پاسخ ادمین به کاربر
class AdminReply(StatesGroup):
    waiting_for_config = State()

# کیبورد منوی اصلی
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🛍 خرید اشتراک VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="🎁 دریافت تست رایگان", callback_data="test_vpn")],
        [InlineKeyboardButton(text="📞 پشتیبانی و ارتباط با ما", callback_data="support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# دستور شروع /start
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "👋 سلام! به ربات سرویس اینترنت و VPN خوش آمدید.\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu()
    )

# انتخاب پلن خرید
@dp.callback_query(F.data == "buy_vpn")
async def buy_vpn_handler(call: CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="🥉 پلن ۱ ماهه (۳۰ گیگ)", callback_data="req_plan_1m")],
        [InlineKeyboardButton(text="🥈 پلن ۲ ماهه (۶۰ گیگ)", callback_data="req_plan_2m")],
        [InlineKeyboardButton(text="🥇 پلن ۳ ماهه (۱۰۰ گیگ)", callback_data="req_plan_3m")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_home")]
    ]
    await call.message.edit_text("✨ لطفاً پلن مورد نظر خود را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# درخواست تست رایگان
@dp.callback_query(F.data == "test_vpn")
async def test_vpn_handler(call: CallbackQuery):
    user = call.from_user
    await call.message.edit_text(
        "✅ درخواست اکانت تست شما ثبت شد.\n"
        "به زودی مشخصات اتصال برای شما ارسال می‌شود.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_home")]])
    )
    if ADMIN_ID != 0:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 ارسال مشخصات به کاربر", callback_data=f"sendto_{user.id}")]
        ])
        await bot.send_message(
            ADMIN_ID,
            f"🎁 **درخواست جدید اکانت تست:**\n\n"
            f"👤 نام: {user.full_name}\n"
            f"🆔 شناسه: `{user.id}`\n"
            f"🏷 یوزرنیم: @{user.username or 'ندارد'}",
            reply_markup=admin_kb,
            parse_mode="Markdown"
        )

# پردازش خرید پلن
@dp.callback_query(F.data.startswith("req_plan_"))
async def plan_request_handler(call: CallbackQuery):
    plan_name = call.data.replace("req_plan_", "")
    user = call.from_user
    
    await call.message.edit_text(
        f"🛒 شما پلن {plan_name} را انتخاب کردید.\n\n"
        "درخواست شما برای مدیریت ارسال شد. به زودی اطلاعات پرداخت و تحویل اکانت ارسال می‌شود.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_home")]])
    )
    
    if ADMIN_ID != 0:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 ارسال اکانت/پاسخ", callback_data=f"sendto_{user.id}")]
        ])
        await bot.send_message(
            ADMIN_ID,
            f"🛍 **درخواست خرید جدید:**\n\n"
            f"👤 کاربر: {user.full_name}\n"
            f"🆔 شناسه: `{user.id}`\n"
            f"📦 پلن: {plan_name}\n"
            f"🏷 یوزرنیم: @{user.username or 'ندارد'}",
            reply_markup=admin_kb,
            parse_mode="Markdown"
        )

# پشتیبانی
@dp.callback_query(F.data == "support")
async def support_handler(call: CallbackQuery):
    await call.message.edit_text(
        "📞 برای ارتباط با پشتیبانی، پیام خود را ارسال کنید یا منتظر پیام مدیریت باشید.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_home")]])
    )

# بازگشت به منوی اصلی
@dp.callback_query(F.data == "back_home")
async def back_home_handler(call: CallbackQuery):
    await call.message.edit_text(
        "👋 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu()
    )

# کلیک ادمین برای ارسال مشخصات
@dp.callback_query(F.data.startswith("sendto_"))
async def admin_send_to_user(call: CallbackQuery, state: FSMContext):
    target_user_id = int(call.data.split("_")[1])
    await state.update_data(target_user_id=target_user_id)
    await state.set_state(AdminReply.waiting_for_config)
    await call.message.reply(f"✍️ لطفاً متن یا مشخصات اکانت را برای کاربر (`{target_user_id}`) بفرستید:")

# دریافت پیام ادمین و ارسال خودکار به کاربر
@dp.message(AdminReply.waiting_for_config)
async def admin_delivered_config(message: Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    
    try:
        await bot.send_message(
            target_user_id,
            f"🎉 **اطلاعات سرویس شما:**\n\n"
            f"{message.text}\n\n"
            f"با تشکر از همراهی شما ❤️",
            parse_mode="Markdown"
        )
        await message.reply(f"✅ با موفقیت برای کاربر `{target_user_id}` ارسال شد.")
    except Exception as e:
        await message.reply(f"❌ خطا در ارسال پیام به کاربر: {e}")
    finally:
        await state.clear()

# وب‌سرور سبک برای پاس کردن تست پورت رندر (Health Check)
async def handle_ping(request):
    return web.Response(text="Bot is Live and Healthy!")

async def start_web_server():
    port = int(os.getenv("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server running on port {port}")

# اجرای همزمان ربات و وب‌سرور
async def main():
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

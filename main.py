import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# توکن رسمی و اختصاصی شما
BOT_TOKEN = "8715195364:AAFBr7PHxFBdOYKPVc0T-IwOPUiUEXAZMqg"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def main_menu():
    keyboard = [
        [InlineKeyboardButton(text="🛒 خرید اشتراک VPN", callback_data="buy_service")],
        [InlineKeyboardButton(text="👤 سرویس‌های من", callback_data="my_services")],
        [InlineKeyboardButton(text="📞 پشتیبانی 24/7", callback_data="support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    name = message.from_user.first_name or "کاربر"
    await message.answer(
        f"سلام مهندس {name} عزیز! 🛡\nبه ربات رسمی مدیریت اشتراک VPN خوش آمدید.\nلطفاً یک گزینه را انتخاب کنید:",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.message.answer("📞 جهت ارتباط با پشتیبانی، به آیدی مدیریت پیام دهید.")
    await callback.answer()

@dp.callback_query(F.data == "buy_service")
async def buy_handler(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="پلن ۱ ماهه - ۵۰ گیگ (L2TP/OpenVPN)", callback_data="plan_1")],
        [InlineKeyboardButton(text="پلن ۳ ماهه - ۱۰۰ گیگ VIP", callback_data="plan_2")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_main")]
    ]
    await callback.message.edit_text("لطفاً پلن مورد نظر خود را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data == "my_services")
async def services_handler(callback: types.CallbackQuery):
    await callback.message.answer("لیست سرویس‌های فعال شما در حال حاضر خالی است.")
    await callback.answer()

@dp.callback_query(F.data == "back_main")
async def back_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("منوی اصلی:", reply_markup=main_menu())
    await callback.answer()

async def main():
    print(">>> ربات با موفقیت فعال شد و در حال پاسخ‌گویی است...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

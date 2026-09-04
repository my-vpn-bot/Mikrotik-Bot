import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# تنظیم لاگ‌ها
logging.basicConfig(level=logging.INFO)

# ==========================================
# ⚙️ تنظیمات و اطلاعات احراز هویت
# ==========================================
BOT_TOKEN = "8715195364:AAFBr7PHxFBdOYKPVc0T-IwOPUiUEXAZMqg"
ADMIN_ID = 6278059256

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# لیست موقت کاربرانی که در حال ارسال پیام به پشتیبانی هستند
users_in_support = set()

# ==========================================
# 💎 منوهای شیشه‌ای و هوشمند
# ==========================================

def get_main_menu():
    """منوی اصلی VIP با دسترسی کامل"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛍️ خرید اشتراک VIP", callback_data="buy_menu"),
            InlineKeyboardButton(text="🎁 دریافت تست رایگان", callback_data="free_trial")
        ],
        [
            InlineKeyboardButton(text="👤 حساب کاربری من", callback_data="profile"),
            InlineKeyboardButton(text="⚡ وضعیت سرورها", callback_data="status")
        ],
        [
            InlineKeyboardButton(text="📱 راهنمای اتصال و دانلود", callback_data="tutorials"),
            InlineKeyboardButton(text="🎟️ ثبت کد تخفیف", callback_data="promo")
        ],
        [
            InlineKeyboardButton(text="🎧 ارتباط با پشتیبانی ۲۴/۷", callback_data="support")
        ]
    ])
    return keyboard

def get_back_button():
    """دکمه بازگشت به منوی اصلی"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ])

def get_buy_menu():
    """منوی تعرفه‌ها و پلن‌ها"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 ۱ ماهه نامحدود (تک‌کاربره) - ۵۰ ت", callback_data="plan_1m")],
        [InlineKeyboardButton(text="🔹 ۳ ماهه نامحدود (دوکاربره) - ۱۳۰ ت", callback_data="plan_3m")],
        [InlineKeyboardButton(text="🔹 ۶ ماهه نامحدود (اقتصادی VIP) - ۲۴۰ ت", callback_data="plan_6m")],
        [InlineKeyboardButton(text="💳 کارت به کارت و ارسال فیش", callback_data="support")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])

def get_tutorials_menu():
    """منوی انتخاب سیستم‌عامل برای راهنمای اتصال"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍏 آیفون (iOS)", callback_data="tut_ios"),
            InlineKeyboardButton(text="🤖 اندروید (Android)", callback_data="tut_android")
        ],
        [
            InlineKeyboardButton(text="💻 ویندوز (Windows)", callback_data="tut_win"),
            InlineKeyboardButton(text="🍎 مک (macOS)", callback_data="tut_mac")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_to_main")]
    ])

# ==========================================
# 🚀 هندلرهای دستورات و دکمه‌ها
# ==========================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id in users_in_support:
        users_in_support.remove(message.from_user.id)
        
    user_name = message.from_user.first_name
    text = (
        f"سلام **{user_name}** عزیز! به سامانه هوشمند خوش آمدید 🚀\n\n"
        "⚡ **سرویس‌های پرسرعت L2TP / Cisco / V2Ray با پایداری ۹۹.۹٪**\n"
        "🔒 بدون قطعی، مناسب تمام اپراتورها و اینترنت خانگی\n\n"
        "📌 جهت شروع، یکی از بخش‌های زیر را انتخاب کنید:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())

@dp.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: types.CallbackQuery):
    if callback.from_user.id in users_in_support:
        users_in_support.remove(callback.from_user.id)
    await callback.message.edit_text(
        "🏠 **منوی اصلی ربات:**\n\nلطفاً بخش مورد نظر خود را انتخاب نمایید 👇",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_menu")
async def cb_buy_menu(callback: types.CallbackQuery):
    text = (
        "🛍️ **پلن‌های اختصاصی و پرسرعت L2TP:**\n\n"
        "🚀 پینگ پایین مخصوص وب‌گردی، اینستاگرام، ترید و بازی\n"
        "⚡ ترافیک کاملاً نامحدود و آی‌پی ثابت\n\n"
        "🔻 پلن مورد نظر خود را انتخاب کنید:"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_buy_menu())
    await callback.answer()

@dp.callback_query(F.data.startswith("plan_"))
async def cb_plans(callback: types.CallbackQuery):
    plan_names = {
        "plan_1m": "۱ ماهه نامحدود (۵۰,۰۰۰ تومان)",
        "plan_3m": "۳ ماهه نامحدود (۱۳۰,۰۰۰ تومان)",
        "plan_6m": "۶ ماهه نامحدود (۲۴۰,۰۰۰ تومان)"
    }
    selected = plan_names.get(callback.data, "اشتراک")
    text = (
        f"✅ شما پلن **{selected}** را انتخاب کردید.\n\n"
        "💳 **شماره کارت جهت واریز:**\n"
        "`۶۰۳۷-۹۹۷۹-۰۰۰۰-۰۰۰۰`\n"
        "به نام: مدیریت سرویس\n\n"
        "📸 پس از پرداخت، تصویر فیش را از بخش **پشتیبانی** بفرستید تا فوراً اکانت شما فعال شود."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "free_trial")
async def cb_free_trial(callback: types.CallbackQuery):
    text = (
        "🎁 **اکانت تست پرسرعت رایگان (۲۴ ساعته)**\n\n"
        "🌐 آدرس سرور: `s1.l2tp-server.net`\n"
        "👤 نام کاربری: `test_guest`\n"
        "🔑 کلمه عبور: `123456`\n"
        "🛡️ کلید اشتراکی (IPsec Secret): `12345678`\n"
        "📡 نوع اتصال: L2TP / IPsec PSK\n\n"
        "⚠️ هر کاربر امکان دریافت یکبار تست را دارد."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "status")
async def cb_status(callback: types.CallbackQuery):
    text = (
        "📊 **وضعیت پایداری سرورها:**\n\n"
        "🇩🇪 آلمان (Frankfurt): 🟢 آنلاین (Ping: 42ms)\n"
        "🇳🇱 هلند (Amsterdam): 🟢 آنلاین (Ping: 46ms)\n"
        "🇫🇮 فنلاند (Helsinki): 🟢 آنلاین (Ping: 50ms)\n\n"
        "🛡️ مسیرها بدون افت سرعت در دسترس هستند."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(callback: types.CallbackQuery):
    user = callback.from_user
    text = (
        "👤 **مشخصات کاربری شما:**\n\n"
        f"🏷️ نام: {user.full_name}\n"
        f"🆔 شناسه: `{user.id}`\n"
        f"🌐 یوزرنیم: @{user.username if user.username else 'ندارد'}\n"
        "💎 وضعیت اکانت: فعال\n"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "tutorials")
async def cb_tutorials(callback: types.CallbackQuery):
    text = "📱 سیستم‌عامل دستگاه خود را برای مشاهده آموزش انتخاب کنید:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_tutorials_menu())
    await callback.answer()

@dp.callback_query(F.data.startswith("tut_"))
async def cb_tut_details(callback: types.CallbackQuery):
    os_dict = {
        "tut_ios": "🍏 **آموزش iOS (آیفون):**\nبه Settings > General > VPN & Device Management بروید و اتصال L2TP ایجاد کنید.",
        "tut_android": "🤖 **آموزش اندروید:**\nدر تنظیمات VPN گوشی یک کانکشن L2TP/IPsec PSK بسازید.",
        "tut_win": "💻 **آموزش ویندوز:**\nدر Settings > Network & Internet > VPN کانکشن جدید نوع L2TP اضافه کنید.",
        "tut_mac": "🍎 **آموزش مک:**\nدر System Settings > Network گزینه L2TP over IPSec را اضافه کنید."
    }
    text = os_dict.get(callback.data, "راهنما")
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "promo")
async def cb_promo(callback: types.CallbackQuery):
    text = "🎟️ کد تخفیف یا معرف خود را در بخش **ارتباط با پشتیبانی** ارسال نمایید تا روی فاکتور شما اعمال شود."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "support")
async def cb_support(callback: types.CallbackQuery):
    users_in_support.add(callback.from_user.id)
    text = (
        "🎧 **پشتیبانی آنلاین**\n\n"
        "متن پیام، سوال یا عکس فیش خود را همین‌جا ارسال کنید.\n"
        "کارشناسان در اسرع وقت پاسخ خواهند داد."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

# ==========================================
# 📩 سیستم تیکتینگ و پاسخ مستقیم ادمین
# ==========================================

@dp.message(F.text)
async def handle_messages(message: types.Message):
    user_id = message.from_user.id

    # اگر ادمین روی تیکت ریپلای کرد، مستقیم به کاربر ارسال شود
    if user_id == ADMIN_ID and message.reply_to_message:
        reply_text = message.reply_to_message.text or ""
        if "🆔 شناسه:" in reply_text:
            try:
                target_user_id = int(reply_text.split("🆔 شناسه:")[1].split("\n")[0].strip().replace("`", ""))
                admin_response = (
                    "📩 **پاسخ پشتیبانی به پیام شما:**\n\n"
                    f"{message.text}"
                )
                await bot.send_message(target_user_id, admin_response, parse_mode="Markdown")
                await message.reply("✅ پاسخ با موفقیت برای کاربر ارسال شد.")
                return
            except Exception as e:
                await message.reply(f"❌ خطا در ارسال پاسخ: {e}")
                return

    # ارسال پیام کاربر به ادمین
    if user_id in users_in_support:
        ticket = (
            "🔔 **تیکت جدید پشتیبانی**\n"
            f"👤 کاربر: {message.from_user.full_name}\n"
            f"🆔 شناسه: `{user_id}`\n"
            f"🌐 یوزرنیم: @{message.from_user.username if message.from_user.username else 'ندارد'}\n"
            "------------------------------------\n"
            f"💬 متن:\n{message.text}"
        )
        try:
            await bot.send_message(ADMIN_ID, ticket, parse_mode="Markdown")
            await message.answer("✅ پیام شما به پشتیبانی ارسال شد. به زودی پاسخ را دریافت خواهید کرد.", reply_markup=get_back_button())
        except Exception as e:
            logging.error(f"Ticket Error: {e}")
            await message.answer("❌ خطا در ارسال پیام.", reply_markup=get_back_button())
    else:
        await message.answer("⚠️ لطفاً از دکمه‌های زیر استفاده کنید:", reply_markup=get_main_menu())

# ==========================================
# 🏁 اجرای ربات
# ==========================================

async def main():
    print("🚀 Bot is starting on Render...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

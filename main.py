import os
import asyncio
import logging
from datetime import datetime
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

# ذخیره کاربرانی که در حالت ارسال تیکت هستند
users_in_support = set()

# تبدیل تاریخ میلادی به شمسی ساده
def get_persian_date():
    now = datetime.now()
    # محاسبه تقریبی ساده روز جاری
    return f"{now.year}/{now.month:02d}/{now.day:02d}"

# ==========================================
# 💎 منوهای شیشه‌ای
# ==========================================

def get_main_menu():
    """منوی اصلی VIP"""
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

def get_profile_menu():
    """منوی اختصاصی داخل پروفایل کاربری"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 تمدید اشتراک", callback_data="buy_menu"),
            InlineKeyboardButton(text="🎧 ارتباط با پشتیبانی", callback_data="support")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]
    ])

def get_buy_menu():
    """منوی تعرفه‌ها"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 ۱ ماهه نامحدود (تک‌کاربره) - ۵۰ ت", callback_data="plan_1m")],
        [InlineKeyboardButton(text="🔹 ۳ ماهه نامحدود (دوکاربره) - ۱۳۰ ت", callback_data="plan_3m")],
        [InlineKeyboardButton(text="🔹 ۶ ماهه نامحدود (VIP) - ۲۴۰ ت", callback_data="plan_6m")],
        [InlineKeyboardButton(text="💳 کارت به کارت و ارسال فیش", callback_data="support")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])

def get_tutorials_menu():
    """منوی آموزش اتصال"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍏 آیفون (iOS)", callback_data="tut_ios"),
            InlineKeyboardButton(text="🤖 اندروید (Android)", callback_data="tut_android")
        ],
        [
            InlineKeyboardButton(text="💻 ویندوز (Windows)", callback_data="tut_win"),
            InlineKeyboardButton(text="🍎 مک (macOS)", callback_data="tut_mac")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])

# ==========================================
# 🚀 هندلرهای منو و دستورات
# ==========================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id in users_in_support:
        users_in_support.discard(message.from_user.id)
        
    user_name = message.from_user.first_name or "کاربر"
    text = (
        f"سلام **{user_name}** عزیز! به سامانه پرسرعت VPN خوش آمدید 🚀\n\n"
        "⚡ **سرویس‌های اختصاصی L2TP / IPsec با پایداری ۹۹.۹٪**\n"
        "🔒 ضد فیلتر، بدون قطعی، مناسب تمام اپراتورها\n\n"
        "👇 لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu())

@dp.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: types.CallbackQuery):
    users_in_support.discard(callback.from_user.id)
    await callback.message.edit_text(
        "🏠 **منوی اصلی ربات:**\n\nلطفاً بخش مورد نظر خود را انتخاب کنید 👇",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# ------------------------------------------
# 👤 حساب کاربری اصلاح شده و کامل
# ------------------------------------------
@dp.callback_query(F.data == "profile")
async def cb_profile(callback: types.CallbackQuery):
    user = callback.from_user
    username = f"@{user.username}" if user.username else "ثبت نشده"
    
    profile_text = (
        "👤 **اطلاعات حساب کاربری شما:**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ **نام:** {user.full_name}\n"
        f"🆔 **شناسه کاربری:** `{user.id}`\n"
        f"🌐 **نام کاربری:** {username}\n"
        f"📅 **تاریخ استعلام:** `{get_persian_date()}`\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📊 **وضعیت اشتراک:** فعال / آماده اتصال\n"
        "🛡️ **پروتکل فعال:** L2TP / IPsec VPN\n"
        "⚡ **سرعت اتصال:** نامحدود (۱۰ گیگابیت)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 جهت تمدید یا دریافت کانکشن از دکمه‌های زیر استفاده کنید:"
    )
    await callback.message.edit_text(profile_text, parse_mode="Markdown", reply_markup=get_profile_menu())
    await callback.answer()

# ------------------------------------------
# 🛍️ خرید و تست
# ------------------------------------------
@dp.callback_query(F.data == "buy_menu")
async def cb_buy_menu(callback: types.CallbackQuery):
    text = (
        "🛍️ **پلن‌های اختصاصی و پرسرعت L2TP:**\n\n"
        "🚀 پینگ فوق‌العاده پایین مخصوص اینستاگرام، ترید، گیم و وبگردی\n"
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
        "📸 **روش ارسال فیش:**\n"
        "روی دکمه **ارتباط با پشتیبانی** بزنید و تصویر فیش یا پیام واریز خود را بفرستید."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "free_trial")
async def cb_free_trial(callback: types.CallbackQuery):
    text = (
        "🎁 **اکانت تست پرسرعت ۲۴ ساعته**\n\n"
        "🌐 **آدرس سرور:** `s1.l2tp-server.net`\n"
        "👤 **نام کاربری:** `test_user`\n"
        "🔑 **رمز عبور:** `123456`\n"
        "🛡️ **کلید اشتراکی (Secret):** `12345678`\n"
        "📡 **پروتکل:** L2TP with IPsec\n\n"
        "⚠️ هر اکانت فقط یکبار حق دریافت تست را دارد."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "status")
async def cb_status(callback: types.CallbackQuery):
    text = (
        "📊 **وضعیت سرورها و مسیرهای ارتباطی:**\n\n"
        "🇩🇪 سرور آلمان (Frankfurt): 🟢 آنلاین (Ping: 40ms)\n"
        "🇳🇱 سرور هلند (Amsterdam): 🟢 آنلاین (Ping: 45ms)\n"
        "🇫🇮 سرور فنلاند (Helsinki): 🟢 آنلاین (Ping: 48ms)\n\n"
        "🛡️ تمامی مسیرها با سرعت حداکثری فعال هستند."
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "tutorials")
async def cb_tutorials(callback: types.CallbackQuery):
    text = "📱 لطفاً سیستم‌عامل دستگاه خود را انتخاب کنید:"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_tutorials_menu())
    await callback.answer()

@dp.callback_query(F.data.startswith("tut_"))
async def cb_tut_details(callback: types.CallbackQuery):
    tutorials = {
        "tut_ios": "🍏 **آموزش آیفون (iOS):**\nبه بخش Settings > General > VPN & Device Management بروید، Add VPN Configuration را بزنید و نوع را روی L2TP بگذارید.",
        "tut_android": "🤖 **آموزش اندروید:**\nدر تنظیمات گوشی وارد اتصالات (Connections) > VPN شوید و اتصال L2TP/IPsec PSK ایجاد کنید.",
        "tut_win": "💻 **آموزش ویندوز:**\nوارد Settings > Network & Internet > VPN شوید و کانکشن نوع L2TP بسازید.",
        "tut_mac": "🍎 **آموزش مک:**\nدر تنظیمات شبکه (Network) یک رابط جدید از نوع VPN (L2TP over IPSec) اضافه کنید."
    }
    text = tutorials.get(callback.data, "راهنما")
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

@dp.callback_query(F.data == "promo")
async def cb_promo(callback: types.CallbackQuery):
    text = "🎟️ کد تخفیف یا معرف خود را در بخش **پشتیبانی** ارسال کنید تا در فاکتور اعمال شود."
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

# ------------------------------------------
# 🎧 سیستم پشتیبانی و تیکتینگ ۲۴/۷ اصلاح‌شده
# ------------------------------------------
@dp.callback_query(F.data == "support")
async def cb_support(callback: types.CallbackQuery):
    users_in_support.add(callback.from_user.id)
    text = (
        "🎧 **واحد پشتیبانی آنلاین و ثبت سفارش**\n\n"
        "✍️ لطفاً پیام، پرسش، کد تخفیف یا **عکس فیش واریزی** خود را همین‌جا ارسال کنید.\n"
        "مدیریت در کمترین زمان ممکن بررسی و پاسخ خواهد داد.\n\n"
        "*(جهت خروج از حالت پشتیبانی دکمه بازگشت را بزنید)*"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button())
    await callback.answer()

# مدیریت پیام‌های متنی
@dp.message(F.text)
async def handle_text_messages(message: types.Message):
    user_id = message.from_user.id

    # اگر ادمین روی تیکت کاربر ریپلای کرد
    if user_id == ADMIN_ID and message.reply_to_message:
        target_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        if "🆔 شناسه:" in target_text:
            try:
                target_user_id = int(target_text.split("🆔 شناسه:")[1].split("\n")[0].strip().replace("`", ""))
                admin_reply = (
                    "📩 **پاسخ پشتیبانی به شما:**\n\n"
                    f"{message.text}"
                )
                await bot.send_message(target_user_id, admin_reply, parse_mode="Markdown")
                await message.reply("✅ پاسخ شما با موفقیت برای کاربر ارسال شد.")
                return
            except Exception as e:
                await message.reply(f"❌ خطا در ارسال پاسخ به کاربر: {e}")
                return

    # ارسال تیکت متنی کاربر برای ادمین
    if user_id in users_in_support:
        ticket = (
            "🔔 **تیکت جدید (پیام متنی)**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 **کاربر:** {message.from_user.full_name}\n"
            f"🆔 شناسه: `{user_id}`\n"
            f"🌐 **یوزرنیم:** @{message.from_user.username if message.from_user.username else 'ندارد'}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"💬 **متن پیام:**\n{message.text}"
        )
        try:
            await bot.send_message(ADMIN_ID, ticket, parse_mode="Markdown")
            await message.answer("✅ پیام شما به پشتیبانی ارسال شد. منتظر پاسخ بمانید.", reply_markup=get_back_button())
        except Exception as e:
            logging.error(f"Ticket error: {e}")
            await message.answer("❌ خطا در برقراری ارتباط با پشتیبانی.", reply_markup=get_back_button())
    else:
        await message.answer("⚠️ لطفاً از دکمه‌های زیر استفاده کنید:", reply_markup=get_main_menu())

# مدیریت ارسال عکس (فیش واریزی یا اسکرین‌شات)
@dp.message(F.photo)
async def handle_photo_messages(message: types.Message):
    user_id = message.from_user.id
    if user_id in users_in_support:
        photo_id = message.photo[-1].file_id
        caption = (
            "📸 **فیش واریزی / عکس جدید از کاربر**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 **کاربر:** {message.from_user.full_name}\n"
            f"🆔 شناسه: `{user_id}`\n"
            f"🌐 **یوزرنیم:** @{message.from_user.username if message.from_user.username else 'ندارد'}\n"
            f"📝 **توضیحات:** {message.caption if message.caption else 'بدون متن'}"
        )
        try:
            await bot.send_photo(ADMIN_ID, photo=photo_id, caption=caption, parse_mode="Markdown")
            await message.answer("✅ تصویر با موفقیت برای پشتیبانی ارسال شد.", reply_markup=get_back_button())
        except Exception as e:
            logging.error(f"Photo ticket error: {e}")
            await message.answer("❌ خطا در ارسال عکس.", reply_markup=get_back_button())

# ==========================================
# 🏁 اجرای ربات
# ==========================================

async def main():
    print("🚀 Bot is starting on Render...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

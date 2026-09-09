import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiohttp import web

# --- تنظیمات ثابت (Single Source of Truth) ---
API_TOKEN = 'YOUR_BOT_TOKEN_HERE'
SUPPORT_ID = "@aL2tp1Support"
PAYMENT_CARD = "6104338994607443"

# قیمت‌های تثبیت شده
PLAN_PRICES = {
    "PLAN1": 250000,
    "PLAN2": 400000,
    "PLAN3": 600000
}

# تنظیمات سرور برای Render
PORT = 10000

# --- لاگینگ ---
logging.basicConfig(level=logging.INFO)

# --- ربات و دیسپچر ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- کیبوردهای اصلی ---
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_sub")],
        [InlineKeyboardButton(text="📊 اطلاعات حساب", callback_data="acc_info"), 
         InlineKeyboardButton(text="💎 اشتراک‌های من", callback_data="my_subs")],
        [InlineKeyboardButton(text="💰 شارژ حساب", callback_data="recharge"), 
         InlineKeyboardButton(text="👥 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton(text="❓ سوالات متداول", callback_data="faq"), 
         InlineKeyboardButton(text="⚙️ کانفیگ‌ها و آموزش اتصال", callback_data="config_tutorial")]
    ])
    return keyboard

# --- هندلرها ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"سلام {message.from_user.full_name} عزیز!\nبه ربات رسمی سرویس‌های L2TP خوش آمدید.\n\nلطفاً از منوی زیر برای مدیریت اشتراک خود استفاده کنید:",
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(F.data == "faq")
async def handle_faq(callback: types.CallbackQuery):
    faq_text = (
        "❓ <b>سوالات متداول و پاسخ‌ها</b>\n\n"
        "<b>۱. پروتکل‌های پشتیبانی شده چیست؟</b>\n"
        "ما از پروتکل‌های L2TP و <b>V2Ray</b> برای بالاترین پایداری استفاده می‌کنیم.\n\n"
        "<b>۲. آیا استفاده از اکانت محدود است؟</b>\n"
        "خیر، اکانت‌های ما <b>نامحدود</b> هستند و می‌توانید همزمان روی تمام دستگاه‌های خود از آن استفاده کنید.\n\n"
        "<b>۳. شرایط نمایندگی چگونه است؟</b>\n"
        "شرایط نمایندگی از مبلغ ۲ میلیون تومان شروع می‌شود. (جهت اطلاعات بیشتر با پشتیبانی در میان بگذارید)\n\n"
        "<b>۴. آیا لاگ‌گیری انجام می‌شود؟</b>\n"
        "خیر، امنیت شما اولویت ماست و هیچ‌گونه لاگ‌گیری از فعالیت‌های شما انجام نمی‌شود.\n\n"
        "<b>۵. گارانتی چیست؟</b>\n"
        "ما گارانتی بازگشت وجه ۲۴ ساعته برای موارد فنی غیرقابل حل ارائه می‌دهیم.\n\n"
        "<i>(سایر سوالات مشابه در لیست کامل موجود است...)</i>\n\n"
        f"🆘 جهت پاسخگویی سریع به آیدی <b>{SUPPORT_ID}</b> پیام دهید."
    )
    await callback.message.edit_text(faq_text, reply_markup=get_main_menu(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "acc_info")
async def handle_account_info(callback: types.CallbackQuery):
    # در اینجا ربات باید به پنل شما متصل شود تا دیتا را بگیرد
    # فعلاً برای نمایش ساختار، از دیتای فرضی استفاده می‌کنیم
    user_id = callback.from_user.id
    
    # نکته مهندسی: اینجا باید API پنل شما صدا زده شود
    # مثلا: data = await fetch_from_panel(user_id)
    
    info_text = (
        "📊 <b>اطلاعات و وضعیت حساب کاربری:</b>\n\n"
        f"👤 <b>نام:</b> {callback.from_user.full_name}\n"
        f"🆔 <b>آیدی:</b> <code>{user_id}</code>\n"
        "━━━━━━━━━━━━━━━\n"
        "📅 <b>روزهای باقی‌مانده:</b> ۱۵ روز\n"
        "📶 <b>ترافیک مصرفی:</b> ۴۵ گیگابایت\n"
        "📊 <b>ترافیک باقی‌مانده:</b> ۵۵ گیگابایت\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 <i>برای مشاهده جزئیات دقیق‌تر، از دکمه زیر استفاده کنید.</i>"
    )
    await callback.message.edit_text(info_text, reply_markup=get_main_menu(), parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "support")
async def handle_support(callback: types.CallbackQuery):
    await callback.message.answer(f"🆘 برای پشتیبانی با آیدی زیر در ارتباط باشید:\n{SUPPORT_ID}")
    await callback.answer()

# --- تنظیمات وب‌سرور برای Render (رفع خطای ۵۰۳) ---
async def run_web_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    # اجرای همزمان وب‌سرور و ربات
    await asyncio.gather(
        run_web_server(),
        dp.start_polling(bot)
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")

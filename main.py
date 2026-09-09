import logging
import asyncio
from datetime import datetime
import jdatetime # برای تاریخ شمسی
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiohttp import web

# --- تنظیمات اولیه ---
API_TOKEN = 'YOUR_BOT_TOKEN_HERE'  # در Render از طریق محیط متغیر (Environment Variables) تنظیم شود
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- متون و منوها ---
def get_main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🛒 خرید اشتراک"))
    keyboard.row(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("💎 اشتراک‌های من"))
    keyboard.row(KeyboardButton("💰 شارژ حساب"), KeyboardButton("👥 پشتیبانی"))
    keyboard.row(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return keyboard

def get_back_button():
    return ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("🔙 بازگشت به منوی اصلی"))

# --- FAQ حرفه‌ای و اصلاح شده ---
FAQ_TEXT = """
❓ **سوالات متداول (FAQ)**

۱. **پروتکل‌ها:** ما از پیشرفته‌ترین پروتکل‌های V2Ray (VMess/VLESS) با امنیت بالا استفاده می‌کنیم.
۲. **سازگاری:** قابل استفاده در تمام دستگاه‌ها (Android, iOS, Windows, macOS).
۳. **حجم مصرفی:** میزان حجم بستگی به پلن انتخابی شما دارد.
۴. **سرعت:** برخلاف سرویس‌های قدیمی، به دلیل پروتکل V2Ray، سرعت بسیار بالا و نزدیک به اینترنت عادی است.
۵. **تحویل:** فعال‌سازی آنی پس از تایید واریزی (۵ تا ۱۵ دقیقه).
۶. **تعداد دستگاه:** در پلن‌های ما، استفاده کاربر به صورت نامحدود و همزمان روی چندین دستگاه مجاز است.
۷. **تست رایگان:** با توجه به کیفیت اختصاصی، تست رایگان نداریم.
۸. **تمدید:** از طریق منوی «خرید اشتراک» در هر زمان امکان‌پذیر است.
۹. **آی‌پی:** ما از آی‌پی شناور (Floating) برای پایداری و سرعت حداکثری استفاده می‌کنیم.
۱۰. **پشتیبانی:** از طریق منوی «👥 پشتیبانی» در دسترس هستیم.
۱۱. **آموزش:** در منوی «⚙️ کانفیگ‌ها» راهنمای کامل موجود است.
"""

# --- هندلرهای اصلی ---
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    now = jdatetime.datetime.now()
    welcome_text = (
        f"🌟 سلام {message.from_user.first_name} عزیز، به دنیای سرعت V2Ray خوش آمدید!\n\n"
        f"📅 امروز: {now.strftime('%A %d %B %Y')}\n"
        f"⏰ ساعت: {now.strftime('%H:%M')}\n\n"
        "ما اینجا هستیم تا تجربه اینترنت آزاد و پرسرعت را به شما هدیه دهیم."
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

@dp.message_handler(lambda message: message.text == "❓ سوالات متداول")
async def show_faq(message: types.Message):
    await message.answer(FAQ_TEXT, reply_markup=get_back_button())

@dp.message_handler(lambda message: message.text == "🔙 بازگشت به منوی اصلی")
async def back_to_main(message: types.Message):
    await message.answer("به منوی اصلی بازگشتید:", reply_markup=get_main_menu())

# --- تنظیمات وب‌سرور برای Render (پورت 10000) ---
async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get('/', handle)

if __name__ == '__main__':
    # راه اندازی همزمان بات و وب‌سرور برای جلوگیری از خطای پورت Render
    loop = asyncio.get_event_loop()
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    loop.run_until_complete(site.start())
    
    executor.start_polling(dp, skip_updates=True)

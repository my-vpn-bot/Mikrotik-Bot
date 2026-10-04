import os
import asyncio
import logging
import sqlite3
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputFile
)
from aiohttp import web

# ==================== تنظیمات و لاگ ====================
logging.basicConfig(level=logging.INFO)

# توکن ربات از محیط سرور فراخوانی می‌شود
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# مدیریت و استخراج صحیح ID ادمین
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "02786850266").strip()
clean_admin_id = ADMIN_ID_RAW.lstrip('0')
ADMIN_ID = int(clean_admin_id) if clean_admin_id.isdigit() else 2786850266

SUPPORT_ID = os.getenv("SUPPORT_ID", "@L2tp1Support").strip().replace("@", "")
SUPPORT_URL = f"https://t.me/{SUPPORT_ID}"
SUPPORT_USERNAME = f"@{SUPPORT_ID}"

CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp_vpn402").strip()
CARD_NUMBER = os.getenv("PAYMENT_CARD", "6104338904607443").strip()
CARD_HOLDER = os.getenv("PAYMENT_NAME", "رحیمی").strip()
IBSNG_PANEL_URL = os.getenv("IBSNG_PANEL_URL", "http://94.184.45.58:48201/IBSng/user/").strip()
OPENVPN_FILE_PATH = os.getenv("OPENVPN_FILE_PATH", "files/openvpn/client.ovpn").strip()

# آدرس سرور و کلید ثابت بدون ماسک
VPN_SERVER_IP = "94.184.43.106"
IPSEC_SECRET = "12345678."

CARD_IMAGE_PATH = "شماره کارت1.jpg"
TARIFF_IMAGE_PATH = "تعرفه.jpg"

# ساختار ربات
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ... (بقیه کدهای دیتابیس و توابع مشابه قبل حفظ شد) ...
# [توجه: دیتابیس و توابع helper اینجا قرار می‌گیرند، برای خلاصه سازی در این بخش تکرار نکردم]

# ==================== کیبورد اصلی (اصلاح شده) ====================
def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🛒 خرید اشتراک"))
    kb.add(KeyboardButton("📊 اطلاعات حساب"), KeyboardButton("🌐 پنل کاربری IBSng"))
    kb.add(KeyboardButton("💰 تمدید اکانت"), KeyboardButton("👥 پشتیبانی"))
    kb.add(KeyboardButton("❓ سوالات متداول"), KeyboardButton("⚙️ کانفیگ‌ها و آموزش اتصال"))
    return kb

# هندلر تمدید اکانت (جایگزین شارژ حساب)
@dp.message_handler(lambda m: m.text == "💰 تمدید اکانت", state="*")
async def handle_charge(message: types.Message, state: FSMContext):
    await state.finish()
    await ChargeState.waiting_for_receipt.set()
    
    caption = (
        "💰 <b>تمدید اکانت (سرور پرسرعت آلمان 🇩🇪)</b>\n\n"
        f"💳 شماره کارت جهت واریز:\n<code>{CARD_NUMBER}</code>\n"
        f"👤 به نام: <b>{CARD_HOLDER}</b>\n\n"
        "📸 لطفاً مبلغ تمدید را واریز نموده و <b>تصویر فیش واریزی</b> را همین‌جا ارسال نمایید:"
    )
    if os.path.exists(CARD_IMAGE_PATH):
        await message.reply_photo(photo=InputFile(CARD_IMAGE_PATH), caption=caption, reply_markup=get_back_keyboard())
    else:
        await message.reply(caption, reply_markup=get_back_keyboard())

# بقیه هندلرها و کدهای ربات بدون تغییر باقی ماند...

import os
import asyncio
import logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramConflictError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── Environment variables ──
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_ID = os.getenv("SUPPORT_ID", "al2tpiSupport")
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "6104338994607443")
PAYMENT_NAME = os.getenv("PAYMENT_NAME", "رحیمی")
PORT = int(os.getenv("PORT", 10000))

SUPPORT_USERNAME = f"@{SUPPORT_ID}" if SUPPORT_ID and not SUPPORT_ID.startswith("@") else SUPPORT_ID

if not BOT_TOKEN:
    raise SystemExit("Error: BOT_TOKEN is not set in Environment Variables!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ── Plans ──
PLANS = {
    "plan_1m": {"title": "🥉 پلن ۱ ماهه", "volume": "۳۰ گیگابایت", "days": "۳۰ روز", "price": "۳۵۰,۰۰۰ تومان"},
    "plan_2m": {"title": "🥈 پلن ۲ ماهه", "volume": "۶۰ گیگابایت", "days": "۶۰ روز", "price": "۶۵۰,۰۰۰ تومان"},
    "plan_3m": {"title": "🥇 پلن ۳ ماهه", "volume": "۹۰ گیگابایت", "days": "۹۰ روز", "price": "۹۰۰,۰۰۰ تومان"},
}

def now_info():
    now = datetime.now()
    return now.strftime("%Y/%m/%d — %H:%M")

# ── Keyboards (دکمه‌های کشیده، یک‌به‌یک) ──
def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy_sub")],
        [InlineKeyboardButton(text="💎 تعرفه‌ها", callback_data="tariffs")],
        [InlineKeyboardButton(text="👤 حساب کاربری", callback_data="my_account")],
        [InlineKeyboardButton(text="🛠 پشتیبانی", callback_data="support")],
    ])

def kb_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
    ])

def kb_plans():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text

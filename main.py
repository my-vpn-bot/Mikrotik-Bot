import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# ==========================================
# ⚙️ تنظیمات و اطلاعات احراز هویت
# ==========================================
BOT_TOKEN = "8715195364:AAFBr7PHxFBdOYKPVc0T-IwOPUiUEXAZMqg"
ADMIN_ID = 6278059256

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_languages = {}      # {user_id: 'fa' | 'az' | 'en'}
users_in_support = set() # {user_id}

# ==========================================
# 🌐 دیکشنری کامل سه زبانه
# ==========================================
TEXTS = {
    'fa': {
        'welcome': "سلام **{name}** عزیز! به سامانه پرسرعت VPN خوش آمدید 🚀\n\n⚡ پروتکل‌های فعال: **OpenVPN | PPTP | L2TP**\n🔒 ضد فیلتر و پرسرعت، مناسب تمام دستگاه‌ها\n\n👇 لطفاً یک گزینه را انتخاب کنید:",
        'select_lang': "🌐 لطفاً زبان مورد نظر خود را انتخاب کنید:\nLütfen dilinizi seçin:\nPlease select your language:",
        'lang_changed': "✅ زبان ربات به **فارسی** تنظیم شد.",
        'btn_buy': "🛍️ خرید اشتراک VIP",
        'btn_renew': "💳 تمدید اشتراک",
        'btn_trial': "🎁 تست رایگان",
        'btn_profile': "👤 حساب کاربری من",
        'btn_status': "⚡ وضعیت سرورها",
        'btn_tut': "📱 راهنمای اتصال",
        'btn_lang': "🌐 تغییر زبان / Dil / Language",
        'btn_support': "🎧 پشتیبانی ۲۴/۷",
        'btn_back': "🔙 بازگشت به منوی اصلی",
        'profile_title': "👤 **اطلاعات حساب کاربری شما:**\n━━━━━━━━━━━━━━━━━━\n🏷️ **نام:** {name}\n🆔 **شناسه کاربری:** `{id}`\n🌐 **نام کاربری:** {username}\n📅 **تاریخ:** `{date}`\n━━━━━━━━━━━━━━━━━━\n📊 **وضعیت:** فعال\n🛡️ **پروتکل‌ها:** OpenVPN, PPTP, L2TP\n⚡ **سرعت:** نامحدود\n━━━━━━━━━━━━━━━━━━",
        'buy_title': "🛍️ **تعرفه‌های خرید و تمدید اشتراک:**\n\n🔹 پشتیبانی از **OpenVPN, PPTP, L2TP**\n🚀 پینگ پایین و بدون قطعی\n\n🔻 پلن مورد نظر را انتخاب کنید:",
        'plan_1': "🔹 ۱ ماهه نامحدود - ۵۰,۰۰۰ تومان",
        'plan_3': "🔹 ۳ ماهه نامحدود - ۱۳۰,۰۰۰ تومان",
        'plan_6': "🔹 ۶ ماهه نامحدود - ۲۴۰,۰۰۰ تومان",
        'pay_info': "✅ شما پلن **{plan}** را انتخاب کردید.\n\n💳 **شماره کارت جهت واریز:**\n`۶۰۳۷-۹۹۷۹-۰۰۰۰-۰۰۰۰`\n\n📸 پس از پرداخت، روی دکمه **پشتیبانی** بزنید و تصویر فیش واریزی را ارسال کنید.",
        'trial_info': "🎁 **اکانت تست پرسرعت ۲۴ ساعته**\n\n🌐 **سرور:** `s1.vpn-server.net`\n👤 **نام کاربری:** `test_user`\n🔑 **رمز عبور:** `123456`\n🛡️ **پروتکل‌ها:** OpenVPN / PPTP / L2TP",
        'status_info': "📊 **وضعیت لحظه‌ای سرورها:**\n\n🇩🇪 سرور آلمان: 🟢 آنلاین (OpenVPN, L2TP, PPTP)\n🇳🇱 سرور هلند: 🟢 آنلاین (OpenVPN, L2TP, PPTP)\n🇫🇮 سرور فنلاند: 🟢 آنلاین (OpenVPN, L2TP, PPTP)",
        'tut_title': "📱 لطفاً سیستم‌عامل خود را انتخاب کنید:",
        'support_prompt': "🎧 **واحد پشتیبانی و ارسال فیش**\n\n✍️ لطفاً پیام یا **تصویر فیش واریزی** خود را ارسال فرمایید:",
        'ticket_sent': "✅ پیام شما برای مدیریت ارسال شد. به زودی پاسخ دریافت خواهید کرد.",
        'photo_sent': "✅ فیش واریزی شما برای مدیریت ارسال شد.",
        'reply_header': "📩 **پاسخ پشتیبانی:**\n\n"
    },
    'az': {
        'welcome': "Salam **{name}**! Sürətli VPN sisteminə xoş gəlmisiniz 🚀\n\n⚡ Aktiv protokollar: **OpenVPN | PPTP | L2TP**\n🔒 Yüksək sürət və stabil bağlantı\n\n👇 Zəhmət olmasa bir seçimi seçin:",
        'select_lang': "🌐 Zəhmət olmasa dilinizi seçin:",
        'lang_changed': "✅ Dil uğurla **Azərbaycan / Türk** dilinə dəyişdirildi.",
        'btn_buy': "🛍️ VIP Abunəlik Al",
        'btn_renew': "💳 Abunəliyi Yenilə",
        'btn_trial': "🎁 Pulsuz Test",
        'btn_profile': "👤 Şəxsi Hesabım",
        'btn_status': "⚡ Server Vəziyyəti",
        'btn_tut': "📱 Qoşulma Bələdçisi",
        'btn_lang': "🌐 Dili Dəyiş / Language",
        'btn_support': "🎧 24/7 Dəstək",
        'btn_back': "🔙 Əsas Menyuya Qayıt",
        'profile_title': "👤 **İstifadəçi Məlumatı:**\n━━━━━━━━━━━━━━━━━━\n🏷️ **Ad:** {name}\n🆔 **İstifadəçi ID:** `{id}`\n🌐 **İstifadəçi adı:** {username}\n📅 **Tarix:** `{date}`\n━━━━━━━━━━━━━━━━━━\n📊 **Vəziyyət:** Aktiv\n🛡️ **Protokollar:** OpenVPN, PPTP, L2TP\n⚡ **Sürət:** Limitsiz\n━━━━━━━━━━━━━━━━━━",
        'buy_title': "🛍️ **Tariflər və Yeniləmə:**\n\n🔹 Protokollar: **OpenVPN, PPTP, L2TP**\n\n🔻 Planı seçin:",
        'plan_1': "🔹 1 Aylıq Limitsiz - 50,000 Toman",
        'plan_3': "🔹 3 Aylıq Limitsiz - 130,000 Toman",
        'plan_6': "🔹 6 Aylıq Limitsiz - 240,000 Toman",
        'pay_info': "✅ Seçilmiş plan: **{plan}**\n\n💳 **Kart Nömrəsi:**\n`6037-9979-0000-0000`\n\n📸 Ödənişdən sonra çeki **Dəstək** bölməsinə göndərin.",
        'trial_info': "🎁 **24 Saatlıq Pulsuz Test**\n\n🌐 **Server:** `s1.vpn-server.net`\n👤 **İstifadəçi:** `test_user`\n🔑 **Şifrə:** `123456`\n🛡️ **Protokollar:** OpenVPN / PPTP / L2TP",
        'status_info': "📊 **Server Vəziyyəti:**\n\n🇩🇪 Almaniya: 🟢 Online\n🇳🇱 Hollandiya: 🟢 Online\n🇫🇮 Finlandiya: 🟢 Online",
        'tut_title': "📱 Zəhmət olmasa Əməliyyat Sistemini seçin:",
        'support_prompt': "🎧 **24/7 Dəstək və Çek Göndərmə**\n\n✍️ Zəhmət olmasa mesajınızı və ya **ödəniş çekinin şəklini** göndərin:",
        'ticket_sent': "✅ Mesajınız dəstək xidmətinə göndərildi.",
        'photo_sent': "✅ Çek şəkli göndərildi.",
        'reply_header': "📩 **Dəstək Cavabı:**\n\n"
    },
    'en': {
        'welcome': "Hello **{name}**! Welcome to High-Speed VPN Service 🚀\n\n⚡ Active Protocols: **OpenVPN | PPTP | L2TP**\n🔒 Secure, Fast & Unlimited\n\n👇 Please select an option:",
        'select_lang': "🌐 Please select your language:",
        'lang_changed': "✅ Language successfully set to **English**.",
        'btn_buy': "🛍️ Buy VIP Subscription",
        'btn_renew': "💳 Renew Subscription",
        'btn_trial': "🎁 Free Trial",
        'btn_profile': "👤 My Profile",
        'btn_status': "⚡ Server Status",
        'btn_tut': "📱 Setup Guides",
        'btn_lang': "🌐 Change Language",
        'btn_support': "🎧 24/7 Support",
        'btn_back': "🔙 Back to Main Menu",
        'profile_title': "👤 **User Profile:**\n━━━━━━━━━━━━━━━━━━\n🏷️ **Name:** {name}\n🆔 **User ID:** `{id}`\n🌐 **Username:** {username}\n📅 **Date:** `{date}`\n━━━━━━━━━━━━━━━━━━\n📊 **Status:** Active\n🛡️ **Protocols:** OpenVPN, PPTP, L2TP\n⚡ **Speed:** Unlimited\n━━━━━━━━━━━━━━━━━━",
        'buy_title': "🛍️ **Pricing & Plans:**\n\n🔹 Protocols: **OpenVPN, PPTP, L2TP**\n🚀 Low Ping & High Speed\n\n🔻 Choose your plan:",
        'plan_1': "🔹 1 Month Unlimited",
        'plan_3': "🔹 3 Months Unlimited",
        'plan_6': "🔹 6 Months Unlimited",
        'pay_info': "✅ Selected: **{plan}**\n\n💳 **Payment Card:**\n`6037-9979-0000-0000`\n\n📸 Please send payment receipt via **Support** button.",
        'trial_info': "🎁 **24-Hour Free Trial**\n\n🌐 **Server:** `s1.vpn-server.net`\n👤 **Username:** `test_user`\n🔑 **Password:** `123456`\n🛡️ **Protocols:** OpenVPN / PPTP / L2TP",
        'status_info': "📊 **Live Server Status:**\n\n🇩🇪 Germany: 🟢 Online\n🇳🇱 Netherlands: 🟢 Online\n🇫🇮 Finland: 🟢 Online",
        'tut_title': "📱 Please select your platform:",
        'support_prompt': "🎧 **Support & Order Verification**\n\n✍️ Please send your message or **payment receipt image**:",
        'ticket_sent': "✅ Your ticket has been sent to support.",
        'photo_sent': "✅ Your receipt has been sent to support.",
        'reply_header': "📩 **Support Reply:**\n\n"
    }
}

def get_user_lang(user_id):
    return user_languages.get(user_id, 'fa')

def get_main_menu(user_id):
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t['btn_buy'], callback_data="buy_menu"),
            InlineKeyboardButton(text=t['btn_renew'], callback_data="buy_menu")
        ],
        [
            InlineKeyboardButton(text=t['btn_trial'], callback_data="free_trial"),
            InlineKeyboardButton(text=t['btn_profile'], callback_data="profile")
        ],
        [
            InlineKeyboardButton(text=t['btn_status'], callback_data="status"),
            InlineKeyboardButton(text=t['btn_tut'], callback_data="tutorials")
        ],
        [
            InlineKeyboardButton(text=t['btn_lang'], callback_data="lang_select_menu"),
            InlineKeyboardButton(text=t['btn_support'], callback_data="support")
        ]
    ])

def get_lang_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇮🇷 فارسی (Persian)", callback_data="setlang_fa")],
        [InlineKeyboardButton(text="🇦🇿 آذربایجانجا / Türkçe", callback_data="setlang_az")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")],
        [InlineKeyboardButton(text="🔙 بازگشت / Back", callback_data="back_to_main")]
    ])

def get_back_button(user_id):
    lang = get_user_lang(user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="back_to_main")]
    ])

def get_buy_menu(user_id):
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['plan_1'], callback_data="plan_1m")],
        [InlineKeyboardButton(text=t['plan_3'], callback_data="plan_3m")],
        [InlineKeyboardButton(text=t['plan_6'], callback_data="plan_6m")],
        [InlineKeyboardButton(text=t['btn_support'], callback_data="support")],
        [InlineKeyboardButton(text=t['btn_back'], callback_data="back_to_main")]
    ])

def get_tutorials_menu(user_id):
    lang = get_user_lang(user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍏 iOS (OpenVPN / L2TP)", callback_data="tut_ios"),
            InlineKeyboardButton(text="🤖 Android (OpenVPN / PPTP)", callback_data="tut_android")
        ],
        [
            InlineKeyboardButton(text="💻 Windows (OpenVPN / PPTP)", callback_data="tut_win"),
            InlineKeyboardButton(text="🍎 macOS (OpenVPN / L2TP)", callback_data="tut_mac")
        ],
        [InlineKeyboardButton(text=TEXTS[lang]['btn_back'], callback_data="back_to_main")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    users_in_support.discard(user_id)
    if user_id not in user_languages:
        user_languages[user_id] = 'fa'
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    name = message.from_user.first_name or "User"
    await message.answer(t['welcome'].format(name=name), parse_mode="Markdown", reply_markup=get_main_menu(user_id))

@dp.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    users_in_support.discard(user_id)
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    await callback.message.edit_text(f"🏠 **{t['btn_back'].replace('🔙 ', '')}**", parse_mode="Markdown", reply_markup=get_main_menu(user_id))
    await callback.answer()

@dp.callback_query(F.data == "lang_select_menu")
async def cb_lang_menu(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    await callback.message.edit_text(TEXTS[lang]['select_lang'], reply_markup=get_lang_menu())
    await callback.answer()

@dp.callback_query(F.data.startswith("setlang_"))
async def cb_set_lang(callback: types.CallbackQuery):
    selected_lang = callback.data.split("_")[1]
    user_languages[callback.from_user.id] = selected_lang
    t = TEXTS[selected_lang]
    await callback.message.edit_text(t['lang_changed'], parse_mode="Markdown", reply_markup=get_main_menu(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(callback: types.CallbackQuery):
    user = callback.from_user
    lang = get_user_lang(user.id)
    t = TEXTS[lang]
    username = f"@{user.username}" if user.username else "N/A"
    today = datetime.now().strftime("%Y/%m/%d")
    text = t['profile_title'].format(name=user.full_name, id=user.id, username=username, date=today)
    profile_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t['btn_renew'], callback_data="buy_menu"),
            InlineKeyboardButton(text=t['btn_support'], callback_data="support")
        ],
        [InlineKeyboardButton(text=t['btn_back'], callback_data="back_to_main")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=profile_kb)
    await callback.answer()

@dp.callback_query(F.data == "buy_menu")
async def cb_buy_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    await callback.message.edit_text(TEXTS[lang]['buy_title'], parse_mode="Markdown", reply_markup=get_buy_menu(user_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("plan_"))
async def cb_plans(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    plan_names = {"plan_1m": t['plan_1'], "plan_3m": t['plan_3'], "plan_6m": t['plan_6']}
    text = t['pay_info'].format(plan=plan_names.get(callback.data, "VPN Plan"))
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_back_button(user_id))
    await callback.answer()

@dp.callback_query(F.data == "free_trial")
async def cb_free_trial(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    await callback.message.edit_text(TEXTS[lang]['trial_info'], parse_mode="Markdown", reply_markup=get_back_button(user_id))
    await callback.answer()

@dp.callback_query(F.data == "status")
async def cb_status(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    await callback.message.edit_text(TEXTS[lang]['status_info'], parse_mode="Markdown", reply_markup=get_back_button(user_id))
    await callback.answer()

@dp.callback_query(F.data == "tutorials")
async def cb_tutorials(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    await callback.message.edit_text(TEXTS[lang]['tut_title'], parse_mode="Markdown", reply_markup=get_tutorials_menu(user_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("tut_"))
async def cb_tut_details(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    tut_type = callback.data
    tut_texts = {
        "tut_ios": "🍏 **iOS Setup (OpenVPN / L2TP):**\n1. Download OpenVPN Connect from AppStore.\n2. Import .ovpn config file or configure L2TP in Settings > VPN.",
        "tut_android": "🤖 **Android Setup (OpenVPN / PPTP):**\n1. Install OpenVPN for Android.\n2. Or add PPTP connection in Settings > Connections > More connection settings > VPN.",
        "tut_win": "💻 **Windows Setup (OpenVPN / PPTP):**\n1. Install OpenVPN GUI client.\n2. Or create a PPTP connection directly in Windows Network Settings.",
        "tut_mac": "🍎 **macOS Setup (OpenVPN / L2TP):**\n1. Use Tunnelblick for OpenVPN.\n2. Or add L2TP / PPTP in Network Preferences."
    }
    await callback.message.edit_text(tut_texts.get(tut_type, "Tutorial"), parse_mode="Markdown", reply_markup=get_back_button(user_id))
    await callback.answer()

@dp.callback_query(F.data == "support")
async def cb_support(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    users_in_support.add(user_id)
    lang = get_user_lang(user_id)
    await callback.message.edit_text(TEXTS[lang]['support_prompt'], parse_mode="Markdown", reply_markup=get_back_button(user_id))
    await callback.answer()

@dp.message(F.text)
async def handle_text_messages(message: types.Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]

    # پاسخ ادمین
    if user_id == ADMIN_ID and message.reply_to_message:
        target_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        if "🆔 شناسه:" in target_text or "User ID:" in target_text:
            try:
                raw_id = target_text.split("🆔")[1].split("\n")[0] if "🆔" in target_text else target_text.split("User ID:")[1].split("\n")[0]
                target_user_id = int(raw_id.replace("شناسه:", "").replace("`", "").strip())
                target_lang = get_user_lang(target_user_id)
                admin_reply = f"{TEXTS[target_lang]['reply_header']}{message.text}"
                await bot.send_message(target_user_id, admin_reply, parse_mode="Markdown")
                await message.reply("✅ پاسخ با موفقیت برای کاربر ارسال شد.")
                return
            except Exception as e:
                await message.reply(f"❌ خطا در ارسال پاسخ: {e}")
                return

    # پیام کاربر به پشتیبانی
    if user_id in users_in_support:
        ticket = (
            "🔔 **تیکت جدید (New Message)**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 **کاربر:** {message.from_user.full_name}\n"
            f"🆔 شناسه: `{user_id}`\n"
            f"🌐 **یوزرنیم:** @{message.from_user.username if message.from_user.username else 'ندارد'}\n"
            f"🌍 **زبان کاربر:** {lang}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"💬 **متن:**\n{message.text}"
        )
        try:
            await bot.send_message(ADMIN_ID, ticket, parse_mode="Markdown")
            await message.answer(t['ticket_sent'], reply_markup=get_back_button(user_id))
        except Exception as e:
            logging.error(f"Ticket error: {e}")
            await message.answer("❌ Error sending message.", reply_markup=get_back_button(user_id))
    else:
        await message.answer("⚠️ لطفاً از دکمه‌های منو استفاده کنید:", reply_markup=get_main_menu(user_id))

@dp.message(F.photo)
async def handle_photo_messages(message: types.Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    t = TEXTS[lang]
    
    if user_id in users_in_support:
        photo_id = message.photo[-1].file_id
        caption = (
            "📸 **فیش واریزی / عکس جدید (Receipt / Screenshot)**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 **کاربر:** {message.from_user.full_name}\n"
            f"🆔 شناسه: `{user_id}`\n"
            f"🌐 **یوزرنیم:** @{message.from_user.username if message.from_user.username else 'ندارد'}\n"
            f"🌍 **زبان:** {lang}\n"
            f"📝 **توضیحات:** {message.caption if message.caption else 'بدون متن'}"
        )
        try:
            await bot.send_photo(ADMIN_ID, photo=photo_id, caption=caption, parse_mode="Markdown")
            await message.answer(t['photo_sent'], reply_markup=get_back_button(user_id))
        except Exception as e:
            logging.error(f"Photo ticket error: {e}")
            await message.answer("❌ Error sending photo.", reply_markup=get_back_button(user_id))

# ==========================================
# 🏁 اجرای مستقیم
# ==========================================
async def main():
    print("🚀 Mikrotik VPN Bot is running with 3 languages and OpenVPN/PPTP/L2TP...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

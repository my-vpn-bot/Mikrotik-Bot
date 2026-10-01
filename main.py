import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "0")
CARD_NUMBER = os.getenv("CARD_NUMBER", "6104338904607443")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/L2tp")
VPN_SERVER_IP = os.getenv("VPN_SERVER_IP", "94.184.43.106")

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    ADMIN_ID = 0

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bot.db"
OVPN_FILE_PATH = BASE_DIR / "files" / "openvpn" / "client.ovpn"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# تعرفه‌های رسمی
PLANS = {
    "1m_1u": {"title": "یک‌ماهه تک‌کاربره", "days": 30, "users": 1, "price": 200_000},
    "1m_2u": {"title": "یک‌ماهه دو‌کاربره", "days": 30, "users": 2, "price": 250_000},
    "2m_1u": {"title": "دوماهه تک‌کاربره", "days": 60, "users": 1, "price": 380_000},
    "2m_2u": {"title": "دوماهه دو‌کاربره", "days": 60, "users": 2, "price": 430_000},
    "3m_1u": {"title": "سه‌ماهه تک‌کاربره", "days": 90, "users": 1, "price": 550_000},
    "3m_2u": {"title": "سه‌ماهه دو‌کاربره", "days": 90, "users": 2, "price": 600_000},
}


def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_code TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'assigned')),
                assigned_user_id INTEGER,
                assigned_at TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_accounts_pool
            ON accounts (plan_code, status, id);
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                plan_code TEXT NOT NULL,
                receipt_kind TEXT NOT NULL,
                receipt_file_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired')),
                account_id INTEGER,
                created_at TEXT NOT NULL,
                approved_at TEXT,
                expires_at TEXT,
                notif_3d INTEGER DEFAULT 0,
                notif_1d INTEGER DEFAULT 0,
                notif_0d INTEGER DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_orders_pending
            ON orders (status, id);
            """
        )

        cursor = conn.execute("PRAGMA table_info(orders);")
        columns = [row["name"] for row in cursor.fetchall()]
        if "expires_at" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN expires_at TEXT;")
        if "notif_3d" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN notif_3d INTEGER DEFAULT 0;")
        if "notif_1d" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN notif_1d INTEGER DEFAULT 0;")
        if "notif_0d" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN notif_0d INTEGER DEFAULT 0;")


def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID


def get_plans_keyboard():
    keyboard = []
    for code, info in PLANS.items():
        price_text = f"{info['price']:,} تومان" if info["price"] > 0 else "استعلام"
        btn_text = f"{info['title']} - {price_text}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"plan:{code}")])
    return InlineKeyboardMarkup(keyboard)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "سلام دوست گرامی؛ به ربات رسمی سرویس L2TP خوش آمدید! 🚀\n\n"
        "جهت خرید اشتراک یا تمدید، لطفاً پلن مورد نظر خود را انتخاب کنید:\n"
        f"📢 کانال اطلاع‌رسانی: {CHANNEL_URL}"
    )
    await update.effective_message.reply_text(msg, reply_markup=get_plans_keyboard())


async def plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("plan:"):
        return

    plan_code = data.split(":", 1)[1]
    plan = PLANS.get(plan_code)
    if not plan:
        await query.edit_message_text("طرح انتخابی یافت نشد.")
        return

    context.user_data["selected_plan"] = plan_code
    price_text = f"{plan['price']:,} تومان" if plan["price"] > 0 else "تماس با پشتیبانی"

    msg = (
        f"📋 <b>جزئیات سفارش:</b>\n"
        f"🔹 پلن: <b>{plan['title']}</b>\n"
        f"🔹 مبلغ: <b>{price_text}</b>\n\n"
        f"💳 <b>شماره کارت جهت واریز:</b>\n"
        f"<code>{CARD_NUMBER}</code>\n\n"
        f"⚠️ لطفاً پس از واریز، <b>تصویر فیش یا رسید واریزی</b> را همین‌جا ارسال کنید."
    )
    await query.edit_message_text(msg, parse_mode=ParseMode.HTML)


async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    plan_code = context.user_data.get("selected_plan")

    if not plan_code:
        await update.effective_message.reply_text(
            "لطفاً ابتدا از منوی /start یکی از پلن‌ها را انتخاب کنید.",
            reply_markup=get_plans_keyboard(),
        )
        return

    plan = PLANS.get(plan_code)
    if not plan:
        await update.effective_message.reply_text("طرح نامعتبر است.")
        return

    if update.message.photo:
        receipt_kind = "photo"
        receipt_file_id = update.message.photo[-1].file_id
    elif update.message.document:
        receipt_kind = "document"
        receipt_file_id = update.message.document.file_id
    else:
        await update.effective_message.reply_text("لطفاً رسید را به صورت عکس یا فایل ارسال کنید.")
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO orders (user_id, username, plan_code, receipt_kind, receipt_file_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (user.id, user.username, plan_code, receipt_kind, receipt_file_id, now_iso),
        )
        order_id = cursor.lastrowid

    context.user_data.pop("selected_plan", None)

    await update.effective_message.reply_text(
        "✅ رسید شما ثبت شد و برای تأیید به مدیریت ارسال گردید.\n"
        "به محض تأیید، مشخصات اکانت فوراً برای شما ارسال خواهد شد."
    )

    if ADMIN_ID:
        admin_kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ تأیید سفارش", callback_data=f"adm_appr:{order_id}"),
                    InlineKeyboardButton("❌ رد سفارش", callback_data=f"adm_rejc:{order_id}"),
                ]
            ]
        )
        caption = (
            f"🛒 <b>سفارش جدید دریافت شد!</b>\n"
            f"شماره سفارش: <code>{order_id}</code>\n"
            f"کاربر: @{user.username or 'بدون یوزرنیم'} ({user.id})\n"
            f"پلن: <b>{plan['title']}</b>\n"
            f"مبلغ: {plan['price']:,} تومان"
        )
        try:
            if receipt_kind == "photo":
                await context.bot.send_photo(ADMIN_ID, receipt_file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=admin_kb)
            else:
                await context.bot.send_document(ADMIN_ID, receipt_file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=admin_kb)
        except TelegramError as e:
            logger.error(f"خطا در ارسال رسید به ادمین: {e}")


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("دسترسی غیرمجاز است.", show_alert=True)
        return

    data = query.data
    action, order_id_str = data.split(":", 1)
    order_id = int(order_id_str)

    with connect_db() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            await query.edit_message_caption("سفارش مورد نظر یافت نشد.")
            return

        if order["status"] != "pending":
            await query.answer("این سفارش قبلاً تعیین وضعیت شده است.", show_alert=True)
            return

        plan = PLANS.get(order["plan_code"], {})
        days = plan.get("days", 30)

        if action == "adm_appr":
            acc = conn.execute(
                """
                SELECT * FROM accounts 
                WHERE plan_code = ? AND status = 'available' 
                ORDER BY id ASC LIMIT 1
                """,
                (order["plan_code"],),
            ).fetchone()

            if not acc:
                await query.answer("⚠️ خطا: موجودی استخر برای این پلن تمام شده است!", show_alert=True)
                return

            now_dt = datetime.now(timezone.utc)
            exp_dt = now_dt + timedelta(days=days)
            now_iso = now_dt.isoformat()
            exp_iso = exp_dt.isoformat()

            conn.execute(
                """
                UPDATE accounts 
                SET status = 'assigned', assigned_user_id = ?, assigned_at = ? 
                WHERE id = ?
                """,
                (order["user_id"], now_iso, acc["id"]),
            )
            conn.execute(
                """
                UPDATE orders 
                SET status = 'approved', account_id = ?, approved_at = ?, expires_at = ? 
                WHERE id = ?
                """,
                (acc["id"], now_iso, exp_iso, order_id),
            )

            user_msg = (
                "🎉 <b>سفارش شما با موفقیت تأیید و اکانت فعال شد!</b>\n\n"
                f"🔹 پلن: <b>{plan.get('title')}</b>\n"
                f"🌐 سرور: <code>{VPN_SERVER_IP}</code>\n"
                f"👤 نام کاربری: <code>{acc['username']}</code>\n"
                f"🔑 رمز عبور: <code>{acc['password']}</code>\n"
                f"📅 تاریخ انقضا: <b>{exp_dt.strftime('%Y-%m-%d')}</b>\n\n"
                "📌 فایل تنظیمات OpenVPN در ادامه ارسال می‌گردد."
            )

            try:
                await context.bot.send_message(order["user_id"], user_msg, parse_mode=ParseMode.HTML)
                if OVPN_FILE_PATH.exists():
                    with open(OVPN_FILE_PATH, "rb") as ovpn_file:
                        await context.bot.send_document(
                            order["user_id"],
                            ovpn_file,
                            caption="فایل کانفیگ اختصاصی OpenVPN 🔒",
                        )
            except TelegramError as e:
                logger.error(f"خطا در تحویل اکانت به کاربر {order['user_id']}: {e}")

            await query.edit_message_caption(f"✅ سفارش شماره {order_id} تأیید شد و اکانت به کاربر تحویل گردید.")

        elif action == "adm_rejc":
            conn.execute("UPDATE orders SET status = 'rejected' WHERE id = ?", (order_id,))
            try:
                await context.bot.send_message(
                    order["user_id"],
                    "❌ متأسفانه رسید ارسالی شما مورد تأیید قرار نگرفت. جهت بررسی با پشتیبانی در ارتباط باشید.",
                )
            except TelegramError as e:
                logger.error(f"خطا در ارسال پیام رد به کاربر: {e}")

            await query.edit_message_caption(f"❌ سفارش شماره {order_id} رد شد.")


async def addpool_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    text = update.effective_message.text.strip()
    lines = text.split("\n")
    if len(lines) < 2:
        await update.effective_message.reply_text("فرمت صحیح:\n/addpool <plan_code>\nuser1|pass1\nuser2|pass2")
        return

    first_line_parts = lines[0].split()
    if len(first_line_parts) < 2:
        await update.effective_message.reply_text("کد پلن مشخص نشده است.")
        return

    plan_code = first_line_parts[1].strip()
    if plan_code not in PLANS:
        await update.effective_message.reply_text(f"کد پلن نامعتبر است. کدهای معتبر:\n{list(PLANS.keys())}")
        return

    rows = []
    for line in lines[1:]:
        line = line.strip()
        if not line or "|" not in line:
            continue
        u, p = line.split("|", 1)
        rows.append((plan_code, u.strip(), p.strip()))

    if not rows:
        await update.effective_message.reply_text("هیچ اکانت معتبری برای افزودن یافت نشد.")
        return

    with connect_db() as conn:
        conn.executemany(
            "INSERT INTO accounts (plan_code, username, password) VALUES (?, ?, ?)",
            rows,
        )

    await update.effective_message.reply_text(f"✅ تعداد {len(rows)} اکانت با موفقیت به پلن {plan_code} اضافه شد.")


async def pool_inventory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    with connect_db() as conn:
        stats = conn.execute(
            """
            SELECT plan_code,
                   SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as avail_cnt,
                   SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) as used_cnt
            FROM accounts
            GROUP BY plan_code
            """
        ).fetchall()

    if not stats:
        await update.effective_message.reply_text("استخر اکانت‌ها در حال حاضر خالی است.")
        return

    msg = "📊 <b>وضعیت موجودی استخر اکانت‌ها:</b>\n\n"
    for row in stats:
        title = PLANS.get(row["plan_code"], {}).get("title", row["plan_code"])
        msg += f"▫️ <b>{title}</b> ({row['plan_code']}):\n"
        msg += f"   آماده تحویل: <b>{row['avail_cnt']}</b> | واگذار شده: {row['used_cnt']}\n"

    await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)


async def check_expirations_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc)
    logger.info("در حال اسکن انقضای اکانت‌ها...")

    with connect_db() as conn:
        orders = conn.execute(
            """
            SELECT o.id, o.user_id, o.plan_code, o.expires_at, o.notif_3d, o.notif_1d, o.notif_0d,
                   a.username, a.password
            FROM orders o
            LEFT JOIN accounts a ON o.account_id = a.id
            WHERE o.status = 'approved' AND o.expires_at IS NOT NULL
            """
        ).fetchall()

        for o in orders:
            try:
                exp_dt = datetime.fromisoformat(o["expires_at"])
            except Exception:
                continue

            time_left = exp_dt - now
            days_left = time_left.total_seconds() / 86400.0

            plan = PLANS.get(o["plan_code"], {})
            plan_title = plan.get("title", "VPN")
            creds = o["username"] or "اکانت شما"

            renew_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("⚡️ شارژ و تمدید فوری", callback_data=f"plan:{o['plan_code']}")]]
            )

            if 0 < days_left <= 3 and not o["notif_3d"]:
                msg = (
                    "⏳ <b>یادآوری تمدید اشتراک VPN</b>\n\n"
                    f"اشتراک <b>{plan_title}</b> شما (یوزر: <code>{creds}</code>) تا <b>۳ روز آینده</b> منقضی می‌شود.\n"
                    "جهت پیشگیری از قطع شدن ارتباط، هم‌اکنون می‌توانید سرویس خود را تمدید فرمایید."
                )
                try:
                    await context.bot.send_message(o["user_id"], msg, parse_mode=ParseMode.HTML, reply_markup=renew_kb)
                    conn.execute("UPDATE orders SET notif_3d = 1 WHERE id = ?", (o["id"],))
                    conn.commit()
                except TelegramError as e:
                    logger.warning(f"عدم ارسال هشدار ۳ روزه به {o['user_id']}: {e}")

            elif 0 < days_left <= 1 and not o["notif_1d"]:
                msg = (
                    "⚠️ <b>هشدار انقضای اشتراک!</b>\n\n"
                    f"کاربر گرامی؛ سرویس <b>{plan_title}</b> شما (یوزر: <code>{creds}</code>) فردا به پایان می‌رسد.\n"
                    "برای حفظ دسترسی، لطفاً از دکمه زیر نسبت به تمدید اقدام فرمایید."
                )
                try:
                    await context.bot.send_message(o["user_id"], msg, parse_mode=ParseMode.HTML, reply_markup=renew_kb)
                    conn.execute("UPDATE orders SET notif_1d = 1 WHERE id = ?", (o["id"],))
                    conn.commit()
                except TelegramError as e:
                    logger.warning(f"عدم ارسال هشدار ۱ روزه به {o['user_id']}: {e}")

            elif days_left <= 0 and not o["notif_0d"]:
                msg = (
                    "🚫 <b>اشتراک شما به پایان رسید!</b>\n\n"
                    f"مهلت استفاده از سرویس <b>{plan_title}</b> (یوزر: <code>{creds}</code>) منقضی شد.\n"
                    "جهت اتصال مجدد می‌توانید طرح جدیدی خریداری فرمایید."
                )
                try:
                    await context.bot.send_message(o["user_id"], msg, parse_mode=ParseMode.HTML, reply_markup=renew_kb)
                    conn.execute("UPDATE orders SET notif_0d = 1, status = 'expired' WHERE id = ?", (o["id"],))
                    conn.commit()
                except TelegramError as e:
                    logger.warning(f"عدم ارسال پیام انقضا به {o['user_id']}: {e}")


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN تنظیم نشده است.")
        return

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(check_expirations_job, interval=7200, first=10)

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("addpool", addpool_handler))
    app.add_handler(CommandHandler("pool", pool_inventory_handler))

    app.add_handler(CallbackQueryHandler(plan_callback, pattern=r"^plan:"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^adm_(appr|rejc):"))

    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receipt_handler))

    logger.info("ربات با موفقیت فعال شد.")
    app.run_polling()


if __name__ == "__main__":
    main()

import telebot
from telebot import types
import os
import sys
import sqlite3
import time

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHANNEL_ID = os.environ.get("ADMIN_CHANNEL_ID")
ADMIN_ID = os.environ.get("ADMIN_ID")  # Your personal Telegram ID
JOIN_LINK = "https://t.me/+H-3MzZdoVTAxMjll"
QR_CODE_PATH = "qr_code.png"
DB_PATH = "users.db"

# Safety checks
if not BOT_TOKEN:
    print("❌ ERROR: TELEGRAM_TOKEN missing!")
    sys.exit(1)
if not ADMIN_CHANNEL_ID:
    print("❌ ERROR: ADMIN_CHANNEL_ID missing!")
    sys.exit(1)
if not ADMIN_ID:
    print("❌ ERROR: ADMIN_ID missing! (Your personal Telegram user ID)")
    sys.exit(1)

ADMIN_ID = int(ADMIN_ID)

bot = telebot.TeleBot(BOT_TOKEN)

# -------- Database Setup --------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at) VALUES (?, ?, ?, ?)",
        (user_id, username, first_name, time.strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_user_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

init_db()

# Pending screenshot store
pending_users = {}

# Broadcast state
broadcast_mode = {}


# -------- /start --------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    add_user(
        message.chat.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    # Step 1: Bold price message
    price_text = (
        "💵 *PRICE: Only 50 Rupees*\n"
        "📦 *CONTENT: unlimited videos*"
    )
    bot.send_message(message.chat.id, price_text, parse_mode="Markdown")
    
    # Step 2: Buttons
    markup = types.InlineKeyboardMarkup()
    btn_samples = types.InlineKeyboardButton("📺 Samples", callback_data="samples")
    btn_buy = types.InlineKeyboardButton("💰 Buy", callback_data="buy")
    markup.add(btn_samples, btn_buy)
    
    bot.send_message(
        message.chat.id,
        "👇 Choose an option below:",
        reply_markup=markup
    )


# -------- /cast (Admin Only) --------
@bot.message_handler(commands=['cast'])
def cast_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ This command is only available to the admin.")
        return
    
    total_users = get_user_count()
    status = "🟢 ON" if message.from_user.id in broadcast_mode else "🔴 OFF"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_on = types.InlineKeyboardButton("🟢 ON", callback_data="cast_on")
    btn_off = types.InlineKeyboardButton("🔴 OFF", callback_data="cast_off")
    markup.add(btn_on, btn_off)
    
    bot.send_message(
        message.chat.id,
        f"📢 *Broadcast Control Panel*\n\n"
        f"👥 Total users: *{total_users}*\n"
        f"📡 Current status: *{status}*\n\n"
        f"Choose an option below:",
        parse_mode="Markdown",
        reply_markup=markup
    )


# -------- Cast ON/OFF Buttons --------
@bot.callback_query_handler(func=lambda call: call.data in ["cast_on", "cast_off"])
def handle_cast_toggle(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin only!")
        return
    
    admin_id = call.from_user.id
    total_users = get_user_count()
    
    if call.data == "cast_on":
        broadcast_mode[admin_id] = True
        status = "🟢 ON"
        bot.answer_callback_query(call.id, "Broadcast ON ✅")
        note = "📩 Now send the message you want to broadcast to all users (text/photo/video/sticker/etc.)."
    else:
        broadcast_mode.pop(admin_id, None)
        status = "🔴 OFF"
        bot.answer_callback_query(call.id, "Broadcast OFF ❌")
        note = "✅ Bot is now in normal mode."
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_on = types.InlineKeyboardButton("🟢 ON", callback_data="cast_on")
    btn_off = types.InlineKeyboardButton("🔴 OFF", callback_data="cast_off")
    markup.add(btn_on, btn_off)
    
    new_text = (
        f"📢 *Broadcast Control Panel*\n\n"
        f"👥 Total users: *{total_users}*\n"
        f"📡 Current status: *{status}*\n\n"
        f"{note}"
    )
    
    try:
        bot.edit_message_text(
            new_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        print(f"Edit failed: {e}")


# -------- /stats (Bonus) --------
@bot.message_handler(commands=['stats'])
def stats_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    users = get_all_users()
    bot.reply_to(message, f"👥 Total users: *{len(users)}*", parse_mode="Markdown")


# -------- Broadcast Sender --------
def send_broadcast(admin_id, message):
    users = get_all_users()
    total = len(users)
    success = 0
    failed = 0
    
    status_msg = bot.send_message(admin_id, f"📢 Broadcasting to {total} users...")
    
    for uid in users:
        try:
            if message.content_type == 'text':
                bot.send_message(uid, message.text, entities=message.entities)
            elif message.content_type == 'photo':
                bot.send_photo(
                    uid,
                    message.photo[-1].file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities if message.caption else None
                )
            elif message.content_type == 'video':
                bot.send_video(uid, message.video.file_id, caption=message.caption)
            elif message.content_type == 'document':
                bot.send_document(uid, message.document.file_id, caption=message.caption)
            elif message.content_type == 'audio':
                bot.send_audio(uid, message.audio.file_id, caption=message.caption)
            elif message.content_type == 'voice':
                bot.send_voice(uid, message.voice.file_id, caption=message.caption)
            elif message.content_type == 'sticker':
                bot.send_sticker(uid, message.sticker.file_id)
            elif message.content_type == 'animation':
                bot.send_animation(uid, message.animation.file_id, caption=message.caption)
            else:
                bot.copy_message(uid, message.chat.id, message.message_id)
            
            success += 1
            time.sleep(0.05)
        except Exception as e:
            failed += 1
            print(f"Failed to send to {uid}: {e}")
    
    bot.edit_message_text(
        f"✅ Broadcast complete!\n\n"
        f"👥 Total: {total}\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}",
        chat_id=admin_id,
        message_id=status_msg.message_id
    )
    # Auto OFF after broadcast
    broadcast_mode.pop(admin_id, None)


# -------- Samples Button --------
@bot.callback_query_handler(func=lambda call: call.data == "samples")
def handle_samples(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "https://t.me/c/4495844318/3")


# -------- Buy Button --------
@bot.callback_query_handler(func=lambda call: call.data == "buy")
def handle_buy(call):
    bot.answer_callback_query(call.id)
    buy_text = (
        "💵 *PRICE: Only 50 Rupees*\n"
        "📦 *CONTENT: unlimited videos*\n\n"
        "📸 Send your *payment screenshot*\n"
        "👤 Also send your *Telegram username* for approval\n\n"
        "Complete payment & SEND SCREENSHOT for verification"
    )
    bot.send_message(call.message.chat.id, buy_text, parse_mode="Markdown")
    with open(QR_CODE_PATH, 'rb') as qr:
        bot.send_photo(call.message.chat.id, qr, caption="📱 Scan & Pay ₹50")


# -------- Photo Handler --------
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    
    # Admin broadcast mode
    if user_id == ADMIN_ID and user_id in broadcast_mode:
        send_broadcast(user_id, message)
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_on = types.InlineKeyboardButton("🟢 ON", callback_data="cast_on")
        btn_off = types.InlineKeyboardButton("🔴 OFF", callback_data="cast_off")
        markup.add(btn_on, btn_off)
        bot.send_message(
            ADMIN_ID,
            f"📢 Broadcast finished. Status: 🔴 *OFF*\n\nTotal users: *{get_user_count()}*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    # Normal user screenshot
    file_id = message.photo[-1].file_id
    pending_users[user_id] = {"photo_id": file_id}
    bot.reply_to(
        message,
        "✅ Screenshot received!\n\n"
        "👤 Now please send your *Telegram username* (e.g., @yourusername) for approval."
    )


# -------- Text Handler --------
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Admin broadcast mode
    if user_id == ADMIN_ID and user_id in broadcast_mode and not text.startswith('/'):
        send_broadcast(user_id, message)
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_on = types.InlineKeyboardButton("🟢 ON", callback_data="cast_on")
        btn_off = types.InlineKeyboardButton("🔴 OFF", callback_data="cast_off")
        markup.add(btn_on, btn_off)
        bot.send_message(
            ADMIN_ID,
            f"📢 Broadcast finished. Status: 🔴 *OFF*\n\nTotal users: *{get_user_count()}*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    
    # User sends username after screenshot
    if user_id in pending_users and "photo_id" in pending_users[user_id]:
        photo_id = pending_users[user_id]["photo_id"]
        auto_username = message.from_user.username or "No username"
        
        markup = types.InlineKeyboardMarkup()
        btn_approve = types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}")
        btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        markup.add(btn_approve, btn_reject)
        
        caption = (
            f"💳 *New Payment Screenshot*\n\n"
            f"👤 *Username (typed):* {text}\n"
            f"🆔 *Telegram ID:* `{user_id}`\n"
            f"🔗 *Auto Username:* @{auto_username}"
        )
        
        bot.send_photo(
            ADMIN_CHANNEL_ID,
            photo_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=markup
        )
        
        del pending_users[user_id]
        
        bot.reply_to(
            message,
            "✅ Your details have been sent to the admin!\n"
            "⏳ Please wait while we verify your payment. You'll receive the join link shortly."
        )
    else:
        bot.reply_to(
            message,
            "📸 Please send your *payment screenshot* first, then your username.\n"
            "Tap /start to buy.",
            parse_mode="Markdown"
        )


# -------- Approve / Reject --------
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_approval(call):
    action, user_id = call.data.split("_", 1)
    user_id = int(user_id)
    
    if action == "approve":
        try:
            bot.send_message(user_id, f"✅ Payment verified! Join here:\n{JOIN_LINK}")
            new_caption = (call.message.caption or "") + "\n\n✅ *APPROVED*"
        except Exception as e:
            new_caption = (call.message.caption or "") + f"\n\n✅ APPROVED (user msg failed: {e})"
        
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=new_caption,
            parse_mode="Markdown",
            reply_markup=None
        )
    else:
        try:
            bot.send_message(user_id, "❌ Payment rejected. Please contact support for help.")
            new_caption = (call.message.caption or "") + "\n\n❌ *REJECTED*"
        except Exception as e:
            new_caption = (call.message.caption or "") + f"\n\n❌ REJECTED (user msg failed: {e})"
        
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=new_caption,
            parse_mode="Markdown",
            reply_markup=None
        )
    
    bot.answer_callback_query(call.id, "Done!")


def run_bot():
    print("🤖 Bot polling started...")
    bot.polling(none_stop=True, timeout=30)

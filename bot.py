import telebot
from telebot import types
import os
import sys
import re

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHANNEL_ID = os.environ.get("ADMIN_CHANNEL_ID")
JOIN_LINK = "https://t.me/+AMrKiPLIi0QzYjU9"
QR_CODE_PATH = "qr_code.png"

# Safety check
if not BOT_TOKEN:
    print("❌ ERROR: TELEGRAM_TOKEN missing!")
    sys.exit(1)
if not ADMIN_CHANNEL_ID:
    print("❌ ERROR: ADMIN_CHANNEL_ID missing!")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Temporary store: {user_id: {"photo_id": ..., "attempts": ...}}
pending_users = {}

# Username validation regex
# 5-32 chars, letter se start, letter/number pe end, beech me letter/number/underscore
USERNAME_REGEX = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{3,30}[a-zA-Z0-9]$')


def is_valid_username(username: str) -> bool:
    return bool(USERNAME_REGEX.match(username))


# /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    btn_samples = types.InlineKeyboardButton("📺 Samples", callback_data="samples")
    btn_buy = types.InlineKeyboardButton("💰 Buy", callback_data="buy")
    markup.add(btn_samples, btn_buy)
    bot.send_message(message.chat.id, "Welcome! Choose an option:", reply_markup=markup)


# Samples button
@bot.callback_query_handler(func=lambda call: call.data == "samples")
def handle_samples(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "https://t.me/samples_fur8ff/5")


# Buy button
@bot.callback_query_handler(func=lambda call: call.data == "buy")
def handle_buy(call):
    bot.answer_callback_query(call.id)
    buy_text = (
        "💵 *PRICE Only 30 Rupees*\n"
        "📦 *CONTENT: 300+ videos*\n\n"
        "📸 Send your *screenshot* after payment\n"
        "👤 Also send your *Telegram username* for approval\n\n"
        "Payment & SEND SCREENSHOT for verify"
    )
    bot.send_message(call.message.chat.id, buy_text, parse_mode="Markdown")
    with open(QR_CODE_PATH, 'rb') as qr:
        bot.send_photo(call.message.chat.id, qr, caption="📱 Scan & Pay ₹30")


# User photo (screenshot) bheje
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    user_id = message.chat.id
    file_id = message.photo[-1].file_id

    # Photo store karo pending me (attempts = 0)
    pending_users[user_id] = {"photo_id": file_id, "attempts": 0}

    bot.reply_to(
        message,
        "✅ Screenshot received!\n\n"
        "👤 Ab apna *Telegram username* bhejo (jaise: @yourusername) for approval."
    )


# User text bheje (username ya kuch aur)
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.chat.id
    text = message.text.strip()

    # Agar user ne pehle screenshot bheja hai
    if user_id in pending_users and "photo_id" in pending_users[user_id]:
        photo_id = pending_users[user_id]["photo_id"]
        attempts = pending_users[user_id].get("attempts", 0)

        # @ hata do agar hai
        clean_username = text.lstrip('@').strip()

        # ❌ Invalid username
        if not is_valid_username(clean_username):
            attempts += 1
            pending_users[user_id]["attempts"] = attempts

            if attempts == 1:
                bot.reply_to(
                    message,
                    "❌ *Invalid username!*\n\n"
                    "Username rules:\n"
                    "• 5-32 characters\n"
                    "• Letters, numbers, underscore (_)\n"
                    "• Letter se start, letter/number pe end\n\n"
                    "👉 Sahi username dobara bhejo (jaise: @yourusername)",
                    parse_mode="Markdown"
                )
            else:
                bot.reply_to(
                    message,
                    "1. MAKE YOUR USERNAME\n"
                    "2. SEND YOUR SCREENSHOT WITH YOUR USERNAME\n\n"
                    "HOW TO MAKE USERNAME: https://t.me/howtousenr/6"
                )
                # Pending clear — user ko dobara screenshot bhejna padega
                del pending_users[user_id]
            return

        # ✅ Valid username — admin ko bhejo
        auto_username = message.from_user.username or "No username"

        markup = types.InlineKeyboardMarkup()
        btn_approve = types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}")
        btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
        markup.add(btn_approve, btn_reject)

        caption = (
            f"💳 *New Payment Screenshot*\n\n"
            f"👤 *Username (typed):* @{clean_username}\n"
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

        # Pending clear karo
        del pending_users[user_id]

        bot.reply_to(
            message,
            "✅ Details admin ko bhej di gayi!\n"
            "⏳ Verify hone ke baad aapko join link milega. Please wait."
        )
    else:
        # Normal text message (agar user ne screenshot nahi bheja)
        bot.reply_to(
            message,
            "📸 Pehle payment ka *screenshot* bhejo, phir apna username.\n"
            "Buy karne ke liye /start dabao."
        )


# Approve / Reject handler
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_approval(call):
    action, user_id = call.data.split("_", 1)
    user_id = int(user_id)

    if action == "approve":
        try:
            bot.send_message(user_id, f"✅ Payment verified! Join here:\n{JOIN_LINK}")
            new_caption = (call.message.caption or "") + "\n\n✅ *APPROVED*"
        except Exception as e:
            new_caption = (call.message.caption or "") + f"\n\n✅ APPROVED (user msg fail: {e})"

        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=new_caption,
            parse_mode="Markdown",
            reply_markup=None
        )
    else:
        try:
            bot.send_message(user_id, "❌ Payment rejected. Please contact support.")
            new_caption = (call.message.caption or "") + "\n\n❌ *REJECTED*"
        except Exception as e:
            new_caption = (call.message.caption or "") + f"\n\n❌ REJECTED (user msg fail: {e})"

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

import telebot
from telebot import types
import os

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHANNEL_ID = os.environ.get("ADMIN_CHANNEL_ID")  # e.g., -1001234567890
JOIN_LINK = "https://t.me/+AMrKiPLIi0QzYjU9"
QR_CODE_PATH = "qr_code.png"  # apna QR code yahan rakho

bot = telebot.TeleBot(BOT_TOKEN)

# /start command - do buttons show karo
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

# Buy button - price + QR code bhejo
@bot.callback_query_handler(func=lambda call: call.data == "buy")
def handle_buy(call):
    bot.answer_callback_query(call.id)
    buy_text = (
        "💵 **PRICE Only 30 Rupees**\n"
        "📦 **CONTENT: 300+ videos**\n\n"
        "Payment & SEND SCREENSHOT for verify"
    )
    bot.send_message(call.message.chat.id, buy_text, parse_mode="Markdown")
    with open(QR_CODE_PATH, 'rb') as qr:
        bot.send_photo(call.message.chat.id, qr, caption="Scan & Pay ₹30")

# Payment screenshot handler
@bot.message_handler(content_types=['photo'])
def handle_screenshot(message):
    # User ka screenshot admin channel ko bhejo
    file_id = message.photo[-1].file_id
    user_id = message.chat.id
    username = message.from_user.username or "No username"
    
    markup = types.InlineKeyboardMarkup()
    btn_approve = types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}")
    btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
    markup.add(btn_approve, btn_reject)
    
    caption = f"Payment screenshot from @{username} (ID: {user_id})"
    bot.send_photo(ADMIN_CHANNEL_ID, file_id, caption=caption, reply_markup=markup)
    bot.reply_to(message, "Screenshot received! Admin verify karega, please wait.")

# Approve/Reject handler
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_approval(call):
    action, user_id = call.data.split("_", 1)
    user_id = int(user_id)
    
    if action == "approve":
        bot.send_message(user_id, f"✅ Payment verified! Join here:\n{JOIN_LINK}")
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n✅ APPROVED",
            reply_markup=None
        )
    else:
        bot.send_message(user_id, "❌ Payment rejected. Please contact support.")
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n❌ REJECTED",
            reply_markup=None
        )
    bot.answer_callback_query(call.id, "Done!")

def run_bot():
    bot.polling(none_stop=True)

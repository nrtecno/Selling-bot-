import os
import threading
from flask import Flask
from bot import run_bot

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

@app.route('/health')
def health():
    return "OK"

if __name__ == "__main__":
    # Bot ko background thread me chalao
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Flask server $PORT par chalao
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

import os
import json
from collections import deque
from datetime import datetime
import telebot


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MESSAGE_THREAD_ID = os.getenv("TELEGRAM_THREAD_ID")

LIMIT = int(os.getenv("TELEGRAM_LIMIT", 20))
FILE_PATH = os.getenv("TELEGRAM_FILE_PATH", "/shared/latest_messages.json")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set")

if not CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID is not set")

if not MESSAGE_THREAD_ID:
    raise ValueError("TELEGRAM_THREAD_ID is not set")

CHAT_ID = int(CHAT_ID)
MESSAGE_THREAD_ID = int(MESSAGE_THREAD_ID)

bot = telebot.TeleBot(TOKEN)
latest_messages = deque(maxlen=LIMIT)

print("Bot process started")

if os.path.exists(FILE_PATH):
    try:
        with open(FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                latest_messages.extend(data)
    except Exception:
        pass


def save_messages():
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(list(latest_messages), f, ensure_ascii=False, indent=2)


@bot.message_handler(func=lambda m:
# True
(
    m.chat.id == CHAT_ID
    and getattr(m, "message_thread_id", None) == MESSAGE_THREAD_ID
)
)
def handle_group_message(message):
    print("=== NEW MESSAGE ===")
    print("chat.id:", message.chat.id)
    print("message_thread_id:", getattr(message, "message_thread_id", None))
    print("message_id:", message.message_id)
    print("text:", message.text or message.caption or "")
    item = {
        "id": str(message.message_id),
        "icon": "📢",
        "text": message.text or message.caption or "",
        "time": datetime.fromtimestamp(message.date).isoformat(),
    }

    latest_messages.appendleft(item)
    save_messages()


if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
import os
import requests
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("ОШИБКА: токен не найден в .env")
    raise SystemExit


BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


print("=" * 70)
print("1. ПРОВЕРЯЕМ БОТА")
print("=" * 70)

response = requests.get(
    f"{BASE_URL}/getMe",
    timeout=20
)

print("HTTP:", response.status_code)

data = response.json()

print("Telegram OK:", data.get("ok"))

if data.get("ok"):
    bot = data["result"]
    print("Имя:", bot.get("first_name"))
    print("Username:", bot.get("username"))
else:
    print("ОШИБКА:", data)
    raise SystemExit


print()
print("=" * 70)
print("2. ИЩЕМ СООБЩЕНИЯ")
print("=" * 70)

response = requests.get(
    f"{BASE_URL}/getUpdates",
    params={
        "timeout": 0,
        "allowed_updates": ["message"]
    },
    timeout=20
)

print("HTTP:", response.status_code)

data = response.json()

print("Telegram OK:", data.get("ok"))

updates = data.get("result", [])

print("Получено updates:", len(updates))


if not updates:
    print()
    print("Telegram не вернул ни одного сообщения.")
    print("Отправь боту обычное сообщение:")
    print("привет")
    print()
    print("После этого снова запусти:")
    print("python telegram_bot.py")

else:

    print()
    print("=" * 70)
    print("НАЙДЕННЫЕ ЧАТЫ")
    print("=" * 70)

    found = False

    for update in updates:

        message = update.get("message")

        if not message:
            continue

        chat = message.get("chat", {})

        chat_id = chat.get("id")

        if not chat_id:
            continue

        found = True

        print()
        print("CHAT_ID:", chat_id)
        print(
            "Имя:",
            chat.get("first_name", "")
        )
        print(
            "Username:",
            chat.get("username", "")
        )
        print(
            "Сообщение:",
            message.get("text", "")
        )

    if not found:
        print(
            "Updates есть, но обычных сообщений "
            "в них не найдено."
        )
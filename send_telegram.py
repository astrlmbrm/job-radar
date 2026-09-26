import json
import os
import requests


INPUT_FILE = "scored_vacancies.json"

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


if not TOKEN:
    raise SystemExit("Не найден TELEGRAM_BOT_TOKEN")

if not CHAT_ID:
    raise SystemExit("Не найден TELEGRAM_CHAT_ID")


def load_vacancies():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def format_salary(vacancy):
    salary = vacancy.get("salary_text")

    if salary:
        return salary

    return "не указана"


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    response.raise_for_status()


def main():
    vacancies = load_vacancies()

    # Пока присылаем только действительно интересные:
    # HOT и GOOD.
    interesting = [
        vacancy
        for vacancy in vacancies
        if vacancy.get("category") in {"HOT", "GOOD"}
    ]

    # Максимум 20 вакансий за один запуск,
    # чтобы Telegram не превращался в свалку.
    interesting = interesting[:20]

    if not interesting:
        send_message(
            "🔎 Job Radar закончил поиск.\n\n"
            "Новых подходящих вакансий не найдено."
        )
        return

    send_message(
        "🎯 JOB RADAR\n\n"
        f"Нашла подходящих вакансий: {len(interesting)}\n"
        "Присылаю лучшие 👇"
    )

    for vacancy in interesting:
        title = vacancy.get("title", "Без названия")
        company = vacancy.get("company") or "Компания не указана"
        location = vacancy.get("location") or "не указана"
        score = vacancy.get("score", 0)
        category = vacancy.get("category", "")
        url = vacancy.get("url", "")
        salary = format_salary(vacancy)

        positive = vacancy.get("positive_reasons", [])

        reasons = "\n".join(
            f"• {reason}"
            for reason in positive[:5]
        )

        text = (
            f"🔥 {category} · {score} баллов\n\n"
            f"{title}\n"
            f"🏢 {company}\n"
            f"💰 {salary}\n"
            f"📍 {location}\n\n"
            f"Почему подходит:\n"
            f"{reasons}\n\n"
            f"🔗 {url}"
        )

        send_message(text)

    print(
        f"Отправлено вакансий в Telegram: "
        f"{len(interesting)}"
    )


if __name__ == "__main__":
    main()
import json
import os
import requests


INPUT_FILE = "scored_vacancies.json"
SENT_FILE = "sent_vacancies.json"

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_VACANCIES_PER_RUN = 20


if not TOKEN:
    raise SystemExit("Не найден TELEGRAM_BOT_TOKEN")

if not CHAT_ID:
    raise SystemExit("Не найден TELEGRAM_CHAT_ID")


def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)


def save_sent_ids(sent_ids):
    with open(SENT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            sorted(sent_ids),
            file,
            ensure_ascii=False,
            indent=2,
        )


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
    vacancies = load_json(INPUT_FILE, [])
    sent_ids = set(load_json(SENT_FILE, []))

    # Берём только HOT и GOOD, которые ещё не отправляли.
    new_vacancies = []

    for vacancy in vacancies:
        vacancy_id = str(vacancy.get("id", ""))

        if not vacancy_id:
            continue

        if vacancy.get("category") not in {"HOT", "GOOD"}:
            continue

        if vacancy_id in sent_ids:
            continue

        new_vacancies.append(vacancy)

    # scoring.py уже сортирует вакансии по убыванию score.
    new_vacancies = new_vacancies[:MAX_VACANCIES_PER_RUN]

    if not new_vacancies:
        send_message(
            "🔎 Job Radar закончил поиск.\n\n"
            "Новых подходящих вакансий сегодня не найдено."
        )

        print("Новых HOT/GOOD вакансий нет.")
        return

    send_message(
        "🎯 JOB RADAR\n\n"
        f"Новых подходящих вакансий: {len(new_vacancies)}\n"
        "Присылаю лучшие 👇"
    )

    successfully_sent = 0

    for vacancy in new_vacancies:
        vacancy_id = str(vacancy["id"])

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
    for reason in positive
)

        if not reasons:
            reasons = "• Подходит по общему скорингу Job Radar"

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

        try:
            send_message(text)

            # Запоминаем вакансию только после успешной отправки.
            sent_ids.add(vacancy_id)
            save_sent_ids(sent_ids)

            successfully_sent += 1

        except requests.RequestException as error:
            print(
                f"Не удалось отправить вакансию "
                f"{vacancy_id}: {error}"
            )

    print(
        f"Успешно отправлено новых вакансий: "
        f"{successfully_sent}"
    )

    print(
        f"Всего вакансий в истории отправки: "
        f"{len(sent_ids)}"
    )


if __name__ == "__main__":
    main()
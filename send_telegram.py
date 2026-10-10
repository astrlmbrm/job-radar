import json
import os
import requests

from vacancy_state import ai_enabled, load_sent_ids, prospective, ranking
from vacancy_state import save_sent_ids as write_sent_ids

INPUT_FILE = "scored_vacancies.json"
AI_INPUT_FILE = "ai_vacancies.json"
SENT_FILE = "sent_vacancies.json"
MAX_VACANCIES_PER_RUN = 20


def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def save_sent_ids(sent_ids):
    write_sent_ids(sent_ids, SENT_FILE)


def format_salary(vacancy):
    return vacancy.get("salary_text") or "не указана"


def send_message(text):
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Не заданы Telegram credentials")
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    response.raise_for_status()
    if response.json().get("ok") is not True:
        raise requests.RequestException("Telegram did not confirm success")


def select_vacancies(vacancies, sent_ids, use_ai):
    candidates = prospective(vacancies, sent_ids)
    if use_ai:
        candidates = [v for v in candidates if not (
            v.get("ai_status") == "success" and v.get("ai_recommendation") == "SKIP"
        )]
        candidates.sort(key=ranking, reverse=True)
    return candidates[:MAX_VACANCIES_PER_RUN]


def concise(value, limit):
    return " ".join(str(value or "").split())[:limit]


def format_message(vacancy, use_ai):
    success = use_ai and vacancy.get("ai_status") == "success"
    if success:
        recommendation = {"APPLY": "откликаться", "CONSIDER": "рассмотреть", "SKIP": "пропустить"}
        assessment = (f"🤖 Соответствие: {vacancy['ai_score']}/100\n"
                      f"Рекомендация: {recommendation[vacancy['ai_recommendation']]}\n"
                      f"Правила: {vacancy.get('category', '')} · {vacancy.get('score', 0)} баллов")
        positive, gaps = vacancy.get("ai_strengths", []), vacancy.get("ai_gaps", [])
    else:
        assessment = f"🎯 {vacancy.get('category', '')} · {vacancy.get('score', 0)} баллов\nAI: оценка недоступна" if use_ai else f"🎯 {vacancy.get('category', '')} · {vacancy.get('score', 0)} баллов"
        positive, gaps = vacancy.get("positive_reasons", []), vacancy.get("negative_reasons", [])
    reasons = "\n".join(f"• {concise(reason, 300)}" for reason in positive[:3])
    if not reasons:
        reasons = "• " + ("Подтверждённых сильных сторон не указано" if success else "Подходит по общему скорингу Job Radar")
    text = (f"{assessment}\n\n{concise(vacancy.get('title') or 'Без названия', 200)}\n"
            f"🏢 {concise(vacancy.get('company') or 'Компания не указана', 150)}\n"
            f"💰 {concise(format_salary(vacancy), 150)}\n"
            f"📍 {concise(vacancy.get('location') or 'не указана', 150)}\n\n"
            f"Почему подходит:\n{reasons}\n")
    if gaps:
        text += "\nПробелы / ограничения:\n" + "\n".join(f"• {concise(gap, 300)}" for gap in gaps[:3]) + "\n"
    if success:
        text += f"\n{concise(vacancy.get('ai_reason'), 600)}\n"
    return text + f"\n🔗 {concise(vacancy.get('url'), 500)}"


def main():
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        raise SystemExit("Не заданы TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
    use_ai = ai_enabled()
    filename = AI_INPUT_FILE if use_ai and os.path.exists(AI_INPUT_FILE) else INPUT_FILE
    vacancies = load_json(filename, [])
    sent_ids = load_sent_ids(SENT_FILE)
    new_vacancies = select_vacancies(vacancies, sent_ids, use_ai)
    if not new_vacancies:
        send_message("🔎 Job Radar закончил поиск.\n\nНовых подходящих вакансий сегодня не найдено.")
        print("Новых подходящих вакансий нет.")
        return
    send_message(f"🎯 JOB RADAR\n\nНовых подходящих вакансий: {len(new_vacancies)}\nПрисылаю лучшие 👇")
    successfully_sent = 0
    for vacancy in new_vacancies:
        vacancy_id = str(vacancy["id"])
        try:
            send_message(format_message(vacancy, use_ai))
        except (requests.RequestException, ValueError):
            # Request errors may include the bot token in a URL. Do not print them.
            print(f"Не удалось отправить вакансию {vacancy_id}")
            continue
        sent_ids.add(vacancy_id)
        save_sent_ids(sent_ids)
        successfully_sent += 1
    print(f"Успешно отправлено новых вакансий: {successfully_sent}")
    print(f"Всего вакансий в истории отправки: {len(sent_ids)}")


if __name__ == "__main__":
    main()

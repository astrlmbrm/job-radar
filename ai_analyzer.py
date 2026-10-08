
import json
import os
from pathlib import Path

from openai import OpenAI


PROFILE_FILE = Path(__file__).with_name("career_profile.json")


def load_career_profile():
    """Загружает карьерный профиль из JSON."""

    with open(PROFILE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def analyze_vacancy(vacancy_text):
    """Анализирует вакансию с помощью OpenAI API."""

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Не найден OPENAI_API_KEY")

    profile = load_career_profile()

    client = OpenAI()

    response = client.responses.create(
        model="gpt-5-nano",
        instructions=(
            "Ты карьерный аналитик. "
            "Оцени вакансию относительно карьерного профиля кандидата. "
            "Опирайся только на предоставленные данные. "
            "Не выдумывай опыт и навыки. "
            "Отделяй обязательные требования от желательных. "
            "Учитывай ограничения кандидата. "
            "Отвечай на русском языке кратко и по существу."
        ),
        input=(
            "КАРЬЕРНЫЙ ПРОФИЛЬ:\n"
            + json.dumps(profile, ensure_ascii=False)
            + "\n\nВАКАНСИЯ:\n"
            + vacancy_text
            + "\n\nДай оценку соответствия, "
            "сильные стороны, пробелы и рекомендацию: "
            "стоит ли откликаться."
        ),
        max_output_tokens=1200,
    )

    return response.output_text


if __name__ == "__main__":
    test_vacancy = (
        "AI-специалист по автоматизации процессов. "
        "Удаленная работа. "
        "Задачи: создание автоматизаций с помощью LLM, "
        "разработка промптов и тестирование AI-решений."
    )

    result = analyze_vacancy(test_vacancy)
    print(result)

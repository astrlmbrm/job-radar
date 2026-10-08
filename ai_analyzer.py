
import json
import os
from pathlib import Path


PROFILE_FILE = Path(__file__).with_name("career_profile.json")


def load_career_profile():
    """Загружает карьерный профиль из JSON."""

    with open(PROFILE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def analyze_vacancy(vacancy_text):
    """Подготавливает вакансию и профиль для AI-анализа."""

    profile = load_career_profile()

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "status": "API key not configured",
            "vacancy": vacancy_text,
            "target_roles": profile["target_roles"],
            "minimum_salary": profile["preferences"]["minimum_salary_rub"]
        }

    return {
        "status": "Ready for AI analysis",
        "vacancy": vacancy_text,
        "profile": profile
    }


if __name__ == "__main__":
    test_vacancy = (
        "AI-специалист по автоматизации процессов. "
        "Удаленная работа. "
        "Задачи: создание автоматизаций с помощью LLM, "
        "разработка промптов и тестирование AI-решений."
    )

    result = analyze_vacancy(test_vacancy)

    print(json.dumps(result, ensure_ascii=False, indent=2))

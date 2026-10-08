
import os


def analyze_vacancy(vacancy_text):
    """Анализ вакансии с помощью AI."""

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return "OpenAI API key пока не настроен."

    return "Ключ найден. AI-анализ будет добавлен следующим шагом."


if __name__ == "__main__":
    test_vacancy = (
        "AI-специалист по автоматизации процессов. "
        "Удаленная работа. "
        "Задачи: создание автоматизаций с помощью LLM, "
        "разработка промптов, интеграция AI-инструментов, "
        "тестирование и улучшение AI-решений."
    )

    result = analyze_vacancy(test_vacancy)
    print(result)

import json
import time

import requests
from bs4 import BeautifulSoup


INPUT_FILE = "filtered_vacancies.json"
OUTPUT_FILE = "enriched_vacancies.json"

HEADERS = {
    "User-Agent": "JobRadar/0.1 (personal vacancy search project)"
}

REQUEST_DELAY = 2


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


def get_vacancy_details(url):
    """Получает описание и навыки со страницы вакансии."""

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

    except requests.RequestException as error:
        return {
            "success": False,
            "description": None,
            "skills": [],
            "error": str(error),
        }

    if response.status_code != 200:
        return {
            "success": False,
            "description": None,
            "skills": [],
            "error": f"HTTP {response.status_code}",
        }

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    description_element = soup.find(
        attrs={"data-qa": "vacancy-description"}
    )

    description = None

    if description_element:
        description = description_element.get_text(
            "\n",
            strip=True
        )

    skills = []

    for element in soup.find_all(
        attrs={"data-qa": "skills-element"}
    ):
        skill = element.get_text(" ", strip=True)

        if skill and skill not in skills:
            skills.append(skill)

    return {
        "success": description is not None,
        "description": description,
        "skills": skills,
        "error": None if description else "Описание не найдено",
    }


def main():

    vacancies = load_json(INPUT_FILE)

    # Если enrichment уже когда-то запускался,
    # продолжаем с сохранённого результата.
    try:
        enriched = load_json(OUTPUT_FILE)

        enriched_by_id = {
            vacancy["id"]: vacancy
            for vacancy in enriched
        }

        print(
            f"Найден предыдущий результат: "
            f"{len(enriched_by_id)} вакансий."
        )

    except FileNotFoundError:
        enriched_by_id = {}

    total = len(vacancies)

    success_count = 0
    error_count = 0
    skipped_count = 0

    for number, vacancy in enumerate(
        vacancies,
        start=1
    ):

        vacancy_id = vacancy["id"]

        # Уже обработанную вакансию повторно
        # с HH не загружаем.
        if vacancy_id in enriched_by_id:
            skipped_count += 1
            continue

        print()
        print(
            f"[{number}/{total}] "
            f'{vacancy["title"]}'
        )

        print(vacancy["url"])

        details = get_vacancy_details(
            vacancy["url"]
        )

        vacancy["description"] = (
            details["description"]
        )

        vacancy["skills"] = (
            details["skills"]
        )

        vacancy["enrichment_success"] = (
            details["success"]
        )

        vacancy["enrichment_error"] = (
            details["error"]
        )

        enriched_by_id[vacancy_id] = vacancy

        if details["success"]:
            success_count += 1

            print(
                "Описание:",
                len(details["description"]),
                "символов"
            )

            print(
                "Навыков:",
                len(details["skills"])
            )

        else:
            error_count += 1

            print(
                "ОШИБКА:",
                details["error"]
            )

        # Ключевой момент:
        # сохраняемся ПОСЛЕ КАЖДОЙ вакансии.
        save_json(
            OUTPUT_FILE,
            list(enriched_by_id.values())
        )

        time.sleep(REQUEST_DELAY)

    print()
    print("=" * 70)
    print("ENRICHMENT ЗАВЕРШЁН")
    print("=" * 70)

    print(
        "Всего в исходном файле:",
        total
    )

    print(
        "Уже были обработаны:",
        skipped_count
    )

    print(
        "Успешно обработано сейчас:",
        success_count
    )

    print(
        "Ошибок сейчас:",
        error_count
    )

    print(
        "Всего сохранено:",
        len(enriched_by_id)
    )

    print()
    print(
        "Результат:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
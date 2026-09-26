import json
import time

from config import SEARCH_QUERIES
from sources.hh import search_hh


OUTPUT_FILE = "vacancies.json"


def collect_vacancies():
    """Собирает вакансии по всем поисковым запросам."""

    all_vacancies = {}

    total_queries = len(SEARCH_QUERIES)

    for number, query in enumerate(SEARCH_QUERIES, start=1):

        print()
        print("=" * 70)
        print(f"[{number}/{total_queries}] {query}")
        print("=" * 70)

        vacancies = search_hh(query)

        print(f"Получено с HH: {len(vacancies)}")

        for vacancy in vacancies:

            vacancy_id = vacancy["id"]

            # Если вакансию видим впервые —
            # сохраняем её.
            if vacancy_id not in all_vacancies:

                vacancy["matched_queries"] = [query]

                all_vacancies[vacancy_id] = vacancy

            # Если такая вакансия уже была найдена
            # другим запросом — второй раз её не сохраняем,
            # но запоминаем дополнительное совпадение.
            else:

                if (
                    query
                    not in all_vacancies[vacancy_id]["matched_queries"]
                ):
                    all_vacancies[vacancy_id][
                        "matched_queries"
                    ].append(query)

        # Небольшая пауза между запросами.
        time.sleep(2)

    return list(all_vacancies.values())


def save_vacancies(vacancies):
    """Сохраняет собранные вакансии в JSON."""

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            vacancies,
            file,
            ensure_ascii=False,
            indent=2
        )


def print_statistics(vacancies):
    """Печатает краткую статистику по сбору."""

    total = len(vacancies)

    with_salary = sum(
        1
        for vacancy in vacancies
        if (
            vacancy["salary_from"] is not None
            or vacancy["salary_to"] is not None
        )
    )

    without_salary = total - with_salary

    rub_salary = sum(
        1
        for vacancy in vacancies
        if vacancy["currency"] == "RUB"
    )

    other_currency = sum(
        1
        for vacancy in vacancies
        if (
            vacancy["currency"] is not None
            and vacancy["currency"] != "RUB"
        )
    )

    print()
    print("=" * 70)
    print("ИТОГ")
    print("=" * 70)

    print("Уникальных вакансий:", total)
    print("С указанной зарплатой:", with_salary)
    print("Без указанной зарплаты:", without_salary)
    print("Зарплата в RUB:", rub_salary)
    print("Зарплата в другой валюте:", other_currency)

    print()
    print("Количество по поисковым запросам:")

    for query in SEARCH_QUERIES:

        count = sum(
            1
            for vacancy in vacancies
            if query in vacancy["matched_queries"]
        )

        print(f"{query}: {count}")

    print()
    print(f"Данные сохранены в: {OUTPUT_FILE}")
    print("Готово.")


if __name__ == "__main__":

    vacancies = collect_vacancies()

    save_vacancies(vacancies)

    print_statistics(vacancies)
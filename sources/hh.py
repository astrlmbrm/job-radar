
import re

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://hh.ru/search/vacancy"

HEADERS = {
    "User-Agent": (
        "JobRadar/0.1 (personal vacancy search project)"
    )
}

CURRENCIES = {"RUB", "USD", "EUR", "AMD", "KZT", "BYR", "UZS"}


def get_vacancy_id(url):
    """Извлекает ID вакансии из ссылки HH."""

    match = re.search(r"/vacancy/(\d+)", url)

    if match:
        return match.group(1)

    return None


def make_clean_url(vacancy_id):
    """Создаёт короткую ссылку без поисковых параметров."""

    return f"https://hh.ru/vacancy/{vacancy_id}"


def get_text(element):
    """Безопасно получает текст HTML-элемента."""

    if element is None:
        return None

    return element.get_text(" ", strip=True) or None


def get_experience(card):
    """Извлекает требуемый опыт работы."""

    element = card.find(
        attrs={
            "data-qa": re.compile(
                r"^vacancy-serp__vacancy-work-experience"
            )
        }
    )

    return get_text(element)


def get_salary(card):
    """
    Извлекает зарплату из поисковой карточки HH.

    Возвращает нижнюю и верхнюю границы,
    валюту и исходный текст зарплаты.
    """

    empty_salary = {
        "salary_from": None,
        "salary_to": None,
        "currency": None,
        "salary_text": None,
    }

    # Ищем валюту внутри карточки.
    # Она позволяет определить блок с зарплатой,
    # не перепутав зарплату с опытом работы.

    currency_element = None

    for element in card.find_all("data"):
        value = element.get("value", "")

        if value in CURRENCIES:
            currency_element = element
            break

    if currency_element is None:
        return empty_salary

    # На проверенной разметке HH суммы и валюта
    # находятся внутри одного родительского span.

    salary_block = currency_element.parent

    if salary_block is None:
        return empty_salary

    values = []

    for element in salary_block.find_all("data"):
        value = element.get("value", "")

        if value.isdigit():
            values.append(int(value))

    salary_from = None
    salary_to = None

    if len(values) >= 2:
        salary_from = values[0]
        salary_to = values[1]

    elif len(values) == 1:
        text = salary_block.get_text(" ", strip=True).lower()

        # Различаем "от 80 000" и "до 80 000".
        if re.search(r"\bдо\s", text):
            salary_to = values[0]
        else:
            salary_from = values[0]

    return {
        "salary_from": salary_from,
        "salary_to": salary_to,
        "currency": currency_element.get("value"),
        "salary_text": get_text(salary_block),
    }


def search_hh(query):
    """Ищет удалённые вакансии в веб-выдаче HH."""

    params = {
        "text": query,
        "work_format": "REMOTE",
    }

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            headers=HEADERS,
            timeout=20,
        )

    except requests.RequestException as error:
        print(f"Ошибка соединения с HH: {error}")
        return []

    print(
        f'HH: ищу "{query}" — '
        f"HTTP {response.status_code}"
    )

    if response.status_code != 200:
        print("HH не отдал поисковую выдачу.")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    cards = soup.find_all(
        attrs={"data-qa": "vacancy-serp__vacancy"}
    )

    # Пустая выдача может означать отсутствие результатов,
    # изменение разметки или страницу проверки.
    if not cards:
        print(
            "Карточки не найдены. "
            "Проверь выдачу HH и наличие ограничений."
        )
        return []

    vacancies = []
    seen_ids = set()

    for card in cards:

        title_link = card.find(
            "a",
            href=re.compile(r"/vacancy/\d+")
        )

        if title_link is None:
            continue

        vacancy_id = get_vacancy_id(
            title_link.get("href", "")
        )

        if vacancy_id is None:
            continue

        if vacancy_id in seen_ids:
            continue

        title = get_text(title_link)

        if not title:
            continue

        seen_ids.add(vacancy_id)

        company = get_text(
            card.find(
                attrs={
                    "data-qa":
                    "vacancy-serp__vacancy-employer-text"
                }
            )
        )

        location = get_text(
            card.find(
                attrs={
                    "data-qa":
                    "vacancy-serp__vacancy-address"
                }
            )
        )

        experience = get_experience(card)

        salary = get_salary(card)

        remote = card.find(
            attrs={
                "data-qa":
                "vacancy-label-work-schedule-remote"
            }
        ) is not None

        vacancy = {
            "id": vacancy_id,
            "title": title,
            "company": company,
            "salary_from": salary["salary_from"],
            "salary_to": salary["salary_to"],
            "currency": salary["currency"],
            "salary_text": salary["salary_text"],
            "location": location,
            "experience": experience,
            "remote": remote,
            "url": make_clean_url(vacancy_id),
            "source": "hh",
            "search_query": query,
        }

        vacancies.append(vacancy)

    return vacancies


# Этот блок выполняется только при прямом запуске hh.py.
# При импорте из main.py он не запускается.

if __name__ == "__main__":

    results = search_hh("технический писатель")

    print()
    print("Найдено вакансий:", len(results))
    print()

    for vacancy in results:

        print("ID:", vacancy["id"])
        print("Название:", vacancy["title"])
        print("Компания:", vacancy["company"])

        print("Зарплата от:", vacancy["salary_from"])
        print("Зарплата до:", vacancy["salary_to"])
        print("Валюта:", vacancy["currency"])
        print("Зарплата текстом:", vacancy["salary_text"])

        print("Локация:", vacancy["location"])
        print("Опыт:", vacancy["experience"])
        print("Удалёнка:", vacancy["remote"])

        print("Ссылка:", vacancy["url"])

        print("-" * 60)
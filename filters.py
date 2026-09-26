import json


INPUT_FILE = "vacancies.json"
OUTPUT_FILE = "filtered_vacancies.json"


# Если эти фразы встречаются в названии,
# вакансия почти наверняка не относится к нашим направлениям.
EXCLUDE_TITLE_PHRASES = [
    # Продажи / коммерция
    "менеджер по продажам",
    "sales manager",
    "account manager",
    "business development manager",
    "менеджер по работе с клиентами",

    # HR
    "рекрутер",
    "recruiter",
    "talent acquisition",
    "hr manager",

    # Руководящие продуктовые роли
    "product owner",
    "product manager",
    "руководитель продукта",

    # Бизнес-анализ
    "business analyst",
    "бизнес-аналитик",

    # Совсем посторонние профессии
    "маркетолог",
    "smm",
    "копирайтер",
    "copywriter",
    "дизайнер",
    "designer",

    # Учебные работы
    "автор студенческих работ",
    "автор работ",
]


def load_vacancies():
    """Загружает наш сохранённый dataset."""

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def get_exclusion_reason(vacancy):
    """
    Проверяет жёсткие причины исключения.

    Возвращает причину исключения
    или None, если вакансию оставляем.
    """

    title = vacancy.get("title", "").lower()

    for phrase in EXCLUDE_TITLE_PHRASES:

        if phrase in title:
            return f'название содержит "{phrase}"'

    # На всякий случай проверяем удалёнку.
    if vacancy.get("remote") is not True:
        return "не подтверждена удалённая работа"

    return None


def filter_vacancies(vacancies):
    """Разделяет вакансии на оставленные и исключённые."""

    accepted = []
    rejected = []

    for vacancy in vacancies:

        reason = get_exclusion_reason(vacancy)

        if reason is None:
            accepted.append(vacancy)

        else:
            rejected.append({
                "id": vacancy["id"],
                "title": vacancy["title"],
                "company": vacancy.get("company"),
                "reason": reason,
                "url": vacancy["url"],
            })

    return accepted, rejected


def save_json(filename, data):
    """Сохраняет данные в JSON."""

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


if __name__ == "__main__":

    vacancies = load_vacancies()

    accepted, rejected = filter_vacancies(vacancies)

    save_json(
        OUTPUT_FILE,
        accepted
    )

    save_json(
        "rejected_vacancies.json",
        rejected
    )

    print("=" * 70)
    print("ФИЛЬТРАЦИЯ")
    print("=" * 70)

    print("Исходных вакансий:", len(vacancies))
    print("Оставлено:", len(accepted))
    print("Исключено:", len(rejected))

    print()
    print("Первые 30 исключённых:")
    print()

    for vacancy in rejected[:30]:

        print(vacancy["title"])
        print("Компания:", vacancy["company"])
        print("Причина:", vacancy["reason"])
        print(vacancy["url"])
        print("-" * 70)

    print()
    print(
        "Подходящие сохранены в:",
        OUTPUT_FILE
    )

    print(
        "Исключённые сохранены в:",
        "rejected_vacancies.json"
    )
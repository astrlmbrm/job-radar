import json
import re
from collections import Counter


INPUT_FILE = "enriched_vacancies.json"
OUTPUT_FILE = "scored_vacancies.json"


# ============================================================
# НАСТРОЙКИ СКОРИНГА
# ============================================================

# Целевые направления.
# Совпадение в НАЗВАНИИ особенно ценно.
TARGET_ROLES = {
    # Knowledge Management
    "knowledge management": 30,
    "knowledge manager": 30,
    "knowledge base": 30,
    "база знаний": 30,
    "управление знаниями": 30,

    # Technical Writing
    "technical writer": 30,
    "технический писатель": 30,

    # Support L2 / Application Support
    "application support": 30,
    "application support analyst": 35,
    "l2 support": 30,
    "support l2": 30,
    "техническая поддержка l2": 30,
    "инженер технической поддержки l2": 30,

    # Quality
    "quality analyst": 30,
    "data quality": 30,
    "content quality": 30,
    "ai quality": 30,

    # Operations
    "data operations": 30,
    "operations analyst": 25,
    "ai operations": 30,
    "prompt operations": 30,

    # AI / vibe coding
    "ai specialist": 25,
    "ai-специалист": 25,
    "специалист по генеративному ии": 30,
    "generative ai": 30,
    "vibe coding": 25,
    "вайбкод": 25,

    # Research
    "research analyst": 25,
    "researcher": 20,
    "исследователь": 20,

    # Широкие технические роли — небольшой бонус,
    # потому что нужно читать описание.
    "technical specialist": 15,
    "технический специалист": 15,
}


# Навыки/задачи, которые повышают релевантность.
POSITIVE_TERMS = {
    "sql": 8,
    "базы данных": 6,
    "database": 5,
    "databases": 5,

    "логи": 7,
    "логов": 7,
    "logs": 7,

    "api": 6,
    "rest api": 6,
    "http": 4,

    "confluence": 6,
    "jira": 4,

    "техническая документация": 8,
    "документации": 4,
    "documentation": 6,

    "база знаний": 8,
    "knowledge base": 8,

    "инструкции": 5,
    "регламенты": 4,

    "анализ данных": 5,
    "data analysis": 5,
    "data quality": 8,

    "python": 4,

    "llm": 7,
    "generative ai": 7,
    "генеративный ии": 7,
    "prompt": 6,
    "промпт": 6,
}


# То, чего хотелось бы избегать.
NEGATIVE_TERMS = {
    "холодные звонки": -25,
    "cold calls": -25,

    "активные продажи": -25,
    "продажи": -12,
    "sales": -10,

    "первая линия": -15,
    "1 линия": -15,
    "first line": -15,
    "l1 support": -12,

    "телефонные звонки": -12,
    "входящие звонки": -10,

    "дежурства": -12,
    "ночные смены": -15,
    "ночные дежурства": -18,
    "on-call": -18,
    "on call": -18,
    "24/7": -10,

    "business development": -20,
    "маркетинг": -12,
    "marketing": -12,

    "project manager": -15,
    "project management": -10,
    "менеджер проектов": -15,

    "product manager": -20,
    "product owner": -20,

    "business analyst": -15,
    "бизнес-аналитик": -15,
}


# Сильные предупреждения по названию.
TITLE_PENALTIES = {
    "senior": -8,
    "lead": -12,
    "teamlead": -15,
    "team lead": -15,
    "руководитель": -15,
    "head of": -20,

    "project manager": -25,
    "менеджер проектов": -25,
    "product manager": -30,
    "product owner": -30,
    "marketing analyst": -20,
    "маркетолог": -25,
}


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

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


def normalize(text):
    if not text:
        return ""

    text = text.lower()
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)

    return text


def contains_term(text, term):
    """
    Для коротких латинских терминов вроде SQL/API
    стараемся не ловить случайные части слов.
    """

    term = normalize(term)

    if term in {"sql", "api", "http", "llm"}:
        return bool(
            re.search(
                rf"(?<![a-zа-я0-9]){re.escape(term)}(?![a-zа-я0-9])",
                text
            )
        )

    return term in text


# ============================================================
# СКОРИНГ
# ============================================================

def score_vacancy(vacancy):

    title = normalize(
        vacancy.get("title", "")
    )

    description = normalize(
        vacancy.get("description", "")
    )

    skills_list = vacancy.get("skills", []) or []

    skills = normalize(
        " ".join(skills_list)
    )

    full_text = f"{title} {description} {skills}"

    score = 0

    positive_reasons = []
    negative_reasons = []

    matched_positive = set()
    matched_negative = set()

    # --------------------------------------------------------
    # 1. Целевая должность
    # --------------------------------------------------------

    for term, points in TARGET_ROLES.items():

        if contains_term(title, term):

            score += points

            positive_reasons.append(
                f'+{points}: целевая роль "{term}"'
            )

            # Берём только самый сильный role match,
            # чтобы "application support analyst"
            # не насуммировал ещё application support.
            break

    # --------------------------------------------------------
    # 2. Полезные навыки
    # --------------------------------------------------------

    for term, points in POSITIVE_TERMS.items():

        if contains_term(full_text, term):

            # Не начисляем похожий термин много раз.
            normalized_term = normalize(term)

            if normalized_term in matched_positive:
                continue

            score += points
            matched_positive.add(normalized_term)

            positive_reasons.append(
                f'+{points}: {term}'
            )

    # --------------------------------------------------------
    # 3. Нежелательные условия
    # --------------------------------------------------------

    for term, points in NEGATIVE_TERMS.items():

        if contains_term(full_text, term):

            normalized_term = normalize(term)

            if normalized_term in matched_negative:
                continue

            score += points
            matched_negative.add(normalized_term)

            negative_reasons.append(
                f'{points}: {term}'
            )

    # --------------------------------------------------------
    # 4. Штрафы именно за название
    # --------------------------------------------------------

    for term, points in TITLE_PENALTIES.items():

        if contains_term(title, term):

            score += points

            negative_reasons.append(
                f'{points}: "{term}" в названии'
            )

    # --------------------------------------------------------
    # 5. Удалёнка
    # --------------------------------------------------------

    if vacancy.get("remote") is True:

        score += 8

        positive_reasons.append(
            "+8: удаленная работа"
        )

    # --------------------------------------------------------
    # 6. Зарплата
    # --------------------------------------------------------

    salary_from = vacancy.get("salary_from")
    salary_to = vacancy.get("salary_to")
    currency = vacancy.get("currency")

    # Пока оцениваем только RUB.
    # Другие валюты не штрафуем.
    if currency == "RUB":

        # Если верхняя граница ниже 80к,
        # вакансия финансово не подходит.
        if salary_to is not None and salary_to < 80000:

            score -= 30

            negative_reasons.append(
                f"-30: зарплата до {salary_to:,} RUB"
            )

        # Если указана только нижняя граница
        # и она ниже 80к — небольшой штраф,
        # потому что потолок неизвестен.
        elif (
            salary_from is not None
            and salary_from < 80000
            and salary_to is None
        ):

            score -= 8

            negative_reasons.append(
                f"-8: зарплата от {salary_from:,} RUB"
            )

        elif (
            salary_from is not None
            and salary_from >= 80000
        ):

            score += 5

            positive_reasons.append(
                f"+5: зарплата от {salary_from:,} RUB"
            )

    # Не даём отрицательные значения ниже нуля.
    score = max(score, 0)

    # --------------------------------------------------------
    # Категория
    # --------------------------------------------------------

    if score >= 55:
        category = "HOT"

    elif score >= 35:
        category = "GOOD"

    elif score >= 20:
        category = "MAYBE"

    else:
        category = "SKIP"

    return {
        "score": score,
        "category": category,
        "positive_reasons": positive_reasons,
        "negative_reasons": negative_reasons,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    vacancies = load_json(INPUT_FILE)

    scored = []

    for vacancy in vacancies:

        result = score_vacancy(vacancy)

        vacancy["score"] = result["score"]
        vacancy["category"] = result["category"]
        vacancy["positive_reasons"] = (
            result["positive_reasons"]
        )
        vacancy["negative_reasons"] = (
            result["negative_reasons"]
        )

        scored.append(vacancy)

    scored.sort(
        key=lambda vacancy: vacancy["score"],
        reverse=True
    )

    save_json(
        OUTPUT_FILE,
        scored
    )

    categories = Counter(
        vacancy["category"]
        for vacancy in scored
    )

    print("=" * 75)
    print("JOB RADAR — SCORING")
    print("=" * 75)

    print("Всего:", len(scored))
    print("HOT:", categories["HOT"])
    print("GOOD:", categories["GOOD"])
    print("MAYBE:", categories["MAYBE"])
    print("SKIP:", categories["SKIP"])

    print()
    print("=" * 75)
    print("ТОП-20")
    print("=" * 75)

    for number, vacancy in enumerate(
        scored[:20],
        start=1
    ):

        print()
        print(
            f'{number}. [{vacancy["score"]}] '
            f'{vacancy["category"]}'
        )

        print(vacancy["title"])

        print(
            "Компания:",
            vacancy.get("company")
        )

        salary_text = vacancy.get(
            "salary_text"
        )

        print(
            "Зарплата:",
            salary_text or "не указана"
        )

        print(
            "Локация:",
            vacancy.get("location")
        )

        print("Почему:")

        for reason in vacancy[
            "positive_reasons"
        ]:
            print(" ", reason)

        for reason in vacancy[
            "negative_reasons"
        ]:
            print(" ", reason)

        print(
            vacancy["url"]
        )

        print("-" * 75)

    print()
    print(
        "Полный рейтинг сохранён в:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
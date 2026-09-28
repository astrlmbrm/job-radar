import json
import re
from collections import Counter


INPUT_FILE = "enriched_vacancies.json"
OUTPUT_FILE = "scored_vacancies.json"


# ============================================================
# НАСТРОЙКИ СКОРИНГА
# ============================================================

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
    "application support analyst": 35,
    "application support": 30,
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

    # Более широкие технические роли
    "technical specialist": 15,
    "технический специалист": 15,
}


# ============================================================
# ГРУППЫ ПОЛЕЗНЫХ НАВЫКОВ
#
# За каждую группу бонус начисляется только ОДИН раз.
# Например "логи", "логов" и "logs" = один навык.
# ============================================================

POSITIVE_GROUPS = [
    ("SQL", 8, ["sql"]),

    (
        "базы данных",
        6,
        ["базы данных", "database", "databases"],
    ),

    (
        "логи",
        7,
        ["логи", "логов", "logs"],
    ),

    (
        "API",
        6,
        ["api", "rest api"],
    ),

    ("HTTP", 4, ["http"]),

    ("Confluence", 6, ["confluence"]),

    ("Jira", 4, ["jira"]),

    (
        "техническая документация",
        8,
        [
            "техническая документация",
            "документации",
            "documentation",
        ],
    ),

    (
        "база знаний",
        8,
        ["база знаний", "knowledge base"],
    ),

    ("инструкции", 5, ["инструкции"]),

    ("регламенты", 4, ["регламенты"]),

    (
        "анализ данных",
        5,
        ["анализ данных", "data analysis"],
    ),

    ("data quality", 8, ["data quality"]),

    ("Python", 4, ["python"]),

    (
        "LLM",
        7,
        ["llm"],
    ),

    (
        "Generative AI",
        7,
        ["generative ai", "генеративный ии"],
    ),

    (
        "prompt",
        6,
        ["prompt", "промпт"],
    ),
]


# ============================================================
# ЖЁСТКИЕ ИСКЛЮЧЕНИЯ
#
# Если встречается такое условие, вакансия нам не подходит
# независимо от количества положительных баллов.
# ============================================================

HARD_EXCLUSIONS = {
    "ночной": "ночная работа",
    "ночная": "ночная работа",
    "ночные": "ночная работа",
    "ночью": "ночная работа",
    "ночная смена": "ночная работа",
    "ночные смены": "ночная работа",
    "ночное время": "ночная работа",
    "ночные дежурства": "ночная работа",
    "night shift": "ночная работа",
    "night shifts": "ночная работа",
    "overnight shift": "ночная работа",
}


# ============================================================
# НЕЖЕЛАТЕЛЬНЫЕ УСЛОВИЯ
# ============================================================

NEGATIVE_GROUPS = [
    (
        "холодные звонки",
        -25,
        ["холодные звонки", "cold calls"],
    ),

    (
        "активные продажи",
        -25,
        ["активные продажи"],
    ),

    (
        "продажи",
        -12,
        ["продажи", "sales"],
    ),

    (
        "первая линия поддержки",
        -15,
        [
            "первая линия",
            "1 линия",
            "first line",
            "l1 support",
        ],
    ),

    (
        "телефонные звонки",
        -12,
        ["телефонные звонки", "входящие звонки"],
    ),

    (
        "дежурства",
        -12,
        ["дежурства"],
    ),

    (
        "on-call",
        -18,
        ["on-call", "on call"],
    ),

    ("24/7", -10, ["24/7"]),

    (
        "business development",
        -20,
        ["business development"],
    ),

    (
        "маркетинг",
        -12,
        ["маркетинг", "marketing"],
    ),

    (
        "project management",
        -15,
        [
            "project manager",
            "project management",
            "менеджер проектов",
        ],
    ),

    (
        "product management",
        -20,
        ["product manager", "product owner"],
    ),

    (
        "business analyst",
        -15,
        ["business analyst", "бизнес-аналитик"],
    ),
]


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
            indent=2,
        )


def normalize(text):
    if not text:
        return ""

    text = text.lower()
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)

    return text


def contains_term(text, term):
    term = normalize(term)

    if term in {"sql", "api", "http", "llm"}:
        return bool(
            re.search(
                rf"(?<![a-zа-я0-9])"
                rf"{re.escape(term)}"
                rf"(?![a-zа-я0-9])",
                text,
            )
        )

    return term in text


def contains_any(text, terms):
    return any(
        contains_term(text, term)
        for term in terms
    )


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

    # --------------------------------------------------------
    # 0. Жёсткие исключения
    # --------------------------------------------------------

    for term, reason in HARD_EXCLUSIONS.items():
        if contains_term(full_text, term):
            return {
                "score": 0,
                "category": "SKIP",
                "positive_reasons": [],
                "negative_reasons": [
                    f'ЖЁСТКОЕ ИСКЛЮЧЕНИЕ: {reason} ("{term}")'
                ],
            }

    # --------------------------------------------------------
    # 1. Целевая должность
    # --------------------------------------------------------

    role_matches = []

    for term, points in TARGET_ROLES.items():
        if contains_term(title, term):
            role_matches.append(
                (points, term)
            )

    if role_matches:
        points, term = max(
            role_matches,
            key=lambda item: item[0],
        )

        score += points

        positive_reasons.append(
            f'+{points}: целевая роль "{term}"'
        )

    # --------------------------------------------------------
    # 2. Полезные навыки
    # --------------------------------------------------------

    for label, points, terms in POSITIVE_GROUPS:
        if contains_any(full_text, terms):
            score += points

            positive_reasons.append(
                f"+{points}: {label}"
            )

    # --------------------------------------------------------
    # 3. Нежелательные условия
    # --------------------------------------------------------

    for label, points, terms in NEGATIVE_GROUPS:
        if contains_any(full_text, terms):
            score += points

            negative_reasons.append(
                f"{points}: {label}"
            )

    # --------------------------------------------------------
    # 4. Штрафы за название
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

    if currency == "RUB":

        if (
            salary_to is not None
            and salary_to < 80000
        ):
            score -= 30

            negative_reasons.append(
                f"-30: зарплата до "
                f"{salary_to:,} RUB"
            )

        elif (
            salary_from is not None
            and salary_from < 80000
            and salary_to is None
        ):
            score -= 8

            negative_reasons.append(
                f"-8: зарплата от "
                f"{salary_from:,} RUB"
            )

        elif (
            salary_from is not None
            and salary_from >= 80000
        ):
            score += 5

            positive_reasons.append(
                f"+5: зарплата от "
                f"{salary_from:,} RUB"
            )

    score = max(score, 0)

    # --------------------------------------------------------
    # 7. Категория
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
        reverse=True,
    )

    save_json(
        OUTPUT_FILE,
        scored,
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
        start=1,
    ):
        print()
        print(
            f'{number}. [{vacancy["score"]}] '
            f'{vacancy["category"]}'
        )

        print(vacancy["title"])

        print(
            "Компания:",
            vacancy.get("company"),
        )

        salary_text = vacancy.get(
            "salary_text"
        )

        print(
            "Зарплата:",
            salary_text or "не указана",
        )

        print(
            "Локация:",
            vacancy.get("location"),
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

        print(vacancy["url"])
        print("-" * 75)

    print()
    print(
        "Полный рейтинг сохранён в:",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()
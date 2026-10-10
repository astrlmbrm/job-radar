"""Shared selection and durable history for AI and Telegram stages."""
import json
import os
from pathlib import Path


def ai_enabled():
    return os.getenv("AI_ENABLED", "false").strip().lower() == "true"


def load_sent_ids(filename="sent_vacancies.json"):
    path = Path(filename)
    if not path.exists():
        return set()
    ids = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(ids, list) or any(
        type(item) not in (str, int) or not str(item).strip() for item in ids
    ):
        raise ValueError("Invalid history; refusing to risk duplicates")
    return {str(item) for item in ids}


def save_sent_ids(ids, filename="sent_vacancies.json"):
    path = Path(filename)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def prospective(vacancies, sent_ids):
    seen = set(sent_ids)
    result = []
    for vacancy in vacancies:
        identifier = vacancy.get("id")
        if identifier is None or not str(identifier).strip():
            continue
        identifier = str(identifier)
        if identifier in seen or vacancy.get("category") not in {"HOT", "GOOD"}:
            continue
        seen.add(identifier)
        result.append(vacancy)
    return sorted(result, key=lambda v: v.get("score", 0), reverse=True)


def ranking(vacancy):
    if vacancy.get("ai_status") == "success":
        return ({"APPLY": 2, "CONSIDER": 1}.get(vacancy.get("ai_recommendation"), -1),
                vacancy.get("ai_score", 0), vacancy.get("score", 0))
    return (0, 0, vacancy.get("score", 0))

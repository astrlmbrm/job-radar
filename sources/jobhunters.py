"""Collect job cards from public Job Hunters HTML, with conservative remote checks.

Not enabled in daily pipeline until verified. No personal details or API keys.
"""
import re
import requests
from bs4 import BeautifulSoup

URL = "https://jobhuntersapp.com/jobs"
HEADERS = {"User-Agent": "JobRadar/0.1 (personal vacancy search project)"}
RESTRICTED_REMOTE = re.compile(
    r"remote\s*\((?:us|usa|uk|eu|canada|united states|united kingdom)\)"
    r"|(?:только|only)\s+(?:сша|рф|россия|usa|us|uk|eu)",
    re.IGNORECASE,
)


def normalize(text):
    return " ".join((text or "").lower().replace("ё", "е").split())


def salary_fields(salary_text):
    normalized = (salary_text or "").replace("\u00a0", " ").replace("\u202f", " ")
    numbers = [int(x.replace(" ", "")) for x in re.findall(r"\d[\d ]*\d|\d+", normalized)]
    if not numbers:
        return None, None, None
    currency = "RUB" if "₽" in normalized or "руб" in normalized.lower() else None
    if "–" in normalized or "—" in normalized or "-" in normalized:
        return numbers[0], numbers[1] if len(numbers)>1 else None, currency
    if re.search(r"\bдо\b|\bup to\b", normalized, re.I):
        return None, numbers[0], currency
    return numbers[0], None, currency


def search_jobhunters():
    response = requests.get(URL, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    vacancies = []
    seen = set()
    for card in soup.select("article.jh-job"):
        title_link = card.select_one('a.jh-job-title[href]')
        if not title_link:
            continue
        match = re.search(r"/jobs/(\d+)(?:[/?#]|$)", title_link["href"])
        if not match:
            continue
        job_id = match.group(1)
        if job_id in seen:
            continue
        title = title_link.get_text(" ", strip=True)
        if not title:
            continue
        seen.add(job_id)
        tags = card.select_one(".jh-job-tags")
        tags_text = tags.get_text(" ", strip=True) if tags else ""
        tags_normalized = normalize(tags_text)
        remote = bool(re.search(r"\bудаленно\b|\bremote\b", tags_normalized))
        if RESTRICTED_REMOTE.search(tags_text):
            remote = False
        if re.search(r"\bгибрид\b|\bкомбинированн\w*\b|\bофис\b|\bon.?site\b|\bhybrid\b", tags_normalized):
            remote = False
        salary_node = card.select_one(".jh-job-salary")
        salary_text = salary_node.get_text(" ", strip=True) if salary_node else None
        salary_from, salary_to, currency = salary_fields(salary_text)
        company_node = card.select_one(".jh-job-company")
        company = company_node.get_text(" ", strip=True) if company_node else None
        if company:
            company = re.sub(r"\s+\d+\s*(?:мин|ч|д|дн|час(?:а|ов)?)\s+назад.*$", "", company).strip()
        # Description is only a listing preview. Do not mix other cards or generic UI text.
        preview = card.get_text(" ", strip=True)[:1200]
        vacancies.append({
            "id": f"jobhunters:{job_id}",
            "title": title,
            "company": company,
            "salary_from": salary_from,
            "salary_to": salary_to,
            "currency": currency,
            "salary_text": salary_text,
            "location": None,
            "experience": tags_text,
            "remote": remote,
            "url": f"https://jobhuntersapp.com/jobs/{job_id}",
            "source": "jobhunters",
            "search_query": "latest",
            "listing_preview": preview,
        })
    return vacancies


if __name__ == "__main__":
    rows = search_jobhunters()
    print("Found:", len(rows))
    print("Confirmed remote, unrestricted by explicit tag:", sum(x["remote"] for x in rows))
    for v in rows[:12]:
        print(v["title"], "| remote:", v["remote"], "| salary:", v["salary_text"], "|", v["url"])

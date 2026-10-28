"""Collect candidate vacancies from the public Job Hunters HTML listing.

Remote is deliberately left unconfirmed until a reliable per-vacancy
work-format field is identified. This module is not enabled in main.py.
"""
import re
import requests
from bs4 import BeautifulSoup

URL = "https://jobhuntersapp.com/jobs"
HEADERS = {"User-Agent": "JobRadar/0.1 (personal vacancy search project)"}


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
        seen.add(job_id)
        title = title_link.get_text(" ", strip=True)
        if not title:
            continue
        vacancies.append({
            "id": f"jobhunters:{job_id}",
            "title": title,
            "company": None,
            "salary_from": None,
            "salary_to": None,
            "currency": None,
            "salary_text": None,
            "location": None,
            "experience": None,
            "remote": None,
            "url": f"https://jobhuntersapp.com/jobs/{job_id}",
            "source": "jobhunters",
            "search_query": "latest",
            "listing_preview": card.get_text(" ", strip=True)[:1200],
        })
    return vacancies


if __name__ == "__main__":
    rows = search_jobhunters()
    print("Found:", len(rows))
    for vacancy in rows[:10]:
        print(vacancy["title"], vacancy["url"])

"""Read-only structural probe for Job Hunters listing and vacancy pages.

Run manually. Prints compact samples, not whole HTML or credentials.
"""
import json
import re
import requests
from bs4 import BeautifulSoup

ROOT = "https://jobhuntersapp.com"
HEADERS = {"User-Agent": "JobRadar/0.1 (personal vacancy search project)"}


def fetch(url):
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def compact(text, limit=220):
    return re.sub(r"\s+", " ", text or "").strip()[:limit]


def inspect_listing():
    soup = fetch(ROOT + "/jobs")
    anchors = []
    seen = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        match = re.search(r"/jobs/(\d+)(?:[/?#]|$)", href)
        if not match or match.group(1) in seen:
            continue
        seen.add(match.group(1))
        anchors.append((match.group(1), a))

    print("Unique numeric job links:", len(anchors))
    for number, (job_id, anchor) in enumerate(anchors[:6], 1):
        print(f"LISTING {number}: id={job_id}, link_text={compact(anchor.get_text(' ', strip=True), 150)!r}")
        for depth, parent in enumerate([anchor, anchor.parent, anchor.parent.parent], 0):
            if parent is not None:
                print("  ancestor", depth, "tag", parent.name, "class", parent.get("class", [])[:6],
                      "text", repr(compact(parent.get_text(' ', strip=True), 260)))


def inspect_detail(job_id):
    soup = fetch(ROOT + "/jobs/" + str(job_id))
    print("\nDETAIL", job_id)
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(script.string or script.get_text())
            records = obj if isinstance(obj, list) else [obj]
            for entry in records:
                if not isinstance(entry, dict):
                    continue
                print("JSON-LD type", entry.get("@type"), "keys", list(entry.keys())[:30])
                print("Title", compact(str(entry.get("title", ""))))
                print("Employment", entry.get("employmentType"))
                print("Location type", entry.get("jobLocationType"))
                print("Hiring organization", compact(str(entry.get("hiringOrganization", "")), 160))
                print("Salary", compact(str(entry.get("baseSalary", "")), 160))
                print("Description length", len(str(entry.get("description", ""))))
        except (ValueError, TypeError) as error:
            print("JSON-LD parse failed:", type(error).__name__)
    for selector in ["h1", "main", "article"]:
        node = soup.select_one(selector)
        print(selector, repr(compact(node.get_text(" ", strip=True), 350)) if node else "missing")
    text = soup.get_text(" ", strip=True).lower()
    for term in ["удаленно", "удалённо", "remote", "гибрид", "hybrid", "офис"]:
        print("Has term", term, term in text)


if __name__ == "__main__":
    inspect_listing()
    inspect_detail(26951)

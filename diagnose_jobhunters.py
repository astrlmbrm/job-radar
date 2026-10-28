"""Safe read-only diagnostic for public Job Hunters pages.

Prints only response metadata and counts. No tokens, cookies, or page bodies.
"""
import re
import requests
from bs4 import BeautifulSoup

URLS = [
    "https://jobhuntersapp.com/jobs",
    "https://jobhuntersapp.com/jobs/26951",
]

HEADERS = {"User-Agent": "JobRadar/0.1 (personal vacancy search; contact via repository)"}

def main():
    for url in URLS:
        print(f"\nChecking: {url}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            print("HTTP:", response.status_code)
            print("Final host:", requests.utils.urlparse(response.url).hostname)
            print("Content type:", response.headers.get("content-type", "unknown"))
            print("Response bytes:", len(response.content))
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            links = sorted({
                a.get("href", "").split("?")[0]
                for a in soup.select('a[href*="/jobs/"]')
                if re.search(r"/jobs/\\d+", a.get("href", ""))
            })
            print("Job detail links in HTML:", len(links))
            all_job_hrefs = sorted({
                a.get("href", "").split("?")[0]
                for a in soup.select('a[href*="/jobs/"]')
            })
            print("All links containing /jobs/:", len(all_job_hrefs))
            print("Other sample job paths:", all_job_hrefs[:8])
            print("Job path occurrences in raw HTML:", len(re.findall(r'/jobs/[0-9]+', response.text)))
            print("Total anchors:", len(soup.select("a[href]")))
            print("Script tags:", len(soup.select("script")))
            print("Script source samples:", [
                tag.get("src", "")[:120]
                for tag in soup.select("script[src]")[:8]
            ])
            print("Embedded JSON scripts:", len(soup.select('script[type="application/json"]')))
            print("HTML text length:", len(soup.get_text(" ", strip=True)))
            print("Sample paths:", links[:5])
            print("JSON-LD scripts:", len(soup.select('script[type="application/ld+json"]')))
            print("Next.js data marker:", bool(soup.select_one("script#__NEXT_DATA__")))
            print("Nuxt marker:", "__NUXT__" in response.text)
            print("HTML title:", (soup.title.get_text(" ", strip=True) if soup.title else "none")[:120])
        except requests.RequestException as error:
            print("Request failed:", type(error).__name__)

if __name__ == "__main__":
    main()

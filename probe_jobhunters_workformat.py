"""Inspect Job Hunters card metadata without enabling notifications."""
import re
import requests
from bs4 import BeautifulSoup

soup = BeautifulSoup(requests.get("https://jobhuntersapp.com/jobs",timeout=25,headers={"User-Agent":"JobRadar/0.1"}).text,"html.parser")
for card in soup.select("article.jh-job")[:8]:
    title = card.select_one("a.jh-job-title")
    if not title:
        continue
    print("\nTITLE:",title.get_text(" ",strip=True))
    for node in card.select("[class]"):
        classes = " ".join(node.get("class",[]))
        if re.search(r"remote|format|work|salary|company|location|tag|meta|badge|type",classes,re.I):
            value = node.get_text(" ",strip=True)
            if value and len(value)<160:
                print("  ",classes[:110],"=>",value[:140])
    for term in ["Workplace:","Location:","Удалённо","Удаленно","Комбинированный","OnSite","Remote","Hybrid"]:
        text=card.get_text(" ",strip=True)
        pos=text.lower().find(term.lower())
        if pos!=-1:
            print("  ",term,repr(text[max(0,pos-35):pos+120]))

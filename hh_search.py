import requests


url = "https://api.hh.ru/vacancies"

params = {
    "text": "технический писатель",
    "per_page": 10,
}

headers = {
    "User-Agent": "JobRadar/0.1"
}

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=10
)

print("Статус запроса:", response.status_code)

if response.status_code != 200:
    print("HH API вернул ошибку:")
    print(response.text)
else:
    data = response.json()

    print("Всего найдено:", data["found"])
    print()

    for vacancy in data["items"]:
        print(vacancy["name"])
        print(vacancy["alternate_url"])
        print("-" * 50)
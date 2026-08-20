import os
import requests

URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_FILE = "cache/catalogue-page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship A9/1.0 (+https://github.com/asmaebihkak24/polite-scraper)"
}


def fetch_and_cache():
    # If the page is already cached, use the local copy
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as file:
            html = file.read()

        print(f"CACHE: {len(html)} bytes")
        return html

    print("FETCH")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=10
    )

    # Only HTTP 200 is considered a successful fetch
    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed: HTTP {response.status_code}"
        )

    html = response.content

    os.makedirs("cache", exist_ok=True)

    with open(CACHE_FILE, "wb") as file:
        file.write(html)

    print(f"Response size: {len(html)} bytes")

    return html


if __name__ == "__main__":
    fetch_and_cache()
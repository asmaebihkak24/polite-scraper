import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = "cache"

HEADERS = {
    "User-Agent": "FlyRankInternship A9/1.0 (+https://github.com/asmaebihkak24/polite-scraper)"
}


def cache_path(page_number):
    return os.path.join(
        CACHE_DIR,
        f"catalogue-page-{page_number}.html"
    )


def fetch_page(url, page_number):
    cache_file = cache_path(page_number)

    # Use cache if the page was already downloaded
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as file:
            html = file.read()

        print(f"CACHE: page={page_number} size={len(html)} bytes")
        return html

    print(f"FETCH: page={page_number}")

    # Wait before a real request
    time.sleep(0.5)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=10
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Fetch failed: HTTP {response.status_code}"
        )

    html = response.content

    os.makedirs(CACHE_DIR, exist_ok=True)

    with open(cache_file, "wb") as file:
        file.write(html)

    print(f"Response size: {len(html)} bytes")

    return html


def discover_pages():
    current_url = BASE_URL
    page_number = 1
    catalogue_pages = 0
    book_links = set()

    while current_url:
        html = fetch_page(current_url, page_number)

        soup = BeautifulSoup(html, "html.parser")

        # Find every book link on the current catalogue page
        for link in soup.select("article.product_pod h3 a"):
            href = link.get("href")

            if href:
                absolute_url = urljoin(current_url, href)
                book_links.add(absolute_url)

        catalogue_pages += 1

        # Find the catalogue's own "next" link
        next_link = soup.select_one("li.next a")

        

        if page_number < 3 and next_link and next_link.get("href"):
             next_url = urljoin(current_url, next_link["href"])

             page_number += 1
             current_url = next_url
        else:
             current_url = None         

    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(book_links)}")


if __name__ == "__main__":
    discover_pages()
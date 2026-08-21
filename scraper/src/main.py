import os
import time
import json
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = "cache"
BOOK_CACHE_DIR = os.path.join(CACHE_DIR, "books")

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

    # Only HTTP 200 is considered successful
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
    book_sources = {}

    while current_url:
        html = fetch_page(current_url, page_number)

        soup = BeautifulSoup(html, "html.parser")

        # Find every book link on the current catalogue page
        for link in soup.select("article.product_pod h3 a"):
            href = link.get("href")

            if href:
                absolute_url = urljoin(current_url, href)

                # Remove duplicates
                book_links.add(absolute_url)

                # Keep the catalogue page where the book was discovered
                book_sources[absolute_url] = current_url

        catalogue_pages += 1

        # Find the catalogue's own "next" link
        next_link = soup.select_one("li.next a")

        # Assignment asks us to process only pages 1, 2 and 3
        if page_number < 3 and next_link and next_link.get("href"):
            next_url = urljoin(current_url, next_link["href"])

            page_number += 1
            current_url = next_url
        else:
            current_url = None

    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(book_links)}")

    return book_links, book_sources


def book_cache_path(product_url):
    """
    Create a cache filename from the book URL.
    """
    filename = product_url.rstrip("/").split("/")[-2]

    return os.path.join(
        BOOK_CACHE_DIR,
        f"{filename}.html"
    )


def fetch_book_page(product_url):
    cache_file = book_cache_path(product_url)

    # Use cached book page if available
    if os.path.exists(cache_file):
        with open(cache_file, "rb") as file:
            html = file.read()

        return html

    # Wait before a real request
    time.sleep(0.5)

    response = requests.get(
        product_url,
        headers=HEADERS,
        timeout=10
    )

    # Only HTTP 200 is considered successful
    if response.status_code != 200:
        raise RuntimeError(
            f"Book fetch failed: HTTP {response.status_code} "
            f"for {product_url}"
        )

    html = response.content

    os.makedirs(BOOK_CACHE_DIR, exist_ok=True)

    with open(cache_file, "wb") as file:
        file.write(html)

    return html


def extract_book(product_url, source_page):
    html = fetch_book_page(product_url)

    soup = BeautifulSoup(html, "html.parser")

    # Limit extraction to the product area
    product = soup.select_one("article.product_page")

    if product is None:
        raise RuntimeError(
            f"Product area not found: {product_url}"
        )

    # Title
    title_element = product.select_one("h1")

    title = (
        title_element.get_text(strip=True)
        if title_element
        else None
    )

    # Price
    price_element = product.select_one(".price_color")

    price_text = (
        price_element.get_text(" ", strip=True)
        if price_element
        else None
    )

    # Availability
    availability_element = product.select_one(".availability")

    availability_text = (
        availability_element.get_text(" ", strip=True)
        if availability_element
        else None
    )

    # Rating
    rating_element = product.select_one(".star-rating")

    rating_text = None

    if rating_element:
        classes = rating_element.get("class", [])

        for rating in ["One", "Two", "Three", "Four", "Five"]:
            if rating in classes:
                rating_text = rating
                break

    # Description
    description = None

    description_heading = product.select_one(
        "#product_description"
    )

    if description_heading:
        description_element = description_heading.find_next_sibling("p")

        if description_element:
            description = description_element.get_text(
                " ",
                strip=True
            )

    # Provenance timestamp
    fetched_at = datetime.now(timezone.utc).isoformat()

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at
    }


def extract_all_books(book_links, book_sources):
    records = []

    for product_url in sorted(book_links):
        source_page = book_sources[product_url]

        record = extract_book(
            product_url,
            source_page
        )

        records.append(record)

    return records


if __name__ == "__main__":
    # Stage 2: discover the 60 unique book URLs
    book_links, book_sources = discover_pages()

    # Stage 3: extract details from every book
    records = extract_all_books(
        book_links,
        book_sources
    )

    # Stage 3 checkpoint
    print(f"unique_urls={len(book_links)}")

    # Print one complete raw record
    if records:
        print(
            json.dumps(
                records[0],
                indent=2,
                ensure_ascii=False
            )
        )
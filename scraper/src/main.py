import os
import time
import json
import requests

from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional


BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"

CACHE_DIR = "cache"
BOOK_CACHE_DIR = os.path.join(CACHE_DIR, "books")
OUTPUT_DIR = "output"

HEADERS = {
    "User-Agent": "FlyRankInternship A9/1.0 (+https://github.com/asmaebihkak24/polite-scraper)"
}


# ============================================================
# Stage 4 - Schema
# ============================================================

class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: Optional[str]
    price_gbp: Optional[float]
    availability_text: Optional[str]
    rating_text: Optional[str]
    description: Optional[str]
    source_page: HttpUrl
    fetched_at: str


# ============================================================
# Stage 5 - Run statistics
# ============================================================

stats = {
    "pages_fetched": 0,
    "cache_hits": 0,
    "valid_records": 0,
    "invalid_records": 0,
    "failed_pages": 0
}


failed_pages = []


# ============================================================
# Cache helpers
# ============================================================

def cache_path(page_number):
    return os.path.join(
        CACHE_DIR,
        f"catalogue-page-{page_number}.html"
    )


def book_cache_path(product_url):
    filename = product_url.rstrip("/").split("/")[-2]

    return os.path.join(
        BOOK_CACHE_DIR,
        f"{filename}.html"
    )


# ============================================================
# Stage 5 - Fetch with retry
# ============================================================

def fetch_url(url, cache_file=None, label="page"):
    """
    Fetch one URL politely.

    - Uses cache when available.
    - Retries once for timeout and 5xx.
    - Does NOT retry 403 or 404.
    """

    # --------------------------------------------------------
    # Cache
    # --------------------------------------------------------

    if cache_file and os.path.exists(cache_file):

        with open(cache_file, "rb") as file:
            html = file.read()

        stats["cache_hits"] += 1

        print(
            f"CACHE: {label} size={len(html)} bytes"
        )

        return html

    # --------------------------------------------------------
    # Real request
    # --------------------------------------------------------

    attempts = 0
    max_attempts = 2

    while attempts < max_attempts:

        attempts += 1

        # Polite delay before a real request
        time.sleep(0.5)

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

            # ------------------------------------------------
            # Success
            # ------------------------------------------------

            if response.status_code == 200:

                html = response.content

                stats["pages_fetched"] += 1

                if cache_file:
                    os.makedirs(
                        os.path.dirname(cache_file),
                        exist_ok=True
                    )

                    with open(cache_file, "wb") as file:
                        file.write(html)

                print(
                    f"FETCH: {label} "
                    f"size={len(html)} bytes"
                )

                return html

            # ------------------------------------------------
            # 404 / 403
            # No retry
            # ------------------------------------------------

            if response.status_code in (403, 404):

                raise RuntimeError(
                    f"HTTP {response.status_code}"
                )

            # ------------------------------------------------
            # 5xx
            # Retry once
            # ------------------------------------------------

            if 500 <= response.status_code <= 599:

                if attempts < max_attempts:

                    print(
                        f"RETRY: {label} "
                        f"HTTP {response.status_code}"
                    )

                    time.sleep(1)

                    continue

                raise RuntimeError(
                    f"HTTP {response.status_code}"
                )

            # ------------------------------------------------
            # Other HTTP errors
            # ------------------------------------------------

            raise RuntimeError(
                f"HTTP {response.status_code}"
            )

        # ----------------------------------------------------
        # Timeout
        # Retry once
        # ----------------------------------------------------

        except requests.exceptions.Timeout:

            if attempts < max_attempts:

                print(
                    f"RETRY: {label} timeout"
                )

                time.sleep(1)

                continue

            raise RuntimeError(
                "Request timed out after retry"
            )

        except requests.exceptions.RequestException as error:

            raise RuntimeError(
                f"Request failed: {error}"
            )

    raise RuntimeError(
        f"Failed to fetch {url}"
    )


# ============================================================
# Stage 2 - Discover catalogue pages
# ============================================================

def discover_pages():

    current_url = BASE_URL
    page_number = 1

    catalogue_pages = 0

    book_links = set()
    book_sources = {}

    while current_url:

        cache_file = cache_path(page_number)

        try:

            html = fetch_url(
                current_url,
                cache_file,
                f"page={page_number}"
            )

        except RuntimeError as error:

            stats["failed_pages"] += 1

            failed_pages.append({
                "url": current_url,
                "reason": str(error)
            })

            print(
                f"FAILED: page={page_number} "
                f"{error}"
            )

            break

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # Find books
        for link in soup.select(
            "article.product_pod h3 a"
        ):

            href = link.get("href")

            if href:

                absolute_url = urljoin(
                    current_url,
                    href
                )

                book_links.add(
                    absolute_url
                )

                book_sources[
                    absolute_url
                ] = current_url

        catalogue_pages += 1

        # Find next page
        next_link = soup.select_one(
            "li.next a"
        )

        if (
            page_number < 3
            and next_link
            and next_link.get("href")
        ):

            current_url = urljoin(
                current_url,
                next_link["href"]
            )

            page_number += 1

        else:

            current_url = None

    print(
        f"catalogue_pages={catalogue_pages}"
    )

    print(
        f"discovered={len(book_links)}"
    )

    return book_links, book_sources


# ============================================================
# Stage 3 - Extract book
# ============================================================

def extract_book(product_url, source_page):

    cache_file = book_cache_path(
        product_url
    )

    try:

        html = fetch_url(
            product_url,
            cache_file,
            "book"
        )

    except RuntimeError as error:

        stats["failed_pages"] += 1

        failed_pages.append({
            "url": product_url,
            "reason": str(error)
        })

        print(
            f"FAILED: book={product_url} "
            f"{error}"
        )

        return None

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    product = soup.select_one(
        "article.product_page"
    )

    if product is None:

        stats["failed_pages"] += 1

        failed_pages.append({
            "url": product_url,
            "reason": "Product area not found"
        })

        print(
            f"FAILED: product area not found: "
            f"{product_url}"
        )

        return None

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title_element = product.select_one("h1")

    title = (
        title_element.get_text(strip=True)
        if title_element
        else None
    )

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    price_element = product.select_one(
        ".price_color"
    )

    price_text = (
        price_element.get_text(
            " ",
            strip=True
        )
        if price_element
        else None
    )

    # --------------------------------------------------------
    # Availability
    # --------------------------------------------------------

    availability_element = product.select_one(
        ".availability"
    )

    availability_text = (
        availability_element.get_text(
            " ",
            strip=True
        )
        if availability_element
        else None
    )

    # --------------------------------------------------------
    # Rating
    # --------------------------------------------------------

    rating_element = product.select_one(
        ".star-rating"
    )

    rating_text = None

    if rating_element:

        classes = rating_element.get(
            "class",
            []
        )

        for rating in [
            "One",
            "Two",
            "Three",
            "Four",
            "Five"
        ]:

            if rating in classes:

                rating_text = rating
                break

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    description = None

    description_heading = product.select_one(
        "#product_description"
    )

    if description_heading:

        description_element = (
            description_heading
            .find_next_sibling("p")
        )

        if description_element:

            description = (
                description_element
                .get_text(
                    " ",
                    strip=True
                )
            )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    fetched_at = (
        datetime.now(timezone.utc)
        .isoformat()
    )

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


# ============================================================
# Stage 3 - Extract all books
# ============================================================

def extract_all_books(
    book_links,
    book_sources
):

    records = []

    for product_url in sorted(book_links):

        source_page = book_sources[
            product_url
        ]

        record = extract_book(
            product_url,
            source_page
        )

        if record is not None:

            records.append(record)

    return records


# ============================================================
# Stage 4 - Normalize price
# ============================================================

def normalize_price(price_text):

    if price_text is None:
        return None

    cleaned = (
        price_text
        .replace("£", "")
        .strip()
    )

    try:

        return float(cleaned)

    except ValueError:

        return None


# ============================================================
# Stage 4 - Validate and store
# ============================================================

def validate_and_store(records):

    good_records = []
    errors = []

    seen_urls = set()

    for record in records:

        # Normalize price
        record["price_gbp"] = normalize_price(
            record.get("price_text")
        )

        product_url = record.get(
            "product_url"
        )

        # Deduplicate by canonical URL
        if product_url in seen_urls:
            continue

        seen_urls.add(product_url)

        try:

            validated = BookRecord.model_validate(
                record
            )

            good_records.append(
                validated.model_dump(
                    mode="json"
                )
            )

        except ValidationError as error:

            errors.append({
                "record": record,
                "reason": str(error)
            })

    stats["valid_records"] = len(
        good_records
    )

    stats["invalid_records"] = len(
        errors
    )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # Good records
    with open(
        os.path.join(
            OUTPUT_DIR,
            "books.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            good_records,
            file,
            indent=2,
            ensure_ascii=False
        )

    # Invalid records
    with open(
        os.path.join(
            OUTPUT_DIR,
            "errors.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            errors,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"valid={len(good_records)}"
    )

    print(
        f"errors={len(errors)}"
    )


# ============================================================
# Stage 5 - Run report
# ============================================================

def write_run_report(
    start_time,
    duration
):

    report = {
        "start_time": start_time,
        "duration_seconds": round(
            duration,
            3
        ),
        "pages_fetched": stats[
            "pages_fetched"
        ],
        "cache_hits": stats[
            "cache_hits"
        ],
        "valid_records": stats[
            "valid_records"
        ],
        "invalid_records": stats[
            "invalid_records"
        ],
        "failed_pages": stats[
            "failed_pages"
        ],
        "failed_page_details": failed_pages
    }

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    with open(
        os.path.join(
            OUTPUT_DIR,
            "run-report.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"failed_pages={stats['failed_pages']}"
    )

    print(
        "Run report written to "
        "output/run-report.json"
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    start_datetime = datetime.now(
        timezone.utc
    )

    start_time = start_datetime.isoformat()

    start_timestamp = time.perf_counter()

    # --------------------------------------------------------
    # Stage 2
    # --------------------------------------------------------

    book_links, book_sources = (
        discover_pages()
    )

    # --------------------------------------------------------
    # Stage 5 TEST
    #
    # Add ONE fake URL deliberately.
    # It should return 404 and therefore fail
    # without being retried.
    # --------------------------------------------------------


    # --------------------------------------------------------
    # Stage 3
    # --------------------------------------------------------

    records = extract_all_books(
        book_links,
        book_sources
    )

    print(
        f"unique_urls={len(book_links)}"
    )

    # --------------------------------------------------------
    # Stage 4
    # --------------------------------------------------------

    if records:

        print(
            json.dumps(
                records[0],
                indent=2,
                ensure_ascii=False
            )
        )

    validate_and_store(
        records
    )

    # --------------------------------------------------------
    # Stage 5 report
    # --------------------------------------------------------

    duration = (
        time.perf_counter()
        - start_timestamp
    )

    write_run_report(
        start_time,
        duration
    )
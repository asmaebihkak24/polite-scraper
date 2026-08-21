# Polite Scraper

A small, polite Python scraper built for the FlyRank Internship A9 assignment.

## Target Classification

- **Target Site:** Books to Scrape (https://books.toscrape.com/)
- **Why:** It is a public sandbox site built specifically for practicing web scraping.
- **Scope:** The first 3 catalogue pages only, containing 60 books.
- **Data Collected:** Book titles, product URLs, raw price text, numeric prices (GBP), availability status, ratings, optional descriptions, source page provenance, and fetch timestamps.
- **Appropriateness:** The project is limited to the site's public catalogue and collects only the data required for the assignment.

I will not reuse this scraper on another site without checking its rules and terms first.

## Lane

- **Language:** Python
- **Parser:** Beautiful Soup
- **HTTP client:** Requests
- **Validation:** Pydantic

## Installation

Clone the repository and install the dependencies:

```bash
pip install -r requirements.txt

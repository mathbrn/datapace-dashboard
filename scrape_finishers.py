#!/usr/bin/env python3
"""
Scrape finisher counts from race results websites using Playwright.
Intercepts API calls made by SPAs to extract the actual data.

Supports: Sporthive/MYLAPS, Mikatiming, Sportmaniacs, TimeTo, generic.

Usage:
    python scrape_finishers.py <URL>
    python scrape_finishers.py "https://results.sporthive.com/events/7113512886511920128"
    python scrape_finishers.py "https://berlinerhm.r.mikatiming.de/2022/"
    python scrape_finishers.py "https://sportmaniacs.com/en/races/edp-media-maraton-de-sevilla-2017/xxx/results"

Output: prints the number of finishers found.
"""
import sys
import json
import re
from playwright.sync_api import sync_playwright


def extract_finishers_from_page(url, timeout=30000):
    """Visit a results page, intercept API calls, extract finisher count."""

    api_responses = []
    finisher_count = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Intercept all API responses
        def handle_response(response):
            url_lower = response.url.lower()
            content_type = response.headers.get("content-type", "")

            # Only capture JSON API responses
            if "json" in content_type or "api" in url_lower:
                try:
                    body = response.text()
                    if len(body) > 50:  # Skip tiny responses
                        api_responses.append({
                            "url": response.url,
                            "status": response.status,
                            "size": len(body),
                            "body": body[:50000]  # Limit size
                        })
                except:
                    pass

        page.on("response", handle_response)

        try:
            page.goto(url, wait_until="networkidle", timeout=timeout)
            # Wait a bit more for lazy-loaded data
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"WARN: Page load issue: {e}", file=sys.stderr)

        # Also try to extract from the rendered page
        try:
            page_text = page.content()
        except:
            page_text = ""

        browser.close()

    # Analyze captured API responses
    print(f"\nIntercepted {len(api_responses)} API responses:", file=sys.stderr)

    for resp in api_responses:
        print(f"  [{resp['status']}] {resp['url'][:120]} ({resp['size']} bytes)", file=sys.stderr)

        try:
            data = json.loads(resp["body"])
        except:
            continue

        # Strategy 1: Look for total/count fields
        count = find_count_in_json(data, resp["url"])
        if count and count > 100:
            if finisher_count is None or count > finisher_count:
                finisher_count = count
                print(f"  -> Found count: {count} from {resp['url'][:80]}", file=sys.stderr)

    # Strategy 2: Parse rendered page for result counts
    if finisher_count is None:
        page_count = find_count_in_html(page_text)
        if page_count:
            finisher_count = page_count
            print(f"  -> Found count from HTML: {page_count}", file=sys.stderr)

    return finisher_count, api_responses


def find_count_in_json(data, url=""):
    """Extract finisher count from various JSON structures."""

    # Direct array of results
    if isinstance(data, list) and len(data) > 10:
        # Check if items look like race results
        if len(data) > 0 and isinstance(data[0], dict):
            keys = set(data[0].keys())
            result_keys = {"rank", "place", "bib", "name", "time", "firstName", "lastName",
                          "generalRanking", "officialTime", "realTime", "chipTime",
                          "gunTime", "netTime", "position", "dorsal"}
            if keys & result_keys:
                return len(data)

    if not isinstance(data, dict):
        return None

    # Common patterns for total count
    for key in ["total", "totalResults", "totalCount", "count", "nbResults",
                "participants_actual", "finishers", "totalFinishers",
                "recordsTotal", "recordsFiltered", "numResults", "totalRecords",
                "pagination.total", "meta.total", "total_entries"]:
        parts = key.split(".")
        obj = data
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                obj = None
                break
        if obj and isinstance(obj, (int, float)) and obj > 10:
            return int(obj)

    # Look for results array
    for key in ["results", "data", "items", "entries", "runners", "athletes",
                "resultList", "rankings", "clasificacion"]:
        if key in data and isinstance(data[key], list) and len(data[key]) > 10:
            arr = data[key]
            if len(arr) > 0 and isinstance(arr[0], dict):
                return len(arr)

    # Sporthive specific: ssrResultsData
    if "ssrResultsData" in data:
        ssr = data["ssrResultsData"]
        if isinstance(ssr, dict):
            total = ssr.get("total") or ssr.get("totalResults")
            if total and int(total) > 0:
                return int(total)

    # Mikatiming specific: look for pagination info
    if "pages" in data and "total" in data:
        return int(data["total"])

    # Nested search (1 level deep)
    for key, val in data.items():
        if isinstance(val, dict):
            for subkey in ["total", "count", "totalResults", "nbResults"]:
                if subkey in val and isinstance(val[subkey], (int, float)) and val[subkey] > 10:
                    return int(val[subkey])

    return None


def find_count_in_html(html):
    """Try to extract finisher count from rendered HTML."""
    if not html:
        return None

    # Look for patterns like "12,345 results" or "12345 clasificados"
    patterns = [
        r'([\d.,]+)\s*(?:results|résultats|resultados|clasificados|finishers|Finisher|Ergebnisse)',
        r'(?:Total|Gesamt|total)\s*:?\s*([\d.,]+)',
        r'(\d[\d.,]*)\s*(?:participants|teilnehmer|coureurs|runners|atletas)',
        r'(?:of|von|de|sur)\s+([\d.,]+)\s*(?:results|résultats)',
        r'Page\s+\d+\s+(?:of|von|de|sur)\s+([\d.,]+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for m in matches:
            try:
                num = int(m.replace(",", "").replace(".", "").replace(" ", ""))
                if num > 100:
                    return num
            except:
                continue

    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    print(f"Scraping: {url}", file=sys.stderr)

    count, responses = extract_finishers_from_page(url)

    if count:
        print(f"\n=== FINISHERS: {count} ===")
    else:
        print(f"\n=== FINISHERS: NOT FOUND ===")
        print("\nCaptured API URLs (try fetching manually):")
        for r in responses:
            if r["size"] > 200:
                print(f"  {r['url']}")

#!/usr/bin/env python3
"""
Scrape finisher counts from Great Run results website.
Uses Playwright to interact with the form and extract total result counts.

Usage:
    python scrape_greatrun.py
"""
from playwright.sync_api import sync_playwright
import re
import json
import sys

# All Great Run events we care about with their IDs
EVENTS = {
    # Great North Run (Half Marathon)
    "AJ Bell Great North Run": {
        "distance": "SEMI",
        "ids": {
            2008: 328, 2009: 380, 2010: 465, 2011: 553, 2012: 609,
            2013: 669, 2014: 723, 2015: 793, 2016: 870, 2017: 918,
            2018: 974, 2019: 1047, 2021: 1099, 2022: 1130, 2023: 1190,
            2024: 1252, 2025: 1324,
        }
    },
    # Great Scottish Run Half Marathon
    "Great Scottish Run": {
        "distance": "SEMI",
        "ids": {
            2013: 669,  # Need to find correct IDs from legacy site
            2022: 1137, 2023: 1196, 2024: 1261, 2025: 1309,
        }
    },
    # Great Manchester Run Half Marathon
    "AJ Bell Great Manchester Run": {
        "distance": "SEMI",
        "ids": {
            2021: 1089, 2022: 1117, 2023: 1187, 2024: 1229, 2025: 1293,
        }
    },
    # Great Bristol Half Marathon
    "AJ Bell Great Bristol Run": {
        "distance": "SEMI",
        "ids": {
            2021: 1085, 2022: 1125, 2023: 1184, 2024: 1226, 2025: 1290,
        }
    },
}


def get_finisher_count(page, event_id, timeout=15000):
    """Get total finisher count for an event by searching and reading pagination."""
    try:
        page.goto('https://results.greatrun.org/results', wait_until='networkidle', timeout=timeout)
        page.wait_for_timeout(1000)

        # Select event in simple search dropdown
        page.select_option('#SearchRace', str(event_id))
        page.wait_for_timeout(500)

        # Search for a very common surname to get results
        page.fill('#Search_SearchTerms_Surname', 'a')
        page.wait_for_timeout(200)

        # Submit
        page.click('#searchSimpleForm button[type="submit"]')
        page.wait_for_timeout(4000)

        # Get page text
        text = page.inner_text('body')

        # Look for total count patterns
        # Pattern: "Showing 1 to 25 of 12345 results"
        match = re.search(r'Showing\s+\d+\s+to\s+\d+\s+of\s+([\d,]+)', text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))

        # Pattern: "12345 results found"
        match = re.search(r'([\d,]+)\s+results?\s+found', text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))

        # Pattern: "Results (12345)"
        match = re.search(r'Results?\s*\(\s*([\d,]+)\s*\)', text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))

        # Count result rows if we can see them
        rows = page.query_selector_all('table tbody tr')
        if len(rows) > 0:
            # Check for pagination - look for last page number
            page_links = re.findall(r'page[=\s]+(\d+)', text, re.IGNORECASE)
            last_page_links = page.query_selector_all('a[href*="page"]')

            # If no pagination info, return row count as minimum
            return f"~{len(rows)}+ (partial, check manually)"

        return None

    except Exception as e:
        return f"ERROR: {str(e)[:80]}"


def main():
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        for event_name, event_info in EVENTS.items():
            print(f"\n=== {event_name} ({event_info['distance']}) ===")
            for year, eid in sorted(event_info["ids"].items()):
                count = get_finisher_count(page, eid)
                print(f"  {year}: {count}")
                if isinstance(count, int):
                    results[f"{event_name}|{event_info['distance']}|{year}"] = count

        browser.close()

    # Print summary
    print("\n\n=== SUMMARY ===")
    for key, count in sorted(results.items()):
        parts = key.split("|")
        print(f"python update_finishers.py \"{parts[0]}\" \"{parts[1]}\" {parts[2]} {count}")

    return results


if __name__ == "__main__":
    main()

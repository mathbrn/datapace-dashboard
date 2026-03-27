#!/usr/bin/env python3
"""
Scrape partner pages for all events using Playwright.
Extracts brand names from logos (alt text) and page structure.
Outputs to scraped_partners.json for review before importing.

Usage:
    python scrape_partners.py              # Scrape all pages with partners_page
    python scrape_partners.py --event "TCS London Marathon"  # Scrape single event
    python scrape_partners.py --batch 1    # Scrape batch 1 (first 34 events)
"""
import sys
import io
import json
import time
import re
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
WEBSITES_FILE = SCRIPT_DIR / "event_websites.json"
OUTPUT_FILE = SCRIPT_DIR / "scraped_partners.json"
SPONSORING_FILE = SCRIPT_DIR / "sponsoring_data.json"


def extract_partners_from_page(page):
    """Extract partner/sponsor names from a page using multiple strategies."""
    partners = []
    seen = set()

    # Strategy 1: Image alt texts containing "partner", "sponsor", "partenaire", brand-like names
    images = page.query_selector_all('img')
    for img in images:
        alt = (img.get_attribute('alt') or '').strip()
        src = (img.get_attribute('src') or '').lower()
        title = (img.get_attribute('title') or '').strip()

        # Skip navigation, UI, and generic images
        skip_words = ['logo', 'icon', 'arrow', 'menu', 'flag', 'cookie', 'banner',
                      'hero', 'slider', 'background', 'facebook', 'twitter', 'instagram',
                      'youtube', 'linkedin', 'email', 'phone', 'map', 'close', 'search',
                      'dossard', 'medal', 'route', 'parcours', 'course', 'runner', 'coureur']

        if alt and len(alt) > 2:
            alt_lower = alt.lower()
            if any(sw in alt_lower for sw in skip_words) and 'partenaire' not in alt_lower and 'sponsor' not in alt_lower:
                continue

            # Clean up common prefixes
            clean = alt
            for prefix in ['Partenaire ', 'Partner ', 'Sponsor ', 'Logo ', 'logo ', 'Official ']:
                if clean.startswith(prefix):
                    clean = clean[len(prefix):]

            clean = clean.strip()
            if clean and clean.lower() not in seen and len(clean) > 1:
                seen.add(clean.lower())
                partners.append(clean)

        # Also check title attribute
        if title and title.lower() not in seen and len(title) > 2:
            title_lower = title.lower()
            if not any(sw in title_lower for sw in skip_words):
                seen.add(title_lower)
                partners.append(title)

    # Strategy 2: Look for headings that indicate partner categories
    categories = {}
    current_cat = "Unknown"

    headings = page.query_selector_all('h1, h2, h3, h4, h5, [class*="title"], [class*="heading"]')
    for h in headings:
        text = h.inner_text().strip()
        text_lower = text.lower()
        if any(kw in text_lower for kw in ['partenaire', 'sponsor', 'partner', 'fournisseur',
                                            'supplier', 'premium', 'officiel', 'official',
                                            'titre', 'title', 'majeur', 'major', 'media']):
            current_cat = text
            if current_cat not in categories:
                categories[current_cat] = []

            # Find nearby images/links
            parent = h.evaluate_handle('el => el.parentElement')
            if parent:
                nearby_imgs = parent.query_selector_all('img')
                for img in nearby_imgs:
                    alt = (img.get_attribute('alt') or '').strip()
                    if alt and len(alt) > 2:
                        clean = alt
                        for prefix in ['Partenaire ', 'Partner ', 'Sponsor ', 'Logo ']:
                            if clean.startswith(prefix):
                                clean = clean[len(prefix):]
                        clean = clean.strip()
                        if clean:
                            categories[current_cat].append(clean)

    return partners, categories


def scrape_event(event_name, url, timeout=15000):
    """Scrape a single event's partner page."""
    from playwright.sync_api import sync_playwright

    result = {
        "event": event_name,
        "url": url,
        "partners": [],
        "categories": {},
        "error": None,
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)  # Wait for lazy-loaded content

            partners, categories = extract_partners_from_page(page)
            result["partners"] = partners
            result["categories"] = {k: v for k, v in categories.items() if v}

            browser.close()
    except Exception as e:
        result["error"] = str(e)[:200]

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--event', type=str, help='Scrape single event by name')
    parser.add_argument('--batch', type=int, help='Batch number (1-4, ~34 events each)')
    parser.add_argument('--limit', type=int, default=0, help='Max events to scrape')
    args = parser.parse_args()

    with open(WEBSITES_FILE, 'r', encoding='utf-8') as f:
        websites = json.load(f)

    with open(SPONSORING_FILE, 'r', encoding='utf-8') as f:
        sponsoring = json.load(f)

    # Filter events with partner pages
    events_to_scrape = []
    for name, info in websites.items():
        if info.get('partners_page'):
            events_to_scrape.append((name, info['partners_page']))

    if args.event:
        events_to_scrape = [(n, u) for n, u in events_to_scrape if args.event.lower() in n.lower()]
    elif args.batch:
        batch_size = len(events_to_scrape) // 4 + 1
        start = (args.batch - 1) * batch_size
        events_to_scrape = events_to_scrape[start:start + batch_size]

    if args.limit:
        events_to_scrape = events_to_scrape[:args.limit]

    print(f"Scraping {len(events_to_scrape)} partner pages...")
    print()

    # Load existing results if any
    existing = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing_list = json.load(f)
            for item in existing_list:
                existing[item['event']] = item

    results = list(existing.values())
    existing_events = set(existing.keys())

    for i, (name, url) in enumerate(events_to_scrape):
        if name in existing_events:
            print(f"[{i+1}/{len(events_to_scrape)}] SKIP (already scraped): {name}")
            continue

        print(f"[{i+1}/{len(events_to_scrape)}] Scraping: {name}")
        print(f"  URL: {url[:80]}")

        result = scrape_event(name, url)

        if result['error']:
            print(f"  ERROR: {result['error'][:80]}")
        else:
            print(f"  Found {len(result['partners'])} partners")
            if result['categories']:
                for cat, brands in result['categories'].items():
                    print(f"    {cat}: {brands[:5]}")

        results.append(result)
        time.sleep(1)  # Rate limiting

    # Save results
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    total = len(results)
    success = sum(1 for r in results if not r.get('error'))
    with_partners = sum(1 for r in results if r.get('partners'))
    total_partners = sum(len(r.get('partners', [])) for r in results)

    print(f"\n{'='*50}")
    print(f"Scraped: {total} pages ({success} success)")
    print(f"With partners: {with_partners}")
    print(f"Total partner names found: {total_partners}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

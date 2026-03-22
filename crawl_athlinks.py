#!/usr/bin/env python3
"""Crawl Athlinks master events to find all US races with finisher data."""
import json, urllib.request, ssl, os, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_META = 'https://reignite-api.athlinks.com/master'
API_COURSE = 'https://alaska.athlinks.com/Events/Race/Api'
OUT = os.path.join(os.path.dirname(__file__), 'athlinks_crawl_results.json')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=12) as r:
        return json.loads(r.read().decode('utf-8'))

results = []
if os.path.exists(OUT):
    with open(OUT, 'r', encoding='utf-8') as f:
        results = json.load(f)
    print(f'Loaded {len(results)} existing')

seen_masters = set(r.get('master_id') for r in results)

# Known big race master IDs + scan range for discovery
known_ids = [
    115192,  # Peachtree Road Race
    6172,    # BOLDERBoulder
    9036,    # Cooper River Bridge Run
    22497,   # Boilermaker
    34523,   # Manchester Road Race
    168976,  # Broad Street Run
    25485,   # Falmouth Road Race
    21991,   # Gate River Run
    18246,   # Bay to Breakers
    20564,   # Portland Marathon
]

# Also scan ranges to discover new races
scan_ranges = list(range(1000, 5000, 100)) + list(range(5000, 50000, 500)) + list(range(50000, 200000, 2000))

all_ids = known_ids + [mid for mid in scan_ranges if mid not in known_ids]

for mid in all_ids:
    if mid in seen_masters:
        continue
    try:
        meta = fetch(f'{API_META}/{mid}/metadata')
        name = meta.get('name', '')
        city = meta.get('city', '')
        events = meta.get('events', [])
        if not events or not name:
            continue

        # Get finisher counts for recent events
        for ev in events[:5]:  # last 5 years
            ev_id = ev.get('id')
            start = ev.get('start', {})
            if not ev_id:
                continue
            # Extract year
            year = None
            if isinstance(start, dict) and 'epoch' in start:
                epoch = start['epoch']
                if epoch > 1e12:
                    epoch = epoch / 1000
                from datetime import datetime
                try:
                    year = datetime.fromtimestamp(epoch).year
                except:
                    continue
            if not year or year < 2018:
                continue

            try:
                course_data = fetch(f'{API_COURSE}/{ev_id}/Course/0')
                courses = course_data.get('Result', {}).get('EventCoursesDropDown', [])
                total = 0
                for c in courses:
                    text = c.get('Text', '')
                    parts = c.get('Value', '').split(':')
                    if len(parts) >= 3 and 'virtual' not in text.lower():
                        total += int(parts[2])
                if total >= 100:
                    results.append({
                        'source': 'athlinks', 'master_id': mid,
                        'event_name': name, 'city': city,
                        'year': year, 'event_id': ev_id,
                        'finishers': total,
                    })
                    seen_masters.add(mid)
                    print(f'FOUND mid={mid}: {name} ({city}) {year} = {total:,} finishers', flush=True)
                    break  # Found data, move to next master
            except:
                pass
    except:
        pass

    # Save periodically
    if len(results) % 20 == 0 and results:
        with open(OUT, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

# Final save
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

total_fin = sum(r['finishers'] for r in results)
print(f'\nDone: {len(results)} races, {len(seen_masters)} masters, {total_fin:,} finishers')

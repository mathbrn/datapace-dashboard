#!/usr/bin/env python3
"""
Aggregator: merge all crawled data into a unified database.
Combines Sporthive, Tracx, Athlinks, and other sources.

Output: unified_race_database.json
"""
import json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DIR = os.path.dirname(__file__)
OUT = os.path.join(DIR, 'unified_race_database.json')

def load_json(filename):
    path = os.path.join(DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load all sources
sporthive = load_json('sporthive_crawl_results.json')
tracx = load_json('tracx_crawl_results.json')
athlinks = load_json('athlinks_crawl_results.json')

print(f'Sources loaded:')
print(f'  Sporthive: {len(sporthive)} races')
print(f'  Tracx: {len(tracx)} races')
print(f'  Athlinks: {len(athlinks)} races')

# Normalize into unified format
unified = []

for r in sporthive:
    unified.append({
        'source': 'sporthive',
        'event_name': r.get('race_name', ''),
        'distance_m': r.get('distance_m', 0),
        'date': r.get('date', ''),
        'year': int(r.get('date', '0000')[:4]) if r.get('date') else 0,
        'finishers': r.get('finishers', 0),
        'avg_time': r.get('avg_time'),
        'country': '',
    })

for r in tracx:
    unified.append({
        'source': 'tracx',
        'event_name': f"{r.get('event_name', '')} - {r.get('race_name', '')}",
        'distance_m': r.get('distance_m', 0),
        'date': r.get('date', ''),
        'year': int(r.get('date', '0000')[:4]) if r.get('date') else 0,
        'finishers': r.get('finishers', 0),
        'avg_time': None,
        'country': '',
    })

for r in athlinks:
    unified.append({
        'source': 'athlinks',
        'event_name': r.get('event_name', ''),
        'distance_m': 0,
        'date': '',
        'year': r.get('year', 0),
        'finishers': r.get('finishers', 0),
        'avg_time': None,
        'country': 'US',
    })

# Filter: only road running distances (5K to Marathon)
road = [r for r in unified if r['finishers'] >= 100]

# Stats
total_fin = sum(r['finishers'] for r in road)
unique_events = len(set(r['event_name'] for r in road))
years = set(r['year'] for r in road if r['year'])

print(f'\nUnified database:')
print(f'  Total races: {len(road)}')
print(f'  Total finishers: {total_fin:,}')
print(f'  Unique event names: {unique_events}')
print(f'  Year range: {min(years) if years else "?"}-{max(years) if years else "?"}')

# By source
from collections import Counter
sources = Counter(r['source'] for r in road)
print(f'\n  By source:')
for s, c in sources.most_common():
    fin = sum(r['finishers'] for r in road if r['source'] == s)
    print(f'    {s}: {c} races, {fin:,} finishers')

# By distance category
def dist_cat(d):
    if d == 0: return 'Unknown'
    if 4000 <= d <= 6000: return '5K'
    if 9000 <= d <= 11000: return '10K'
    if 15000 <= d <= 17000: return '10Mile/16K'
    if 20000 <= d <= 22000: return 'Half Marathon'
    if 41000 <= d <= 43000: return 'Marathon'
    return f'{d//1000}K'

cats = Counter(dist_cat(r['distance_m']) for r in road)
print(f'\n  By distance:')
for c, n in cats.most_common():
    print(f'    {c}: {n} races')

# Top events
top = sorted(road, key=lambda x: -x['finishers'])[:20]
print(f'\n  Top 20 by finishers:')
for r in top:
    print(f'    {r["finishers"]:>8,} | {r["event_name"][:50]} | {r["year"]} | {r["source"]}')

# Save
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(road, f, indent=2, ensure_ascii=False)
print(f'\nSaved to {OUT}')

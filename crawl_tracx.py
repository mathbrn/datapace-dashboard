#!/usr/bin/env python3
"""Crawl ALL 860 Tracx events and extract race data."""
import json, urllib.request, ssl, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TOKEN = 'Bearer 40496C26-9BEF-4266-8A27-43C78540F669'
API = 'https://api.tracx.events/v1'
OUT = os.path.join(os.path.dirname(__file__), 'tracx_crawl_results.json')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api_get(path):
    req = urllib.request.Request(f'{API}/{path}', headers={
        'Authorization': TOKEN, 'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))

results = []
if os.path.exists(OUT):
    with open(OUT, 'r', encoding='utf-8') as f:
        results = json.load(f)
    print(f'Loaded {len(results)} existing')

seen = set(r.get('event_id') for r in results)
page = 1
total_pages = 58

while page <= total_pages:
    try:
        data = api_get(f'events?page={page}&per_page=15')
        events = data.get('events', [])
        total_pages = data.get('meta', {}).get('pagination', {}).get('total_pages', 58)
        for ev in events:
            eid = ev['id']
            if eid in seen:
                continue
            seen.add(eid)
            try:
                races = api_get(f'events/{eid}/races')
                for race in races:
                    dist = race.get('distance', 0)
                    count = race.get('participant_count', 0)
                    name = race.get('name', '?')
                    sport = race.get('sport', '')
                    start = str(race.get('start', ''))[:10]
                    if count >= 50 and dist >= 5000 and sport == 'running':
                        results.append({
                            'source': 'tracx', 'event_id': eid,
                            'event_name': ev.get('name', '?'),
                            'race_name': name, 'distance_m': dist,
                            'date': start, 'finishers': count,
                        })
            except:
                pass
        print(f'Page {page}/{total_pages} | events={len(seen)} | races={len(results)}', flush=True)
    except Exception as e:
        print(f'Page {page} error: {e}', flush=True)
    page += 1

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

total_fin = sum(r['finishers'] for r in results)
print(f'\nDone: {len(results)} races, {len(seen)} events, {total_fin:,} finishers')

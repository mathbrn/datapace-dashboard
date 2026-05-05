#!/usr/bin/env python3
"""
Auto Update 4D — J+1 automatic data fetcher for ASO Dashboard

Workflow:
1. Query World Athletics for yesterday's road races
2. Match against our events (datapace.db or Excel)
3. Route to platform-specific fetchers (Sporthive, TimeTo, Tracx, ChronoRace, RTRT, Athlinks)
4. Update 4D data: finishers, avg_time, winner_men, winner_women
5. Regenerate dashboard + commit + push
6. Generate log report

Usage:
    python auto_update_4d.py [--date YYYY-MM-DD] [--dry-run]

Scheduled via .github/workflows/auto_update_4d.yml (daily 06:00 UTC).
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

# Force UTF-8 output on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import requests

SCRIPT_DIR = Path(__file__).parent
LOGS_DIR = SCRIPT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# WORLD ATHLETICS CALENDAR
# ============================================================================
WA_ENDPOINT = "https://graphql-prod-4860.edge.aws.worldathletics.org/graphql"
WA_API_KEY = "da2-5eqvkoavsnhjxfqd47jvjteray"

WA_QUERY = """
query getCalendarEvents($startDate: String, $endDate: String, $regionType: String, $limit: Int, $offset: Int) {
  getCalendarEvents(startDate: $startDate, endDate: $endDate, regionType: $regionType, limit: $limit, offset: $offset) {
    results { id name dateRange venue area disciplines hasResults }
  }
}
"""


def fetch_worldathletics_races(date_str, window_days=1):
    """Fetch road races with ±window_days around the given date."""
    sess = requests.Session()
    sess.headers.update({"x-api-key": WA_API_KEY, "Content-Type": "application/json"})
    target = datetime.date.fromisoformat(date_str)
    start = (target - datetime.timedelta(days=window_days)).isoformat()
    end = (target + datetime.timedelta(days=window_days)).isoformat()
    races = []
    offset = 0
    while True:
        resp = sess.post(WA_ENDPOINT, json={
            "query": WA_QUERY,
            "variables": {"startDate": start, "endDate": end,
                          "regionType": "world", "limit": 100, "offset": offset}
        }, timeout=30)
        if not resp.ok:
            print(f"  WA error: HTTP {resp.status_code}")
            break
        data = resp.json()
        hits = ((data.get("data") or {}).get("getCalendarEvents") or {}).get("results", [])
        if not hits:
            break
        races.extend(hits)
        if len(hits) < 100:
            break
        offset += 100
    print(f"  World Athletics: {len(races)} races in [{start}..{end}]")
    return races


# ============================================================================
# EVENT MATCHING
# ============================================================================
def normalize_name(s):
    """Normalize for fuzzy matching: lowercase + strip accents."""
    if not s:
        return ""
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def load_our_events():
    """Load events from dashboard data (Excel finishers file). Also attaches
    country code from event_platform_map.json when available."""
    import openpyxl
    path = SCRIPT_DIR / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["ALL"]
    # Load country map
    pmap_path = SCRIPT_DIR / "event_platform_map.json"
    country_map = {}
    if pmap_path.exists():
        with open(pmap_path, "r", encoding="utf-8") as f:
            pmap = json.load(f)
        for k, info in pmap.items():
            if info.get("country"):
                country_map[info.get("name", k).lower()] = info["country"]
    rows = []
    headers = None
    for row in ws.iter_rows(values_only=True):
        if headers is None:
            headers = list(row)
            continue
        d = dict(zip(headers, row))
        race = str(d.get("Race", "") or "").strip()
        if race:
            rows.append({
                "name": race,
                "city": str(d.get("City", "") or "").strip(),
                "distance": str(d.get("Distance", "") or "").strip(),
                "period": str(d.get("Période", "") or "").strip(),
                "country": country_map.get(race.lower()),
            })
    wb.close()
    return rows


def extract_country_code(venue):
    """Extract ISO country code from WA venue like 'Paris (FRA)'."""
    if not venue:
        return None
    m = re.search(r"\(([A-Z]{2,3})\)\s*$", venue)
    return m.group(1) if m else None


def match_wa_to_ours(wa_races, our_events):
    """Match WA races to our dashboard events by best name+city+country score."""
    # Aliases: normalized WA name → our event name (exact, score=100)
    ALIASES = {
        "tcs london marathon": "TCS London Marathon",
        "london marathon": "TCS London Marathon",
        "virgin money london marathon": "TCS London Marathon",
        "haspa marathon hamburg": "Haspa Marathon Hamburg",
        "hamburg marathon": "Haspa Marathon Hamburg",
        "haspa marathon": "Haspa Marathon Hamburg",
        "vienna city marathon": "Vienna City Marathon",
        "wien marathon": "Vienna City Marathon",
        "vienna marathon": "Vienna City Marathon",
        "volkswagen prague marathon": "Prague International Marathon",
        "orlen prague marathon": "Prague International Marathon",
        "prague marathon": "Prague International Marathon",
        "bmw berlin marathon": "BMW Berlin Marathon",
        "berlin marathon": "BMW Berlin Marathon",
        "bank of america chicago marathon": "Bank of America Chicago Marathon",
        "chicago marathon": "Bank of America Chicago Marathon",
        "tcs new york city marathon": "TCS New York City Marathon",
        "new york city marathon": "TCS New York City Marathon",
        "tokyo marathon": "Tokyo Marathon",
        "nn marathon rotterdam": "NN Marathon Rotterdam",
        "rotterdam marathon": "NN Marathon Rotterdam",
        "boston marathon": "Boston Marathon",
        "schneider electric marathon de paris": "Schneider Electric Marathon de Paris",
        "marathon de paris": "Schneider Electric Marathon de Paris",
        "edp maratona de lisboa": "EDP Maratona de Lisboa",
        "maratona de lisboa": "EDP Maratona de Lisboa",
        "tcs amsterdam marathon": "TCS Amsterdam Marathon",
        "amsterdam marathon": "TCS Amsterdam Marathon",
        "stockholm marathon": "Stockholm Marathon",
        "athens classic marathon": "Athens Classic Marathon",
        "athens marathon": "Athens Classic Marathon",
        "generali berlin half marathon": "Generali Berlin Half Marathon",
        "berlin half marathon": "Generali Berlin Half Marathon",
        "brighton marathon": "Brighton Marathon",
        "mainova frankfurt marathon": "Mainova Frankfurt Marathon",
        "frankfurt marathon": "Mainova Frankfurt Marathon",
        "adidas manchester marathon": "Adidas Manchester Marathon",
        "manchester marathon": "Adidas Manchester Marathon",
        "great north run": "AJ Bell Great North Run",
        "aj bell great north run": "AJ Bell Great North Run",
        "great manchester run": "AJ Bell Great Manchester Run",
        "aj bell great manchester run": "AJ Bell Great Manchester Run",
        "great bristol run": "AJ Bell Great Bristol Run",
        "aj bell great bristol run": "AJ Bell Great Bristol Run",
        "hoka semi de paris": "HOKA Semi de Paris",
        "semi de paris": "HOKA Semi de Paris",
        "paris half marathon": "HOKA Semi de Paris",
        "edp lisboa meia maratona": "EDP Lisboa Meia Maratona",
        "lisboa half marathon": "EDP Lisboa Meia Maratona",
        "nn cpc loop den haag": "NN CPC Loop Den Haag - Half Marathon",
        "the half": "The Big Half",
        "big half": "The Big Half",
    }
    # Build lookup: normalized our_name → event dict
    our_by_norm = {normalize_name(ev["name"]): ev for ev in our_events}

    matches = []
    STOPWORDS = {"the", "de", "la", "le", "les", "du", "of", "a", "and", "et",
                 "marathon", "semi", "half", "run", "race", "runs", "races",
                 "10k", "21k", "42k", "10km", "city", "international"}
    for wa in wa_races:
        wa_name = normalize_name(wa.get("name", ""))
        wa_venue_raw = wa.get("venue", "") or ""
        wa_venue = normalize_name(wa_venue_raw)
        wa_country = extract_country_code(wa_venue_raw)

        # Check aliases first (exact match → score = 100, bypasses fuzzy)
        alias_target = ALIASES.get(wa_name)
        if alias_target:
            our_ev = our_by_norm.get(normalize_name(alias_target))
            if our_ev:
                matches.append({"wa": wa, "our": our_ev, "score": 100})
                continue

        wa_words = set(wa_name.split()) - STOPWORDS
        best = None
        best_score = 0
        for ev in our_events:
            our_name = normalize_name(ev["name"])
            our_city = normalize_name(ev["city"])
            our_country = ev.get("country")
            our_words = set(our_name.split()) - STOPWORDS
            common = wa_words & our_words
            score = len(common) * 10
            # City match bonus
            if our_city and wa_venue:
                if our_city == wa_venue or our_city in wa_venue or wa_venue in our_city:
                    score += 5
                elif not common:
                    continue
            # Country match (bonus/penalty)
            if our_country and wa_country:
                if our_country == wa_country:
                    score += 5
                else:
                    score -= 10  # strong penalty for country mismatch
            # Distance type match
            if "half" in wa_name and ev.get("distance") == "SEMI":
                score += 3
            elif "half" not in wa_name and "marathon" in wa_name and ev.get("distance") == "MARATHON":
                score += 3
            elif "10k" in wa_name and ev.get("distance") == "10KM":
                score += 3
            if score > best_score:
                best_score = score
                best = ev
        if best and best_score >= 20:
            matches.append({"wa": wa, "our": best, "score": best_score})
    print(f"  Matched: {len(matches)} events")
    return matches


# ============================================================================
# PLATFORM FETCHERS
# ============================================================================
def fetch_timeto_4d(event_name, year):
    """Fetch 4D from TimeTo/SportInnovation API (ASO France)."""
    try:
        sess = requests.Session()
        sess.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
        resp = sess.get("https://sportinnovation.fr/api/events", timeout=15)
        events = resp.json()
        target = None
        norm_name = normalize_name(event_name)
        for ev in events:
            # TimeTo uses 'title' (not 'name')
            ev_title = ev.get("title", "") or ev.get("name", "")
            ev_norm = normalize_name(ev_title)
            # Match first 15 chars OR last word (distinguishes Marathon/Semi/10K)
            key_words = norm_name.split()
            name_match = norm_name[:15] in ev_norm or ev_norm[:15] in norm_name
            # Need distinguishing keyword if multiple Paris events
            if name_match and str(year) in ev_title:
                # Prefer exact name match over substring
                if ev_norm == norm_name or (key_words and key_words[0] in ev_norm and key_words[-1] in ev_norm):
                    target = ev
                    break
                if not target:
                    target = ev
        if not target:
            return None
        print(f"    TimeTo: matched event id={target['id']} title={target.get('title','')[:50]}")
        resp2 = sess.get(f"https://sportinnovation.fr/api/events/{target['id']}/races", timeout=15)
        races = resp2.json()
        # Filter races matching the event distance
        main_race = max(races, key=lambda r: r.get("totals", {}).get("maxGeneralRanking", 0))
        race_id = main_race["id"]
        print(f"    TimeTo: fetching race {race_id} ({main_race.get('title','')})")
        resp3 = sess.get(f"https://sportinnovation.fr/api/races/{race_id}/results", timeout=180)
        results = resp3.json()
        return compute_4d_from_results(results, source="timeto")
    except Exception as e:
        print(f"  TimeTo error for {event_name}: {e}")
        return None


def fetch_sporthive_4d(event_id, year):
    """Fetch 4D from Sporthive/MYLAPS API. Needs event_id."""
    try:
        sess = requests.Session()
        resp = sess.get(f"https://eventresults-api.speedhive.com/sporthive/events/{event_id}/races", timeout=15)
        if not resp.ok:
            return None
        races = resp.json()
        if not races:
            return None
        # Pick race with most finishers
        r = max(races, key=lambda x: x.get("classificationsCount", 0))
        count = r.get("classificationsCount", 0)
        speed = r.get("raceStatistics", {}).get("averageSpeedInKmh", 0)
        distance = r.get("distance", 0) / 1000  # meters → km
        if speed and distance:
            hours = distance / speed
            total_sec = int(hours * 3600)
            h, m, s = total_sec // 3600, (total_sec % 3600) // 60, total_sec % 60
            avg_time = f"{h:02d}:{m:02d}:{s:02d}"
            return {"finishers": count, "avg_time": avg_time, "avg_speed_kmh": round(speed, 2),
                    "winner_men": None, "winner_women": None,
                    "source": "sporthive", "confidence": "medium"}
    except Exception as e:
        print(f"  Sporthive error: {e}")
    return None


def fetch_chronorace_4d(db_name, year):
    """Fetch 4D from ACN Timing / ChronoRace (Rotterdam-like events)."""
    try:
        sess = requests.Session()
        sess.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
        # Scan LIVE tables 1-60, pick the one with most results
        best = (0, None, None)
        for i in range(1, 20):
            table = f"LIVE{i}"
            resp = sess.get(f"https://results.chronorace.be/api/results/table/search/{db_name}/{table}",
                            params={"fromRecord": 0, "pageSize": 1}, timeout=15)
            if resp.ok:
                count = resp.json().get("Count", 0)
                if count > best[0]:
                    best = (count, table, None)
        if best[0] < 100:
            return None
        # Fetch all results
        all_rows = []
        offset = 0
        while offset < best[0]:
            resp = sess.get(f"https://results.chronorace.be/api/results/table/search/{db_name}/{best[1]}",
                            params={"fromRecord": offset, "pageSize": 1000}, timeout=30)
            data = resp.json()
            for g in data.get("Groups", []):
                all_rows.extend(g.get("SlaveRows", []))
            offset += 1000
        # Parse times
        times = []
        men_winner = women_winner = None
        for row in all_rows:
            time_str = re.sub(r"<[^>]+>", "", str(row[16] if len(row) > 16 else "")).strip()
            m = re.match(r"(\d+):(\d{2}):(\d{2})", time_str)
            if not m:
                continue
            t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            if 7200 < t < 28800:
                times.append(t)
                gender = str(row[2] or "").upper()
                if gender == "M" and not men_winner:
                    men_winner = f"{m.group(1).zfill(2)}:{m.group(2)}:{m.group(3)}"
                elif gender in ("F", "W", "V") and not women_winner:
                    women_winner = f"{m.group(1).zfill(2)}:{m.group(2)}:{m.group(3)}"
        if not times:
            return None
        avg = sum(times) / len(times)
        h, mn, s = int(avg // 3600), int((avg % 3600) // 60), int(avg % 60)
        return {"finishers": len(times), "avg_time": f"{h:02d}:{mn:02d}:{s:02d}",
                "avg_speed_kmh": round(42.195 / (avg / 3600), 2),
                "winner_men": men_winner, "winner_women": women_winner,
                "source": "chronorace", "confidence": "high"}
    except Exception as e:
        print(f"  ChronoRace error: {e}")
    return None


def fetch_rtrt_4d(event_code, year):
    """Fetch 4D from RTRT.me API (Great Run events).

    event_code: GR-NORTH, GR-MANCHESTER, GR-SCOTTISH, GR-BRISTOL, GR-BIRMINGHAM, GR-SOUTH
    """
    try:
        sess = requests.Session()
        params = {"appid": "623f2dd5e7847810bb1f0a07", "token": "9FA560A93CFC014488AB"}
        # Code pattern: {CODE}-{YYYY}
        code = event_code if event_code else "GR-NORTH"
        if "-" + str(year) not in code:
            code = f"{code}-{year}"
        r = sess.get(f"https://api.rtrt.me/events/{code}", params=params, timeout=15)
        if not r.ok:
            return None
        data = r.json()
        finishers = data.get("finishers")
        if not finishers or int(finishers) < 100:
            return None
        return {"finishers": int(finishers),
                "avg_time": None, "avg_speed_kmh": None,
                "winner_men": None, "winner_women": None,
                "source": "rtrt", "confidence": "high"}
    except Exception as e:
        print(f"  RTRT error: {e}")
        return None


def fetch_athlinks_4d(master_id_or_info, year):
    """Fetch 4D from Athlinks API.

    master_id_or_info: master_id (int) or dict with master_id/event_id
    """
    try:
        master_id = master_id_or_info
        if isinstance(master_id_or_info, dict):
            master_id = master_id_or_info.get("master_id") or master_id_or_info.get("platform_id")
        if not master_id:
            return None
        sess = requests.Session()
        sess.headers.update({
            "User-Agent": "Mozilla/5.0", "Accept": "application/json",
            "Origin": "https://www.athlinks.com", "Referer": "https://www.athlinks.com/",
        })
        r = sess.get(f"https://reignite-api.athlinks.com/master/{master_id}/metadata", timeout=15)
        if not r.ok:
            return None
        data = r.json()
        # New Athlinks schema: data['events'] list with race_id + description
        events = data.get("events", [])
        if not events:
            return None
        # Find event matching target year (by epoch timestamp)
        import datetime as _dt
        target_event = None
        for ev in events:
            end_ep = (ev.get("end") or {}).get("epoch", 0)
            if not end_ep:
                continue
            ev_year = _dt.datetime.fromtimestamp(end_ep / 1000, _dt.timezone.utc).year
            if ev_year == year:
                target_event = ev
                break
        if not target_event and events:
            target_event = events[0]  # most recent
        if not target_event:
            return None
        # Parse finishers from description (format "10Km Run -43337\r\n...")
        desc = target_event.get("description", "") or ""
        import re as _re
        # Look for main race line (biggest count, excluding small wheelchair/push categories)
        counts = _re.findall(r"-(\d{3,})", desc)
        finishers = max(int(c) for c in counts) if counts else None
        # Fallback: try races array
        if not finishers:
            for race in target_event.get("races", []):
                fc = race.get("finisherCount") or race.get("participantCount")
                if fc and fc > (finishers or 0):
                    finishers = fc
        if not finishers:
            return None
        return {"finishers": finishers,
                "avg_time": None, "avg_speed_kmh": None,
                "winner_men": None, "winner_women": None,
                "source": "athlinks", "confidence": "high"}
    except Exception as e:
        print(f"  Athlinks error: {e}")
        return None


def fetch_mikatiming_4d(platform_info_or_year, year):
    """Fetch 4D from Mikatiming (Berlin, London, Hamburg, Chicago, etc.).

    platform_info_or_year: dict with keys:
      subdomain, event_code, event_code_pattern
      winners_event_code  — optional, separate code for winner extraction (e.g. ELIT for London)
      finishers_event_code — optional, separate code for finisher count (e.g. MAS for London)
    """
    try:
        info = platform_info_or_year if isinstance(platform_info_or_year, dict) else {}
        subdomain = info.get("subdomain", "")
        event_code = info.get("event_code") or info.get("event_code_pattern", "MAL").format(yyyy=year)
        winners_event_code = info.get("winners_event_code") or event_code
        finishers_event_code = info.get("finishers_event_code") or event_code
        if not subdomain:
            return None

        # Dot in first path segment → full hostname
        if subdomain.startswith("http") or "." in subdomain.split("/")[0]:
            base = subdomain.rstrip("/")
            if not base.startswith("http"):
                base = f"https://{subdomain}"
        else:
            tld = "de" if subdomain in ("hamburg", "berlin-marathon", "vienna", "berlin-halbmarathon") else "com"
            base = f"https://{subdomain}.r.mikatiming.{tld}"

        sess = requests.Session()
        sess.headers.update({"User-Agent": "Mozilla/5.0"})

        # Skip wheelchair/para times (too fast for ambulating athletes)
        # Men: wheelchair ~1:20-1:30 → min 1:40:00 (6000s); Women: wheelchair ~1:38 → min 1:56:40 (7000s)
        MIN_SECS = {"M": 6000, "W": 7000}

        def time_to_secs(t):
            p = t.split(":")
            return int(p[0]) * 3600 + int(p[1]) * 60 + int(p[2]) if len(p) == 3 else 0

        def get_winner_time(sex):
            url = f"{base}/{year}/?pid=list&event={winners_event_code}&num_results=10&search%5Bsex%5D={sex}"
            r = sess.get(url, timeout=15)
            if not r.ok:
                return None
            times = re.findall(r"type-time[^>]*>(?:<div[^>]*>[^<]*(?:Finish|Netto|Net)[^<]*</div>)?(\d{2}:\d{2}:\d{2})", r.text)
            if not times:
                times = re.findall(r"(\d{2}:\d{2}:\d{2})", r.text)
            seen = set()
            for t in times:
                if t not in seen:
                    seen.add(t)
                    secs = time_to_secs(t)
                    if MIN_SECS[sex] <= secs <= 36000:
                        return t
            return None

        men_winner = get_winner_time("M")
        women_winner = get_winner_time("W")

        # Finisher count via page navigation (max_page × 25, accurate to ±24)
        r_p1 = sess.get(f"{base}/{year}/?pid=list&event={finishers_event_code}&num_results=25&page=1", timeout=30)
        page_nums = [int(p) for p in re.findall(r"page=(\d+)", r_p1.text) if p.isdigit()]
        max_page = max(page_nums, default=0)
        finishers = max_page * 25 if max_page >= 2 else None

        if not men_winner and not women_winner and not finishers:
            return None

        return {"finishers": finishers,
                "avg_time": None, "avg_speed_kmh": None,
                "winner_men": men_winner, "winner_women": women_winner,
                "source": "mikatiming", "confidence": "medium"}
    except Exception as e:
        print(f"  Mikatiming error: {e}")
        return None


def fetch_nyrr_4d(event_code, year):
    """Fetch 4D from NYRR API (TCS NYC Marathon).

    `event_code` example: 'M2026'. Default to 'M{yyyy}' if not provided.
    """
    try:
        if not event_code:
            event_code = f"M{year}"
        sess = requests.Session()
        sess.headers.update({"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        # Try several filter shapes (NYRR API is opaque)
        for body in [
            {"pageIndex": 1, "pageSize": 1, "raceIds": [event_code]},
            {"pageIndex": 1, "pageSize": 1, "eventId": event_code},
            {"pageIndex": 1, "pageSize": 1, "eventCode": event_code},
        ]:
            r = sess.post("https://rmsprodapi.nyrr.org/api/v2/runners/finishers-filter",
                          json=body, timeout=30)
            if not r.ok:
                continue
            data = r.json()
            total = data.get("totalItems", 0)
            # Reject sentinel values (full-DB count)
            if 100 < total < 100000 and data.get("items"):
                # Get winner: first item ordered by overallPlace
                first = data["items"][0]
                # Need to fetch sorted to get actual winner
                r2 = sess.post("https://rmsprodapi.nyrr.org/api/v2/runners/finishers-filter",
                               json=dict(body, pageSize=5, sortBy="overallPlace"), timeout=30)
                items = r2.json().get("items", []) if r2.ok else [first]
                men = next((i for i in items if i.get("gender") == "M"), None)
                women = next((i for i in items if i.get("gender") == "W"), None)
                return {"finishers": total,
                        "avg_time": None, "avg_speed_kmh": None,
                        "winner_men": men.get("overallTime") if men else None,
                        "winner_women": women.get("overallTime") if women else None,
                        "source": "nyrr", "confidence": "low"}  # low until filter validated
        return None
    except Exception as e:
        print(f"  NYRR error: {e}")
        return None


def fetch_baa_4d(event_id_or_year, year):
    """Fetch 4D from BAA Boston Marathon results page."""
    try:
        sess = requests.Session()
        sess.headers.update({"User-Agent": "Mozilla/5.0"})
        url = f"https://results.baa.org/{year}/"
        r = sess.get(url, timeout=15, allow_redirects=False)
        # If redirected, year not available yet
        if r.status_code in (301, 302, 303):
            print(f"  BAA: year {year} not yet available (redirect to {r.headers.get('Location','?')})")
            return None
        r = sess.get(url, timeout=15, allow_redirects=True)
        if not r.ok:
            return None
        # Try to find total finishers in HTML
        finishers = None
        for pat in [r"([\d,]+)\s*(?:Finishers|Total)", r"Total[^\d]*([\d,]+)"]:
            m = re.search(pat, r.text, re.IGNORECASE)
            if m:
                try:
                    finishers = int(m.group(1).replace(",", ""))
                    break
                except ValueError:
                    pass
        # Try to find first male/female winner in the page
        # BAA pages typically show top finishers in the "Top Finishers" section
        times = re.findall(r"(\d:\d{2}:\d{2})", r.text)
        men_winner = times[0] if times else None
        women_winner = times[1] if len(times) > 1 else None
        if not finishers and not men_winner:
            return None
        return {"finishers": finishers,
                "avg_time": None, "avg_speed_kmh": None,
                "winner_men": men_winner, "winner_women": women_winner,
                "source": "baa", "confidence": "low"}
    except Exception as e:
        print(f"  BAA error: {e}")
        return None


def fetch_tracx_4d(event_id, year):
    """Fetch 4D from Tracx Events API."""
    try:
        sess = requests.Session()
        sess.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0",
                             "Authorization": "Bearer 40496C26-9BEF-4266-8A27-43C78540F669"})
        resp = sess.get(f"https://api.tracx.events/v1/events/{event_id}/races", timeout=15)
        if not resp.ok:
            return None
        races = resp.json()
        # Pick marathon/semi
        main = max(races, key=lambda r: r.get("participant_count", 0))
        count = main.get("participant_count", 0)
        return {"finishers": count, "avg_time": None, "avg_speed_kmh": None,
                "winner_men": None, "winner_women": None,
                "source": "tracx", "confidence": "low"}
    except Exception as e:
        print(f"  Tracx error: {e}")
    return None


# ============================================================================
# HELPERS
# ============================================================================
def compute_4d_from_results(results, source="generic"):
    """Compute 4D stats from a list of individual results (TimeTo format)."""
    def parse_time(t):
        if not t:
            return None
        parts = str(t).strip().split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
        except ValueError:
            pass
        return None

    times = []
    men_winner = women_winner = None
    for r in results:
        t = parse_time(r.get("realTime") or r.get("officialTime"))
        if t and 1800 < t < 28800:
            times.append(t)
            if r.get("sexRanking") == 1 and r.get("sex") == "M" and not men_winner:
                men_winner = r.get("officialTime")
            elif r.get("sexRanking") == 1 and r.get("sex") == "F" and not women_winner:
                women_winner = r.get("officialTime")

    if not times:
        return None
    avg = sum(times) / len(times)
    h, m, s = int(avg // 3600), int((avg % 3600) // 60), int(avg % 60)
    return {
        "finishers": len(times),
        "avg_time": f"{h:02d}:{m:02d}:{s:02d}",
        "avg_speed_kmh": round(42.195 / (avg / 3600), 2),
        "winner_men": men_winner,
        "winner_women": women_winner,
        "source": source,
        "confidence": "high",
    }


PLATFORM_MAP = {
    "timeto": fetch_timeto_4d,
    "sporthive": fetch_sporthive_4d,
    "chronorace": fetch_chronorace_4d,
    "tracx": fetch_tracx_4d,
    "mikatiming": fetch_mikatiming_4d,
    "nyrr": fetch_nyrr_4d,
    "baa": fetch_baa_4d,
    "rtrt": fetch_rtrt_4d,
    "athlinks": fetch_athlinks_4d,
}


def discover_platform(event_name, year, date_str=None):
    """Try known platforms. Returns (platform, platform_id_or_info_dict).
    For Mikatiming, the second value is a dict with subdomain+event_code."""
    map_path = SCRIPT_DIR / "event_platform_map.json"
    if map_path.exists():
        with open(map_path, "r", encoding="utf-8") as f:
            pmap = json.load(f)
        key = normalize_name(event_name)
        for ev_key, info in pmap.items():
            ref_name = normalize_name(info.get("name", ev_key))
            if ref_name and (ref_name[:15] in key or key[:15] in ref_name):
                platform = info.get("platform")
                # Mikatiming: pass the whole info dict (subdomain, event_code, event_code_pattern)
                if platform == "mikatiming":
                    pid_info = {
                        "subdomain": info.get("subdomain", ""),
                        "event_code": info.get("event_code"),
                        "event_code_pattern": info.get("event_code_pattern", "MAL"),
                    }
                    if not pid_info["event_code"] and "event_code_pattern" in info:
                        pid_info["event_code"] = info["event_code_pattern"].format(yyyy=year)
                    return platform, pid_info
                pid = info.get("platform_id")
                # Sporthive: year-specific IDs
                if not pid and "sporthive_ids_by_year" in info:
                    pid = info["sporthive_ids_by_year"].get(str(year))
                # Date-pattern substitution (ChronoRace)
                if not pid and "platform_id_pattern" in info and date_str:
                    yyyy, mm, dd = date_str.split("-")
                    pid = info["platform_id_pattern"].format(yyyy=yyyy, mm=mm, dd=dd)
                return platform, pid
    lname = event_name.lower()
    if any(k in lname for k in ["paris", "lyon", "montmartre"]) and "rotterdam" not in lname:
        return "timeto", None
    if "rotterdam" in lname and date_str:
        yyyy, mm, dd = date_str.split("-")
        return "chronorace", f"{yyyy}{mm}{dd}_rotterdam"
    return None, None


# ============================================================================
# UPDATE ACTIONS
# ============================================================================
def update_finishers(race_name, distance, year, count, dry_run=False):
    """Call update_finishers.py script."""
    if dry_run:
        print(f"  [DRY] update_finishers: {race_name} {distance} {year} = {count}")
        return True
    result = subprocess.run(
        ["python", "update_finishers.py", race_name, distance, str(year), str(count)],
        cwd=str(SCRIPT_DIR), capture_output=True, text=True)
    print(f"  update_finishers output: {result.stdout.strip()[:200]}")
    return result.returncode == 0


def update_avg_time(race_name, year, distance_m, count, avg_time, speed, dry_run=False):
    """Add avg_times_sporthive.json entry. NEVER overwrite existing data."""
    path = SCRIPT_DIR / "avg_times_sporthive.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    existing = next((e for e in data if e.get("race") == race_name
                     and e.get("year") == year and e.get("dist_m") == distance_m), None)
    if existing and existing.get("avg_time"):
        print(f"  [SKIP] avg_times: {race_name} {year} deja rempli ({existing['avg_time']})")
        return
    data.append({
        "label": f"{race_name} {year}",
        "race": race_name,
        "dist_m": distance_m,
        "year": year,
        "count": count,
        "avg_time": avg_time,
        "avg_speed_kmh": speed,
    })
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  avg_times added: {race_name} {year} = {avg_time}")


def log_update(event_name, event_date, data, dry_run=False):
    """Append an update entry to update_log.json (top of list, max 20, dedup by event+date)."""
    path = SCRIPT_DIR / "update_log.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            log = json.load(f)
    else:
        log = {"updates": []}
    # Remove existing entry for same event+date
    log["updates"] = [u for u in log["updates"]
                      if not (u.get("event") == event_name and u.get("date") == event_date)]
    # Prepend new entry
    entry = {
        "event": event_name,
        "date": event_date,
        "data": data,
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    log["updates"].insert(0, entry)
    # Keep last 20
    log["updates"] = log["updates"][:20]
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"  update_log: {event_name} {event_date} -> {list(data.keys())}")


def update_winners(race_name, year, distance, men_time, women_time, dry_run=False):
    """Add chronos to temp_chronos_1.json. NEVER overwrite existing data."""
    path = SCRIPT_DIR / "temp_chronos_1.json"
    if not path.exists():
        print(f"  [SKIP] temp_chronos_1.json not found")
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    existing = next((e for e in data if e.get("course") == race_name
                     and e.get("annee") == year and e.get("distance") == distance), None)
    if existing and (existing.get("temps_homme") or existing.get("temps_femme")):
        print(f"  [SKIP] chronos: {race_name} {year} deja rempli")
        return
    if existing:
        existing["temps_homme"] = men_time
        existing["temps_femme"] = women_time
    else:
        data.append({"course": race_name, "distance": distance, "annee": year,
                     "temps_homme": men_time, "nom_homme": None,
                     "temps_femme": women_time, "nom_femme": None})
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  chronos added: {race_name} {year} H={men_time} F={women_time}")


# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="Target date (default: yesterday)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    args = parser.parse_args()

    if args.date:
        target_date = datetime.date.fromisoformat(args.date)
    else:
        target_date = datetime.date.today() - datetime.timedelta(days=1)

    date_str = target_date.isoformat()
    print(f"=== Auto Update 4D for {date_str} ===")

    log = {"date": date_str, "wa_races": [], "matched": [], "updates": [], "errors": []}

    # 1. Fetch calendar
    wa_races = fetch_worldathletics_races(date_str)
    log["wa_races"] = [{"name": r.get("name"), "venue": r.get("venue"),
                        "area": r.get("area"), "dateRange": r.get("dateRange"),
                        "hasResults": r.get("hasResults")} for r in wa_races]

    # 2. Load our events
    our_events = load_our_events()
    print(f"  Our events: {len(our_events)}")

    # 3. Match (deduplicate: keep only best score per our event)
    raw_matches = match_wa_to_ours(wa_races, our_events)
    best_per_event = {}
    for m in raw_matches:
        k = m["our"]["name"]
        if k not in best_per_event or m.get("score", 0) > best_per_event[k].get("score", 0):
            best_per_event[k] = m
    matches = list(best_per_event.values())
    print(f"  After dedup: {len(matches)} unique events")
    log["matched"] = [{"wa_name": m["wa"]["name"], "our_name": m["our"]["name"],
                       "score": m.get("score")} for m in matches]

    # 4. For each match, try to fetch 4D data
    year = target_date.year
    for match in matches:
        our_name = match["our"]["name"]
        print(f"\n  → {our_name}")
        platform, platform_id = discover_platform(our_name, year, date_str)
        if not platform:
            print(f"    No platform found")
            continue
        fetcher = PLATFORM_MAP.get(platform)
        if not fetcher:
            continue
        result = fetcher(platform_id or our_name, year)
        if not result:
            print(f"    No data from {platform}")
            continue

        # Determine distance
        dist_code = "MARATHON" if match["our"]["distance"] == "MARATHON" else \
                    "SEMI" if match["our"]["distance"] == "SEMI" else "10KM"
        dist_m = 42195 if dist_code == "MARATHON" else 21097 if dist_code == "SEMI" else 10000

        # Update (track what actually changed for the log)
        logged_data = {}
        if result.get("finishers"):
            update_finishers(our_name, dist_code, year, result["finishers"], args.dry_run)
            logged_data["finishers"] = result["finishers"]
        if result.get("avg_time"):
            update_avg_time(our_name, year, dist_m, result.get("finishers", 0),
                            result["avg_time"], result.get("avg_speed_kmh"), args.dry_run)
            logged_data["avg_time"] = result["avg_time"]
        if result.get("winner_men") or result.get("winner_women"):
            dist_label = {"MARATHON": "MARATHON", "SEMI": "SEMI", "10KM": "10KM"}.get(dist_code, dist_code)
            update_winners(our_name, year, dist_label,
                           result.get("winner_men"), result.get("winner_women"), args.dry_run)
            if result.get("winner_men"):
                logged_data["winner_men"] = result["winner_men"]
            if result.get("winner_women"):
                logged_data["winner_women"] = result["winner_women"]
        # Log the update for dashboard notifications
        if logged_data:
            # Use WA dateRange if available, else the target date
            event_date = (match["wa"].get("dateRange") or "").replace(" ", "")
            if not event_date:
                event_date = date_str
            log_update(our_name, event_date, logged_data, args.dry_run)

        log["updates"].append({
            "event": our_name, "year": year,
            "platform": platform,
            "finishers": result.get("finishers"),
            "avg_time": result.get("avg_time"),
            "winner_men": result.get("winner_men"),
            "winner_women": result.get("winner_women"),
        })

    # 5. Regenerate dashboard (only when there are actual updates)
    if log["updates"] and not args.dry_run:
        print(f"\n=== Regenerating dashboard ({len(log['updates'])} updates) ===")
        subprocess.run(["python", "create_chronos.py"], cwd=str(SCRIPT_DIR))
        subprocess.run(["python", "generate_dashboard.py"], cwd=str(SCRIPT_DIR))

    # 6. Always save log + commit (even 0 updates) so every cron run is auditable
    log_path = LOGS_DIR / f"update_4d_{date_str}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n  Report saved: {log_path}")

    if not args.dry_run:
        subprocess.run(["git", "add", "-A"], cwd=str(SCRIPT_DIR))
        n = len(log["updates"])
        msg = (f"Auto Update 4D {date_str} — {n} update(s)"
               if n > 0 else f"Auto Update 4D {date_str} — 0 update (log only)")
        r = subprocess.run(["git", "commit", "-m", msg], cwd=str(SCRIPT_DIR),
                            capture_output=True, text=True)
        if r.returncode == 0:
            subprocess.run(["git", "push"], cwd=str(SCRIPT_DIR))
            print(f"  Pushed: {msg}")
        else:
            print(f"  Nothing new to commit")

    return 0


if __name__ == "__main__":
    sys.exit(main())

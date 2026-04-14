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


def fetch_worldathletics_races(date_str):
    """Fetch road races on a given date from World Athletics."""
    sess = requests.Session()
    sess.headers.update({"x-api-key": WA_API_KEY, "Content-Type": "application/json"})
    races = []
    offset = 0
    while True:
        resp = sess.post(WA_ENDPOINT, json={
            "query": WA_QUERY,
            "variables": {"startDate": date_str, "endDate": date_str,
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
    print(f"  World Athletics: {len(races)} races on {date_str}")
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
    """Load events from dashboard data (Excel finishers file)."""
    import openpyxl
    path = SCRIPT_DIR / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["ALL"]
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
            })
    wb.close()
    return rows


def match_wa_to_ours(wa_races, our_events):
    """Match WA races to our dashboard events by best name+city score."""
    matches = []
    # Stopwords ignored when counting common words
    STOPWORDS = {"the", "de", "la", "le", "les", "du", "of", "a", "and", "et",
                 "marathon", "semi", "half", "run", "race", "runs", "races",
                 "10k", "21k", "42k", "10km", "city", "international"}
    for wa in wa_races:
        wa_name = normalize_name(wa.get("name", ""))
        wa_venue = normalize_name(wa.get("venue", ""))
        wa_words = set(wa_name.split()) - STOPWORDS
        best = None
        best_score = 0
        for ev in our_events:
            our_name = normalize_name(ev["name"])
            our_city = normalize_name(ev["city"])
            our_words = set(our_name.split()) - STOPWORDS
            # Score = common non-stopword words
            common = wa_words & our_words
            score = len(common) * 10
            # City match bonus (must overlap)
            if our_city and wa_venue:
                if our_city == wa_venue or our_city in wa_venue or wa_venue in our_city:
                    score += 5
                elif not common:
                    continue  # no name match, no city → skip
            # Distance type match bonus
            wa_lower = wa_name
            if "half" in wa_lower and ev.get("distance") == "SEMI":
                score += 3
            elif "half" not in wa_lower and "marathon" in wa_lower and ev.get("distance") == "MARATHON":
                score += 3
            elif "10k" in wa_lower and ev.get("distance") == "10KM":
                score += 3
            if score > best_score:
                best_score = score
                best = ev
        # Require minimum score 15 to avoid spurious matches
        # (15 = 1 common word + city match, or 1 distinctive word + distance bonus)
        if best and best_score >= 15:
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
}


def discover_platform(event_name, year, date_str=None):
    """Try known platforms. date_str (YYYY-MM-DD) used for dynamic platform_id patterns."""
    map_path = SCRIPT_DIR / "event_platform_map.json"
    if map_path.exists():
        with open(map_path, "r", encoding="utf-8") as f:
            pmap = json.load(f)
        key = normalize_name(event_name)
        for ev_key, info in pmap.items():
            ref_name = normalize_name(info.get("name", ev_key))
            if ref_name and (ref_name[:15] in key or key[:15] in ref_name):
                pid = info.get("platform_id")
                # Apply date pattern substitution
                if not pid and "platform_id_pattern" in info and date_str:
                    yyyy, mm, dd = date_str.split("-")
                    pid = info["platform_id_pattern"].format(yyyy=yyyy, mm=mm, dd=dd)
                return info.get("platform"), pid
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
    """Add/update avg_times_sporthive.json entry."""
    path = SCRIPT_DIR / "avg_times_sporthive.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Remove existing entry if any
    data = [e for e in data if not (e.get("race") == race_name and e.get("year") == year
                                     and e.get("dist_m") == distance_m)]
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
    print(f"  avg_times updated: {race_name} {year} = {avg_time}")


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

        # Update
        if result.get("finishers"):
            update_finishers(our_name, dist_code, year, result["finishers"], args.dry_run)
        if result.get("avg_time"):
            update_avg_time(our_name, year, dist_m, result.get("finishers", 0),
                            result["avg_time"], result.get("avg_speed_kmh"), args.dry_run)

        log["updates"].append({
            "event": our_name, "year": year,
            "platform": platform,
            "finishers": result.get("finishers"),
            "avg_time": result.get("avg_time"),
            "winner_men": result.get("winner_men"),
            "winner_women": result.get("winner_women"),
        })

    # 5. Regenerate + push
    if log["updates"] and not args.dry_run:
        print(f"\n=== Regenerating dashboard ({len(log['updates'])} updates) ===")
        subprocess.run(["python", "create_chronos.py"], cwd=str(SCRIPT_DIR))
        subprocess.run(["python", "generate_dashboard.py"], cwd=str(SCRIPT_DIR))
        subprocess.run(["git", "add", "-A"], cwd=str(SCRIPT_DIR))
        msg = f"Auto Update 4D {date_str}: {len(log['updates'])} event(s)"
        r = subprocess.run(["git", "commit", "-m", msg], cwd=str(SCRIPT_DIR), capture_output=True, text=True)
        if r.returncode == 0:
            subprocess.run(["git", "push"], cwd=str(SCRIPT_DIR))
            print(f"  Pushed: {msg}")
        else:
            print(f"  No changes to commit")

    # 6. Log report
    log_path = LOGS_DIR / f"update_4d_{date_str}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n  Report saved: {log_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

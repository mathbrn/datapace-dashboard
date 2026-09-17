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
import inspect
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


class WorldAthleticsUnavailable(RuntimeError):
    """Le catalogue World Athletics est injoignable : on ne peut rien matcher
    ce jour-la. A distinguer d'un jour sans course."""


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
        # Une exception non rattrapee ici faisait planter tout le run : ni log
        # ecrit, ni commit, donc aucune trace du jour manque.
        try:
            resp = sess.post(WA_ENDPOINT, json={
                "query": WA_QUERY,
                "variables": {"startDate": start, "endDate": end,
                              "regionType": "world", "limit": 100, "offset": offset}
            }, timeout=30)
        except Exception as e:
            print(f"  WA injoignable: {type(e).__name__}: {e}")
            raise WorldAthleticsUnavailable(str(e)) from e
        if not resp.ok:
            print(f"  WA error: HTTP {resp.status_code}")
            if offset == 0:
                raise WorldAthleticsUnavailable(f"HTTP {resp.status_code}")
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


MOIS_INDEX = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
              "juin": 6, "juillet": 7, "aout": 8, "septembre": 9,
              "octobre": 10, "novembre": 11, "decembre": 12}


def events_due_without_calendar(our_events, target_date):
    """Repli quand le catalogue World Athletics est injoignable.

    Le calendrier WA ne sert qu'a savoir quelles courses ont eu lieu. On peut
    s'en passer : on prend les evenements du map dont le mois (colonne
    « Période » de l'Excel) est deja passe dans l'annee cible et dont la
    cellule finishers est encore vide. Un fetch sur une course pas encore
    courue ne renvoie rien — c'est sans risque, juste logge en
    fetch_returned_nothing.
    """
    year = target_date.year
    filled = _years_already_filled(year)
    due = []
    for ev in our_events:
        mois = MOIS_INDEX.get(normalize_name(ev.get("period", "")).lower())
        if not mois or mois > target_date.month:
            continue
        if (ev["name"], ev["distance"]) in filled:
            continue
        platform, _ = discover_platform(ev["name"], year)
        if not platform or platform not in PLATFORM_MAP:
            continue
        due.append({"wa": {"name": ev["name"], "dateRange": ""},
                    "our": ev, "score": 0})
    return due


def _years_already_filled(year):
    """Couples (course, distance) dont la cellule de l'annee est deja remplie."""
    import openpyxl
    path = SCRIPT_DIR / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["ALL"]
    filled = set()
    headers = None
    col = None
    for row in ws.iter_rows(values_only=True):
        if headers is None:
            headers = list(row)
            for i, h in enumerate(headers):
                if isinstance(h, (int, float)) and int(h) == year:
                    col = i
            continue
        if col is None:
            break
        race = str(row[3] or "").strip()
        if race and row[col] not in (None, ""):
            filled.add((race, str(row[2] or "").strip()))
    wb.close()
    return filled


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
def fetch_timeto_4d(event_name, year, dist_code=None):
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
        # La course visee est celle de la distance demandee, pas la plus grosse
        # de l'evenement (Run in Lyon = marathon + semi + 10K sous un seul id).
        main_race = pick_race_for_distance(
            races, dist_code,
            get_distance_m=lambda r: r.get("distance") or r.get("distance_m"),
            get_title=lambda r: r.get("title") or r.get("name") or "")
        if not main_race:
            print(f"    TimeTo: aucune course {dist_code} identifiable — abandon")
            return None
        race_id = main_race["id"]
        print(f"    TimeTo: fetching race {race_id} ({main_race.get('title','')})")
        resp3 = sess.get(f"https://sportinnovation.fr/api/races/{race_id}/results", timeout=180)
        results = resp3.json()
        return compute_4d_from_results(results, source="timeto")
    except Exception as e:
        print(f"  TimeTo error for {event_name}: {e}")
        return None


def fetch_sporthive_4d(event_id, year, dist_code=None):
    """Fetch 4D from Sporthive/MYLAPS API. Needs event_id."""
    try:
        sess = requests.Session()
        url = f"https://eventresults-api.speedhive.com/sporthive/events/{event_id}/races"
        resp = sess.get(url, timeout=15)
        if not resp.ok:
            print(f"    Sporthive events/{event_id}/races: HTTP {resp.status_code}")
            return None
        races = resp.json()
        if not races:
            print(f"    Sporthive events/{event_id}: aucune course renvoyee")
            return None
        # Viser la distance demandee, pas la plus grosse course de l'evenement
        r = pick_race_for_distance(
            races, dist_code,
            get_distance_m=lambda x: x.get("distance"),
            get_title=lambda x: x.get("name") or x.get("title") or "")
        if not r:
            print(f"    Sporthive: aucune course {dist_code} identifiable — abandon")
            print(f"      courses vues={[(str(x.get('name') or x.get('title'))[:26], x.get('distance')) for x in races][:8]}")
            return None
        count = r.get("classificationsCount", 0)
        if not count:
            print(f"    Sporthive: course trouvee ({r.get('name')}) mais "
                  f"classificationsCount absent — cles={sorted(r.keys())[:12]}")
            return None
        speed = r.get("raceStatistics", {}).get("averageSpeedInKmh", 0)
        distance = r.get("distance", 0) / 1000  # meters → km
        avg_time = None
        if speed and distance:
            hours = distance / speed
            total_sec = int(hours * 3600)
            h, m, s = total_sec // 3600, (total_sec % 3600) // 60, total_sec % 60
            avg_time = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            # Sans vitesse moyenne on perdait AUSSI les finishers : la fonction
            # tombait jusqu'au `return None` final. Les finishers sont la
            # donnee principale, on les renvoie meme sans temps moyen.
            print(f"    Sporthive: pas de vitesse moyenne pour {r.get('name')}, "
                  f"finishers seuls")
        return {"finishers": count, "avg_time": avg_time,
                "avg_speed_kmh": round(speed, 2) if speed else None,
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
            # best[0] est le Count renvoye par l'API : c'est deja un comptage de
            # finishers valable. Le jeter parce que les chronos sont illisibles
            # revenait a perdre la donnee prioritaire du dashboard.
            print(f"    ChronoRace {db_name}: aucun temps exploitable, "
                  f"finishers seuls ({best[0]})")
            return {"finishers": best[0], "avg_time": None, "avg_speed_kmh": None,
                    "winner_men": None, "winner_women": None,
                    "source": "chronorace", "confidence": "medium"}
        avg = sum(times) / len(times)
        h, mn, s = int(avg // 3600), int((avg % 3600) // 60), int(avg % 60)
        return {"finishers": len(times), "avg_time": f"{h:02d}:{mn:02d}:{s:02d}",
                "avg_speed_kmh": round(42.195 / (avg / 3600), 2),
                "winner_men": men_winner, "winner_women": women_winner,
                "source": "chronorace", "confidence": "high"}
    except Exception as e:
        print(f"  ChronoRace error: {e}")
    return None


def fetch_rtrt_4d(event_code, year, dist_code=None):
    """Fetch 4D from RTRT.me API (Great Run events).

    event_code: GR-NORTH, GR-MANCHESTER, GR-SCOTTISH, GR-BRISTOL, GR-BIRMINGHAM, GR-SOUTH

    ATTENTION — `GET /events/{code}` renvoie `finishers` = total de l'EPREUVE
    (10K + semi cumules). L'ecrire dans la cellule d'une distance donnee est
    faux : c'est ce qui a produit « Great Manchester Run 10KM = 31340 » et
    « Great North 10K = 48705 » au run #130. On passe donc par
    `/events/{code}/stats`, qui ventile par course, et on ne renvoie une valeur
    que si une seule course correspond sans ambiguite a la distance demandee.
    A defaut : None. Jamais le total.
    """
    if not dist_code:
        return None
    try:
        sess = requests.Session()
        params = {"appid": "623f2dd5e7847810bb1f0a07", "token": "9FA560A93CFC014488AB"}
        code = event_code if event_code else "GR-NORTH"
        if "-" + str(year) not in code:
            code = f"{code}-{year}"
        r = sess.get(f"https://api.rtrt.me/events/{code}/stats",
                     params=params, timeout=15)
        if not r.ok:
            print(f"    RTRT {code}/stats: HTTP {r.status_code}")
            return None
        tags = (((r.json() or {}).get("stats") or {}).get("tags") or {})
        if not isinstance(tags, dict):
            print(f"    RTRT {code}: pas de stats.tags exploitable "
                  f"(cles racine: {list((r.json() or {}).keys())[:8]})")
            return None
        # Diagnostic : les noms de tags reels conditionnent le ciblage par
        # distance. Sans cette trace, un echec est indiscernable d'une course
        # absente. A retirer une fois la correspondance etablie.
        print(f"    RTRT {code}: tags disponibles = {list(tags.keys())[:15]}")
        if not tags:
            # stats vide : l'edition existe-t-elle seulement sous ce code ?
            try:
                ev = sess.get(f"https://api.rtrt.me/events/{code}",
                              params=params, timeout=15)
                if ev.ok:
                    j = ev.json() or {}
                    info = j.get("event") or j
                    print(f"      /events/{code} -> total={info.get('finishers')} "
                          f"name={str(info.get('name'))[:40]!r} "
                          f"cles={list(info.keys())[:10]}")
                else:
                    print(f"      /events/{code} -> HTTP {ev.status_code} "
                          f"(edition absente sous ce code ?)")
            except Exception as e2:
                print(f"      sonde /events/{code} impossible: {e2}")
            return None

        # Mots-cles distinguant la course dans le nom du tag
        wanted = {"MARATHON": ("marathon",), "SEMI": ("half", "semi"),
                  "10KM": ("10k", "10 k")}.get(dist_code, ())
        exclude = ("half", "semi", "10k", "relay", "junior", "mini", "virtual") \
            if dist_code == "MARATHON" else ("virtual", "relay", "junior", "mini")

        candidates = []
        for tag, payload in tags.items():
            low = str(tag).lower()
            if any(x in low for x in exclude if x not in wanted):
                continue
            if not any(w in low for w in wanted):
                continue
            total = 0
            for key, val in (payload or {}).items():
                if str(key).upper().startswith("FINISH") and isinstance(val, dict):
                    total += int(val.get("valid_count") or 0)
            if total >= 100:
                candidates.append((tag, total))

        # Ambigu (0 ou plusieurs courses correspondantes) -> on n'ecrit rien
        if len(candidates) != 1:
            if candidates:
                print(f"  RTRT {code}: {len(candidates)} courses possibles pour "
                      f"{dist_code} ({[c[0] for c in candidates]}) — abandon")
            return None

        tag, finishers = candidates[0]
        return {"finishers": finishers,
                "avg_time": None, "avg_speed_kmh": None,
                "winner_men": None, "winner_women": None,
                "source": f"rtrt:{tag}", "confidence": "high"}
    except Exception as e:
        print(f"  RTRT error: {e}")
        return None



# Courses annexes a exclure d'un decompte de finishers : handisport, relais,
# defis et versions virtuelles ne sont pas la course principale.
# Pause systematique avant chaque appel Athlinks, pour ne pas declencher
# la limitation de debit quand plusieurs epreuves se suivent dans un run.
_ATHLINKS_DELAI = 2.0

ATHLINKS_SECONDAIRE = ("wheelchair", "wheel", "handcycle", "hand cycle", "push",
                       "relay", "virtual", "junior", "kids", "centipede",
                       "bonus", "challenge", "walk only")


def parse_athlinks_description(desc):
    """Transforme la description d'une edition Athlinks en liste de courses.

    Une ligne par course, le nombre de finishers en fin de ligne. Le separateur
    varie ( ' - ' ou une tabulation ) et les milliers sont parfois separes par
    une virgule :
        'Marathon - 5,279'              -> Marathon / 5279
        '12K Run\t             19814'   -> 12K Run / 19814
        '10 Mi Wheelchair Race - 8'     -> 10 Mi Wheelchair Race / 8
    L'ancien motif exigeait un tiret et ignorait les virgules : « 5,279 » etait
    lu « 279 », et les evenements a tabulations ne donnaient aucune ligne.
    """
    out = []
    for ligne in re.split(r"[\r\n]+", desc or ""):
        ligne = ligne.strip()
        if not ligne:
            continue
        m = re.match(r"^(?P<title>.*?)[\s\-\t]*(?P<n>\d[\d,\s]*)$", ligne)
        if not m:
            continue
        titre = m.group("title").strip(" -\t")
        brut = re.sub(r"[,\s]", "", m.group("n"))
        if not titre or not brut.isdigit():
            continue
        out.append({"title": titre, "count": int(brut)})
    return out


def pick_athlinks_race(lignes, dist_code):
    """Choisit la course correspondant a la distance demandee.

    Les courses annexes sont ecartees d'abord. Pour AUTRE (10 miles, 12K, 15K...)
    aucune distance de reference n'existe : on n'accepte que s'il ne reste
    qu'une seule course principale, sinon None.
    """
    principales = [l for l in lignes
                   if not any(x in l["title"].lower() for x in ATHLINKS_SECONDAIRE)]
    if not principales:
        return None
    if dist_code == "AUTRE":
        if len(principales) == 1:
            return principales[0]
        print(f"    {len(principales)} courses principales pour AUTRE "
              f"({[l['title'][:24] for l in principales][:6]}) — ambigu, abandon")
        return None
    return pick_race_for_distance(principales, dist_code,
                                  get_distance_m=lambda r: None,
                                  get_title=lambda r: r["title"])


def fetch_athlinks_4d(master_id_or_info, year, dist_code=None):
    """Fetch 4D from Athlinks API.

    master_id_or_info: master_id (int) or dict with master_id/event_id
    """
    try:
        master_id = master_id_or_info
        if isinstance(master_id_or_info, dict):
            master_id = master_id_or_info.get("master_id") or master_id_or_info.get("platform_id")
        if not master_id:
            print("    Athlinks: aucun master_id dans event_platform_map.json")
            return None
        # Sans master_id, discover_platform retombe sur le NOM de l'epreuve, qui
        # partait tel quel dans l'URL : /master/Gasparilla Distance Classic/
        # metadata -> 403 garanti. Un master_id est toujours numerique.
        if not str(master_id).strip().isdigit():
            print(f"    Athlinks: master_id non numerique ({master_id!r}) — "
                  f"entree a completer dans event_platform_map.json")
            return None
        sess = requests.Session()
        sess.headers.update({
            "User-Agent": "Mozilla/5.0", "Accept": "application/json",
            "Origin": "https://www.athlinks.com", "Referer": "https://www.athlinks.com/",
        })
        url = f"https://reignite-api.athlinks.com/master/{master_id}/metadata"
        # Athlinks limite le debit : apres quelques dizaines de requetes
        # rapprochees, il renvoie 403 sur des master_id parfaitement valides
        # (run #137 : les 6 epreuves qui avaient repondu au run precedent sont
        # passees en 403). Espacement systematique + reprise exponentielle.
        import time as _t
        _t.sleep(_ATHLINKS_DELAI)
        r = None
        for essai, attente in enumerate((5, 15, 40)):
            r = sess.get(url, timeout=20)
            if r.status_code != 403:
                break
            if essai < 2:
                print(f"    Athlinks master/{master_id}: 403, nouvelle tentative "
                      f"dans {attente} s")
                _t.sleep(attente)
        if not r.ok:
            print(f"    Athlinks master/{master_id}/metadata: HTTP {r.status_code}")
            return None
        data = r.json()
        # New Athlinks schema: data['events'] list with race_id + description
        events = data.get("events", [])
        if not events:
            print(f"    Athlinks master/{master_id}: aucun evenement "
                  f"(cles racine: {list(data.keys())[:8]})")
            return None
        # Diagnostic : savoir si l'edition de l'annee ciblee existe chez eux.
        import datetime as _dt0
        annees = []
        for _ev in events:
            _e = (_ev.get("end") or {}).get("epoch", 0)
            if _e:
                annees.append(_dt0.datetime.fromtimestamp(
                    _e / 1000, _dt0.timezone.utc).year)
        print(f"    Athlinks master/{master_id}: {len(events)} edition(s), "
              f"annees={sorted(set(annees), reverse=True)[:6]}, cible={year}")
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
        # La description liste une course par ligne : "10Km Run -43337".
        # Prendre le plus grand nombre revenait a choisir la plus grosse course
        # de l'evenement quelle que soit la distance demandee — meme bug que
        # partout ailleurs. On parse chaque ligne et on vise la bonne distance.
        desc = target_event.get("description", "") or ""
        lignes = parse_athlinks_description(desc)
        choisi = pick_athlinks_race(lignes, dist_code)
        finishers = choisi["count"] if choisi else None

        # Repli : tableau races structure, qui porte parfois la distance
        if not finishers:
            races = target_event.get("races", []) or []
            r = pick_race_for_distance(
                races, dist_code,
                get_distance_m=lambda x: x.get("distance") or x.get("distanceMeters"),
                get_title=lambda x: x.get("name") or x.get("description") or "")
            if r:
                finishers = r.get("finisherCount") or r.get("participantCount")

        if not finishers:
            # Diagnostic : distinguer « mauvais master_id / edition absente »
            # de « course de cette distance introuvable dans l'evenement ».
            print(f"    Athlinks: aucune course {dist_code} identifiable — abandon")
            print(f"      annee ciblee={year}, evenement retenu="
                  f"{str(target_event.get('name') or target_event.get('title'))[:60]!r}")
            print(f"      courses vues={[l['title'][:30] for l in lignes][:10]}")
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
        # « Mozilla/5.0 » seul est une signature de bot : mikatiming repond 403
        # (run #139, Berlin / Stockholm / Brighton). En-tetes de navigateur reel.
        sess.headers.update({
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/131.0.0.0 Safari/537.36"),
            "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                       "image/avif,image/webp,*/*;q=0.8"),
            "Accept-Language": "en-US,en;q=0.9,de;q=0.8,fr;q=0.7",
        })

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
                print(f"    Mikatiming {winners_event_code} vainqueur {sex}: "
                      f"HTTP {r.status_code}")
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

        # Comptage des finishers.
        # L'ancienne formule `max_page * 25` etait une ESTIMATION a ±24 pres, et
        # toujours un multiple de 25 : elle produisait donc mecaniquement des
        # chiffres ronds, ce que la regle « zero tolerance » interdit. On compte
        # desormais exactement : (max_page - 1) * 25 + lignes de la derniere page.
        RE_TEMPS = r"type-time[^>]*>(?:<div[^>]*>[^<]*(?:Finish|Netto|Net)[^<]*</div>)?\d{2}:\d{2}:\d{2}"
        finishers = None
        liste = f"{base}/{year}/?pid=list&event={finishers_event_code}&num_results=25"
        r_p1 = sess.get(f"{liste}&page=1", timeout=30)
        if not r_p1.ok:
            print(f"    Mikatiming {finishers_event_code}: HTTP {r_p1.status_code} sur la liste")
        else:
            page_nums = [int(p) for p in re.findall(r"page=(\d+)", r_p1.text) if p.isdigit()]
            max_page = max(page_nums, default=0)
            if max_page >= 2:
                r_last = sess.get(f"{liste}&page={max_page}", timeout=30)
                if r_last.ok:
                    n_last = len(re.findall(RE_TEMPS, r_last.text))
                    if n_last:
                        finishers = (max_page - 1) * 25 + n_last
                    else:
                        print(f"    Mikatiming {finishers_event_code}: derniere page "
                              f"({max_page}) illisible, comptage abandonne")
                else:
                    print(f"    Mikatiming {finishers_event_code}: HTTP "
                          f"{r_last.status_code} sur la page {max_page}")
            else:
                # Diagnostic : distinguer « page de resultats vide » (mauvais
                # code evenement ou edition absente) de « resultats presents
                # mais sans pagination » (liste tenant sur une seule page).
                n_temps = len(re.findall(RE_TEMPS, r_p1.text))
                print(f"    Mikatiming {finishers_event_code}: pagination absente "
                      f"(max_page={max_page}), {n_temps} temps sur la page 1, "
                      f"{len(r_p1.text)} octets")
                if n_temps:
                    finishers = n_temps
                    print(f"      -> liste tenant sur une page : {n_temps} finishers")

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



_TRACX_CATALOGUE = None


def _tracx_id_par_nom(sess, nom, year):
    """Retrouve l'id Tracx d'un evenement a partir de son nom.

    Le catalogue (~860 evenements) est pagine et mis en cache pour le run.
    On exige que tous les mots significatifs du nom recherche soient presents
    dans le nom Tracx, et on privilegie l'edition de l'annee ciblee.
    """
    global _TRACX_CATALOGUE
    if _TRACX_CATALOGUE is None:
        _TRACX_CATALOGUE = []
        page = 1
        while page <= 12:
            r = sess.get("https://api.tracx.events/v1/events",
                         params={"page": page, "per_page": 100}, timeout=20)
            if not r.ok:
                print(f"    Tracx catalogue page {page}: HTTP {r.status_code}")
                break
            lot = r.json()
            if isinstance(lot, dict):
                lot = lot.get("data") or lot.get("events") or []
            if not lot:
                break
            _TRACX_CATALOGUE.extend(lot)
            if len(lot) < 100:
                break
            page += 1
        print(f"    Tracx catalogue: {len(_TRACX_CATALOGUE)} evenements")

    STOP = {"the", "de", "la", "le", "du", "of", "by", "presented", "marathon",
            "half", "run", "race", "series", "tcs", "aj", "bell"}
    cibles = {w for w in normalize_name(nom).split() if w not in STOP and len(w) > 2}
    if not cibles:
        return None
    candidats = []
    for ev in _TRACX_CATALOGUE:
        titre = normalize_name(str(ev.get("name") or ev.get("title") or ""))
        if not titre or not cibles.issubset(set(titre.split())):
            continue
        millesime = str(ev.get("year") or ev.get("start_date") or ev.get("date") or "")
        candidats.append((str(year) in millesime, ev.get("id")))
    if not candidats:
        return None
    # priorite a l'edition de l'annee ciblee
    candidats.sort(key=lambda x: not x[0])
    if len(candidats) > 1 and not candidats[0][0]:
        print(f"    Tracx: {len(candidats)} correspondances pour {nom!r} sans "
              f"edition {year} identifiable — abandon")
        return None
    return candidats[0][1]


def fetch_tracx_4d(event_id, year, dist_code=None):
    """Fetch 4D from Tracx Events API."""
    try:
        sess = requests.Session()
        sess.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0",
                             "Authorization": "Bearer 40496C26-9BEF-4266-8A27-43C78540F669"})
        # Sans platform_id, discover_platform retombe sur le NOM de l'epreuve,
        # qui partait tel quel dans l'URL -> 404 garanti (run #139 :
        # « events/TCS Sydney Marathon presented by ASICS/races: HTTP 404 »).
        # Meme defaut qu'athlinks, mais Tracx expose un catalogue : on resout
        # l'identifiant par le nom plutot que d'exiger qu'il soit dans le map.
        if not str(event_id).strip().isdigit():
            resolu = _tracx_id_par_nom(sess, str(event_id), year)
            if not resolu:
                print(f"    Tracx: aucun evenement trouve pour {event_id!r}")
                return None
            print(f"    Tracx: {event_id!r} -> id={resolu}")
            event_id = resolu
        resp = sess.get(f"https://api.tracx.events/v1/events/{event_id}/races", timeout=15)
        if not resp.ok:
            print(f"    Tracx events/{event_id}/races: HTTP {resp.status_code}")
            return None
        races = resp.json()
        if isinstance(races, dict):
            # certaines reponses enveloppent la liste
            races = races.get("data") or races.get("races") or []
        if not races:
            print(f"    Tracx events/{event_id}: aucune course renvoyee")
            return None
        # Viser la distance demandee, pas la plus grosse course de l'evenement
        main = pick_race_for_distance(
            races, dist_code,
            get_distance_m=lambda r: r.get("distance") or r.get("distance_m"),
            get_title=lambda r: r.get("name") or r.get("title") or "")
        if not main:
            print(f"    Tracx: aucune course {dist_code} identifiable — abandon")
            print(f"      courses vues={[(str(x.get('name') or x.get('title'))[:26], x.get('distance') or x.get('distance_m')) for x in races][:8]}")
            return None
        count = main.get("participant_count", 0)
        if not count:
            print(f"    Tracx: course trouvee ({main.get('name')}) mais "
                  f"participant_count absent — cles={sorted(main.keys())[:12]}")
            return None
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
        # Les finishers sont la donnee prioritaire du dashboard : meme si aucun
        # temps n'est exploitable, le nombre de resultats reste un comptage
        # valable. Renvoyer None ici jetait une epreuve entiere pour un simple
        # probleme de format de chrono.
        if results:
            print(f"    {source}: aucun temps exploitable sur {len(results)} "
                  f"resultats, finishers seuls")
            return {"finishers": len(results), "avg_time": None,
                    "avg_speed_kmh": None, "winner_men": None,
                    "winner_women": None, "source": source,
                    "confidence": "medium"}
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


# Distance ciblee, en metres, et tolerance
DIST_TARGETS = {"MARATHON": (42195, 1200), "SEMI": (21097, 700), "10KM": (10000, 450)}

# Mots-cles dans le titre d'une course, quand la distance chiffree manque
DIST_WORDS = {
    "MARATHON": (("marathon", "42k", "42.2", "full"),
                 ("half", "semi", "demi", "10k", "5k", "relay")),
    "SEMI": (("half", "semi", "demi", "21k", "21.1"),
             ("10k", "5k", "relay", "quarter")),
    "10KM": (("10k", "10 km", "10km"),
             ("half", "semi", "relay", "5k", "100k")),
}


def pick_race_for_distance(races, dist_code, get_distance_m=None, get_title=None):
    """Choisit, parmi les courses d'un evenement, celle qui correspond a la
    distance demandee. Renvoie None si c'est ambigu.

    C'est LE correctif structurel de ce script. Le dashboard tient une ligne par
    couple (epreuve, distance), alors que les APIs raisonnent par evenement : un
    meme evenement heberge un 10K et un semi. Les fetchers prenaient
    `max(races, key=participants)` — « la plus grosse course » — et ecrivaient
    donc le meme chiffre dans les deux lignes. Cf. la corruption du run #130.

    On retient d'abord la distance chiffree (fiable), sinon les mots-cles du
    titre. Zero ou plusieurs candidats -> None : mieux vaut une cellule vide.
    """
    if not races or dist_code not in DIST_TARGETS:
        return None
    get_distance_m = get_distance_m or (lambda r: r.get("distance"))
    get_title = get_title or (lambda r: r.get("title") or r.get("name") or "")

    target, tol = DIST_TARGETS[dist_code]
    by_metres = []
    for r in races:
        try:
            d = float(get_distance_m(r) or 0)
        except (TypeError, ValueError):
            continue
        if d and abs(d - target) <= tol:
            by_metres.append(r)
    if len(by_metres) == 1:
        return by_metres[0]
    if len(by_metres) > 1:
        print(f"    {len(by_metres)} courses a {target} m — ambigu, abandon")
        return None

    inc, exc = DIST_WORDS[dist_code]
    by_words = []
    for r in races:
        low = normalize_name(str(get_title(r)))
        if not low or any(x in low for x in exc):
            continue
        if any(x in low for x in inc):
            by_words.append(r)
    if len(by_words) == 1:
        return by_words[0]
    if len(by_words) > 1:
        print(f"    {len(by_words)} courses correspondent a {dist_code} par le "
              f"titre — ambigu, abandon")
    return None


def _names_match(a, b):
    """Deux noms d'evenement normalises designent-ils la meme course ?

    Egalite stricte, volontairement. L'ancienne regle comparait les 15 premiers
    caracteres : le prefixe de « aj bell great bristol run » et celui de
    « aj bell great birmingham run » valent tous deux « aj bell great b », si
    bien que les quatre courses de la famille « AJ Bell Great ... » se
    confondaient. Degat constate au run #130 du 2026-09-17 : le total de
    Birmingham ecrit dans les cellules de Bristol.

    Un suffixe suffit a distinguer deux vraies courses (« Great North Run » vs
    « Great North 10K »), donc aucune tolerance de prefixe n'est sure ici. Les
    noms de `event_platform_map.json` doivent reproduire a l'identique ceux de
    la colonne Race de l'Excel — 86 des 88 entrees le faisaient deja, les 2
    autres ont ete alignees.
    """
    return bool(a) and a == b


_PMAP_CACHE = None


def _load_platform_map():
    """event_platform_map.json, lu une seule fois (le mode repli appelle
    discover_platform des centaines de fois)."""
    global _PMAP_CACHE
    if _PMAP_CACHE is None:
        map_path = SCRIPT_DIR / "event_platform_map.json"
        if map_path.exists():
            with open(map_path, "r", encoding="utf-8") as f:
                _PMAP_CACHE = json.load(f)
        else:
            _PMAP_CACHE = {}
    return _PMAP_CACHE


def discover_platform(event_name, year, date_str=None):
    """Try known platforms. Returns (platform, platform_id_or_info_dict).
    For Mikatiming, the second value is a dict with subdomain+event_code."""
    pmap = _load_platform_map()
    if pmap:
        key = normalize_name(event_name)
        for ev_key, info in pmap.items():
            ref_name = normalize_name(info.get("name", ev_key))
            if ref_name and _names_match(key, ref_name):
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
                # `master_id` accepte en synonyme de `platform_id` : les entrees
                # athlinks documentent naturellement l'identifiant sous ce nom,
                # et n'en lire qu'un seul faisait silencieusement retomber sur
                # le nom de l'epreuve (run #134).
                pid = info.get("platform_id") or info.get("master_id")
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

def _git_commit_et_pousse(msg):
    """Commit puis push, en verifiant reellement que le push aboutit.

    L'ancien code ignorait le code de retour de `git push` et affichait
    « Pushed » quoi qu'il arrive. Quand quelqu'un poussait pendant le run, le
    push etait rejete en non-fast-forward, le runner etait detruit, et le
    travail disparaissait SANS AUCUNE TRACE — c'est ce qui est arrive au
    run #140 (chronos Stockholm et Brighton perdus). On rebase et on retente.
    """
    r = subprocess.run(["git", "commit", "-m", msg], cwd=str(SCRIPT_DIR),
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("  Rien a commiter")
        return False
    for essai in range(3):
        p = subprocess.run(["git", "push"], cwd=str(SCRIPT_DIR),
                           capture_output=True, text=True)
        if p.returncode == 0:
            print(f"  Pousse: {msg}")
            return True
        print(f"  Push refuse (tentative {essai + 1}/3) : "
              f"{(p.stderr or '').strip().splitlines()[-1] if p.stderr else '?'}")
        pr = subprocess.run(["git", "pull", "--rebase"], cwd=str(SCRIPT_DIR),
                            capture_output=True, text=True)
        if pr.returncode != 0:
            print(f"  ECHEC du rebase, travail NON pousse : "
                  f"{(pr.stderr or '').strip()[:300]}")
            return False
    print("  ECHEC : impossible de pousser apres 3 tentatives, travail perdu")
    return False


def run_one(target_date, dry_run=False, regenerate=True, commit=True):
    """Traite une seule date. Retourne le log de la journee."""
    date_str = target_date.isoformat()
    print(f"=== Auto Update 4D for {date_str} ===")

    log = {"date": date_str, "wa_races": [], "matched": [], "updates": [],
           "skipped": [], "errors": []}

    # 1. Fetch calendar (peut etre indisponible : on bascule alors en repli)
    wa_down = None
    try:
        wa_races = fetch_worldathletics_races(date_str)
    except WorldAthleticsUnavailable as e:
        wa_down = str(e)
        wa_races = []
        log["errors"].append({"stage": "worldathletics", "error": wa_down})
        print(f"  Catalogue World Athletics injoignable → mode repli.")
    log["wa_races"] = [{"name": r.get("name"), "venue": r.get("venue"),
                        "area": r.get("area"), "dateRange": r.get("dateRange"),
                        "hasResults": r.get("hasResults")} for r in wa_races]

    # 2. Load our events
    our_events = load_our_events()
    print(f"  Our events: {len(our_events)}")

    # 3. Match (deduplicate: keep only best score per our event)
    if wa_down:
        # Sans calendrier : on vise les evenements du map dont le mois est
        # passe et dont la donnee manque encore.
        matches = events_due_without_calendar(our_events, target_date)
        log["mode"] = "fallback_no_calendar"
        print(f"  Repli : {len(matches)} evenement(s) a tenter sans calendrier")
    else:
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
    seen_counts = {}  # finishers -> (course, distance) deja servis dans ce run
    for match in matches:
        our_name = match["our"]["name"]
        print(f"\n  → {our_name}")

        def skip(reason, platform=None):
            """Trace un echec dans le log (sinon il reste invisible : cf. les
            50 logs 2026-04/06 qui affichaient tous errors:[] alors que 98%
            des matches n'aboutissaient a rien)."""
            log["skipped"].append({"event": our_name, "reason": reason,
                                   "platform": platform})
            print(f"    SKIP ({reason})")

        platform, platform_id = discover_platform(our_name, year, date_str)
        if not platform:
            skip("no_platform_mapped")
            continue
        fetcher = PLATFORM_MAP.get(platform)
        if not fetcher:
            skip("no_fetcher_implemented", platform)
            continue
        # Determine distance (avant le fetch : certains fetchers en ont besoin
        # pour viser la bonne course et non le total de l'epreuve)
        # AUTRE (10 miles, 12K, 15K...) doit rester AUTRE : le rabattre sur
        # 10KM faisait chercher une course de 10 km dans des epreuves qui n'en
        # ont pas (Bay to Breakers est un 12K, Broad Street un 10 miles), d'ou
        # des « aucune course 10KM identifiable » systematiques.
        _d = (match["our"]["distance"] or "").strip().upper()
        dist_code = _d if _d in ("MARATHON", "SEMI", "10KM", "AUTRE") else "10KM"
        dist_m = {"MARATHON": 42195, "SEMI": 21097, "10KM": 10000}.get(dist_code)

        try:
            if "dist_code" in inspect.signature(fetcher).parameters:
                result = fetcher(platform_id or our_name, year, dist_code=dist_code)
            else:
                result = fetcher(platform_id or our_name, year)
        except Exception as e:
            log["errors"].append({"event": our_name, "platform": platform,
                                  "error": f"{type(e).__name__}: {e}"})
            print(f"    ERREUR {platform}: {type(e).__name__}: {e}")
            continue
        if not result:
            skip("fetch_returned_nothing", platform)
            continue

        # Garde-fou : un meme nombre de finishers ne peut pas valoir pour deux
        # couples (course, distance) differents dans un meme run. Quand ca
        # arrive, c'est que le fetcher a renvoye le total de l'epreuve (10K +
        # semi cumules) au lieu du compte de la course. C'est exactement ce qui
        # s'est produit au run #130 : 19256 ecrit sur Bristol semi, Bristol 10K
        # et Birmingham 10K. On refuse d'ecrire plutot que de salir la base.
        n = result.get("finishers")
        if n and n in seen_counts and seen_counts[n] != (our_name, dist_code):
            log["skipped"].append({
                "event": our_name, "platform": platform,
                "reason": "duplicate_count_across_events",
                "detail": f"{n} deja attribue a {seen_counts[n][0]} "
                          f"({seen_counts[n][1]}) — total d'epreuve probable",
            })
            print(f"    REFUS : {n} deja attribue a {seen_counts[n][0]} "
                  f"({seen_counts[n][1]}) — total d'epreuve probable")
            continue

        # Update (track what actually changed for the log)
        logged_data = {}
        if result.get("finishers"):
            seen_counts[result["finishers"]] = (our_name, dist_code)
            update_finishers(our_name, dist_code, year, result["finishers"], dry_run)
            logged_data["finishers"] = result["finishers"]
        if result.get("avg_time") and dist_m:
            # dist_m est None pour AUTRE : distance non standard, donc pas de
            # temps moyen comparable a enregistrer.
            update_avg_time(our_name, year, dist_m, result.get("finishers", 0),
                            result["avg_time"], result.get("avg_speed_kmh"), dry_run)
            logged_data["avg_time"] = result["avg_time"]
        if result.get("winner_men") or result.get("winner_women"):
            dist_label = {"MARATHON": "MARATHON", "SEMI": "SEMI", "10KM": "10KM"}.get(dist_code, dist_code)
            update_winners(our_name, year, dist_label,
                           result.get("winner_men"), result.get("winner_women"), dry_run)
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
            log_update(our_name, event_date, logged_data, dry_run)

        log["updates"].append({
            "event": our_name, "year": year,
            "platform": platform,
            "finishers": result.get("finishers"),
            "avg_time": result.get("avg_time"),
            "winner_men": result.get("winner_men"),
            "winner_women": result.get("winner_women"),
        })

    # 5. Regenerate dashboard (only when there are actual updates)
    if log["updates"] and not dry_run and regenerate:
        print(f"\n=== Regenerating dashboard ({len(log['updates'])} updates) ===")
        subprocess.run(["python", "create_chronos.py"], cwd=str(SCRIPT_DIR))
        subprocess.run(["python", "generate_dashboard.py"], cwd=str(SCRIPT_DIR))

    # 5b. Recapitulatif : sans ca un run ou 100% des fetchs echouent ressemble
    #     exactement a un run ou il n'y avait rien a collecter.
    from collections import Counter as _C
    reasons = _C(s["reason"] for s in log["skipped"])
    log["summary"] = {
        "wa_races": len(log["wa_races"]),
        "matched": len(matches),
        "updated": len(log["updates"]),
        "skipped": len(log["skipped"]),
        "errors": len(log["errors"]),
        "skip_reasons": dict(reasons),
        "mode": log.get("mode", "worldathletics_calendar"),
    }
    print(f"\n  --- Recap {date_str} ---")
    print(f"  WA races={len(log['wa_races'])}  matched={len(matches)}  "
          f"updated={len(log['updates'])}  skipped={len(log['skipped'])}  "
          f"errors={len(log['errors'])}")
    for r, n in reasons.most_common():
        print(f"    {n:3d}x {r}")
    if matches and not log["updates"]:
        print(f"  ATTENTION: {len(matches)} course(s) matchee(s), AUCUNE donnee recuperee.")

    # 6. Always save log + commit (even 0 updates) so every cron run is auditable
    log_path = LOGS_DIR / f"update_4d_{date_str}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"\n  Report saved: {log_path}")

    if not dry_run and commit:
        subprocess.run(["git", "add", "-A"], cwd=str(SCRIPT_DIR))
        n = len(log["updates"])
        s = log["summary"]
        if n > 0:
            msg = f"Auto Update 4D {date_str} — {n} update(s)"
        elif s["matched"] > 0:
            # cas le plus trompeur : des courses matchees mais rien de collecte
            msg = (f"Auto Update 4D {date_str} — 0 update / "
                   f"{s['matched']} matchee(s), {s['skipped']} echec(s)")
        else:
            msg = f"Auto Update 4D {date_str} — aucune course ce jour-la"
        _git_commit_et_pousse(msg)

    return log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="Target date (default: yesterday)")
    parser.add_argument("--from", dest="date_from", default=None,
                        help="Backfill: premiere date de la plage (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", default=None,
                        help="Backfill: derniere date de la plage (YYYY-MM-DD, defaut: hier)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    args = parser.parse_args()

    # --- Mode backfill : on balaie une plage de dates ---
    if args.date_from:
        d0 = datetime.date.fromisoformat(args.date_from)
        d1 = (datetime.date.fromisoformat(args.date_to) if args.date_to
              else datetime.date.today() - datetime.timedelta(days=1))
        if d1 < d0:
            print("ERREUR: --to est anterieur a --from")
            return 1
        ndays = (d1 - d0).days + 1
        print(f"=== BACKFILL {d0} -> {d1} ({ndays} jours) ===\n")
        all_updates = []
        for i in range(ndays):
            day = d0 + datetime.timedelta(days=i)
            try:
                # un seul regen + un seul commit a la fin de la plage
                log = run_one(day, dry_run=args.dry_run, regenerate=False, commit=False)
                all_updates.extend(log["updates"])
                if log.get("mode") == "fallback_no_calendar":
                    # Sans calendrier le balayage ne depend plus du jour mais du
                    # mois : une seule passe sur la date la plus tardive couvre
                    # toute la plage. Rejouer chaque jour serait redondant.
                    if day != d1:
                        print(f"  Mode repli : une seule passe, sur {d1}.")
                        log = run_one(d1, dry_run=args.dry_run,
                                      regenerate=False, commit=False)
                        all_updates.extend(log["updates"])
                    else:
                        print("  Mode repli : plage traitee en une passe.")
                    break
            except Exception as e:
                print(f"  [ERREUR] {day}: {e}")
            print()

        print(f"\n=== BACKFILL TERMINE : {len(all_updates)} mise(s) a jour ===")
        for u in all_updates:
            print(f"  {u['event']} {u['year']}: finishers={u.get('finishers')} "
                  f"avg={u.get('avg_time')} H={u.get('winner_men')} F={u.get('winner_women')}")

        if all_updates and not args.dry_run:
            print("\n=== Regeneration du dashboard ===")
            subprocess.run(["python", "create_chronos.py"], cwd=str(SCRIPT_DIR))
            subprocess.run(["python", "generate_dashboard.py"], cwd=str(SCRIPT_DIR))

        if not args.dry_run:
            subprocess.run(["git", "add", "-A"], cwd=str(SCRIPT_DIR))
            msg = f"Auto Update 4D backfill {d0} -> {d1} — {len(all_updates)} update(s)"
            _git_commit_et_pousse(msg)
        return 0

    # --- Mode normal : une seule date ---
    if args.date:
        target_date = datetime.date.fromisoformat(args.date)
    else:
        target_date = datetime.date.today() - datetime.timedelta(days=1)
    run_one(target_date, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())

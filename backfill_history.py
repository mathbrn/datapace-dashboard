#!/usr/bin/env python3
"""
Backfill History — Maximise le taux de remplissage du dashboard.

Parcourt chaque cellule vide (event × year) dans le fichier finishers
et tente de la remplir via les APIs disponibles.

Usage:
    python backfill_history.py --dry-run          # Rapport + preview
    python backfill_history.py                    # Remplissage reel
    python backfill_history.py --year 2024        # Cibler une seule annee
    python backfill_history.py --event "Paris"    # Cibler un seul event
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from collections import defaultdict, Counter

import openpyxl
import requests

# Force UTF-8 output on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

SCRIPT_DIR = Path(__file__).parent

# Import fetchers from auto_update_4d
sys.path.insert(0, str(SCRIPT_DIR))
from auto_update_4d import (
    fetch_timeto_4d, fetch_sporthive_4d, fetch_chronorace_4d, fetch_tracx_4d,
    fetch_mikatiming_4d, fetch_nyrr_4d, fetch_baa_4d, fetch_rtrt_4d, fetch_athlinks_4d,
)

PLATFORM_FETCHERS = {
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


# ==========================================================================
# DIAGNOSTIC
# ==========================================================================
def load_finishers_data():
    """Return (rows, year_cols). Each row has name, city, distance, hist (dict year→val)."""
    path = SCRIPT_DIR / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["ALL"]
    rows = []
    headers = None
    year_cols = []
    for row in ws.iter_rows(values_only=True):
        if headers is None:
            headers = list(row)
            year_cols = [c for c in headers if isinstance(c, int) and 2000 <= c <= 2030]
            continue
        d = dict(zip(headers, row))
        race = str(d.get("Race", "") or "").strip()
        if not race:
            continue
        hist = {}
        for yr in year_cols:
            v = d.get(yr)
            if v is None:
                hist[yr] = None
                continue
            if isinstance(v, str) and v.strip() in ("", "x", "-"):
                hist[yr] = v.strip() or None
                continue
            try:
                iv = int(float(v))
                hist[yr] = iv if iv > 0 else None
            except (ValueError, TypeError):
                hist[yr] = None
        rows.append({
            "name": race,
            "city": str(d.get("City", "") or "").strip(),
            "distance": str(d.get("Distance", "") or "").strip(),
            "period": str(d.get("Période", "") or "").strip(),
            "hist": hist,
        })
    wb.close()
    return rows, year_cols


def print_diagnostic(rows, year_cols):
    """ETAPE 1 — Rapport complet du taux de remplissage."""
    total = 0
    filled = 0
    empty_per_event = Counter()
    empty_per_year = Counter()
    for r in rows:
        for yr in year_cols:
            v = r["hist"].get(yr)
            # "x" = pre-first-edition, skip from stats
            if v == "x":
                continue
            total += 1
            if isinstance(v, int) and v > 0:
                filled += 1
            else:
                empty_per_event[r["name"]] += 1
                empty_per_year[yr] += 1

    print("=" * 70)
    print(f"DIAGNOSTIC DE REMPLISSAGE")
    print("=" * 70)
    print(f"Evenements suivis: {len(rows)}")
    print(f"Annees tracees:    {year_cols[0]} -> {year_cols[-1]} ({len(year_cols)} annees)")
    print(f"Cellules totales:  {total} (exclus les 'x' = pre-1ere-edition)")
    print(f"Remplies:          {filled} ({filled/total*100:.1f}%)")
    print(f"Vides:             {total - filled} ({(total-filled)/total*100:.1f}%)")
    print()
    print("--- Top 20 events avec le plus de cellules vides ---")
    for name, n in empty_per_event.most_common(20):
        print(f"  {n:3d} | {name}")
    print()
    print("--- Top 10 annees avec le plus de cellules vides ---")
    for yr, n in empty_per_year.most_common(10):
        print(f"  {yr}: {n} vides")


# ==========================================================================
# VALIDATION
# ==========================================================================
def validate_count(count, event_name=""):
    """Return (ok: bool, reason: str). Apply strict rules."""
    if not isinstance(count, int):
        return False, "not an integer"
    if count < 100:
        return False, f"trop faible ({count} < 100, probablement elite)"
    if count > 200_000:
        return False, f"trop eleve ({count} > 200000)"
    # Reject perfectly round numbers
    if count % 1000 == 0:
        return False, f"chiffre rond ({count}, probablement estimation)"
    return True, "ok"


# ==========================================================================
# BACKFILL
# ==========================================================================
def load_platform_map():
    path = SCRIPT_DIR / "event_platform_map.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(s):
    import unicodedata
    return unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()


def find_platform_entry(event_name, pmap):
    """Find the platform_map entry matching our event name.
    Requires EXACT match (lowercased + accents-stripped) to avoid
    fuzzy matching disasters like 'Harmonie Mutuelle Tours' → 'Run in Lyon'."""
    key = normalize(event_name)
    for _, info in pmap.items():
        ref = normalize(info.get("name", ""))
        if ref and ref == key:
            return info
    return None


def build_fetch_param(info, year):
    """Build the parameter to pass to the fetcher based on platform."""
    plat = info.get("platform")
    if plat == "mikatiming":
        code = info.get("event_code") or info.get("event_code_pattern", "MAL").format(yyyy=year)
        return {"subdomain": info.get("subdomain", ""), "event_code": code,
                "event_code_pattern": info.get("event_code_pattern", "MAL")}
    if plat == "sporthive":
        ids = info.get("sporthive_ids_by_year") or {}
        return ids.get(str(year))
    if plat == "chronorace":
        pattern = info.get("platform_id_pattern", "{yyyy}{mm}{dd}_rotterdam")
        # Without a date we can't build; return None
        return None
    if plat == "rtrt":
        return info.get("platform_id")  # e.g. "GR-NORTH"
    if plat == "athlinks":
        return info.get("platform_id")  # master_id
    if plat == "baa":
        return None
    if plat == "nyrr":
        return f"M{year}"
    if plat == "timeto":
        return None  # fetcher searches by name
    return info.get("platform_id")


def try_backfill(event_name, year, info, dry_run=True):
    """Try to fetch 4D data for an event+year via its platform."""
    plat = info.get("platform")
    fetcher = PLATFORM_FETCHERS.get(plat)
    if not fetcher:
        return None, f"no fetcher for {plat}"
    param = build_fetch_param(info, year)
    if param is None and plat in ("sporthive", "chronorace"):
        return None, f"{plat}: platform_id manquant pour {year}"
    try:
        # Use the MAPPED name from platform_map (info['name']), not the Excel row name.
        # This avoids sending alias names to the fetcher.
        lookup_name = info.get("name", event_name)
        if plat == "timeto":
            result = fetcher(lookup_name, year)
        else:
            result = fetcher(param, year)
    except Exception as e:
        return None, f"exception: {e}"
    if not result:
        return None, "no data"
    return result, "ok"


def apply_finishers(event_name, distance, year, count, dry_run):
    """Call update_finishers.py to write the finisher count."""
    dist_code = {"MARATHON": "MARATHON", "SEMI": "SEMI", "10KM": "10KM",
                 "AUTRE": "AUTRE"}.get(distance, distance or "MARATHON")
    if dry_run:
        print(f"    [DRY] update_finishers: {event_name} {dist_code} {year} = {count}")
        return True
    r = subprocess.run(
        ["python", "update_finishers.py", event_name, dist_code, str(year), str(count)],
        cwd=str(SCRIPT_DIR), capture_output=True, text=True)
    print(f"    {r.stdout.strip()[:200]}")
    return r.returncode == 0


# ==========================================================================
# MAIN
# ==========================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--event", default=None)
    parser.add_argument("--min-year", type=int, default=2015)
    parser.add_argument("--max-year", type=int, default=2026)
    parser.add_argument("--max-calls", type=int, default=200,
                        help="Limite de safety sur le nombre d'appels API")
    args = parser.parse_args()

    rows, year_cols = load_finishers_data()

    # ETAPE 1 — diagnostic
    print_diagnostic(rows, year_cols)

    # ETAPE 2 — backfill
    pmap = load_platform_map()
    target_events = [r for r in rows
                     if (not args.event or normalize(args.event) in normalize(r["name"]))]
    target_years = [y for y in year_cols
                    if (args.min_year <= y <= args.max_year)
                    and (not args.year or y == args.year)]

    # Identify cells to fill (only those with an API-mappable platform)
    tasks = []
    for r in target_events:
        info = find_platform_entry(r["name"], pmap)
        if not info or not info.get("platform"):
            continue
        if info["platform"] not in PLATFORM_FETCHERS:
            continue
        for yr in target_years:
            v = r["hist"].get(yr)
            # Skip filled and 'x' cells
            if v == "x" or (isinstance(v, int) and v > 0):
                continue
            tasks.append({"event": r, "year": yr, "info": info})

    print()
    print("=" * 70)
    print(f"BACKFILL — {len(tasks)} cellules vides candidates")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'REEL'}")
    print(f"Limite API: {args.max_calls} appels")
    print("=" * 70)

    report = {"filled": [], "rejected": [], "no_data": [], "errors": []}
    calls = 0
    for t in tasks:
        if calls >= args.max_calls:
            print(f"\n[LIMITE] {args.max_calls} appels atteinte — arret.")
            break
        r = t["event"]
        yr = t["year"]
        plat = t["info"]["platform"]
        calls += 1
        print(f"\n[{calls}/{min(len(tasks), args.max_calls)}] {r['name']} {yr} via {plat}")
        result, msg = try_backfill(r["name"], yr, t["info"], args.dry_run)
        if not result:
            report["no_data"].append({"event": r["name"], "year": yr,
                                       "platform": plat, "reason": msg})
            print(f"    -> {msg}")
            continue
        count = result.get("finishers")
        if not count:
            report["no_data"].append({"event": r["name"], "year": yr,
                                       "platform": plat, "reason": "no finishers in response"})
            continue
        ok, reason = validate_count(count, r["name"])
        if not ok:
            report["rejected"].append({"event": r["name"], "year": yr,
                                        "platform": plat, "count": count, "reason": reason})
            print(f"    -> REJETE: {reason}")
            continue
        # Apply
        ok = apply_finishers(r["name"], r["distance"], yr, count, args.dry_run)
        if ok:
            report["filled"].append({"event": r["name"], "year": yr,
                                      "platform": plat, "count": count,
                                      "source": result.get("source", plat),
                                      "confidence": result.get("confidence", "medium")})

    # ETAPE 5 — rapport final
    print()
    print("=" * 70)
    print("RAPPORT FINAL")
    print("=" * 70)
    print(f"Remplies:       {len(report['filled'])}")
    print(f"Rejetees:       {len(report['rejected'])}")
    print(f"Pas de donnees: {len(report['no_data'])}")
    print(f"Appels API:     {calls}")
    if report["filled"]:
        print()
        print("--- Cellules remplies (top 20) ---")
        for f in report["filled"][:20]:
            print(f"  {f['event']:45s} {f['year']} = {f['count']:>6} ({f['platform']}, {f['confidence']})")
    if report["rejected"]:
        print()
        print("--- Rejetees (top 10) ---")
        for r in report["rejected"][:10]:
            print(f"  {r['event']:45s} {r['year']} {r['count']:>6} -> {r['reason']}")

    # Save report
    (SCRIPT_DIR / "logs").mkdir(exist_ok=True)
    out = SCRIPT_DIR / "logs" / f"backfill_{datetime.date.today().isoformat()}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nRapport sauvegarde: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

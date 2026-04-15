#!/usr/bin/env python3
"""
WebFetch History — Helper pour appliquer des donnees historiques recuperees
manuellement (Wikipedia, sites officiels) avec verification stricte.

REGLE ABSOLUE: avant toute application/requete pour (event, year),
verifier dans Excel que la cellule est REELLEMENT vide.

Usage:
    python webfetch_history.py < input.json
    # ou en programmatique:
    from webfetch_history import apply_data, is_empty, load_existing_data
"""
import json
import subprocess
import sys
from pathlib import Path
import openpyxl

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

SCRIPT_DIR = Path(__file__).parent


def load_existing_data():
    """Charge toute la matrice Excel pour verif O(1)."""
    path = SCRIPT_DIR / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["ALL"]
    headers = None
    year_cols = []
    existing = {}
    for row in ws.iter_rows(values_only=True):
        if headers is None:
            headers = list(row)
            year_cols = [c for c in headers if isinstance(c, int) and 2000 <= c <= 2030]
            continue
        d = dict(zip(headers, row))
        race = str(d.get("Race", "") or "").strip()
        if not race:
            continue
        for yr in year_cols:
            existing[(race, yr)] = d.get(yr)
    wb.close()
    return existing


def is_empty(event_name, year, existing):
    """True ssi cellule strictement vide. Tout autre contenu = NON vide."""
    v = existing.get((event_name, year))
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def validate_count(count):
    """Strict validation."""
    if not isinstance(count, int):
        return False, "not int"
    if count < 100:
        return False, f"trop faible ({count})"
    if count > 200_000:
        return False, f"trop eleve ({count})"
    if count % 1000 == 0:
        return False, f"chiffre rond ({count})"
    return True, "ok"


def apply_data(items, dry_run=False):
    """Apply a list of {event, distance, year, count, source} entries.
    Pre-checks Excel emptiness BEFORE any write."""
    existing = load_existing_data()
    applied, skipped, rejected = 0, 0, 0
    for it in items:
        name, dist = it["event"], it["distance"]
        year, count, source = it["year"], it["count"], it.get("source", "?")
        # PRE-CHECK ABSOLU
        if not is_empty(name, year, existing):
            current = existing.get((name, year))
            print(f"  [SKIP] {name} {year} deja rempli ({current!r})")
            skipped += 1
            continue
        ok, reason = validate_count(count)
        if not ok:
            print(f"  [REJET] {name} {year} = {count} ({reason})")
            rejected += 1
            continue
        if dry_run:
            print(f"  [DRY] {name} {dist} {year} = {count} (source: {source})")
            applied += 1
            continue
        r = subprocess.run(
            ["python", "update_finishers.py", name, dist, str(year), str(count)],
            capture_output=True, text=True)
        out = r.stdout.strip()[:120]
        print(f"  {name} {year} = {count} -> {out}")
        if r.returncode == 0:
            applied += 1
    print(f"\nApplied: {applied}, Skipped: {skipped}, Rejected: {rejected}")
    return applied, skipped, rejected


if __name__ == "__main__":
    data = json.load(sys.stdin)
    apply_data(data.get("items", data), dry_run=("--dry-run" in sys.argv))

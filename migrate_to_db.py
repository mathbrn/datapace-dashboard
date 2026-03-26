#!/usr/bin/env python3
"""
Migration Excel → SQLite
=========================
Lit tous les fichiers Excel et JSON existants et peuple la base SQLite.
Peut etre relance sans risque (upsert).

Usage:
    python migrate_to_db.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
import datetime
import pandas as pd
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from datapace.config import FILES, DATA_DIR, ASO_KEYWORDS, WMM_KEYWORDS, DB_FILE
from datapace.database import init_db, get_db, get_or_create_event, upsert_finisher, upsert_winner, upsert_avg_time, log_crawl, get_stats

# Allow overriding DB path via env var (useful when mounted FS doesn't support SQLite)
import os as _os
_DB_PATH = Path(_os.environ.get("DATAPACE_DB", str(DB_FILE)))


def detect_badge(name: str) -> str:
    """Detecte le badge (WMM, ASO, Autre) d'un evenement."""
    low = name.lower()
    if any(k in low for k in WMM_KEYWORDS):
        return "WMM"
    if any(k in low for k in ASO_KEYWORDS):
        return "ASO"
    return "Autre"


def migrate_finishers(conn):
    """Migre l'onglet ALL du fichier finishers."""
    path = FILES["finishers"]
    if not path.exists():
        print(f"  SKIP: {path.name} non trouve")
        return 0

    df = pd.read_excel(path, sheet_name="ALL")
    year_cols = sorted([c for c in df.columns if isinstance(c, int) and 2000 <= c <= 2030])
    count = 0

    for _, r in df.iterrows():
        race = str(r.get("Race", "")).strip()
        if not race or race == "nan":
            continue

        period = str(r.get("Période", "")).strip()
        city = str(r.get("City", "")).strip()
        distance = str(r.get("Distance", "")).strip()

        if distance not in ("MARATHON", "SEMI", "10KM", "AUTRE"):
            continue

        badge = detect_badge(race)
        event_id = get_or_create_event(conn, race, distance, city, period, badge)

        for yr in year_cols:
            v = r.get(yr)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            sv = str(v).strip()
            if sv == "-":
                upsert_finisher(conn, event_id, yr, -1, source="excel", skip_existing=False)
                count += 1
            elif sv.lower() == "elite":
                upsert_finisher(conn, event_id, yr, -2, source="excel", skip_existing=False)
                count += 1
            elif sv.lower() == "x":
                # Event did not exist yet — skip, no entry needed
                pass
            else:
                try:
                    iv = int(float(v))
                    if iv > 0:
                        upsert_finisher(conn, event_id, yr, iv, source="excel", skip_existing=False)
                        count += 1
                except (ValueError, TypeError):
                    pass

    return count


def migrate_winners(conn):
    """Migre le fichier Chronos_Vainqueurs.xlsx."""
    path = FILES["winners"]
    if not path.exists():
        print(f"  SKIP: {path.name} non trouve")
        return 0

    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    count = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        course, distance, year, men, women = row
        if not course:
            continue

        race_name = str(course).strip()
        dist_map = {"42K": "MARATHON", "21K": "SEMI", "10K": "10KM"}
        db_dist = dist_map.get(str(distance), "AUTRE")

        event_id = get_or_create_event(conn, race_name, db_dist)

        men_t = str(men) if men and str(men) not in ("N/A", "Annule", "Annulé", "None") else None
        women_t = str(women) if women and str(women) not in ("N/A", "Annule", "Annulé", "None") else None

        if men_t or women_t:
            upsert_winner(conn, event_id, int(year), men_t, women_t, source="chronos_xlsx")
            count += 1

    return count


def migrate_avg_times(conn):
    """Migre les temps moyens depuis les Excel marathon + semi."""
    count = 0

    # Marathon files
    for year in [2024, 2025, 2026]:
        key = f"marathon_{year}"
        path = FILES.get(key)
        if not path or not path.exists():
            continue

        if year == 2024:
            df = pd.read_excel(path, header=None)
            for _, r in df.iterrows():
                vals = r.tolist()
                race = avg = None
                for v in vals:
                    if isinstance(v, str) and len(v) > 4 and v not in ("nan", "RACE", "Race"):
                        race = v.strip()
                    elif isinstance(v, datetime.time):
                        avg = v.strftime("%H:%M:%S")
                if race and avg:
                    eid = get_or_create_event(conn, race, "MARATHON")
                    upsert_avg_time(conn, eid, year, avg_time=avg, source="excel_marathon")
                    count += 1
        else:
            df = pd.read_excel(path, sheet_name="Finishers", header=None)
            if len(df.columns) >= 10:
                df.columns = ["_", "city", "race", "finishers", "avg_time", "best",
                              "men_time", "women_time", "top10_avg", "sub3"]
                for _, r in df.iloc[3:].iterrows():
                    race = str(r["race"]).strip() if pd.notna(r["race"]) else ""
                    if not race or race in ("nan", "Race"):
                        continue
                    avg = fmt_time(r.get("avg_time"))
                    men = fmt_time(r.get("men_time"))
                    women = fmt_time(r.get("women_time"))
                    if avg or men or women:
                        eid = get_or_create_event(conn, race, "MARATHON")
                        upsert_avg_time(conn, eid, year, avg, men, women, source="excel_marathon")
                        count += 1

    # Semi file (multi-sheet)
    path = FILES.get("semi")
    if path and path.exists():
        xls = pd.ExcelFile(path)
        for sheet in xls.sheet_names:
            try:
                yr = int(sheet)
            except ValueError:
                continue
            df = pd.read_excel(path, sheet_name=sheet, header=None)
            if len(df.columns) < 8:
                df = df.reindex(columns=range(8))
            df.columns = ["_", "city", "race", "finishers", "avg_time", "men_time", "women_time", "top10_avg"]
            for _, r in df.iloc[3:].iterrows():
                race = str(r["race"]).strip() if pd.notna(r["race"]) else ""
                if not race or race in ("nan", "Race"):
                    continue
                avg = fmt_time(r.get("avg_time"))
                men = fmt_time(r.get("men_time"))
                women = fmt_time(r.get("women_time"))
                if avg or men or women:
                    eid = get_or_create_event(conn, race, "SEMI")
                    upsert_avg_time(conn, eid, yr, avg, men, women, source="excel_semi")
                    count += 1

    return count


def migrate_sporthive_avg(conn):
    """Migre les temps moyens calcules depuis Sporthive API."""
    path = DATA_DIR / "avg_times_sporthive.json"
    if not path.exists():
        return 0

    with open(path, "r") as f:
        data = json.load(f)

    count = 0
    for item in data:
        race = item.get("race", "")
        year = item.get("year", 0)
        avg = item.get("avg_time", "")
        if race and year and avg:
            eid = get_or_create_event(conn, race, "MARATHON")  # best guess
            upsert_avg_time(conn, eid, year, avg_time=avg, source="sporthive_api")
            count += 1

    return count


def migrate_crawl_results(conn):
    """Migre les resultats de crawl dans la table crawl_log."""
    count = 0
    sources = [
        ("sporthive_crawl_results.json", "sporthive"),
        ("tracx_crawl_results.json", "tracx"),
        ("athlinks_crawl_results.json", "athlinks"),
    ]

    for filename, source in sources:
        path = DATA_DIR / filename
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for r in data:
            log_crawl(
                conn,
                source=source,
                event_name=r.get("event_name", r.get("race_name", "")),
                race_name=r.get("race_name", ""),
                distance_m=r.get("distance_m", 0),
                year=r.get("year", int(r.get("date", "0000")[:4]) if r.get("date") else 0),
                finishers=r.get("finishers", 0),
                avg_time=r.get("avg_time"),
                raw_json=json.dumps(r, ensure_ascii=False),
            )
            count += 1

    return count


def fmt_time(val):
    """Convertit une valeur Excel en format HH:MM:SS."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime.time):
        return val.strftime("%H:%M:%S")
    if isinstance(val, float) and 0 < val < 1:
        total_seconds = int(round(val * 86400))
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    s = str(val).strip()
    return None if s in ("", "nan", "NaT", "None") else s


def main():
    print("\n╔══════════════════════════════════════╗")
    print("║   DataPace — Migration Excel → DB    ║")
    print("╚══════════════════════════════════════╝\n")

    init_db(_DB_PATH)

    with get_db(_DB_PATH) as conn:
        print("Migration des finishers...")
        n = migrate_finishers(conn)
        print(f"  → {n} entrees finishers")

        print("Migration des chronos vainqueurs...")
        n = migrate_winners(conn)
        print(f"  → {n} entrees winners")

        print("Migration des temps moyens (Excel)...")
        n = migrate_avg_times(conn)
        print(f"  → {n} entrees avg times")

        print("Migration des temps moyens (Sporthive API)...")
        n = migrate_sporthive_avg(conn)
        print(f"  → {n} entrees Sporthive avg")

        print("Migration des resultats de crawl...")
        n = migrate_crawl_results(conn)
        print(f"  → {n} entrees crawl log")

    print("\n── Statistiques finales ──")
    stats = get_stats(_DB_PATH)
    for key, val in stats.items():
        if key != "sources":
            print(f"  {key}: {val}")
    if stats.get("sources"):
        print("  Sources crawl:")
        for src, cnt in stats["sources"].items():
            print(f"    {src}: {cnt}")

    print(f"\nBase SQLite: {_DB_PATH}")
    print(f"Taille: {_DB_PATH.stat().st_size / 1024:.0f} Ko\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Journal des ajouts de donnees, source unique des notifications du dashboard.

Toute ecriture dans le dashboard — finishers, temps moyen, chronos vainqueurs —
doit passer par log_update(), qu'elle vienne de l'Update 4D automatique ou d'un
ajout manuel. Le dashboard lit update_log.json et affiche une notification par
entree.

Usage en ligne de commande (ajouts manuels) :
    python update_log.py "Nom de l'epreuve" --finishers 36259
    python update_log.py "Nom" --men 2:04:42 --women 2:18:31 --avg 4:13:24
    python update_log.py "Nom" --date 2026-08-30 --finishers 36259
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

CHEMIN = Path(__file__).parent / "update_log.json"
MAX_ENTREES = 200  # un gros rattrapage doit tenir entier, sinon les comptes du resume sont faux


def log_update(event_name, event_date, data, dry_run=False):
    """Ajoute une entree en tete du journal (max 20, dedoublonnee event+date)."""
    data = {k: v for k, v in (data or {}).items() if v not in (None, "", 0)}
    if not data:
        return False
    log = {"updates": []}
    if CHEMIN.exists():
        try:
            with open(CHEMIN, "r", encoding="utf-8") as f:
                log = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    log["updates"] = [u for u in log.get("updates", [])
                      if not (u.get("event") == event_name
                              and u.get("date") == event_date)]
    log["updates"].insert(0, {
        "event": event_name,
        "date": event_date,
        "data": data,
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    log["updates"] = log["updates"][:MAX_ENTREES]
    if not dry_run:
        with open(CHEMIN, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"  notification: {event_name} {event_date} -> {list(data.keys())}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("event")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--finishers", type=int)
    ap.add_argument("--avg", dest="avg_time")
    ap.add_argument("--men", dest="winner_men")
    ap.add_argument("--women", dest="winner_women")
    a = ap.parse_args()
    ok = log_update(a.event, a.date, {
        "finishers": a.finishers, "avg_time": a.avg_time,
        "winner_men": a.winner_men, "winner_women": a.winner_women,
    })
    if not ok:
        print("Rien a journaliser : aucune donnee fournie.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

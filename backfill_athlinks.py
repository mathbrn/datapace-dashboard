#!/usr/bin/env python3
"""Rattrapage de l'historique Athlinks, toutes annees.

Une seule requete par epreuve suffit : `alaython alaska.athlinks.com/Events/Race/
Api/{raceId}/Course/0` rend `MasterEvent.EventRaces`, l'historique complet —
jusqu'a 54 editions — avec pour chacune sa date et le detail de ses courses.
Le mode repli de `auto_update_4d.py` ne regarde que l'annee en cours ; ce
script-ci balaie toutes les annees de l'onglet ALL.

Les regles du dashboard s'appliquent telles quelles :
- une cellule deja remplie n'est jamais ecrasee (protection de
  `update_finishers.py`) ;
- la course est choisie par sa distance en metres, jamais « la plus grosse » ;
- virtuels, relais, courses annexes et courses a moins de dix resultats
  ecartes ;
- les chiffres ronds (multiples de 500) sont refuses, comme partout.

Usage :
    python backfill_athlinks.py [--dry-run] [--depuis 2000]
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import openpyxl
import requests

import auto_update_4d as a

SCRIPT_DIR = Path(__file__).parent
EXCEL = SCRIPT_DIR / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx"


def series_connues():
    """{(nom, distance): {annee: valeur}} des cellules deja remplies."""
    wb = openpyxl.load_workbook(EXCEL, read_only=True)
    ws = wb["ALL"]
    entetes = [c for c in next(ws.iter_rows(max_row=1, values_only=True))]
    cols = {y: i for i, y in enumerate(entetes) if isinstance(y, int)}
    series = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        nom, dist = row[3], row[2]
        if not nom or not dist:
            continue
        cle = (str(nom).replace("\xa0", " ").strip(), dist)
        series[cle] = {y: row[i] for y, i in cols.items()
                       if isinstance(row[i], int) and row[i] > 0}
    return series


def vraisemblable(serie, annee, n, mini=0.4, maxi=3.0):
    """Le chiffre tient-il dans la serie connue de l'epreuve ?

    Athlinks ne detient pour certaines editions anciennes qu'un import
    **partiel** : 4 582 arrivants pour la Peachtree Road Race 2000, qui en
    compte 50 000, et 778 pour Lilac Bloomsday 2008, qui en compte 48 000. Le
    `ResultCount` est le nombre de resultats qu'ils possedent, pas le nombre
    d'arrivants de la course. Sur les annees ou le dashboard a deja une valeur,
    l'API tombe au coureur pres (ecart median 0,0 % sur les dix epreuves), donc
    la serie connue est une reference fiable : on compare le candidat a la
    mediane des trois annees connues les plus proches.
    """
    if not serie:
        return True, "aucune reference"
    proches = sorted(serie, key=lambda y: abs(y - annee))[:3]
    ref = sorted(serie[y] for y in proches)[len(proches) // 2]
    if not ref:
        return True, "reference nulle"
    r = n / ref
    if r < mini:
        return False, f"{r:.0%} de la reference {ref} ({proches}) — import partiel"
    if r > maxi:
        return False, f"{r:.0%} de la reference {ref} ({proches}) — invraisemblable"
    return True, f"{r:.0%} de la reference {ref}"


def cellules_vides(depuis):
    """{(nom, distance): [annees vides]} pour l'onglet ALL."""
    wb = openpyxl.load_workbook(EXCEL, read_only=True)
    ws = wb["ALL"]
    entetes = [c for c in next(ws.iter_rows(max_row=1, values_only=True))]
    cols = {y: i for i, y in enumerate(entetes) if isinstance(y, int)}
    vides = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        nom, dist = row[3], row[2]
        if not nom or not dist:
            continue
        manquantes = [y for y, i in sorted(cols.items())
                      if y >= depuis and row[i] in (None, "")]
        if manquantes:
            vides[(str(nom).replace("\xa0", " ").strip(), dist)] = manquantes
    return vides


def course_de_lannee(editions, annee, dist_code):
    """La course visee pour une annee, ou None."""
    cible = [e for e in editions if (e.get("RaceDate") or "").startswith(str(annee))]
    if not cible:
        return None
    courses = []
    for e in cible:
        for c in (e.get("EventCourses") or []):
            if c.get("IsVirtual"):
                continue
            nom = (c.get("CourseName") or "").lower()
            if any(mot in nom for mot in a.COURSES_ANNEXES):
                continue
            if (c.get("ResultCount") or 0) < 10:
                continue
            courses.append(c)
    if not courses:
        return None
    courses = a.sans_variantes(courses, lambda c: c.get("CourseName") or "")
    return a.pick_race_for_distance(
        courses, dist_code,
        get_distance_m=lambda c: c.get("DistUnit"),
        get_title=lambda c: c.get("CourseName") or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--depuis", type=int, default=2000)
    args = ap.parse_args()

    carte = json.load(open(SCRIPT_DIR / "event_platform_map.json", encoding="utf-8"))
    series = series_connues()
    epreuves = [v for v in carte.values()
                if v.get("platform") == "athlinks" and v.get("race_id")]
    vides = cellules_vides(args.depuis)

    sess = requests.Session()
    sess.headers.update(a.ATHLINKS_HEADERS)
    ecrites, refusees, introuvables = 0, [], 0

    for ev in epreuves:
        nom, dist = ev["name"], ev.get("distance")
        annees = vides.get((nom, dist), [])
        if not annees:
            print(f"== {nom} [{dist}] : aucune cellule vide")
            continue
        # La cible en metres des epreuves AUTRE est lue dans la carte.
        a.__dict__["_CIBLE_AUTRE_M"] = ev.get("distance_m")
        editions = a._athlinks_editions(sess, ev["race_id"], ev.get("master_id")
                                        or ev.get("platform_id"))
        if not editions:
            print(f"== {nom} [{dist}] : historique injoignable")
            continue
        dispo = sorted({(e.get("RaceDate") or "")[:4] for e in editions}, reverse=True)
        print(f"== {nom} [{dist}] : {len(editions)} editions "
              f"({dispo[-1]}-{dispo[0]}), {len(annees)} cellule(s) vide(s)")
        for annee in annees:
            c = course_de_lannee(editions, annee, dist)
            if not c:
                introuvables += 1
                continue
            n = c.get("ResultCount") or 0
            ok, motif = vraisemblable(series.get((nom, dist), {}), annee, n)
            if not ok:
                refusees.append((nom, annee, n, motif))
                print(f"   {annee} : {n} REFUSE ({motif})")
                continue
            if n % 500 == 0:
                refusees.append((nom, annee, n, "chiffre rond"))
                print(f"   {annee} : {n} REFUSE (chiffre rond)")
                continue
            print(f"   {annee} : {n} ({c.get('CourseName')!r}, "
                  f"{c.get('DistUnit')} m)")
            if args.dry_run:
                continue
            r = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "update_finishers.py"),
                 nom, dist, str(annee), str(n)],
                capture_output=True, text=True)
            if "[SKIP]" in r.stdout:
                print(f"      {r.stdout.strip().splitlines()[0]}")
            elif "[NOUVEAU]" in r.stdout:
                ecrites += 1
        time.sleep(2)

    print(f"\n--- Recap : {ecrites} cellule(s) ecrite(s), "
          f"{len(refusees)} refusee(s), {introuvables} annee(s) sans course "
          f"identifiable")
    for x in refusees:
        print("   refuse:", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())

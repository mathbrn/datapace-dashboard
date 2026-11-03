#!/usr/bin/env python3
"""Rattrapage de l'historique, toutes plateformes et toutes annees.

`auto_update_4d.py` ne regarde que l'annee en cours, meme en mode repli : une
cellule de 2013 restee vide ne sera jamais tentee. Ce script-ci parcourt, pour
chaque epreuve de `event_platform_map.json` dont la plateforme a un fetcher,
**toutes** les annees vides de l'onglet ALL et appelle le fetcher sur chacune.

`backfill_athlinks.py` fait la meme chose pour Athlinks, mais en une requete
par epreuve : l'API alaska rend l'historique complet d'un bloc. Les autres
plateformes n'ont pas d'equivalent, il faut une requete par annee — d'ou un
script separe, plus lent, et le parametre --plateformes pour le cibler.

Garde-fous, identiques a ceux d'athlinks :
- une cellule deja remplie n'est jamais ecrasee ;
- les chiffres ronds (multiples de 500) sont refuses ;
- `vraisemblable()` compare le candidat a la mediane des trois annees connues
  les plus proches et refuse en dessous de 40 % ou au-dela de 300 %. Les APIs
  ne detiennent pas toujours un classement complet pour les editions
  anciennes, et un import partiel ressemble a une petite edition.

Usage :
    python backfill_toutes_annees.py --dry-run
    python backfill_toutes_annees.py --plateformes tracx,sporthive
"""
import argparse
import inspect
import sys
import time

import auto_update_4d as a
from backfill_athlinks import cellules_vides, series_connues, vraisemblable

# Athlinks a son script dedie, bien plus econome en requetes.
EXCLUES = {"athlinks"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--depuis", type=int, default=2000)
    ap.add_argument("--plateformes", default="",
                    help="liste separee par des virgules ; defaut : toutes "
                         "celles qui ont un fetcher, sauf athlinks")
    args = ap.parse_args()

    carte = a._load_platform_map()
    voulues = {p.strip() for p in args.plateformes.split(",") if p.strip()}
    series = series_connues()
    vides = cellules_vides(args.depuis)

    ecrites, refusees, vains = 0, [], 0
    for ev in carte.values():
        plat = ev.get("platform")
        if not plat or plat in EXCLUES or plat not in a.PLATFORM_MAP:
            continue
        if voulues and plat not in voulues:
            continue
        nom, dist = ev.get("name"), ev.get("distance")
        annees = vides.get((nom, dist), [])
        if not annees:
            continue
        print(f"\n== {nom} [{dist}] via {plat} : {len(annees)} annee(s) vide(s)")
        fetcher = a.PLATFORM_MAP[plat]
        prend_dist = "dist_code" in inspect.signature(fetcher).parameters
        for annee in annees:
            a.__dict__["_CIBLE_AUTRE_M"] = ev.get("distance_m")
            _, info = a.discover_platform(nom, annee)
            try:
                r = (fetcher(info or nom, annee, dist_code=dist) if prend_dist
                     else fetcher(info or nom, annee))
            except Exception as e:
                print(f"   {annee} : erreur {type(e).__name__}: {str(e)[:80]}")
                continue
            n = (r or {}).get("finishers")
            if not n:
                vains += 1
                continue
            ok, motif = vraisemblable(series.get((nom, dist), {}), annee, n)
            if not ok:
                refusees.append((nom, annee, n, motif))
                print(f"   {annee} : {n} REFUSE ({motif})")
                continue
            if n % 500 == 0:
                refusees.append((nom, annee, n, "chiffre rond"))
                print(f"   {annee} : {n} REFUSE (chiffre rond)")
                continue
            print(f"   {annee} : {n} finishers")
            if args.dry_run:
                continue
            if a.update_finishers(nom, dist, annee, n):
                ecrites += 1
                series.setdefault((nom, dist), {})[annee] = n
            if r.get("winner_men") or r.get("winner_women"):
                a.update_winners(nom, annee, dist, r.get("winner_men"),
                                 r.get("winner_women"))
            if r.get("avg_time") and ev.get("distance_m"):
                a.update_avg_time(nom, annee, ev["distance_m"], n,
                                  r["avg_time"], r.get("avg_speed_kmh"))
            time.sleep(1)

    print(f"\n--- Recap : {ecrites} cellule(s) ecrite(s), {len(refusees)} "
          f"refusee(s), {vains} annee(s) sans donnee")
    for x in refusees:
        print("   refuse:", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Temps moyens et chronos vainqueurs du Maraton Warszawski, depuis les PDF.

STS-Timing ne publie pas de classement complet exploitable en HTML : la page
`tabela.php` est un tableau live de dix lignes, `index.php` n'en rend que 200
sans parametre de pagination, et `wyniki.php` est un formulaire de recherche.
Le classement officiel complet est en revanche dans un PDF, un par edition.

`pdftotext -layout` en rend des lignes de la forme :

     1   M2  Takeuchi Ryoma   Warszawa   ...  JPN  1992  M30  1  2:11:21  2:11:21  1
   Pos. Bib  Nom              Ville           Pays AnNais Cat MsCat brut  net     K/M

Le sexe se lit dans la categorie (M30 / K30), le temps retenu est le net.
**Cinq lignes sur 9 539 n'ont ni categorie ni rang de sexe** (finishers sans
groupe d'age) : elles comptent dans le total et dans la moyenne, mais pas dans
les vainqueurs, d'ou deux motifs de lecture distincts.

Controle : l'edition 2025 rend 9 544 arrivants et 2:11:21 / 2:33:41, soit
exactement les valeurs deja en base, venues d'une autre source.

Les PDF pesent jusqu'a 48 Mo : chacun est supprime apres lecture.

Usage :
    python backfill_warszawski.py [--dry-run] [--annees 2016-2025]
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

import requests

import auto_update_4d as a

EPREUVE = "NN Maraton Warszawski"
DIST, DIST_M = "MARATHON", 42195
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
# Le nom du PDF a change trois fois en dix ans.
NOMS = ("WynikiMaraton.pdf", "mw{annee}.pdf")

# Ligne de resultat complete, avec categorie et rang de sexe.
AVEC_CAT = re.compile(r"^\s*(\d{1,5})\s+\S+\s+.*?\s([MK])\d{2}\s+\d+\s+"
                      r"(\d{1,2}:\d{2}:\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+\d+\s*$")
# Ligne sans categorie : on ne garde que le rang et les deux temps.
SANS_CAT = re.compile(r"^\s*(\d{1,5})\s+\S+\s+.*?\s"
                      r"(\d{1,2}:\d{2}:\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s*$")


def sec(t):
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s


def hms(n):
    return "%02d:%02d:%02d" % (n // 3600, n % 3600 // 60, n % 60)


def lire_pdf(chemin):
    """(rang max, moyenne nette, vainqueur H, vainqueur F) ou None."""
    txt = subprocess.run(["pdftotext", "-layout", chemin, "-"],
                         capture_output=True, text=True, errors="replace").stdout
    rangs, nets, hommes, femmes = set(), [], [], []
    for ligne in txt.splitlines():
        m = AVEC_CAT.match(ligne)
        if m:
            rangs.add(int(m.group(1)))
            nets.append(sec(m.group(4)))
            (hommes if m.group(2) == "M" else femmes).append(sec(m.group(4)))
            continue
        m = SANS_CAT.match(ligne)
        if m:
            rangs.add(int(m.group(1)))
            nets.append(sec(m.group(3)))
    if not rangs or not nets:
        return None
    return (max(rangs), hms(round(sum(nets) / len(nets))),
            hms(min(hommes)) if hommes else None,
            hms(min(femmes)) if femmes else None, len(nets))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--annees", default="2016-2025")
    args = ap.parse_args()
    d, f = (int(x) for x in args.annees.split("-"))

    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    ecrits = 0
    for annee in range(d, f + 1):
        url = None
        for motif in NOMS:
            u = f"https://live.sts-timing.pl/mw{annee}/{motif.format(annee=annee)}"
            if s.head(u, timeout=20, allow_redirects=True).status_code == 200:
                url = u
                break
        if not url:
            print(f"{annee} : aucun PDF de resultats")
            continue
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            r = s.get(url, timeout=300)
            tmp.write(r.content)
            tmp.close()
            lu = lire_pdf(tmp.name)
        finally:
            os.unlink(tmp.name)
        if not lu:
            print(f"{annee} : PDF illisible ({url.rsplit('/', 1)[-1]})")
            continue
        total, moy, hh, ff, n = lu
        print(f"{annee} : {total} arrivants ({n} chronos lus), moyenne {moy}, "
              f"H {hh}, F {ff}")
        if args.dry_run:
            continue
        if hh or ff:
            a.update_winners(EPREUVE, annee, DIST, hh, ff)
        if moy:
            a.update_avg_time(EPREUVE, annee, DIST_M, n, moy, None)
        ecrits += 1
    print(f"\n--- {ecrits} edition(s) traitee(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

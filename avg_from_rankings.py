#!/usr/bin/env python3
"""Temps moyen calcule sur le classement complet.

Pourquoi ce script : sur les neuf plateformes dont `auto_update_4d.py` sait
lire les finishers, deux seulement produisent un temps moyen — sporthive, qui
publie `raceStatistics.averageSpeedInKmh`, et timeto, dont l'API rend tous les
resultats en une requete. Les sept autres renvoient `avg_time: None` par
construction, ce qui explique les 218 temps moyens du dashboard pour 1934
lignes. Ici on va chercher TOUS les chronos du classement, page apres page, et
on en fait la moyenne.

    python avg_from_rankings.py "BMW Berlin Marathon" MARATHON 2026
    python avg_from_rankings.py "BMW Berlin Marathon" MARATHON 2026 --dry-run

L'ecriture se fait dans `avg_times_sporthive.json` (jamais d'ecrasement, comme
`update_avg_time`) et produit une notification via `update_log.py`.

Adaptateurs : mikatiming, chronorace, tracx. La plateforme et ses parametres
viennent de `event_platform_map.json`.
"""

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent

NAVIGATEUR = {
    # « Mozilla/5.0 » seul est une signature de bot : mikatiming repond 403.
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8,fr;q=0.7",
}

# Bornes de plausibilite, en secondes. Le plancher ecarte les fauteuils et
# handbikes, qui courent bien plus vite et tireraient la moyenne vers le bas ;
# le plafond ecarte les chronos aberrants et les temps de relais cumules.
BORNES = {
    "MARATHON": (6000, 43200),   # 1h40 - 12h
    "SEMI": (2700, 21600),       # 45min - 6h
    "10KM": (1500, 10800),       # 25min - 3h
    "5KM": (720, 7200),          # 12min - 2h
}

DIST_M = {"MARATHON": 42195, "SEMI": 21097, "10KM": 10000, "5KM": 5000}


def bornes_pour(dist_code, distance_m=None):
    """Bornes de plausibilite, deduites de la distance pour AUTRE."""
    if dist_code in BORNES:
        return BORNES[dist_code]
    if distance_m:
        km = distance_m / 1000.0
        return int(km * 2.5 * 60), int(km * 20 * 60)   # 2'30 a 20'00 au km
    return 600, 43200


def en_secondes(t):
    p = str(t).strip().split(":")
    try:
        if len(p) == 3:
            return int(p[0]) * 3600 + int(p[1]) * 60 + int(float(p[2]))
        if len(p) == 2:
            return int(p[0]) * 60 + int(float(p[1]))
    except ValueError:
        pass
    return None


def en_chrono(secondes):
    s = int(round(secondes))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


# ---------------------------------------------------------------------------
# Adaptateurs : chacun rend la liste des chronos du classement
# ---------------------------------------------------------------------------

# Une ligne de classement mikatiming porte deux chronos : le temps officiel
# (depart du sas) puis le temps net. On ne peut pas les distinguer par leur
# etiquette : elle est traduite dans la langue du site — « Finish » cote
# anglais, « Ziel » cote allemand (Berlin), « Netto »/« Brutto » ailleurs. Un
# filtre sur ces mots rendait zero chrono sur la page allemande de Berlin.
# On decoupe donc par ligne et on retient le DERNIER chrono de la ligne, qui
# est le temps net quelle que soit la langue.
RE_MIKA_LIGNE = re.compile(r'<li class="[^"]*list-group-item[^"]*">(.*?)</li>',
                           re.S)
RE_MIKA_TEMPS = re.compile(r'type-time[^>]*>(?:<div[^>]*>[^<]*</div>)?\s*'
                           r'(\d{1,2}:\d{2}:\d{2})')


def _chronos_de_page(html):
    """Un chrono par ligne de classement : le dernier temps de la ligne."""
    chronos = []
    for ligne in RE_MIKA_LIGNE.findall(html):
        if "list-group-header" in ligne:
            continue
        temps = RE_MIKA_TEMPS.findall(ligne)
        if temps:
            chronos.append(temps[-1])
    return chronos


def url_liste_mikatiming(info, year):
    """(session, base_url, event_code) pour une epreuve mikatiming, ou None."""
    sub = info.get("subdomain") or ""
    if not sub:
        return None
    if not sub.startswith("http"):
        if "." not in sub.split("/")[0]:
            return None
        sub = f"https://{sub}"
    code = info.get("event_code")
    if not code and info.get("event_code_pattern"):
        code = info["event_code_pattern"].format(yyyy=year)
    if not code:
        return None
    sess = requests.Session()
    sess.headers.update(NAVIGATEUR)
    return sess, f"{sub.rstrip('/')}/{year}/", code


def compte_finishers_mikatiming(info, year, sess=None, base=None, code=None):
    """Nombre exact d'arrivants, par recherche dichotomique de la derniere page.

    Les pages recentes n'affichent plus de liens « page=N » : le comptage de
    `auto_update_4d.py`, qui lisait `max(page=...)` dans le HTML, abandonnait
    donc (« pagination absente »). Le parametre `page` fonctionne pourtant.
    On cherche la derniere page non vide — une dizaine de requetes au lieu de
    plusieurs centaines — puis total = (derniere - 1) * 100 + lignes.
    """
    if sess is None:
        prepare = url_liste_mikatiming(info, year)
        if not prepare:
            return None
        sess, base, code = prepare

    def lignes(page):
        url = f"{base}?pid=list&event={code}&num_results=100&page={page}"
        try:
            r = sess.get(url, timeout=60)
        except requests.RequestException:
            return None
        if not r.ok:
            return None
        return len(_chronos_de_page(r.text))

    n1 = lignes(1)
    if not n1:
        return None
    if n1 < 100:
        return n1
    # borne haute par doublement, puis dichotomie
    basse, haute = 1, 2
    while True:
        n = lignes(haute)
        if n is None:
            return None
        if n == 0:
            break
        basse = haute
        haute *= 2
        if haute > 65536:
            return None
    while haute - basse > 1:
        milieu = (basse + haute) // 2
        n = lignes(milieu)
        if n is None:
            return None
        if n > 0:
            basse = milieu
        else:
            haute = milieu
    derniere = lignes(basse)
    if not derniere:
        return None
    return (basse - 1) * 100 + derniere


def chronos_mikatiming(info, year, verbeux=True):
    """Classement mikatiming, 100 lignes par page.

    `num_results` plafonne a 100 : au-dela la page retombe silencieusement a
    25, donc on ne demande jamais plus. On s'arrete sur la premiere page vide.
    """
    sub = info.get("subdomain") or ""
    if not sub:
        return None
    if not sub.startswith("http"):
        sub = f"https://{sub}" if "." in sub.split("/")[0] else None
        if sub is None:
            return None
    code = info.get("event_code")
    if not code and info.get("event_code_pattern"):
        code = info["event_code_pattern"].format(yyyy=year)
    if not code:
        return None

    sess = requests.Session()
    sess.headers.update(NAVIGATEUR)
    base = f"{sub.rstrip('/')}/{year}/"
    chronos = []
    page = 1
    while page <= 2000:
        url = (f"{base}?pid=list&event={code}&num_results=100&page={page}")
        try:
            r = sess.get(url, timeout=60)
        except requests.RequestException as e:
            print(f"  page {page}: {type(e).__name__}, arret")
            break
        if not r.ok:
            print(f"  page {page}: HTTP {r.status_code}, arret")
            break
        lot = _chronos_de_page(r.text)
        if not lot:
            break
        chronos.extend(lot)
        if verbeux and page % 25 == 0:
            print(f"  page {page}: {len(chronos)} chronos")
        if len(lot) < 100:          # derniere page
            break
        page += 1
    return chronos


def chronos_chronorace(info, year, verbeux=True):
    """Classement ChronoRace : Groups[].SlaveRows[], 1000 lignes par requete.

    Le contexte `db` et la table `LIVEn` viennent du map ; sans numero de
    table on scanne LIVE1..LIVE40 et on retient la plus fournie, comme le
    fetcher de `auto_update_4d.py`.
    """
    db = info.get("db") or info.get("platform_id")
    if db and "{" in str(db):
        db = None
    if not db and info.get("platform_id_pattern"):
        db = None               # motif a date : non resoluble ici
    if not db:
        return None
    sess = requests.Session()
    sess.headers.update({"User-Agent": NAVIGATEUR["User-Agent"],
                         "Accept": "application/json"})
    racine = "https://results.chronorace.be/api/results/table/search"

    tables = [info["table"]] if info.get("table") else [
        f"LIVE{n}" for n in range(1, 41)]
    meilleure, total = None, 0
    for tb in tables:
        try:
            r = sess.get(f"{racine}/{db}/{tb}",
                         params={"srch": "", "pageSize": 1, "fromRecord": 0},
                         timeout=30)
        except requests.RequestException:
            continue
        if not r.ok:
            continue
        try:
            n = r.json().get("Count") or 0
        except ValueError:
            continue
        if n > total:
            meilleure, total = tb, n
    if not meilleure:
        return None
    if verbeux:
        print(f"  ChronoRace {db}/{meilleure}: {total} lignes")

    # Colonnes utiles reperees dans TableDefinition.Columns
    chronos = []
    offset = 0
    while offset < total:
        r = sess.get(f"{racine}/{db}/{meilleure}",
                     params={"srch": "", "pageSize": 1000,
                             "fromRecord": offset}, timeout=60)
        if not r.ok:
            break
        data = r.json()
        for g in data.get("Groups") or []:
            for ligne in g.get("SlaveRows") or []:
                for cell in ligne:
                    m = re.search(r"(\d{1,2}:\d{2}:\d{2})", str(cell))
                    if m:
                        chronos.append(m.group(1))
                        break
        offset += 1000
        if verbeux and offset % 5000 == 0:
            print(f"  {len(chronos)} chronos")
    return chronos


def chronos_tracx(info, year, verbeux=True):
    """Classement Tracx : /events/{id}/races/{race}/rankings/{rk}/results."""
    event_id = info.get("platform_id")
    if not event_id:
        return None
    sess = requests.Session()
    sess.headers.update({
        "Authorization": "Bearer 40496C26-9BEF-4266-8A27-43C78540F669",
        "Accept": "application/json",
        "User-Agent": NAVIGATEUR["User-Agent"]})
    api = "https://api.tracx.events/v1"
    r = sess.get(f"{api}/events/{event_id}/races", timeout=30)
    if not r.ok:
        return None
    races = r.json()
    if isinstance(races, dict):
        races = races.get("data") or races.get("races") or []
    if not races:
        return None
    course = max(races, key=lambda x: x.get("participant_count") or 0)
    rid = course.get("id")
    rk = sess.get(f"{api}/events/{event_id}/races/{rid}/rankings", timeout=30)
    if not rk.ok:
        return None
    rankings = rk.json()
    if isinstance(rankings, dict):
        rankings = rankings.get("data") or []
    if not rankings:
        return None
    rkid = rankings[0].get("id")
    chronos, page = [], 1
    while page <= 4000:
        rr = sess.get(f"{api}/events/{event_id}/races/{rid}/rankings/"
                      f"{rkid}/results", params={"page": page}, timeout=60)
        if not rr.ok:
            break
        lot = rr.json()
        if isinstance(lot, dict):
            lot = lot.get("data") or lot.get("results") or []
        if not lot:
            break
        for e in lot:
            t = e.get("finish") or e.get("chip_time") or e.get("time")
            if t:
                chronos.append(t)
        page += 1
        if verbeux and page % 50 == 0:
            print(f"  page {page}: {len(chronos)} chronos")
        time.sleep(0.1)
    return chronos


ADAPTATEURS = {
    "mikatiming": chronos_mikatiming,
    "chronorace": chronos_chronorace,
    "tracx": chronos_tracx,
}


# ---------------------------------------------------------------------------

def normaliser(nom):
    return re.sub(r"\s+", " ", str(nom).replace("\xa0", " ")).strip().lower()


def info_epreuve(nom):
    with open(SCRIPT_DIR / "event_platform_map.json", encoding="utf-8") as f:
        carte = json.load(f)
    cle = normaliser(nom)
    for ev_cle, info in carte.items():
        if normaliser(info.get("name", ev_cle)) == cle:
            return info
    return None


def ecrire_moyenne(course, year, distance_m, count, chrono, vitesse,
                   dry_run=False):
    """Meme protection que update_avg_time : jamais d'ecrasement."""
    path = SCRIPT_DIR / "avg_times_sporthive.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    deja = next((e for e in data if e.get("race") == course
                 and e.get("year") == year
                 and e.get("dist_m") == distance_m), None)
    if deja and deja.get("avg_time"):
        print(f"[SKIP] {course} {year} a deja un temps moyen "
              f"({deja['avg_time']})")
        return False
    entree = {"label": f"{course} {year}", "race": course,
              "dist_m": distance_m, "year": year, "count": count,
              "avg_time": chrono, "avg_speed_kmh": vitesse}
    if deja:
        deja.update(entree)
    else:
        data.append(entree)
    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[ECRIT] {course} {year} = {chrono} (sur {count} chronos)")
    return True


def moyenne_classement(course, dist_code, year, dry_run=False):
    info = info_epreuve(course)
    if not info:
        print(f"{course!r} absent de event_platform_map.json")
        return None
    plateforme = info.get("platform")
    adaptateur = ADAPTATEURS.get(plateforme)
    if not adaptateur:
        print(f"{course}: plateforme {plateforme!r} sans adaptateur "
              f"(disponibles: {', '.join(sorted(ADAPTATEURS))})")
        return None

    print(f"{course} {dist_code} {year} — {plateforme}")
    brut = adaptateur(info, year)
    if not brut:
        print("  aucun chrono recupere")
        return None

    distance_m = DIST_M.get(dist_code) or info.get("distance_m")
    bas, haut = bornes_pour(dist_code, distance_m)
    secondes = [s for s in (en_secondes(t) for t in brut)
                if s and bas <= s <= haut]
    rejetes = len(brut) - len(secondes)
    if not secondes:
        print(f"  {len(brut)} chronos lus, aucun dans [{en_chrono(bas)}, "
              f"{en_chrono(haut)}]")
        return None

    moy = statistics.mean(secondes)
    med = statistics.median(secondes)
    vitesse = round(distance_m / 1000.0 / (moy / 3600.0), 3) if distance_m else None
    print(f"  {len(secondes)} chronos retenus ({rejetes} hors bornes)")
    print(f"  moyenne {en_chrono(moy)} | mediane {en_chrono(med)}"
          + (f" | {vitesse} km/h" if vitesse else ""))

    if distance_m:
        ecrit = ecrire_moyenne(course, year, distance_m, len(secondes),
                               en_chrono(moy), vitesse, dry_run)
        if ecrit and not dry_run:
            from update_log import log_update
            log_update(course, f"{year}-01-01", {"avg_time": en_chrono(moy)})
    else:
        print("  distance inconnue (AUTRE sans distance_m) : rien d'ecrit")
    return en_chrono(moy)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course")
    ap.add_argument("distance", choices=["MARATHON", "SEMI", "10KM", "5KM", "AUTRE"])
    ap.add_argument("annee", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    resultat = moyenne_classement(a.course, a.distance, a.annee, a.dry_run)
    return 0 if resultat else 1


if __name__ == "__main__":
    sys.exit(main())

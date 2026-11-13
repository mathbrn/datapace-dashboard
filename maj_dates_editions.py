"""Date exacte de l'edition de l'annee pour chaque course -> event_dates.json.

L'onglet Tableau affichait « A venir » sur une cellule vide de l'annee en
cours, a partir du seul mois de la colonne « Periode ». Ce module donne la
date exacte, ce qui permet :
  - d'afficher « 29 nov. » au lieu de « A venir » ;
  - de trancher le mois en cours, que l'ancienne regle traitait toujours
    comme passe ;
  - de signaler une course deja courue dont la donnee manque encore.

Sources, par priorite :
  1. Calendrier World Athletics (`getCalendarEvents`, courses sur route) :
     toute l'annee, passe compris. Rapprochement par `rapprochement.py`
     avec filtre pays.
  2. Flux AIMS (`events.ics`) : a venir uniquement, sans ville ; sert de
     complement, avec un seuil de rapprochement plus exigeant.

Garde-fou : une date dont le mois s'ecarte de plus d'un mois de la colonne
« Periode » est refusee (faux rapprochement probable) et listee dans
`rejets`. Une course non rapprochee herite de la date d'une autre course du
meme evenement, si et seulement si le mois coincide avec sa Periode
(`"source": "evenement"`).

Usage :
    python maj_dates_editions.py            # annee en cours
    python maj_dates_editions.py --annee 2027
Rafraichi par auto_update_4d.py une fois par semaine.
"""
import datetime
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).parent
FICHIER = ICI / "event_dates.json"
EXCEL = ICI / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx"
SEUIL_AIMS = 0.70

MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
        "decembre": 12}


def _sans_accents(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def periodes():
    """{'Evenement|DISTANCE': mois (1-12) ou 0}"""
    import openpyxl
    wb = openpyxl.load_workbook(EXCEL, read_only=True)
    out = {}
    for r in wb["ALL"].iter_rows(min_row=2, values_only=True):
        if not r[3]:
            continue
        cle = str(r[3]).replace("\xa0", " ").strip() + "|" + str(r[2] or "").strip()
        out[cle] = MOIS.get(_sans_accents(str(r[0] or "")).lower().strip(), 0)
    wb.close()
    return out


def _ecart_mois(a, b):
    d = abs(a - b) % 12
    return min(d, 12 - d)


def source_wa(annee):
    import maj_labels_wa
    for e in maj_labels_wa.calendrier(annee):
        if "road" not in (e.get("disciplines") or "").lower() or not e.get("startDate"):
            continue
        yield e["name"], e.get("venue", ""), e["startDate"][:10], "WA"


def source_aims():
    import requests
    txt = requests.get("https://aims-worldrunning.org/events.ics",
                       headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text
    txt = re.sub(r"\r?\n[ \t]", "", txt)  # depliage iCalendar
    for bloc in txt.split("BEGIN:VEVENT")[1:]:
        champ = dict(re.findall(r"^([A-Z]+)[^:\n]*:(.*)$", bloc, re.M))
        d = champ.get("DTSTART", "")
        if len(d) >= 8 and champ.get("SUMMARY"):
            yield (champ["SUMMARY"].replace("\\,", ",").strip(), "",
                   f"{d[:4]}-{d[4:6]}-{d[6:8]}", "AIMS")


def maj(annee=None):
    import rapprochement as R
    annee = annee or datetime.date.today().year
    per = periodes()
    dates, rejets = {}, []

    def candidates():
        try:
            yield from source_wa(annee)
        except Exception as e:
            print(f"  Calendrier WA indisponible : {type(e).__name__}: {e}")
        try:
            yield from source_aims()
        except Exception as e:
            print(f"  Flux AIMS indisponible : {type(e).__name__}: {e}")

    for nom, venue, date, src in candidates():
        if not date.startswith(str(annee)):
            continue
        ville, pays = R.depuis_venue(venue) if venue else ("", None)
        ep, sc, _ = R.rapprocher(nom, ville, pays)
        if not ep or (src == "AIMS" and sc < SEUIL_AIMS):
            continue
        cle = f"{ep['evenement']}|{ep['distance']}"
        m = per.get(cle, 0)
        if m and _ecart_mois(int(date[5:7]), m) > 1:
            rejets.append({"ligne": cle, "nom_ext": nom, "date": date, "source": src,
                           "motif": f"mois {date[5:7]} incompatible avec la Periode ({m})"})
            continue
        prec = dates.get(cle)
        # WA prime sur AIMS ; a source egale, le meilleur score
        if prec and (prec["source"] == "WA" and src == "AIMS"
                     or prec["source"] == src and prec["score"] >= sc):
            continue
        dates[cle] = {"date": date, "source": src, "nom_ext": nom, "score": round(sc, 3)}

    # Heritage de la date d'une autre course du meme evenement
    par_ev = {}
    for cle, v in dates.items():
        par_ev.setdefault(cle.rsplit("|", 1)[0], []).append(v["date"])
    herites = 0
    for cle, m in per.items():
        if cle in dates:
            continue
        ev = cle.rsplit("|", 1)[0]
        ok = [d for d in par_ev.get(ev, []) if m and int(d[5:7]) == m]
        if len(set(ok)) == 1:
            dates[cle] = {"date": ok[0], "source": "evenement"}
            herites += 1

    doc = {"_commentaire": "Genere par maj_dates_editions.py : date de l'edition de l'annee "
                           "par ligne 'Evenement|DISTANCE'. Ne pas editer a la main ; "
                           "corriger un rapprochement dans event_aliases.json.",
           "annee": annee, "maj_le": datetime.date.today().isoformat(),
           "dates": dict(sorted(dates.items())), "rejets": rejets}
    FICHIER.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    src = {}
    for v in dates.values():
        src[v["source"]] = src.get(v["source"], 0) + 1
    print(f"Dates {annee} : {len(dates)} lignes sur {len(per)} {src}, {len(rejets)} rejet(s)")
    return doc


def maj_si_ancien(jours=7):
    """Comme maj_labels_wa.maj_si_ancien : True si les dates ont change.
    Ne leve jamais."""
    try:
        avant = {}
        if FICHIER.exists():
            d = json.loads(FICHIER.read_text(encoding="utf-8"))
            avant = {k: v["date"] for k, v in d.get("dates", {}).items()}
            age = (datetime.date.today() - datetime.date.fromisoformat(d.get("maj_le", "2000-01-01"))).days
            if age < jours and d.get("annee") == datetime.date.today().year:
                return False
        apres = {k: v["date"] for k, v in maj()["dates"].items()}
        return apres != avant
    except Exception as e:
        print(f"  Dates d'edition non rafraichies : {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    a = None
    if "--annee" in sys.argv:
        a = int(sys.argv[sys.argv.index("--annee") + 1])
    maj(a)

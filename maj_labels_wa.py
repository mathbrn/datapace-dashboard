"""Labels World Athletics des epreuves du dashboard -> event_labels.json.

Le programme « World Athletics Label Road Races » classe chaque annee
quelque 340 courses sur route en quatre niveaux : Platinum, Gold, Elite et
Label. Le niveau se lit dans le calendrier World Athletics, champ
`competitionGroup` (« World Athletics Label Road Races – Gold »), parfois
combine a un championnat national.

Chaque course labellisee est rapprochee d'une ligne (evenement, distance)
du dashboard par `rapprochement.py`. Le resultat alimente le badge et le
filtre « Label WA » de `generate_dashboard.py`.

Le reglement des labels (C1.6, regle 17.2) oblige chaque course labellisee a
publier ses resultats officiels sur son site : ces epreuves sont donc la
cible prioritaire de l'Update 4D.

Usage :
    python maj_labels_wa.py            # annee en cours
    python maj_labels_wa.py --annee 2025
Rafraichi automatiquement par auto_update_4d.py une fois par semaine.
"""
import datetime
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).parent
FICHIER = ICI / "event_labels.json"
NIVEAUX = ("Platinum", "Gold", "Elite", "Label")

QUERY = """query getCalendarEvents($startDate: String, $endDate: String, $regionType: String, $limit: Int, $offset: Int) {
  getCalendarEvents(startDate: $startDate, endDate: $endDate, regionType: $regionType, limit: $limit, offset: $offset) {
    hits results { id name venue startDate disciplines competitionGroup }
  }
}"""


def calendrier(annee):
    import requests
    import auto_update_4d as a
    ep, cle = a._wa_config()
    out, off = [], 0
    while True:
        r = requests.post(ep, json={"query": QUERY, "variables": {
            "startDate": f"{annee}-01-01", "endDate": f"{annee}-12-31",
            "regionType": "world", "limit": 200, "offset": off}},
            headers={"x-api-key": cle, "User-Agent": "Mozilla/5.0"}, timeout=60)
        r.raise_for_status()
        d = r.json()["data"]["getCalendarEvents"]
        out += d["results"]
        off += len(d["results"])
        if not d["results"] or off >= d["hits"]:
            break
    return out


def niveau(groupe):
    m = re.search(r"Label Road Races\s*[–-]\s*(\w+)", groupe or "")
    return m.group(1) if m and m.group(1) in NIVEAUX else None


def maj(annee=None):
    import rapprochement as R
    annee = annee or datetime.date.today().year
    labels, non_suivies = {}, []
    for e in calendrier(annee):
        n = niveau(e.get("competitionGroup"))
        if not n:
            continue
        ville, pays = R.depuis_venue(e.get("venue", ""))
        ep, sc, motif = R.rapprocher(e["name"], ville, pays)
        if not ep:
            non_suivies.append({"nom": e["name"], "label": n, "lieu": e.get("venue")})
            continue
        cle = f"{ep['evenement']}|{ep['distance']}"
        ordre = NIVEAUX.index
        if cle in labels and ordre(labels[cle]["label"]) <= ordre(n):
            continue  # garder le niveau le plus eleve si deux courses visent la meme ligne
        labels[cle] = {"label": n, "annee": annee, "nom_wa": e["name"],
                       "wa_id": e["id"], "score": sc}
    doc = {"_commentaire": "Genere par maj_labels_wa.py : niveau de label World Athletics "
                           "(Platinum, Gold, Elite, Label) par ligne 'Evenement|DISTANCE'. "
                           "Ne pas editer a la main ; corriger un rapprochement dans event_aliases.json.",
           "annee": annee, "maj_le": datetime.date.today().isoformat(),
           "labels": dict(sorted(labels.items())),
           "labellisees_non_suivies": non_suivies}
    FICHIER.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    par = {}
    for v in labels.values():
        par[v["label"]] = par.get(v["label"], 0) + 1
    print(f"Labels WA {annee} : {len(labels)} lignes du dashboard {par}, "
          f"{len(non_suivies)} courses labellisees non suivies")
    return doc


def maj_si_ancien(jours=7):
    """Rafraichit le fichier s'il a plus de `jours` jours (ou date d'une autre
    annee). Rend True si les labels ont change, pour que l'appelant
    regenere le dashboard. Ne leve jamais : un echec ne doit pas faire tomber
    le cron."""
    try:
        avant = {}
        if FICHIER.exists():
            d = json.loads(FICHIER.read_text(encoding="utf-8"))
            avant = {k: v["label"] for k, v in d.get("labels", {}).items()}
            age = (datetime.date.today() - datetime.date.fromisoformat(d.get("maj_le", "2000-01-01"))).days
            if age < jours and d.get("annee") == datetime.date.today().year:
                return False
        apres = {k: v["label"] for k, v in maj()["labels"].items()}
        return apres != avant
    except Exception as e:
        print(f"  Labels WA non rafraichis : {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    a = None
    if "--annee" in sys.argv:
        a = int(sys.argv[sys.argv.index("--annee") + 1])
    maj(a)

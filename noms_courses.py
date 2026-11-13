"""Nom propre de chaque course (couple epreuve, distance).

L'onglet ALL ne porte qu'un nom par ligne, la colonne Race, qui sert aussi de
cle de regroupement : toutes les lignes d'un meme nom forment un evenement
dans la vue par evenement. Certains evenements nomment pourtant chaque
distance differemment — le TCS Amsterdam Marathon court un « Mizuno Half
Marathon », le BTR Liverpool Half Marathon & 10 Mile un « BTR Liverpool
10 Mile ». `course_names.json` porte ces noms, sans toucher a l'Excel, dont
les colonnes sont lues par position par plusieurs scripts.

Format de `course_names.json` :

    "courses": {
        "<Race de l'onglet ALL>|<DISTANCE>": {
            "nom": "<nom affiche de la course>",
            "anciens_noms": ["<nom sous lequel les fichiers annexes la
                              connaissent encore>"]
        }
    }

`anciens_noms` sert quand une course a ete rattachee a un autre evenement :
`avg_times_sporthive.json`, `sponsoring_data.json`, `create_chronos.py` et
`event_platform_map.json` gardent l'ancien nom, et les fonctions ci-dessous
font le lien, au lieu de renommer quatre fichiers.
"""
import json
from pathlib import Path

_CHEMIN = Path(__file__).parent / "course_names.json"
_CACHE = None


def _propre(s):
    return str(s or "").replace("\xa0", " ").strip()


def courses():
    """{'Race|DISTANCE': {'nom': ..., 'anciens_noms': [...]}}"""
    global _CACHE
    if _CACHE is None:
        _CACHE = {}
        try:
            with open(_CHEMIN, encoding="utf-8") as f:
                brut = json.load(f).get("courses", {})
            for cle, v in brut.items():
                if "|" not in cle or not isinstance(v, dict):
                    continue
                ev, dist = cle.rsplit("|", 1)
                _CACHE[_propre(ev) + "|" + _propre(dist)] = {
                    "nom": _propre(v.get("nom")) or _propre(ev),
                    "anciens_noms": [_propre(a) for a in v.get("anciens_noms", [])
                                     if _propre(a)],
                }
        except (OSError, ValueError) as exc:
            print(f"  course_names.json illisible : {exc}")
    return _CACHE


def nom_course(evenement, distance):
    """Nom affiche de la course, ou le nom de l'evenement s'il n'y en a pas."""
    c = courses().get(_propre(evenement) + "|" + _propre(distance))
    return c["nom"] if c else _propre(evenement)


def nom_plateforme(evenement, distance):
    """Nom sous lequel les fichiers annexes connaissent la course.

    C'est le premier ancien nom s'il y en a un (la course a change
    d'evenement), sinon le nom de l'evenement. Sert a retrouver l'entree de
    `event_platform_map.json`.
    """
    c = courses().get(_propre(evenement) + "|" + _propre(distance))
    if c and c["anciens_noms"]:
        return c["anciens_noms"][0]
    return _propre(evenement)


def renommage_annexes():
    """{ancien nom: nom de course} pour realigner les fichiers annexes."""
    out = {}
    for v in courses().values():
        for a in v["anciens_noms"]:
            out[a] = v["nom"]
    return out


def evenement_de(nom, distance):
    """Race de l'onglet ALL correspondant a un nom de course ou a un ancien nom.

    Rend None si le nom n'est ni une course nommee ni un ancien nom pour
    cette distance : l'appelant garde alors le nom tel quel.
    """
    n = _propre(nom)
    for cle, v in courses().items():
        ev, dist = cle.rsplit("|", 1)
        if dist != _propre(distance):
            continue
        if n == v["nom"] or n in v["anciens_noms"]:
            return ev
    return None

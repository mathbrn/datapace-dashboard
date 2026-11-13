"""Rapprochement d'un nom de course exterieur avec une epreuve du dashboard.

Sert a l'Update 4D (catalogue World Athletics -> lignes de l'onglet ALL) et a
la recherche de nouveaux evenements. Remplace le score « mots communs x 10 »
de `match_wa_to_ours`, qui confondait « Boston Half » et le Boston Marathon,
ratait « Schneider Electric Marathon de Paris » (devenu ASICS) ou
« 48th Warsaw Marathon » (NN Maraton Warszawski), et prenait un cross de
Cardiff pour le Cardiff Half Marathon.

Principe, dans l'ordre :

1. **Alias confirmes** (`event_aliases.json`) : un nom exterieur deja
   rapproche a la main pointe directement vers sa ligne. Score 1,0.
2. **Filtres durs** : le pays doit concorder quand les deux sont connus, et
   la distance aussi (un nom qui annonce un semi ne designe jamais une ligne
   marathon).
3. **Score de nom** pondere par la rarete des mots (IDF calcule sur le
   corpus du dashboard) : « shenzhen » pese lourd, « standard » ou
   « chartered » presque rien. Les sponsors, qui changent d'une annee a
   l'autre, comptent donc peu ; la ville et le nom propre de la course
   comptent beaucoup.
4. **Ville** : la ville de l'epreuve (souvent en francais dans l'Excel :
   Varsovie, Athenes, Pekin) est traduite, et les variantes locales
   (Warszawa, Warszawski, Wien) sont rattachees a la meme racine.

Le resultat porte un score entre 0 et 1 et un motif lisible ; `SEUIL` fixe
la decision. Mesure sur `rapprochement_gold.json` par
`python rapprochement.py --eval`.
"""
import json
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).parent
SEUIL = 0.55
# Facteurs reductifs, regles sur rapprochement_gold.json (cf. --eval).
F_VILLES_DIFFERENTES = 0.65
F_MOT_PROPRE = 0.7
F_QUALIFICATIF = 0.4

# --- Normalisation -----------------------------------------------------------

GENERIQUES = {
    "the", "de", "du", "des", "la", "le", "les", "el", "il", "of", "and", "et",
    "y", "e", "di", "der", "die", "das", "van", "by", "presented", "powered",
    "edition", "edicion", "edizione", "ed", "annual", "official",
    "marathon", "marathons", "maraton", "maratona", "marathona", "maratonu",
    "marato", "maratho", "marathlon", "half", "semi", "halbmarathon", "halve",
    "medio", "media", "mezza", "meia", "mitja", "run", "running", "race",
    "races", "road", "course", "corrida", "carrera", "lauf", "loop", "city",
    "international", "internacional", "internazionale", "km", "k", "mile",
    "miles", "festival", "weekend", "week", "end", "classic",
    "full", "official",
}

# Qualificatifs qui designent une AUTRE course quand un seul des deux noms les
# porte : « Osaka Women's Marathon » n'est pas l'Osaka Marathon, le « Cardiff
# Cross Challenge » n'est pas le Cardiff Half, « Stramilano SottoZero » n'est
# pas la Stramilano.
QUALIFICATIFS = {
    "women", "womens", "woman", "ladies", "femmes", "femme", "feminine",
    "mujer", "mujeres", "donna", "donne", "frauen", "dames", "girls",
    "cross", "trail", "night", "nocturne", "nocturna", "notturna", "kids",
    "junior", "juniors", "youth", "championship", "championships",
    "sottozero", "bridge", "winter", "christmas", "xmas", "santa", "virtual",
    "relay", "ekiden", "ultra", "eco", "series", "challenge",
}

# Mots d'entreprise : un sponsor change d'une annee a l'autre (Schneider
# Electric -> ASICS a Paris, Standard Chartered -> BYD a Singapour). Ils
# pesent tres peu dans le score.
MOTS_ENTREPRISE = {
    "bank", "banco", "banque", "group", "groupe", "electric", "automobile",
    "airlines", "airways", "insurance", "assurance", "assurances", "mutuelle",
    "energy", "motors", "holdings", "telecom", "mobile", "hospital", "health",
    "foods", "beverages", "financial", "capital", "investments", "airport",
}

# Ville (forme de l'Excel ou forme locale) -> racine commune.
VILLES = {
    "athenes": "athens", "athina": "athens", "bruxelles": "brussels",
    "brussel": "brussels", "lisbonne": "lisbon", "lisboa": "lisbon",
    "londres": "london", "vienne": "vienna", "wien": "vienna",
    "pekin": "beijing", "varsovie": "warsaw", "warszawa": "warsaw",
    "warszawski": "warsaw", "copenhague": "copenhagen", "kobenhavn": "copenhagen",
    "seville": "sevilla", "barcelone": "barcelona", "geneve": "geneva",
    "geneva": "geneva", "rome": "roma", "milan": "milano", "singapour": "singapore",
    "le caire": "cairo", "moscou": "moscow", "moskva": "moscow",
    "munich": "munchen", "muenchen": "munchen", "cologne": "koln", "koeln": "koln",
    "hambourg": "hamburg", "francfort": "frankfurt", "frankfurter": "frankfurt",
    "bombay": "mumbai", "new delhi": "delhi", "bengalore": "bengaluru",
    "bangalore": "bengaluru", "prag": "prague", "praha": "prague",
    "turin": "torino", "florence": "firenze", "venise": "venezia",
    "naples": "napoli", "anvers": "antwerp", "antwerpen": "antwerp",
    "la haye": "den haag", "the hague": "den haag", "gand": "gent",
    "bale": "basel", "berne": "bern", "nankin": "nanjing",
    "samarcande": "samarkand", "port gentil": "port gentil",
    "mexico": "mexico", "ciudad de mexico": "mexico", "edimbourg": "edinburgh",
    "dublin": "dublin", "tokyo": "tokyo", "seoul": "seoul", "osaka": "osaka",
    "berlin": "berlin", "rotterdam": "rotterdam", "amsterdam": "amsterdam",
    "valence": "valencia", "saragosse": "zaragoza", "lucerne": "luzern",
    "zurich": "zurich", "istanbul": "istanbul", "riyad": "riyadh",
    "le cap": "cape town", "kapstadt": "cape town", "porto": "porto",
    "oporto": "porto", "ljubljana": "ljubljana", "budapest": "budapest",
    "bucarest": "bucharest", "bucuresti": "bucharest", "sofia": "sofia",
    "cracovie": "krakow", "krakow": "krakow", "poznan": "poznan",
    "taipei": "taipei", "pekin ": "beijing", "shanghai": "shanghai",
}

# Pays de event_countries.json (francais) -> code World Athletics.
PAYS = {
    "Afrique du Sud": "RSA", "Allemagne": "GER", "Arabie Saoudite": "KSA",
    "Argentine": "ARG", "Arménie": "ARM", "Australie": "AUS", "Autriche": "AUT",
    "Bahreïn": "BRN", "Belgique": "BEL", "Bhouthan": "BHU",
    "Bosnie-Herzégovine": "BIH", "Brunei": "BRU", "Brésil": "BRA",
    "Bulgarie": "BUL", "Canada": "CAN", "Chili": "CHI", "Chine": "CHN",
    "Chypre": "CYP", "Colombie": "COL", "Corée du Sud": "KOR", "Croatie": "CRO",
    "Cuba": "CUB", "Curacao": "CUW", "Danemark": "DEN", "Egypte": "EGY",
    "Emirats Arabes Unis": "UAE", "Espagne": "ESP", "Estonie": "EST",
    "Etats-Unis": "USA", "Ethiopie": "ETH", "Finlande": "FIN", "France": "FRA",
    "Gabon": "GAB", "Grèce": "GRE", "Hong Kong": "HKG", "Hongrie": "HUN",
    "Inde": "IND", "Indonésie": "INA", "Irlande": "IRL", "Italie": "ITA",
    "Japon": "JPN", "Kazakhstan": "KAZ", "Kenya": "KEN", "Koweït": "KUW",
    "Lettonie": "LAT", "Liban": "LBN", "Lithuanie": "LTU", "Luxembourg": "LUX",
    "Macédoine du Nord": "MKD", "Malaisie": "MAS", "Maroc": "MAR",
    "Mexique": "MEX", "Monaco": "MON", "Nigeria": "NGR", "Norvège": "NOR",
    "Nouvelle-Zélande": "NZL", "Oman": "OMA", "Ouzbékistan": "UZB",
    "Pays-Bas": "NED", "Philippines": "PHI", "Pologne": "POL",
    "Portugal": "POR", "Pérou": "PER", "Qatar": "QAT", "Roumanie": "ROU",
    "Royaume-Uni": "GBR", "Rwanda": "RWA", "République Tchèque": "CZE",
    "Serbie": "SRB", "Singapour": "SGP", "Slovaquie": "SVK", "Slovénie": "SLO",
    "Sri Lanka": "SRI", "Suisse": "SUI", "Suède": "SWE", "Sénégal": "SEN",
    "Taïwan": "TPE", "Thailande": "THA", "Tunisie": "TUN", "Turquie": "TUR",
    "Vietnam": "VIE",
}


def sans_accents(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


ORDINAL = re.compile(r"^(\d+(st|nd|rd|th|e|eme|er|a|o|ª|º)?|[ivxlc]+)$")


def ville_racine(v):
    v = re.sub(r"\(.*?\)", "", sans_accents(v)).replace("-", " ").strip()
    v = re.sub(r"\s+", " ", v)
    return VILLES.get(v, v)


def mots(nom):
    """Mots significatifs d'un nom : sans accents, ordinaux, annees ni mots
    generiques ; chaque variante de ville ramenee a sa racine."""
    s = re.sub(r"[-'’`´]", " ", sans_accents(nom))
    out = []
    for w in re.findall(r"[a-z0-9]+", s):
        if w in GENERIQUES or ORDINAL.match(w) or re.fullmatch(r"(19|20)\d\d", w):
            continue
        if len(w) < 3 or re.fullmatch(r"\d+(k|km|m|mi|miles)?", w):
            continue
        out.append(VILLES.get(w, w))
    # villes en deux mots (le caire, new delhi, la haye...)
    joint = " ".join(re.findall(r"[a-z0-9]+", s))
    for k, v in VILLES.items():
        if " " in k and k in joint:
            out.append(v.replace(" ", ""))
    return set(out)


def classe_distance(nom):
    """Distance annoncee par un nom, ou None si le nom ne dit rien."""
    s = sans_accents(nom)
    if re.search(r"half|semi|medio|mezza|meia|halb|halve|mitja|21[ .,]?(k|km)\b|1/2", s):
        return "SEMI"
    if re.search(r"\b10 ?(k|km)\b|\b10 ?000\b", s):
        return "10KM"
    if re.search(r"\b5 ?(k|km)\b", s):
        return "5KM"
    if re.search(r"\b(10|12|15|16|20|25|30) ?(mile|miles|km|k)\b|\bmiles?\b", s):
        return "AUTRE"
    if re.search(r"marat|maraton", s):
        return "MARATHON"
    return None


# --- Corpus du dashboard -----------------------------------------------------

@lru_cache(maxsize=1)
def epreuves():
    """Lignes (evenement, distance) de l'onglet ALL, avec tous leurs noms."""
    import openpyxl
    wb = openpyxl.load_workbook(ICI / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx",
                                read_only=True)
    try:
        cn = json.loads((ICI / "course_names.json").read_text(encoding="utf-8"))["courses"]
    except Exception:
        cn = {}
    try:
        pays = json.loads((ICI / "event_countries.json").read_text(encoding="utf-8"))
    except Exception:
        pays = {}
    out = []
    for r in wb["ALL"].iter_rows(min_row=2, values_only=True):
        if not r[3]:
            continue
        nom = str(r[3]).replace("\xa0", " ").strip()
        d = str(r[2] or "").strip()
        alt = cn.get(f"{nom}|{d}", {})
        noms = [nom] + [x for x in [alt.get("nom")] + alt.get("anciens_noms", []) if x]
        p = (pays.get(nom) or {}).get("pays") if isinstance(pays.get(nom), dict) else None
        out.append({"evenement": nom, "distance": d, "noms": noms,
                    "ville": ville_racine(r[1] or ""), "pays": PAYS.get(p or "", None)})
    wb.close()
    return out


@lru_cache(maxsize=1)
def idf():
    docs = [set().union(*(mots(n) for n in e["noms"])) | {e["ville"].replace(" ", "")}
            for e in epreuves()]
    df = {}
    for d in docs:
        for w in d:
            df[w] = df.get(w, 0) + 1
    n = len(docs)
    return {w: math.log((n + 1) / (c + 0.5)) for w, c in df.items()}, math.log(n + 1)


@lru_cache(maxsize=1)
def marques():
    """Mots des marques de sponsoring_data.json (adidas, asics, generali...)."""
    try:
        sp = json.loads((ICI / "sponsoring_data.json").read_text(encoding="utf-8"))
    except Exception:
        return frozenset(MOTS_ENTREPRISE)
    m = set(MOTS_ENTREPRISE)
    for b in sp.get("brands", {}):
        for w in re.findall(r"[a-z0-9]+", sans_accents(b)):
            if len(w) >= 3 and w not in VILLES.values():
                m.add(w)
    return frozenset(m)


@lru_cache(maxsize=1)
def partenaires():
    """Mots des marques partenaires de chaque epreuve (sponsoring_data.json) :
    « Journal-Constitution » pour la Peachtree, « Renascenca » pour Fatima. Un
    tel mot absent du nom exterieur n'est pas un signe d'autre course."""
    out = {}
    try:
        sp = json.loads((ICI / "sponsoring_data.json").read_text(encoding="utf-8"))
    except Exception:
        return out
    for x in sp.get("partnerships", []):
        out.setdefault(x.get("event"), set()).update(
            w for w in re.findall(r"[a-z0-9]+", sans_accents(x.get("brand", ""))) if len(w) >= 3)
    return out


def poids(w):
    if w in marques():
        return 0.15
    table, defaut = idf()
    # mot inconnu du dashboard : poids median, pas maximal (sinon un sponsor
    # inconnu, « schneider », pese plus que le nom de la ville)
    return table.get(w, defaut * 0.6)


@lru_cache(maxsize=1)
def alias():
    try:
        brut = json.loads((ICI / "event_aliases.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {sans_accents(k).strip(): v for k, v in brut.get("alias", {}).items()}


# --- Score -------------------------------------------------------------------

def _proche(a, b):
    """Deux mots egaux, ou presque pour les mots longs (fautes de saisie :
    Giulietta / Giuletta, Lentemarathon / Lentermarathon)."""
    if a == b:
        return True
    # un chiffre distingue deux courses (Bangsaen10 / Bangsaen21)
    if re.search(r"\d", a + b):
        return False
    if min(len(a), len(b)) >= 6:
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a, b).ratio() >= 0.85
    return False


def _communs(m1, m2):
    return {w for w in m1 if any(_proche(w, x) for x in m2)}


def score(nom_ext, ville_ext, pays_ext, ep, distance_ext=None):
    """(score 0-1, motif) du rapprochement d'un nom exterieur avec une ligne.

    Couverture ponderee dans les DEUX sens : le nom exterieur doit se
    retrouver dans celui du dashboard, et reciproquement. Un seul mot commun
    (la ville) ne suffit plus quand l'un des noms porte d'autres mots
    distinctifs (« Hong Kong-Zhuhai-Macao Bridge Half » contre le semi du
    marathon de Hong Kong).
    """
    cl = distance_ext or classe_distance(nom_ext)
    if cl and ep["distance"] and cl != ep["distance"]:
        return 0.0, f"distance {cl} != {ep['distance']}"
    if pays_ext and ep["pays"] and pays_ext != ep["pays"]:
        return 0.0, f"pays {pays_ext} != {ep['pays']}"
    m_ext = mots(nom_ext)
    v_ext = ville_racine(ville_ext or "")
    meilleur, motif, m_best = 0.0, "", set()
    for nom in ep["noms"]:
        m_ep = mots(nom)
        if not m_ext or not m_ep:
            continue
        c_ext = _communs(m_ext, m_ep)
        c_ep = _communs(m_ep, m_ext)
        cov_ext = sum(map(poids, c_ext)) / max(sum(map(poids, m_ext)), 1e-9)
        cov_ep = sum(map(poids, c_ep)) / max(sum(map(poids, m_ep)), 1e-9)
        s = 0.65 * min(cov_ext, cov_ep) + 0.35 * max(cov_ext, cov_ep)
        if s > meilleur:
            meilleur, motif, m_best = s, "mots communs : " + ", ".join(sorted(c_ext)), m_ep
    if not meilleur:
        return 0.0, "aucun mot commun"
    # mot propre au dashboard, absent du nom exterieur : autre course
    # (« Midnattsloppet Stockholm » contre « adidas Stockholm Half »). Les
    # villes, marques et partenaires connus de l'epreuve n'en sont pas.
    table, defaut = idf()
    sponsors = partenaires().get(ep["evenement"], set())
    propres = {w for w in m_best - _communs(m_best, m_ext)
               if w not in marques() and w not in sponsors
               and w != ep["ville"].replace(" ", "") and w not in QUALIFICATIFS
               and table.get(w, defaut) >= 0.6 * defaut}
    if propres:
        meilleur *= F_MOT_PROPRE
        motif += " - propre au dashboard : " + ",".join(sorted(propres))
    # qualificatif present d'un seul cote : autre course
    q = (m_ext ^ m_best) & QUALIFICATIFS
    if q:
        meilleur *= F_QUALIFICATIF
        motif += " - qualificatif " + ",".join(sorted(q))
    vt = ep["ville"].replace(" ", "")
    tous_ep = set().union(*(mots(n) for n in ep["noms"]))
    meme_ville = bool(vt) and (vt == v_ext.replace(" ", "") or vt in m_ext
                               or (v_ext and v_ext.replace(" ", "") in tous_ep))
    if meme_ville:
        meilleur = min(1.0, meilleur + 0.15)
        motif += " + meme ville"
    elif v_ext and vt:
        meilleur *= F_VILLES_DIFFERENTES
        motif += " - villes differentes"
    if cl and cl == ep["distance"]:
        meilleur = min(1.0, meilleur + 0.05)
    return round(meilleur, 3), motif


def rapprocher(nom_ext, ville_ext="", pays_ext=None, distance_ext=None, seuil=SEUIL):
    """Meilleure ligne du dashboard pour un nom exterieur, ou None.

    Rend (ligne, score, motif). `ligne` est un dict {evenement, distance, ...}.
    """
    a = alias().get(sans_accents(nom_ext).strip())
    if a and a.get("evenement") is None:
        return None, 0.0, "alias : course non suivie"
    if a:
        lignes = [ep for ep in epreuves() if ep["evenement"] == a["evenement"]]
        voulue = a.get("distance") or distance_ext or classe_distance(nom_ext)
        choix = ([ep for ep in lignes if ep["distance"] == voulue] if voulue else [])
        if not choix and len(lignes) == 1:
            choix = lignes
        if not choix and not voulue:
            choix = [ep for ep in lignes if ep["distance"] == "MARATHON"]
        if choix:
            return choix[0], 1.0, "alias confirme"
    best = (None, 0.0, "")
    for ep in epreuves():
        s, m = score(nom_ext, ville_ext, pays_ext, ep, distance_ext)
        if s > best[1]:
            best = (ep, s, m)
    if best[1] >= seuil:
        return best
    return None, best[1], best[2]


def depuis_venue(venue):
    """« Warszawa (POL) » -> ("Warszawa", "POL")."""
    v = venue or ""
    m = re.findall(r"\(([A-Z]{3})\)", v)
    ville = re.sub(r"\(.*?\)", "", v.split(",")[0]).strip()
    return ville, (m[-1] if m else None)


# --- Evaluation --------------------------------------------------------------

def evaluer(chemin=ICI / "rapprochement_gold.json", seuil=SEUIL, verbeux=True):
    gold = json.loads(Path(chemin).read_text(encoding="utf-8"))["cas"]
    vp = fp = fn = vn = 0
    erreurs = []
    for g in gold:
        ville, pays = depuis_venue(g.get("venue", ""))
        ep, s, motif = rapprocher(g["nom"], ville, pays, seuil=seuil)
        trouve = f"{ep['evenement']}|{ep['distance']}" if ep else None
        attendu = g.get("attendu")
        if attendu and trouve == attendu:
            vp += 1
        elif attendu and trouve is None:
            fn += 1; erreurs.append(("rate", g["nom"], attendu, s, motif))
        elif attendu:
            fp += 1; fn += 1; erreurs.append(("mauvais", g["nom"], f"{trouve} au lieu de {attendu}", s, motif))
        elif trouve:
            fp += 1; erreurs.append(("faux positif", g["nom"], trouve, s, motif))
        else:
            vn += 1
    prec = vp / (vp + fp) if vp + fp else 1.0
    rap = vp / (vp + fn) if vp + fn else 1.0
    if verbeux:
        print(f"cas={len(gold)}  vrais positifs={vp}  faux positifs={fp}  rates={fn}  vrais negatifs={vn}")
        print(f"precision={prec:.1%}  rappel={rap:.1%}")
        for e in erreurs:
            print("  ", e)
    return prec, rap


if __name__ == "__main__":
    import sys
    if "--eval" in sys.argv:
        evaluer()
    else:
        ep, s, m = rapprocher(" ".join(a for a in sys.argv[1:] if not a.startswith("--")))
        print(ep and f"{ep['evenement']}|{ep['distance']}", s, m)

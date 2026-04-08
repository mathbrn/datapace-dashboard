#!/usr/bin/env python3
"""
ASO Dashboard Generator (internal)
==================================
Genere datapace_dashboard.html.

Source de donnees (par priorite) :
    1. Base SQLite (datapace.db) — si presente
    2. Fichiers Excel (fallback)

Usage :
    python generate_dashboard.py
"""

import os
import pandas as pd
import json
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

SCRIPT_DIR = Path(__file__).parent
_DB_PATH = Path(os.environ.get("DATAPACE_DB", str(SCRIPT_DIR / "datapace.db")))

FILES = {
    "finishers":     SCRIPT_DIR / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx",
    "marathon_2024": SCRIPT_DIR / "Temps_moyen_par_marathon_2024.xlsx",
    "marathon_2025": SCRIPT_DIR / "Temps_moyen_par_marathon_2025.xlsx",
    "marathon_2026": SCRIPT_DIR / "Temps_moyen_par_marathon_2026.xlsx",
    "semi":          SCRIPT_DIR / "Temps_moyen_semi-marathon.xlsx",
    "winners":       SCRIPT_DIR / "Chronos_Vainqueurs.xlsx",
}
OUTPUT_FILE = SCRIPT_DIR / "datapace_dashboard.html"

WMM_KEYWORDS = [
    "tcs new york city marathon", "tcs london marathon", "boston marathon",
    "tcs sydney marathon", "bmw berlin marathon",
    "bank of america chicago marathon", "tokyo marathon",
]

# --- Circuit definitions ---
# EMC: European Marathon Classics — matched by city (marathon distance only)
EMC_CITIES = {"rome", "vienna", "vienne", "madrid", "london", "londres",
              "copenhagen", "copenhague", "warsaw", "varsovie",
              "lisbon", "lisbonne", "frankfurt"}
# L5G: Las 5 Grandes — 5 grands marathons espagnols, matched by city (marathon distance only)
L5G_CITIES = {"sevilla", "seville", "séville", "madrid",
              "barcelona", "barcelone", "valencia", "valence", "bilbao"}

CIRCUIT_COLORS = {
    "WMM": "#38BDF8",
    "EMC": "#F87171",
    "RNR": None,  # secondary color of the event's distance
    "L5G": "#DC2626",
}

def compute_circuits(race_name, distance, city):
    """Return list of circuit codes for a given event."""
    circuits = []
    rl = race_name.lower()
    cl = city.lower()
    # WMM
    if any(k in rl for k in WMM_KEYWORDS):
        circuits.append("WMM")
    # EMC — marathon distance, European cities
    if distance == "MARATHON" and cl in EMC_CITIES:
        circuits.append("EMC")
    # RNR — Rock 'n' Roll in the name
    if "rock" in rl and "roll" in rl:
        circuits.append("RNR")
    # L5G — marathon distance, Spanish cities
    if distance == "MARATHON" and cl in L5G_CITIES:
        circuits.append("L5G")
    return circuits


def fmt_time(val):
    if val is None or (isinstance(val, float) and pd.isna(val)): return None
    if isinstance(val, datetime.time): return val.strftime("%H:%M:%S")
    if isinstance(val, float) and 0 < val < 1:
        # Excel fraction of day -> HH:MM:SS
        total_seconds = int(round(val * 86400))
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    s = str(val).strip()
    return None if s in ("", "nan", "NaT", "None") else s


def safe_int(val):
    try: v = int(float(val)); return v if v > 0 else None
    except: return None


def j(obj): return json.dumps(obj, ensure_ascii=False, default=str)


def check_files():
    missing = [k for k, p in FILES.items() if not p.exists()]
    if missing:
        print("Fichiers manquants :")
        for k in missing:
            print(f"  - {FILES[k].name}")
        print("\nPlace les fichiers Excel dans le meme dossier que ce script.")
        sys.exit(1)
    print("Tous les fichiers Excel trouves.")


CITY_REGION = {
    # Europe
    "Amsterdam": "Europe", "Athènes": "Europe", "Barcelone": "Europe", "Bath": "Europe",
    "Berlin": "Europe", "Birmingham": "Europe", "Boulogne-Billancourt": "Europe",
    "Breda": "Europe",
    "Brighton": "Europe", "Bristol": "Europe", "Cardiff": "Europe", "Copenhague": "Europe",
    "Dublin": "Europe", "Frankfurt": "Europe", "Gateshead": "Europe", "Geneve": "Europe", "Genève": "Europe", "Glasgow": "Europe",
    "Göteborg (Suède)": "Europe", "Hamburg": "Europe", "Istanbul": "Europe", "Lisbonne": "Europe",
    "Ljubljana": "Europe",
    "Londres": "Europe", "Lyon": "Europe", "Madrid": "Europe", "Manchester": "Europe",
    "Marseille": "Europe", "Milan": "Europe", "Munich": "Europe", "Nantes": "Europe",
    "Naples": "Europe", "Newcastle": "Europe", "Paris": "Europe", "Portsmouth": "Europe",
    "Porto": "Europe",
    "Prague": "Europe", "Rome": "Europe", "Rotterdam": "Europe", "Seville": "Europe",
    "Rennes": "Europe", "Stockholm": "Europe", "Toulouse": "Europe", "Tours": "Europe",
    "Utrecht": "Europe", "Valence": "Europe",
    "Varsovie": "Europe", "Vienne": "Europe",
    # North America
    "Atlanta": "Amérique du Nord", "Austin": "Amérique du Nord", "Austin, TX": "Amérique du Nord",
    "Baltimore": "Amérique du Nord", "Boston": "Amérique du Nord", "Boulder": "Amérique du Nord",
    "Charleston": "Amérique du Nord", "Chicago": "Amérique du Nord", "Cincinnati": "Amérique du Nord",
    "Columbus": "Amérique du Nord", "Dallas": "Amérique du Nord", "Denver": "Amérique du Nord",
    "Detroit": "Amérique du Nord", "Duluth": "Amérique du Nord", "Eugene": "Amérique du Nord",
    "Falmouth": "Amérique du Nord", "Fargo": "Amérique du Nord", "Fort Worth": "Amérique du Nord",
    "Honolulu": "Amérique du Nord", "Houston": "Amérique du Nord",
    "Indianapolis": "Amérique du Nord", "Jacksonville": "Amérique du Nord",
    "Las Vegas": "Amérique du Nord", "Long Beach": "Amérique du Nord",
    "Los Angeles": "Amérique du Nord", "Memphis": "Amérique du Nord",
    "Miami": "Amérique du Nord", "Minneapolis": "Amérique du Nord",
    "Montréal": "Amérique du Nord", "Nashville": "Amérique du Nord",
    "New Orleans": "Amérique du Nord", "New York": "Amérique du Nord",
    "Newport Beach": "Amérique du Nord", "Oklahoma City": "Amérique du Nord",
    "Orlando": "Amérique du Nord", "Philadelphia": "Amérique du Nord",
    "Phoenix": "Amérique du Nord", "Pittsburgh": "Amérique du Nord",
    "Portland": "Amérique du Nord", "Richmond": "Amérique du Nord",
    "Sacramento": "Amérique du Nord", "San Antonio": "Amérique du Nord",
    "San Diego": "Amérique du Nord", "San Francisco": "Amérique du Nord",
    "San Jose": "Amérique du Nord", "Spokane": "Amérique du Nord",
    "Tampa": "Amérique du Nord", "Toronto": "Amérique du Nord",
    "Utica": "Amérique du Nord", "Vancouver": "Amérique du Nord",
    "Virginia Beach": "Amérique du Nord", "Washington DC": "Amérique du Nord",
    "Mexico City": "Amérique du Nord",
    # Asia
    "Beijing": "Asie", "Chon Buri": "Asie", "Hong Kong": "Asie",
    "Kuala Lumpur": "Asie", "Marugame": "Asie", "Mumbai": "Asie",
    "New Delhi": "Asie", "Osaka": "Asie", "Seoul": "Asie",
    "Shanghai": "Asie", "Singapour": "Asie", "Taipei": "Asie", "Tokyo": "Asie",
    # Oceania
    "Brisbane": "Océanie", "Gold Coast": "Océanie", "Melbourne": "Océanie", "Sydney": "Océanie",
    # Middle East
    "Dubai": "Moyen-Orient", "Riyadh": "Moyen-Orient",
    # South America
    "Bogota": "Amérique du Sud",
    # Africa
    "Cape Town": "Afrique",
}

def get_region(city):
    return CITY_REGION.get(city, "Autre")

def load_finishers():
    df = pd.read_excel(FILES["finishers"], sheet_name="ALL")
    year_cols = sorted([c for c in df.columns if isinstance(c, int) and 2000 <= c <= 2030])
    rows = []
    for _, r in df.iterrows():
        race = str(r.get("Race", "")).strip()
        if not race or race == "nan": continue
        def gv(col, r=r):
            v = r.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)): return None
            sv = str(v).strip()
            if sv == "-": return -1  # Edition annulee
            if sv.lower() == "elite": return -2  # Elite only
            if sv.lower() == "x": return -3  # Event did not exist yet
            try: iv = int(float(v)); return iv if iv > 0 else None
            except: return None
        hist = {yr: v for yr in year_cols if (v := gv(yr)) is not None}
        # Find first edition year = first year that is NOT 'x' (event existed)
        # Only show star for events created in 2000 or later
        first_yr = None
        for yr in sorted(year_cols):
            v = gv(yr)
            if v != -3:  # first year that is not 'x' = event exists
                if yr >= 2000:
                    first_yr = yr
                break  # stop at first non-x year regardless
        city = str(r.get("City", "")).strip()
        dist = str(r.get("Distance", "")).strip()
        circ = compute_circuits(race, dist, city)
        rows.append({"p": str(r.get("Période", "")).strip(), "c": city,
                     "d": dist, "r": race,
                     "rg": get_region(city),
                     "hist": hist, "fy": first_yr, "ci": circ})
    print(f"  Finishers  : {len(rows)} courses")
    return rows


def load_biggest():
    df = pd.read_excel(FILES["finishers"], sheet_name="BIGGEST EVENTS")
    year_cols = sorted([c for c in df.columns if isinstance(c, int) and 2000 <= c <= 2030])
    rows = []
    for _, r in df.iterrows():
        race = str(r.get("Race", "")).strip()
        if not race or race == "nan": continue
        def gv(col, r=r):
            v = r.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)): return None
            sv = str(v).strip()
            if sv == "-": return -1  # Edition annulee
            if sv.lower() == "elite": return -2  # Elite only
            try: iv = int(float(v)); return iv if iv > 0 else None
            except: return None
        hist = {yr: v for yr in year_cols if (v := gv(yr)) is not None}
        city = str(r.get("City", "")).strip()
        rows.append({"c": city, "r": race, "rg": get_region(city),
                     "hist": hist})
    print(f"  Biggest    : {len(rows)} courses")
    return rows


def load_marathon(year):
    path = FILES[f"marathon_{year}"]
    if year == 2024:
        df = pd.read_excel(path, header=None); rows = []
        for _, r in df.iterrows():
            vals = r.tolist(); race = avg = None; finishers = None
            for v in vals:
                if isinstance(v, str) and len(v) > 4 and v not in ("nan", "RACE", "Race"): race = v.strip()
                elif isinstance(v, (int, float)) and not (isinstance(v, float) and pd.isna(v)) and float(v) > 100: finishers = int(float(v))
                elif isinstance(v, datetime.time): avg = v.strftime("%H:%M:%S")
            if race: rows.append({"race": race, "city": "", "finishers": finishers,
                                  "avg": avg, "men": None, "women": None, "year": year})
    else:
        df = pd.read_excel(path, sheet_name="Finishers", header=None)
        df.columns = ["_", "city", "race", "finishers", "avg_time", "best",
                      "men_time", "women_time", "top10_avg", "sub3"]
        rows = []
        for _, r in df.iloc[3:].iterrows():
            race = str(r["race"]).strip() if pd.notna(r["race"]) else ""
            if not race or race in ("nan", "Race"): continue
            rows.append({"race": race,
                         "city": str(r["city"]).strip() if pd.notna(r["city"]) else "",
                         "finishers": safe_int(r["finishers"]),
                         "avg": fmt_time(r["avg_time"]), "men": fmt_time(r["men_time"]),
                         "women": fmt_time(r["women_time"]), "year": year})
    print(f"  Marathon {year}: {len(rows)} courses")
    return rows


def load_semi():
    path = FILES["semi"]
    xls = pd.ExcelFile(path)
    all_data = {}
    for sheet in xls.sheet_names:
        try:
            yr = int(sheet)
        except ValueError:
            continue
        df = pd.read_excel(path, sheet_name=sheet, header=None)
        if len(df.columns) < 8:
            df = df.reindex(columns=range(8))
        df.columns = ["_", "city", "race", "finishers", "avg_time", "men_time", "women_time", "top10_avg"]
        # Find header row
        start = 3
        for i, row in df.iterrows():
            if str(row.get("race", "")).strip().lower() in ("race", "race "):
                start = i + 1
                break
        rows = []
        for _, r in df.iloc[start:].iterrows():
            race = str(r["race"]).strip() if pd.notna(r["race"]) else ""
            if not race or race in ("nan", "Race"): continue
            rows.append({"race": race,
                         "city": str(r["city"]).strip() if pd.notna(r["city"]) else "",
                         "finishers": safe_int(r["finishers"]),
                         "avg": fmt_time(r["avg_time"]), "men": fmt_time(r["men_time"]),
                         "women": fmt_time(r["women_time"]), "year": yr})
        if rows:
            all_data[yr] = rows
            print(f"  Semi {yr}   : {len(rows)} courses")
    return all_data


def load_winners():
    path = FILES["winners"]
    if not path.exists():
        print("  Winners    : fichier absent, onglet desactive")
        return []
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        course, distance, year, men, women = row
        if (men and men != "N/A" and men != "Annule") or (women and women != "N/A" and women != "Annule"):
            rows.append({"r": str(course), "d": str(distance), "y": int(year),
                         "m": str(men) if men and men not in ("N/A", "Annule", "Annulé") else "",
                         "w": str(women) if women and women not in ("N/A", "Annule", "Annulé") else ""})
    print(f"  Winners    : {len(rows)} resultats")
    return rows


def load_sporthive_avg():
    """Load average times computed from Sporthive API."""
    path = SCRIPT_DIR / "avg_times_sporthive.json"
    if not path.exists():
        return []
    import json as jlib
    with open(path, "r") as f:
        data = jlib.load(f)
    # Map to standard format: {race, year, avg, dist_category}
    rows = []
    race_map = {
        "TCS Marathon": "TCS Amsterdam Marathon",
        "Mizuno Half Marathon": "TCS Mizuno Half Marathon",
        "Mizuno Halve Marathon": "TCS Mizuno Half Marathon",
        "NN Marathon Rotterdam 2018": "NN Marathon Rotterdam",
        "NN Marathon Rotterdam 2019": "NN Marathon Rotterdam",
        "NN Marathon Rotterdam 2021": "NN Marathon Rotterdam",
        "NN Marathon Rotterdam 2022": "NN Marathon Rotterdam",
        "NN Marathon Rotterdam 2023": "NN Marathon Rotterdam",
        "NN Marathon Rotterdam 2024": "NN Marathon Rotterdam",
        "NN Halve Marathon": "NN CPC Loop Den Haag - Half Marathon",
        "EDP Meia Maratona de Lisboa": "EDP Lisboa Meia Maratona",
        "EDP Maratona de Lisboa": "EDP Maratona de Lisboa",
        "Half Marathon": None,
        "Maratón": None,
        "Media Maratón": None,
        "Marathon": None,
    }
    label_map = {
        "LLHM": "London Landmarks Half Marathon",
        "Cardiff": "Cardiff Half Marathon",
        "Manchester HM": "Manchester Half Marathon",
        "Royal Parks": "Royal Parks Half Marathon",
        "ManM": "Adidas Manchester Marathon",
        "Brighton HM": "Brighton Half Marathon",
    }
    for item in data:
        rname = item["race"]
        label = item["label"].rsplit(" ", 1)[0]  # remove year
        mapped = race_map.get(rname)
        if mapped is None:
            mapped = label_map.get(label, rname)
        elif mapped:
            pass  # use mapped name
        rows.append({"race": mapped, "year": item["year"],
                     "avg": item["avg_time"], "men": "", "women": ""})
    print(f"  Sporthive avg: {len(rows)} temps moyens")
    return rows


def build_times_db(md, sd):
    db = {}; all_e = []
    for rows in md.values(): all_e.extend(rows)
    for rows in sd.values(): all_e.extend(rows)
    # Add Sporthive average times
    sp_avg = load_sporthive_avg()
    all_e.extend(sp_avg)
    all_e.sort(key=lambda x: x.get("year", 0))
    for row in all_e:
        if row.get("avg") or row.get("men"):
            db[row["race"].lower()] = {
                "men": row.get("men") or "", "women": row.get("women") or "",
                "avg": row.get("avg") or "", "yr": row.get("year")}
    return db


JS_LOGIC = '''function isWmm(r){var l=r.toLowerCase();return WMM_KEYWORDS.some(function(k){return l.indexOf(k)>=0;});}
function isLight(){return document.documentElement.hasAttribute('data-theme');}
var LIGHT_MAP={'#38BDF8':'#0B7BC0','#FCDB00':'#A88F00','#DC2626':'#991B1B','#EF4444':'#B91C1C','#FF8A50':'#CC5A20','#5CDFA0':'#2BA368','#F472B6':'#C04080','#FF4A6B':'#CC2040','#22C55E':'#1A8A42','#2DBF7E':'#1F8A5A','#FF6B9D':'#CC3870','#F87171':'#B91C1C','#2563EB':'#1D4ED8','#60A5FA':'#2563EB','#3B82F6':'#1D4ED8','#BFDBFE':'#93C5FD','#1E3A8A':'#172554','#1D4ED8':'#1E3A8A','#1E40AF':'#1E3A8A','#93C5FD':'#60A5FA'};
function lc(c){return isLight()?(LIGHT_MAP[c]||c):c;}
function col(r){return lc('#DC2626');}
function colDist(r){return lc(r.d==='10KM'?'#5CDFA0':r.d==='SEMI'?'#FF8A50':r.d==='AUTRE'?'#F472B6':'#2563EB');}
var CIRC_COLORS={WMM:'#38BDF8',EMC:'#F87171',L5G:'#DC2626'};
var CIRC_DIST_SEC={MARATHON:'#F87171',SEMI:'#FFB088','10KM':'#88EEBB',AUTRE:'#FF99CC'};
function circColor(code,dist){if(code==='RNR')return lc(CIRC_DIST_SEC[dist]||'#F87171');return lc(CIRC_COLORS[code]||'#F87171');}
function circBadges(r){var ci=r.ci||[];if(!ci.length)return'';return ci.map(function(c){var col=circColor(c,r.d);return'<span class="circ-badge" style="border:1px solid '+col+'40;color:'+col+';background:transparent;font-size:9px;padding:1px 6px;border-radius:100px;text-transform:uppercase;margin-left:4px;white-space:nowrap">'+c+'</span>';}).join('');}
function hasCircuit(r,code){return(r.ci||[]).indexOf(code)>=0;}
function colByName(name){var r=RAW.find(function(x){return x.r===name;});return r?colDist(r):lc('#60A5FA');}
function toMin(t){if(!t)return null;var p=String(t).split(':');if(p.length===3)return parseInt(p[0])*60+parseInt(p[1])+parseInt(p[2])/60;return null;}
function fmt(n){if(n===-1)return'Annul\u00e9';if(n===-2)return'Elite';if(n===-3)return'';if(!n||isNaN(n))return'\u2014';return n>=1000?(n/1000).toFixed(1)+'k':n.toString();}
function fmtFull(n){if(n===-1)return'Annul\u00e9';if(n===-2)return'Elite Only';if(n===-3)return'';if(!n||isNaN(n))return'\u2014';return Math.round(n).toLocaleString('fr-FR');}
function delta(a,b){if(!a||!b||isNaN(a)||isNaN(b))return null;return((b-a)/a*100);}
function lightenHex(hex,amt){var r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);r=Math.min(255,r+Math.round((255-r)*amt));g=Math.min(255,g+Math.round((255-g)*amt));b=Math.min(255,b+Math.round((255-b)*amt));return'#'+[r,g,b].map(function(c){return c.toString(16).padStart(2,'0');}).join('');}
function hv(r,yr){return(r.hist||{})[yr]||null;}
function lastFin(r){var ks=Object.keys(r.hist||{}).map(Number).filter(function(y){var v=(r.hist||{})[y];return v&&v>0;}).sort(function(a,b){return b-a;});return ks.length?{yr:ks[0],v:(r.hist||{})[ks[0]]}:null;}
function fmtHM(mins){var h=Math.floor(mins/60),m=Math.round(mins%60);return h+'h'+String(m).padStart(2,'0');}
function fmtHMMin(mins){return fmtHM(mins)+'min';}
function csVar(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim();}
function mkGRID(){return isLight()?'rgba(0,0,0,0.05)':'rgba(255,255,255,0.03)';}
function mkTICK(){return{color:isLight()?'#888':'#555',font:{size:10}};}
function mkTT(cb){var lt=isLight();var o={backgroundColor:lt?'#ffffff':'#1a1a2e',borderColor:lt?'rgba(0,0,0,0.08)':'rgba(255,255,255,0.08)',borderWidth:1,titleColor:'#888',bodyColor:lt?'#0a0a0a':'#f0f0f0',padding:12,cornerRadius:6,displayColors:true,boxWidth:8,boxHeight:8,boxPadding:4,titleFont:{size:10,family:'Inter',weight:'400'},bodyFont:{size:13,family:'Inter',weight:'500'}};if(cb)o.callbacks=cb;return o;}
function mkBorder(){return'transparent';}
var GRID=mkGRID();
var TICK=mkTICK();TICK.maxRotation=0;TICK.minRotation=0;TICK.autoSkip=true;TICK.maxTicksLimit=12;
var TT=mkTT();


function getTimeData(rn){
  var l=rn.toLowerCase();
  var keys=Object.keys(TIMES_DB);
  for(var i=0;i<keys.length;i++){var k=keys[i];if(l.indexOf(k)>=0||k.indexOf(l.substring(0,12))>=0)return TIMES_DB[k];}
  return null;
}
var _spCols=_spCols||{'Equipementier sport':'#22C55E','Banque/Finance':'#38BDF8','Assurance':'#818CF8','Finance/Investissement':'#38BDF8','Automobile':'#FF8A50','Tech/IT':'#F472B6','Energie':'#FCDB00','Industrie/Energie':'#FCDB00','Sante':'#2DBF7E','Fondation/Mecenat':'#FF6B9D','Aviation/Transport':'#5CDFA0','Nutrition/Alimentaire':'#FF9F45','Audio/Wearables':'#C084FC','Paiement/Finance':'#34D399','Retail/Mode':'#FB923C','Conglomeral/Tech':'#94A3B8','Transport':'#60A5FA','Boisson/Brasserie':'#FCD34D','Hydratation/Consommation':'#FB923C','Horlogerie/Luxe':'#E2E8F0','Nutrition/Boisson':'#FF9F45','Tech/Wearables':'#F472B6','Tech/App sport':'#F472B6','Nutrition sport':'#FF9F45','Horlogerie/Chronometrage':'#E2E8F0','Crypto/Fintech':'#34D399','Telecom':'#60A5FA','Eau/Boisson':'#5CDFA0','Energie/Petrole':'#FCDB00','Alimentaire/Livraison':'#FF9F45','Restauration/Boisson':'#FCD34D','Tech/Tourisme':'#F472B6','Fitness/Tech':'#F472B6','Mobilite/Location':'#FF8A50','Alimentaire':'#FF9F45','Retail/Distribution sport':'#FB923C','Automobile/EV':'#FF8A50','Industrie/Ressources':'#94A3B8','Retail/Pharmacie':'#FB923C','Environnement/Recyclage':'#5CDFA0','Marketing sportif':'#94A3B8','Hygiene/Cosmetique':'#F472B6','Cosmetique':'#F472B6','Tech/SaaS':'#F472B6','Immobilier':'#94A3B8','Restauration':'#FCD34D','Fintech/Paiement':'#34D399','Industrie/Batteries':'#94A3B8','Tech/Electronique':'#F472B6','Luxe/Joaillerie':'#E2E8F0','Transport/Croisiere':'#60A5FA','Grande distribution':'#FB923C','Organisateur/Media':'#94A3B8','Immobilier/Tech':'#94A3B8','Conglomerat/Tech':'#94A3B8'};
function buildOvSponsoring(eventName,eventColor){
  if(typeof SP_PARTNERSHIPS==='undefined')return '';
  var ec=eventColor||'var(--purple)';
  var now=new Date().getFullYear();
  var parts=SP_PARTNERSHIPS.filter(function(p){return p.event===eventName&&p.years&&p.years.indexOf(now)>=0;});
  if(!parts.length){
    var ln=eventName.toLowerCase();
    parts=SP_PARTNERSHIPS.filter(function(p){return p.years&&p.years.indexOf(now)>=0&&(p.event.toLowerCase().indexOf(ln.substring(0,15))>=0||ln.indexOf(p.event.toLowerCase().substring(0,15))>=0);});
  }
  if(!parts.length)return '';
  var byType={title:[],premium:[],major:[],official:[],partner:[]};
  parts.forEach(function(p){(byType[p.type]||byType.partner).push(p);});
  var lt=isLight();
  var ecLight=lightenHex(ec,0.3);
  var tConf={
    title:{label:'TITRE',border:ec,text:lt?ec:'#fff',bg:ec+(lt?'1F':'26')},
    premium:{label:'PREMIUM',border:ec+'B3',text:lt?ec:ecLight,bg:ec+(lt?'14':'1F')},
    major:{label:'MAJEUR',border:ec+'B3',text:lt?ec:ecLight,bg:ec+(lt?'14':'1F')},
    official:{label:'OFFICIEL',border:ec+(lt?'66':'80'),text:ec,bg:ec+(lt?'0F':'14')},
    partner:{label:'FOURNISSEUR',border:lt?'rgba(0,0,0,0.15)':'#ffffff25',text:lt?'#666':'#888',bg:'transparent'}
  };
  var h='<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border)">'
    +'<div class="ov-chart-label" style="margin-bottom:10px">Partenaires '+now+'</div>';
  ['title','premium','major','official','partner'].forEach(function(t){
    var items=byType[t];if(!items.length)return;
    var tc=tConf[t];
    var names=items.map(function(p){return'<span style="font-size:12px;color:var(--text);" title="'+p.brand+' ('+p.years[0]+'-'+p.years[p.years.length-1]+')">'+p.brand+'</span>';}).join('<span style="color:var(--text3);margin:0 2px;">,</span> ');
    h+='<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;">'
      +'<span style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:3px 10px;border-radius:100px;border:1px solid '+tc.border+';color:'+tc.text+';background:'+tc.bg+';flex-shrink:0;">'+tc.label+'</span>'
      +names+'</div>';
  });
  h+='</div>';
  return h;
}
function getWinnersRecords(rn){
  var entries=WINNERS.filter(function(w){return w.r===rn;});
  if(!entries.length){
    var l=rn.toLowerCase();
    entries=WINNERS.filter(function(w){return w.r.toLowerCase().indexOf(l.substring(0,15))>=0||l.indexOf(w.r.toLowerCase().substring(0,15))>=0;});
  }
  if(!entries.length)return null;
  var bestM=null,bestMyr=null,bestW=null,bestWyr=null;
  entries.forEach(function(w){
    var ms=winToSec(w.m),ws=winToSec(w.w);
    if(ms&&(bestM===null||ms<bestM)){bestM=ms;bestMyr=w.y;}
    if(ws&&(bestW===null||ws<bestW)){bestW=ws;bestWyr=w.y;}
  });
  return{men:bestM?secToTime(bestM):'',menYr:bestMyr,women:bestW?secToTime(bestW):'',womenYr:bestWyr};
}
function buildTimeHistory(rn){
  var l=rn.toLowerCase(),hist=[],seen={};
  // 1. Search TEMPS_MARATHON
  [2024,2025,2026].forEach(function(yr){
    var rows=TEMPS_MARATHON[String(yr)]||[];
    for(var i=0;i<rows.length;i++){var rl=rows[i].race.toLowerCase();if(l.indexOf(rl.substring(0,10))>=0||rl.indexOf(l.substring(0,10))>=0){if(toMin(rows[i].avg)){hist.push({yr:String(yr),min:toMin(rows[i].avg)});seen[yr]=1;}break;}}
  });
  // 2. Search TEMPS_SEMI
  var sKeys=Object.keys(TEMPS_SEMI);sKeys.forEach(function(syr){if(seen[syr])return;var srows=TEMPS_SEMI[syr]||[];for(var i=0;i<srows.length;i++){var rl=srows[i].race.toLowerCase();if(l.indexOf(rl.substring(0,10))>=0||rl.indexOf(l.substring(0,10))>=0){if(toMin(srows[i].avg)){hist.push({yr:syr,min:toMin(srows[i].avg)});seen[syr]=1;}break;}}});
  // 3. Search TEMPS_AVG (Sporthive computed averages)
  if(typeof TEMPS_AVG!=='undefined'){TEMPS_AVG.forEach(function(ta){if(seen[ta.yr])return;var rl=ta.race.toLowerCase();if(l.indexOf(rl.substring(0,10))>=0||rl.indexOf(l.substring(0,10))>=0){if(toMin(ta.avg)){hist.push({yr:String(ta.yr),min:toMin(ta.avg)});seen[ta.yr]=1;}}});}
  hist.sort(function(a,b){return parseInt(a.yr)-parseInt(b.yr);});
  return hist;
}
var cT=null,ovChartF=null,ovChartT=null,ovChartM=null,ovChartW=null;
function buildWinnerHistory(rn){
  var l=rn.toLowerCase();
  var entries=WINNERS.filter(function(w){return w.r===rn;});
  if(!entries.length){entries=WINNERS.filter(function(w){return w.r.toLowerCase().indexOf(l.substring(0,15))>=0||l.indexOf(w.r.toLowerCase().substring(0,15))>=0;});}
  if(!entries.length)return{men:[],women:[]};
  entries.sort(function(a,b){return a.y-b.y;});
  var men=[],women=[];
  entries.forEach(function(w){
    var ms=winToSec(w.m),ws=winToSec(w.w);
    if(ms)men.push({yr:w.y,sec:ms,time:w.m});
    if(ws)women.push({yr:w.y,sec:ws,time:w.w});
  });
  return{men:men,women:women};
}

function toggleTheme(){
  var html=document.documentElement;
  var btn=document.getElementById('theme-btn');
  if(html.getAttribute('data-theme')==='light'){
    html.removeAttribute('data-theme');
    btn.innerHTML='&#x263E; Dark';
    localStorage.setItem('dp-theme','dark');
  }else{
    html.setAttribute('data-theme','light');
    btn.innerHTML='&#x2600; Light';
    localStorage.setItem('dp-theme','light');
  }
  // Update all Chart.js instances
  if(typeof Chart!=='undefined'){
    var gridColor=getComputedStyle(html).getPropertyValue('--border').trim();
    var textColor=getComputedStyle(html).getPropertyValue('--text3').trim();
    Object.keys(Chart.instances||{}).forEach(function(k){
      var c=Chart.instances[k];
      if(c.options.scales){
        ['x','y','y1'].forEach(function(ax){
          if(c.options.scales[ax]){
            c.options.scales[ax].ticks=c.options.scales[ax].ticks||{};
            c.options.scales[ax].ticks.color=textColor;
            c.options.scales[ax].grid=c.options.scales[ax].grid||{};
            c.options.scales[ax].grid.color=gridColor;
          }
        });
      }
      c.update('none');
    });
  }
  // Re-render tabs to update colors
  if(typeof filterTable==='function')filterTable();
  if(typeof initBiggestYears==='function')initBiggestYears();
  if(typeof updateWinnersTable==='function')updateWinnersTable();
}
(function(){var saved=localStorage.getItem('dp-theme');if(saved==='light'){document.documentElement.setAttribute('data-theme','light');var b=document.getElementById('theme-btn');if(b)b.innerHTML='&#x2600; Light';}})();

// ===== EXPORT PANEL (PNG / PDF) =====
function toggleExportMenu(e){
  if(e)e.stopPropagation();
  var m=document.getElementById('export-menu');
  m.style.display=m.style.display==='none'?'block':'none';
}
document.addEventListener('click',function(e){
  var btn=document.getElementById('export-btn');
  var menu=document.getElementById('export-menu');
  if(menu&&menu.style.display!=='none'&&!btn.contains(e.target)&&!menu.contains(e.target)){
    menu.style.display='none';
  }
});
function getActiveTabInfo(){
  var tabs=document.querySelectorAll('.tab');
  var names=['data','overview','compare','trends','biggest','temps','winners','sponsoring'];
  var labels=['Tableau','Vue_d_ensemble','Comparer','Evolution','Top_evenements','Temps_moyen','Winners_Times','Sponsoring'];
  for(var i=0;i<tabs.length;i++){
    if(tabs[i].classList.contains('active'))return{id:names[i],label:labels[i]};
  }
  return{id:'data',label:'Tableau'};
}
function safeFn(s){return String(s||'').replace(/[^a-zA-Z0-9-]/g,'_').replace(/_+/g,'_').replace(/^_|_$/g,'');}
function getFilterParts(tabId){
  var parts=[];
  function add(id){var el=document.getElementById(id);if(el&&el.value&&el.value!=='ALL')parts.push(safeFn(el.value));}
  if(tabId==='data'){
    add('dist-data');add('region-data');add('size-data');
    var s=document.getElementById('search-data');if(s&&s.value)parts.push(safeFn(s.value));
  }else if(tabId==='trends'){
    add('dist-trends');add('region-trends');
    var n=document.getElementById('topn-trends');if(n)parts.push('top'+n.value);
  }else if(tabId==='biggest'){
    add('dist-biggest');add('region-biggest');
    var nb=document.getElementById('topn-biggest');if(nb)parts.push('top'+nb.value);
    add('year-biggest');
  }else if(tabId==='temps'){
    add('dist-temps');add('region-temps');
    var nt=document.getElementById('topn-temps');if(nt)parts.push('top'+nt.value);
    add('year-temps');
  }else if(tabId==='winners'){
    add('win-dist');add('region-winners');add('win-gender');
    var wn=document.getElementById('win-topn');if(wn&&wn.value)parts.push('top'+wn.value);
    add('win-year');
  }else if(tabId==='overview'){
    var ov=document.getElementById('ov-search');if(ov&&ov.value)parts.push(safeFn(ov.value));
  }else if(tabId==='compare'){
    var a=document.getElementById('cmp-input-a');var b=document.getElementById('cmp-input-b');
    if(a&&a.value)parts.push(safeFn(a.value));
    if(b&&b.value)parts.push('vs_'+safeFn(b.value));
  }
  return parts;
}
function buildExportFilename(ext){
  var info=getActiveTabInfo();
  var parts=['datapace',info.label].concat(getFilterParts(info.id));
  var d=new Date();var ts=d.getFullYear()+String(d.getMonth()+1).padStart(2,'0')+String(d.getDate()).padStart(2,'0');
  parts.push(ts);
  return parts.filter(Boolean).join('_')+'.'+ext;
}
function exportPanel(format){
  document.getElementById('export-menu').style.display='none';
  var panel=document.querySelector('.panel.active');
  if(!panel){alert('Aucun onglet actif.');return;}
  if(typeof html2canvas==='undefined'){alert('Librairie export non chargee (verifiez votre connexion).');return;}
  // Resolve background color from theme variables
  var rootStyle=getComputedStyle(document.documentElement);
  var bg=(rootStyle.getPropertyValue('--bg')||'').trim()||'#ffffff';
  var btn=document.getElementById('export-btn');
  var origHtml=btn.innerHTML;
  btn.innerHTML='Export en cours...';
  btn.style.pointerEvents='none';
  // Temporarily remove max-height constraints so full content is captured
  var restores=[];
  panel.querySelectorAll('*').forEach(function(el){
    var cs=getComputedStyle(el);
    if(cs.overflow==='auto'||cs.overflow==='scroll'||cs.overflowY==='auto'||cs.overflowY==='scroll'){
      restores.push({el:el,overflow:el.style.overflow,overflowY:el.style.overflowY,maxHeight:el.style.maxHeight,height:el.style.height});
      el.style.overflow='visible';el.style.overflowY='visible';el.style.maxHeight='none';
    }
  });
  setTimeout(function(){
    html2canvas(panel,{backgroundColor:bg,scale:2,logging:false,useCORS:true,windowWidth:panel.scrollWidth,windowHeight:panel.scrollHeight}).then(function(canvas){
      restores.forEach(function(r){r.el.style.overflow=r.overflow;r.el.style.overflowY=r.overflowY;r.el.style.maxHeight=r.maxHeight;r.el.style.height=r.height;});
      // Add padding around the captured content by drawing it into a larger canvas
      var padding=60*2; // 60px visual padding, scale=2
      var padded=document.createElement('canvas');
      padded.width=canvas.width+padding*2;
      padded.height=canvas.height+padding*2;
      var pctx=padded.getContext('2d');
      pctx.fillStyle=bg;
      pctx.fillRect(0,0,padded.width,padded.height);
      pctx.drawImage(canvas,padding,padding);
      var finalCanvas=padded;
      var filename=buildExportFilename(format);
      if(format==='png'){
        var link=document.createElement('a');
        link.download=filename;
        link.href=finalCanvas.toDataURL('image/png');
        document.body.appendChild(link);link.click();document.body.removeChild(link);
      }else if(format==='pdf'){
        if(typeof jspdf==='undefined'||!jspdf.jsPDF){alert('Librairie PDF non chargee.');}
        else{
          var imgData=finalCanvas.toDataURL('image/png');
          var orientation=finalCanvas.width>=finalCanvas.height?'landscape':'portrait';
          var pdf=new jspdf.jsPDF({orientation:orientation,unit:'px',format:[finalCanvas.width,finalCanvas.height],hotfixes:['px_scaling']});
          pdf.addImage(imgData,'PNG',0,0,finalCanvas.width,finalCanvas.height,undefined,'FAST');
          pdf.save(filename);
        }
      }
      btn.innerHTML=origHtml;btn.style.pointerEvents='';
    }).catch(function(err){
      restores.forEach(function(r){r.el.style.overflow=r.overflow;r.el.style.overflowY=r.overflowY;r.el.style.maxHeight=r.maxHeight;r.el.style.height=r.height;});
      console.error('Export error:',err);
      alert('Erreur export: '+(err&&err.message?err.message:'inconnue'));
      btn.innerHTML=origHtml;btn.style.pointerEvents='';
    });
  },50);
}

function switchTab(name){
  var names=['data','overview','compare','trends','biggest','temps','winners','sponsoring'];
  document.querySelectorAll('.tab').forEach(function(t,i){t.classList.toggle('active',names[i]===name);});
  document.querySelectorAll('.panel').forEach(function(p){p.classList.remove('active');});
  document.getElementById('panel-'+name).classList.add('active');
  if(name==='trends')updateTrends();
  if(name==='biggest')updateBiggest();
  if(name==='temps')updateTemps();
  if(name==='winners')updateWinners();
  if(name==='data')filterTable();
  if(name==='sponsoring'){
    if(!window._spInit){window._spInit=true;initSponsoring();}
    else{setTimeout(function(){spRenderTreemap();spHighlight(_spActiveBrand);},50);}
  }
}
// Insights functions removed (ASO version)

function ovSearch(){
  var q=document.getElementById('ov-search').value.toLowerCase().trim();
  var box=document.getElementById('ov-results');
  if(q.length<2){box.innerHTML='<div class="ov-placeholder">Tapez au moins 2 caracteres</div>';return;}
  var matches=RAW.filter(function(r){return r.r.toLowerCase().indexOf(q)>=0||r.c.toLowerCase().indexOf(q)>=0;});
  if(!matches.length){box.innerHTML='<div class="ov-placeholder">Aucun resultat</div>';return;}
  var dc={MARATHON:'#60A5FA18',SEMI:'#FF8A5018','10KM':'#5CDFA018'};
  var dt={MARATHON:'#60A5FA',SEMI:'#FF8A50','10KM':'#5CDFA0'};
  var html='';
  matches.forEach(function(r){
    var idx=RAW.indexOf(r);
    var dl=r.d==='10KM'?'10 km':r.d==='SEMI'?'Semi':r.d==='AUTRE'?'Autre':'Marathon';
    html+='<div class="ov-result-item" data-idx="'+idx+'" onclick="ovSelect('+idx+')">'
      +'<span class="ov-result-dist" style="background:'+dc[r.d]+';color:'+dt[r.d]+'">'+dl+'</span>'
      +'<span style="flex:1">'+r.r+'</span>'
      +'<span style="font-size:11px;color:var(--text3)">'+r.c+' - '+r.p+'</span>'
      +'</div>';
  });
  box.innerHTML=html;
}

function ovSelect(idx){
  document.querySelectorAll('.ov-result-item').forEach(function(el){el.classList.toggle('selected',parseInt(el.dataset.idx)===idx);});
  var ev=RAW[idx];
  var ac=colDist(ev);
  var acLight=lightenHex(ac,0.4);
  var dl=ev.d==='MARATHON'?'Marathon':ev.d==='SEMI'?'Semi-marathon':ev.d==='AUTRE'?'Autre':'10 km';
  // Gather data
  var histKeys=Object.keys(ev.hist||{}).map(Number).sort(function(a,b){return a-b;});
  var positiveHistory=histKeys.map(function(yr){return{yr:yr,v:(ev.hist||{})[yr]};}).filter(function(e){return e.v&&e.v>0;});
  var lastEd=positiveHistory.length?positiveHistory[positiveHistory.length-1]:null;
  var prevEd=positiveHistory.length>=2?positiveHistory[positiveHistory.length-2]:null;
  var td=getTimeData(ev.r);
  var wr=getWinnersRecords(ev.r);
  var wh=buildWinnerHistory(ev.r);
  var th=buildTimeHistory(ev.r);
  var nYears=positiveHistory.length;
  var firstYr=positiveHistory.length?positiveHistory[0].yr:null;

  // --- Metrics cards (only show if data exists) ---
  function ovMetric(label,value,borderColor,sub){return'<div class="ov-stat" style="border:none;border-left:3px solid '+borderColor+';border-radius:0 8px 8px 0;"><div class="ov-stat-label">'+label+'</div><div class="ov-stat-value" style="font-size:28px;font-weight:700">'+value+'</div>'+(sub||'')+'</div>';}
  var stats='<div class="ov-stats">';
  if(lastEd){
    var finSub='';
    if(prevEd&&prevEd.v>0){var d=((lastEd.v-prevEd.v)/prevEd.v*100);finSub='<div style="font-size:11px;margin-top:3px;color:'+(d>=0?'#22C55E':'#EF4444')+'">'+(d>=0?'+':'')+d.toFixed(1)+'% vs '+prevEd.yr+'</div>';}
    stats+=ovMetric('Finishers ('+lastEd.yr+')',fmtFull(lastEd.v),ac,finSub);
  }
  if(td&&td.avg){stats+=ovMetric('Temps moyen ('+td.yr+')',td.avg,'#888');}
  var menVal=wr&&wr.men?wr.men:(td&&td.men?td.men:null);
  var menYr=wr&&wr.menYr?wr.menYr:(td?td.yr:null);
  if(menVal){stats+=ovMetric('Record homme'+(menYr?' ('+menYr+')':''),menVal,ac);}
  var wmVal=wr&&wr.women?wr.women:(td&&td.women?td.women:null);
  var wmYr=wr&&wr.womenYr?wr.womenYr:(td?td.yr:null);
  if(wmVal){stats+=ovMetric('Record femme'+(wmYr?' ('+wmYr+')':''),wmVal,acLight);}
  stats+='</div>';

  // --- Build charts section adaptively ---
  var chartsHtml='';
  // Finishers chart/card
  if(nYears>=2){
    chartsHtml+='<div class="ov-chart-box"><div class="ov-chart-label">Finishers par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-fin"></canvas></div></div>';
  } else if(nYears===1){
    chartsHtml+='<div class="ov-chart-box"><div class="ov-chart-label">Finishers</div><div style="text-align:center;padding:2rem 0"><div style="font-size:28px;font-weight:700">'+fmtFull(lastEd.v)+'</div><div style="font-size:12px;color:var(--text3);margin-top:4px">en '+lastEd.yr+'</div></div></div>';
  }
  // Temps moyen chart/card
  if(th.length>=2){
    chartsHtml+='<div class="ov-chart-box"><div class="ov-chart-label">Temps moyen par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-time"></canvas></div></div>';
  } else if(th.length===1){
    chartsHtml+='<div class="ov-chart-box"><div class="ov-chart-label">Temps moyen</div><div style="text-align:center;padding:2rem 0"><div style="font-size:22px;font-weight:700">'+fmtHM(th[0].min)+'</div><div style="font-size:12px;color:var(--text3);margin-top:4px">en '+th[0].yr+'</div></div></div>';
  }

  var charts2Html='';
  // Record homme chart/card
  if(wh.men.length>=2){
    charts2Html+='<div class="ov-chart-box"><div class="ov-chart-label">Record Homme par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-men"></canvas></div></div>';
  } else if(wh.men.length===1){
    charts2Html+='<div class="ov-chart-box"><div class="ov-chart-label">Record Homme</div><div style="text-align:center;padding:2rem 0"><div style="font-size:22px;font-weight:700;color:'+ac+'">'+wh.men[0].time+'</div><div style="font-size:12px;color:var(--text3);margin-top:4px">en '+wh.men[0].yr+'</div></div></div>';
  }
  // Record femme chart/card
  if(wh.women.length>=2){
    charts2Html+='<div class="ov-chart-box"><div class="ov-chart-label">Record Femme par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-women"></canvas></div></div>';
  } else if(wh.women.length===1){
    charts2Html+='<div class="ov-chart-box"><div class="ov-chart-label">Record Femme</div><div style="text-align:center;padding:2rem 0"><div style="font-size:22px;font-weight:700;color:'+acLight+'">'+wh.women[0].time+'</div><div style="font-size:12px;color:var(--text3);margin-top:4px">en '+wh.women[0].yr+'</div></div></div>';
  }

  // --- Context banner ---
  var banner='';
  if(nYears>0&&nYears<3){banner='<div style="font-size:12px;color:var(--text3);padding:8px 12px;background:var(--bg3);border-radius:6px;margin-bottom:1rem">Donnees disponibles depuis '+firstYr+' ('+nYears+' edition'+(nYears>1?'s':'')+')</div>';}

  var badgeCol=ac;
  var circHtml=circBadges(ev);
  var html='<div class="ov-card">'
    +'<div class="ov-card-header"><div>'
    +'<div class="ov-card-title">'+ev.r+'</div>'
    +'<div class="ov-card-meta"><span>'+ev.c+' &middot; '+ev.p+'</span></div>'
    +'</div>'
    +'<div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap"><span class="ov-badge" style="border:1px solid '+badgeCol+'40;color:'+badgeCol+';background:transparent;font-size:10px;padding:3px 10px;border-radius:100px;">'+dl+'</span>'+circHtml+'</div>'
    +'</div>'
    +banner
    +stats
    +(chartsHtml?'<div class="ov-charts">'+chartsHtml+'</div>':'')
    +(charts2Html?'<div class="ov-charts">'+charts2Html+'</div>':'')
    +buildOvSponsoring(ev.r,ac)
    +'</div>';
  document.getElementById('ov-card-wrap').innerHTML=html;

  // --- Render charts ---
  if(ovChartF)ovChartF.destroy();ovChartF=null;
  if(ovChartT)ovChartT.destroy();ovChartT=null;
  if(ovChartM)ovChartM.destroy();ovChartM=null;
  if(ovChartW)ovChartW.destroy();ovChartW=null;

  // Finishers chart (2+ data points)
  var fc=document.getElementById('ov-chart-fin');
  if(fc&&nYears>=2){
    ovChartF=new Chart(fc,{type:'bar',
      data:{labels:positiveHistory.map(function(e){return e.yr;}),datasets:[{data:positiveHistory.map(function(e){return e.v;}),backgroundColor:ac,hoverBackgroundColor:ac+'CC',borderRadius:3,borderSkipped:false}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:mkTT({label:function(ctx){return' '+fmtFull(ctx.parsed.y)+' finishers';}})},
        scales:{x:{grid:{display:false},ticks:{color:'#555',font:{size:10},maxRotation:0,minRotation:0,autoSkip:true,maxTicksLimit:12},border:{display:false}},y:{beginAtZero:true,grid:{color:'rgba(255,255,255,0.03)'},ticks:{color:'#555',font:{size:10},callback:function(v){return fmt(v);}},border:{display:false}}}
      }
    });
  }
  // Temps moyen chart (2+ data points)
  var tc=document.getElementById('ov-chart-time');
  if(tc&&th.length>=2){
    ovChartT=new Chart(tc,{type:'line',
      data:{labels:th.map(function(e){return e.yr;}),datasets:[{data:th.map(function(e){return e.min;}),borderColor:'#888',backgroundColor:'rgba(136,136,136,0.06)',tension:0.3,pointRadius:4,pointBackgroundColor:'#888',borderWidth:2,fill:true}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:mkTT({label:function(ctx){return' '+fmtHMMin(ctx.parsed.y);}})},
        scales:{x:{grid:{display:false},ticks:{color:'#555',font:{size:10},maxRotation:0,minRotation:0,autoSkip:true,maxTicksLimit:12},border:{display:false}},y:{grid:{color:'rgba(255,255,255,0.03)'},ticks:{color:'#555',font:{size:10},callback:function(v){return fmtHM(v);}},border:{display:false}}}
      }
    });
  }
  // Record homme chart (2+ data points)
  var mcv=document.getElementById('ov-chart-men');
  if(mcv&&wh.men.length>=2){
    ovChartM=new Chart(mcv,{type:'line',
      data:{labels:wh.men.map(function(e){return e.yr;}),datasets:[{data:wh.men.map(function(e){return e.sec/60;}),borderColor:ac,backgroundColor:ac+'14',tension:0.3,pointRadius:4,pointBackgroundColor:ac,borderWidth:2,fill:true}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:mkTT({label:function(ctx){var i=ctx.dataIndex;return' '+wh.men[i].time;}})},
        scales:{x:{grid:{display:false},ticks:{color:'#555',font:{size:10},maxRotation:0,minRotation:0,autoSkip:true,maxTicksLimit:12},border:{display:false}},y:{grid:{color:'rgba(255,255,255,0.03)'},ticks:{color:'#555',font:{size:10},callback:function(v){return fmtHM(v);}},border:{display:false}}}
      }
    });
  }
  // Record femme chart (2+ data points)
  var wcv=document.getElementById('ov-chart-women');
  if(wcv&&wh.women.length>=2){
    ovChartW=new Chart(wcv,{type:'line',
      data:{labels:wh.women.map(function(e){return e.yr;}),datasets:[{data:wh.women.map(function(e){return e.sec/60;}),borderColor:acLight,backgroundColor:acLight+'14',tension:0.3,pointRadius:4,pointBackgroundColor:acLight,borderWidth:2,fill:true}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:mkTT({label:function(ctx){var i=ctx.dataIndex;return' '+wh.women[i].time;}})},
        scales:{x:{grid:{display:false},ticks:{color:'#555',font:{size:10},maxRotation:0,minRotation:0,autoSkip:true,maxTicksLimit:12},border:{display:false}},y:{grid:{color:'rgba(255,255,255,0.03)'},ticks:{color:'#555',font:{size:10},callback:function(v){return fmtHM(v);}},border:{display:false}}}
      }
    });
  }
}

function trendShades(base,n){
  var r=parseInt(base.slice(1,3),16),g=parseInt(base.slice(3,5),16),b=parseInt(base.slice(5,7),16);
  var out=[];
  for(var i=0;i<n;i++){
    var t=n<=1?0.5:(i/(n-1));
    var f=0.35+t*0.65;
    out.push('rgb('+Math.round(r*f+255*(1-f))+','+Math.round(g*f+255*(1-f))+','+Math.round(b*f+255*(1-f))+')');
  }
  return out;
}
var TREND_PALETTES={MARATHON:['#2563EB','#60A5FA','#3B82F6','#BFDBFE','#1E3A8A','#172554','#DBEAFE','#1D4ED8','#2563EB','#60A5FA','#1E40AF','#BFDBFE','#1D4ED8','#1E40AF','#3B82F6','#93C5FD','#1E3A8A','#DBEAFE','#1E40AF','#1D4ED8'],SEMI:['#FF8A50','#FFB088','#E06020','#CC4400','#FFCC99','#FF6B2B','#D45500','#FFA070','#B84000','#FFD4B0','#FF9060','#E87040','#C05020','#FFBB90','#FF7744','#D46030','#AA3500','#FFDDBB','#FF8040','#EE6622'],'10KM':['#5CDFA0','#88EEBB','#2BA368','#1A8050','#AAFFDD','#44CC88','#339966','#77DDAA','#228855','#BBFFCC','#66DDAA','#55CC99','#44BB88','#99EEBB','#33AA77','#22BB88','#11AA66','#CCFFDD','#55BB99','#44AA88'],AUTRE:['#F472B6','#FF99CC','#D44D90','#BB3377','#FFBBDD','#E85DA3','#CC4488','#FF88BB','#AA2266','#FFCCDD','#F08AC0','#DD66AA','#CC5599','#FFAACC','#E070B0','#BB4488','#FF77BB','#D05595','#AA3377','#FFDDEE']};
function trendColor(r,i,dist,total){
  if(dist==='ALL'){return lc(r.d==='10KM'?'#5CDFA0':r.d==='SEMI'?'#FF8A50':r.d==='AUTRE'?'#F472B6':'#60A5FA');}
  var pal=TREND_PALETTES[dist];
  if(pal)return lc(pal[i%pal.length]);
  return lc('#60A5FA');
}
function trendShortName(r){
  var c=r.c||'';
  if(c.length<=12)return c;
  var words=c.split(/[\s-]+/);
  return words[0];
}
var _trendSorted=[];
function updateTrends(){
  var dist=document.getElementById('dist-trends').value;
  var topn=parseInt(document.getElementById('topn-trends').value);
  var region=document.getElementById('region-trends').value;
  var src=RAW.filter(function(r){if(dist!=='ALL'&&r.d!==dist)return false;if(region!=='ALL'&&r.rg!==region)return false;return true;});
  if(cT)cT.destroy();
  var sorted=src.slice().sort(function(a,b){
    var ka=Object.keys(a.hist||{}).map(Number).sort(function(x,y){return y-x;});
    var kb=Object.keys(b.hist||{}).map(Number).sort(function(x,y){return y-x;});
    return((a.hist||{})[ka[0]]||0)<((b.hist||{})[kb[0]]||0)?1:-1;
  }).slice(0,topn);
  _trendSorted=sorted;
  var allYears=[];
  sorted.forEach(function(r){Object.keys(r.hist||{}).map(Number).forEach(function(y){if(allYears.indexOf(y)<0)allYears.push(y);});});
  allYears.sort(function(a,b){return a-b;});
  var datasets=sorted.map(function(r,i){
    var c=trendColor(r,i,dist,sorted.length);
    return{label:r.r,data:allYears.map(function(yr){var v=(r.hist||{})[yr];return v&&v>0?v:null;}),borderColor:c,backgroundColor:'transparent',tension:0.35,fill:false,pointRadius:3,pointHoverRadius:7,spanGaps:true,borderWidth:2,pointBackgroundColor:c,_rawIdx:RAW.indexOf(r),_dist:r.d};
  });
  var minYr=allYears.length?allYears[0]:'';var maxYr=allYears.length?allYears[allYears.length-1]:'';
  var distNames={MARATHON:'MARATHON',SEMI:'SEMI-MARATHON','10KM':'10 KM',AUTRE:'AUTRE'};
  var titleParts=['EVOLUTION'];
  if(dist!=='ALL')titleParts.push(distNames[dist]||dist);
  if(region!=='ALL')titleParts.push(region.toUpperCase());
  if(minYr&&maxYr)titleParts.push(minYr+'-'+maxYr);
  var lbl=document.getElementById('trends-section-lbl');
  if(lbl)lbl.textContent=titleParts.join(' \u00b7 ');
  var legEl=document.getElementById('trends-legend');
  if(legEl){
    var legHtml='';
    if(dist==='ALL'){
      legHtml+='<span class="leg-item"><span class="leg-dot" style="background:#60A5FA"></span>Marathon</span>';
      legHtml+='<span class="leg-item"><span class="leg-dot" style="background:#FF8A50"></span>Semi-marathon</span>';
      legHtml+='<span class="leg-item"><span class="leg-dot" style="background:#5CDFA0"></span>10 km</span>';
      legHtml+='<span class="leg-item"><span class="leg-dot" style="background:#F472B6"></span>Autre</span>';
    }else{
      sorted.forEach(function(r,i){
        var c=trendColor(r,i,dist,sorted.length);
        var idx=RAW.indexOf(r);
        legHtml+='<span class="leg-item leg-clickable" data-tidx="'+idx+'" onclick="trendLegClick('+idx+')" style="cursor:pointer"><span class="leg-dot" style="background:'+c+'"></span>'+r.r+'</span>';
      });
    }
    legEl.innerHTML=legHtml;
  }
  var endLabelPlugin={id:'trendEndLabels',afterDatasetsDraw:function(chart){
    var ctx=chart.ctx;
    chart.data.datasets.forEach(function(ds,di){
      var meta=chart.getDatasetMeta(di);
      if(!meta.visible)return;
      var last=null;
      for(var k=meta.data.length-1;k>=0;k--){
        if(ds.data[k]!==null&&ds.data[k]!==undefined){last=meta.data[k];break;}
      }
      if(!last)return;
      var sr=_trendSorted[di];
      if(!sr)return;
      ctx.save();
      ctx.font='10px Inter,sans-serif';
      ctx.fillStyle=ds.borderColor;
      ctx.textAlign='left';
      ctx.textBaseline='middle';
      ctx.fillText(trendShortName(sr),last.x+6,last.y);
      ctx.restore();
    });
  }};
  var trendCfg={type:'line',data:{labels:allYears.map(String),datasets:datasets},plugins:[endLabelPlugin],options:{responsive:true,maintainAspectRatio:false,layout:{padding:{right:70}},interaction:{mode:'nearest',intersect:false},onClick:function(evt,items){
    if(items.length){var di=items[0].datasetIndex;var idx=datasets[di]._rawIdx;if(idx>=0)biggestClick(idx);}
  },plugins:{legend:{display:false},tooltip:mkTT({title:function(items){return items.length?items[0].dataset.label:'';},label:function(ctx){
    var v=ctx.parsed.y;var yr=parseInt(ctx.label);
    var line=' '+fmtFull(v)+' finishers';
    var di=ctx.datasetIndex;var ds=ctx.chart.data.datasets[di];
    var prevIdx=ctx.dataIndex-1;
    while(prevIdx>=0&&(ds.data[prevIdx]===null||ds.data[prevIdx]===undefined))prevIdx--;
    if(prevIdx>=0&&ds.data[prevIdx]){
      var prev=ds.data[prevIdx];var prevYr=parseInt(ctx.chart.data.labels[prevIdx]);
      var delta=((v-prev)/prev*100).toFixed(1);
      line+='  ('+(delta>=0?'+':'')+delta+'% vs '+prevYr+')';
    }
    return line;
  }})},scales:{x:{grid:{color:mkGRID()},ticks:TICK,border:{color:mkBorder()}},y:{beginAtZero:true,grid:{color:mkGRID()},ticks:{color:mkTICK().color,font:{size:11},callback:function(v){return fmt(v);}},border:{color:mkBorder()}}}}};
  cT=new Chart(document.getElementById('chart-trends'),trendCfg);
}
function trendLegClick(idx){biggestClick(idx);}

function getBiggestSrc(){
  var dist=document.getElementById('dist-biggest').value;
  var region=document.getElementById('region-biggest').value;
  return RAW.filter(function(r){if(dist!=='ALL'&&r.d!==dist)return false;if(region!=='ALL'&&r.rg!==region)return false;return true;});
}

function initBiggestYears(){
  var src=getBiggestSrc();
  var allYears=[];
  src.forEach(function(r){Object.keys(r.hist||{}).forEach(function(y){var yi=parseInt(y);if(allYears.indexOf(yi)<0)allYears.push(yi);});});
  allYears.sort(function(a,b){return b-a;});
  var sel=document.getElementById('year-biggest');
  var prev=sel.value;
  sel.innerHTML='';
  allYears.forEach(function(y){var o=document.createElement('option');o.value=y;o.textContent=y;sel.appendChild(o);});
  if(prev&&allYears.indexOf(+prev)>=0)sel.value=prev;
}

function colDistOnly(r){return lc(r.d==='10KM'?'#5CDFA0':r.d==='SEMI'?'#FF8A50':r.d==='AUTRE'?'#F472B6':'#2563EB');}
function updateBiggest(){
  var n=parseInt(document.getElementById('topn-biggest').value);
  var yr=parseInt(document.getElementById('year-biggest').value);
  var src=getBiggestSrc();
  var sorted=src.filter(function(r){var v=(r.hist||{})[yr];return v&&!isNaN(v)&&v>0;}).sort(function(a,b){return((b.hist||{})[yr]||0)-((a.hist||{})[yr]||0);}).slice(0,n);
  var maxVal=sorted.length?((sorted[0].hist||{})[yr]||1):1;
  var html='';
  sorted.forEach(function(r,i){
    var v=(r.hist||{})[yr];
    var pct=(v/maxVal*80+5).toFixed(1);
    var barCol=colDistOnly(r);
    var rank=String(i+1).padStart(2,'0');
    var valInside=pct>25;
    var valLabel=fmtFull(v);
    var idx=RAW.indexOf(r);
    var cBdg=circBadges(r);
    html+='<div class="time-bar-row bt-row" data-name="'+r.r.replace(/"/g,'&quot;')+'" data-city="'+(r.c||'').replace(/"/g,'&quot;')+'" data-val="'+valLabel+' finishers" data-idx="'+idx+'" onclick="biggestClick('+idx+')">'
      +'<div class="time-bar-label" title="'+r.r+'"><span class="time-bar-rank">'+rank+'</span> \u00b7 '+r.r+cBdg+'</div>'
      +'<div class="time-bar-track"><div class="time-bar-fill" style="width:'+pct+'%;background:'+barCol+'cc">'+(valInside?valLabel:'')+'</div></div>'
      +'<div class="time-bar-val">'+(valInside?'':valLabel)+'</div></div>';
  });
  var wrap=document.getElementById('biggest-bars');
  wrap.style.maxHeight='none';
  wrap.style.height=Math.max(sorted.length*36,100)+'px';
  wrap.innerHTML=html;
  initBarTips();
}
function biggestClick(idx){
  if(idx<0)return;
  switchTab('overview');
  var ev=RAW[idx];
  if(!ev)return;
  document.getElementById('ov-search').value=ev.r;
  ovSearch();
  setTimeout(function(){ovSelect(idx);},100);
}

function updateTempsYears(){
  var dist=document.getElementById('dist-temps').value;
  var sel=document.getElementById('year-temps');
  var prev=sel.value;
  var srcObj=dist==='SEMI'?TEMPS_SEMI:TEMPS_MARATHON;
  var yrs=Object.keys(srcObj).sort(function(a,b){return parseInt(b)-parseInt(a);});
  sel.innerHTML=yrs.map(function(y){return'<option value="'+y+'">'+y+'</option>';}).join('');
  if(yrs.indexOf(prev)>=0)sel.value=prev;
}

function raceRegion(name){var m=RAW.find(function(r){return r.r===name;});return m?m.rg:'Autre';}
function tempsFindRaw(name){return RAW.find(function(r){return r.r===name||r.r.toLowerCase()===name.toLowerCase();});}
function tempsNav(name){var r=tempsFindRaw(name);if(!r)return;var idx=RAW.indexOf(r);if(idx>=0)biggestClick(idx);}
function tempsPrevAvg(race,dist,yr){
  var prevYr=yr-1;
  var srcObj=dist==='SEMI'?TEMPS_SEMI:TEMPS_MARATHON;
  var prev=srcObj[String(prevYr)];
  if(!prev)return null;
  var m=prev.find(function(d){return d.race===race;});
  return m?m.avg:null;
}
function minToTime(m){var h=Math.floor(m/60);var mn=Math.floor(m%60);var s=Math.round((m-Math.floor(m))*60);return h+'h'+String(mn).padStart(2,'0')+'m'+String(s).padStart(2,'0');}
function updateTemps(){
  var dist=document.getElementById('dist-temps').value;
  var yr=parseInt(document.getElementById('year-temps').value);
  var sortMode=document.getElementById('sort-temps').value;
  var topn=parseInt(document.getElementById('topn-temps').value);
  var region=document.getElementById('region-temps').value;
  var src=dist==='SEMI'?(TEMPS_SEMI[String(yr)]||[]):(TEMPS_MARATHON[String(yr)]||[]);
  var data=region==='ALL'?src.slice():src.filter(function(d){return raceRegion(d.race||d.r||'')===region;});
  if(sortMode==='avg'){data.sort(function(a,b){var ma=toMin(a.avg),mb=toMin(b.avg);if(!ma)return 1;if(!mb)return -1;return ma-mb;});}
  else{data.sort(function(a,b){return b.finishers-a.finishers;});}
  var withAvg=data.filter(function(d){return toMin(d.avg);});
  var displayed=data.slice(0,topn);
  var fastest=withAvg.length?withAvg.reduce(function(a,b){return toMin(a.avg)<toMin(b.avg)?a:b;}):null;
  var slowest=withAvg.length?withAvg.reduce(function(a,b){return toMin(a.avg)>toMin(b.avg)?a:b;}):null;
  var avgAll=withAvg.length?withAvg.reduce(function(s,d){return s+toMin(d.avg);},0)/withAvg.length:0;
  var distLabel=dist==='SEMI'?'Semi-marathon':'Marathon';
  var barCol=dist==='SEMI'?lc('#FF8A50'):lc('#2563EB');
  document.getElementById('metrics-temps').innerHTML=
    '<div class="metric" style="grid-column:span 2"><div class="metric-label">Temps moyen global</div><div class="metric-value" style="font-size:28px;color:'+barCol+'">'+minToTime(avgAll)+'</div><div class="metric-sub">'+distLabel+' '+yr+' \u00b7 '+src.length+' courses</div></div>'
    +'<div class="metric"><div class="metric-label" style="color:'+barCol+'">Plus rapide</div><div class="metric-value" style="font-size:18px;color:'+barCol+'">'+(fastest?fastest.avg:'-')+'</div><div class="metric-sub" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+(fastest?fastest.race:'')+'</div></div>'
    +'<div class="metric"><div class="metric-label">Plus lent</div><div class="metric-value" style="font-size:16px;color:var(--text3)">'+(slowest?slowest.avg:'-')+'</div><div class="metric-sub" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text3)">'+(slowest?slowest.race:'')+'</div></div>';
  // Inverted bar logic: longest bar = fastest time
  var minM=withAvg.length?Math.min.apply(null,withAvg.map(function(d){return toMin(d.avg);})):0;
  var maxM=withAvg.length?Math.max.apply(null,withAvg.map(function(d){return toMin(d.avg);})):1;
  var barsHtml='';
  displayed.forEach(function(d){
    var m=toMin(d.avg);
    // Invert: fastest gets longest bar
    var pct=m?((maxM-m)/(maxM-minM+0.001)*75+10).toFixed(1):'0';
    // Delta vs previous year
    var prevAvg=tempsPrevAvg(d.race,dist,yr);
    var deltaHtml='';
    if(prevAvg){
      var pm=toMin(prevAvg);
      if(pm){
        var diffMin=m-pm;
        var absDiff=Math.abs(diffMin);
        var diffH=Math.floor(absDiff/60);var diffMn=Math.floor(absDiff%60);var diffS=Math.round((absDiff-Math.floor(absDiff))*60);
        var diffStr=diffH>0?diffH+'h'+String(diffMn).padStart(2,'0')+'m':(diffMn>0?diffMn+'m'+String(diffS).padStart(2,'0')+'s':diffS+'s');
        if(diffMin>0.08){deltaHtml='<span style="color:'+lc('#FF4A6B')+';font-size:9px;margin-left:6px">\u25b2 +'+diffStr+'</span>';}
        else if(diffMin<-0.08){deltaHtml='<span style="color:'+lc('#22C55E')+';font-size:9px;margin-left:6px">\u25bc -'+diffStr+'</span>';}
      }
    }
    // Tooltip data
    var tipParts=d.race+'\\n'+d.avg+' (temps moyen)\\n'+fmtFull(d.finishers)+' finishers';
    if(prevAvg)tipParts+='\\nvs '+(yr-1)+' : '+prevAvg;
    var safeRace=d.race.replace(/&/g,'&amp;').replace(/"/g,'&quot;');
    barsHtml+='<div class="time-bar-row" title="'+tipParts.replace(/"/g,'&quot;')+'" data-race="'+safeRace+'" onclick="tempsNav(this.dataset.race)" style="cursor:pointer"><div class="time-bar-label">'+d.race+'</div><div class="time-bar-track"><div class="time-bar-fill" style="width:'+(m?pct:0)+'%;background:'+barCol+'cc"></div></div><div class="time-bar-val">'+(d.avg||'-')+deltaHtml+'</div></div>';
  });
  document.getElementById('time-bars').innerHTML=barsHtml;
}

function applyFrozen(tbl){
  if(!tbl)return;
  var ths=tbl.querySelectorAll('thead tr th');
  if(ths.length<4)return;
  var widths=[62,70,110,180];
  var left=0;
  for(var i=0;i<4;i++){
    var w=widths[i];
    tbl.querySelectorAll('tr th:nth-child('+(i+1)+'),tr td:nth-child('+(i+1)+')').forEach(function(c){
      c.classList.add('frozen-cell');
      c.style.position='sticky';
      c.style.left=left+'px';
      c.style.zIndex=c.tagName==='TH'?'3':'2';
      c.style.minWidth=w+'px';
      c.style.width=w+'px';
      if(i===3){c.style.boxShadow='2px 0 6px rgba(0,0,0,0.45)';c.style.overflow='hidden';c.style.textOverflow='ellipsis';c.style.whiteSpace='nowrap';}
    });
    left+=w;
  }
}

function filterTable(){
  var q=(document.getElementById('search-data').value||'').toLowerCase();
  var dist=document.getElementById('dist-data').value;
  var month=document.getElementById('month-data').value;
  var badge=document.getElementById('badge-data').value;
  var sizeFilter=document.getElementById('size-data').value;
  var periode=document.getElementById('afficher-data').value;
  var region=document.getElementById('region-data').value;
  var thead=document.getElementById('table-head-row');
  var tbl=document.getElementById('data-table');
  // Determine year range
  var now=new Date().getFullYear();
  var minYr=periode==='all'?0:now-parseInt(periode)+1;
  // Collect all years across all data
  var globalYears=[];
  RAW.forEach(function(r){Object.keys(r.hist||{}).map(Number).forEach(function(y){if(y>=minYr&&globalYears.indexOf(y)<0)globalYears.push(y);});});
  globalYears.sort(function(a,b){return a-b;});
  // Filter races
  var f=RAW.filter(function(r){
    if(dist!=='ALL'&&r.d!==dist)return false;
    if(month!=='ALL'&&r.p!==month)return false;
    if(region!=='ALL'&&r.rg!==region)return false;
    if(q&&r.r.toLowerCase().indexOf(q)<0&&r.c.toLowerCase().indexOf(q)<0)return false;
    // Circuit filter
    if(badge!=='ALL'){
      var ci=r.ci||[];
      if(badge==='NONE'){if(ci.length>0)return false;}
      else{if(ci.indexOf(badge)<0)return false;}
    }
    // Size filter (based on peak finishers across visible years)
    if(sizeFilter!=='ALL'){
      var peak=0;
      globalYears.forEach(function(y){var v=(r.hist||{})[y];if(v&&v>0&&v>peak)peak=v;});
      var sz=parseInt(sizeFilter);
      if(sz===20000&&peak<20000)return false;
      if(sz===10000&&(peak<10000||peak>=20000))return false;
      if(sz===5000&&(peak<5000||peak>=10000))return false;
      if(sz===0&&peak>=5000)return false;
    }
    return globalYears.some(function(y){return(r.hist||{})[y];});
  });
  // Sort
  var sortMode=document.getElementById('sort-data').value;
  var monthOrder={Janvier:1,Fevrier:2,Février:2,Mars:3,Avril:4,Mai:5,Juin:6,Juillet:7,Aout:8,Août:8,Septembre:9,Octobre:10,Novembre:11,Decembre:12,Décembre:12};
  var distOrder={MARATHON:1,SEMI:2,'10KM':3,AUTRE:4};
  var lastYr=globalYears.length?globalYears[globalYears.length-1]:0;
  if(sortMode==='month'){f.sort(function(a,b){return(monthOrder[a.p]||99)-(monthOrder[b.p]||99);});}
  else if(sortMode==='distance'){f.sort(function(a,b){return(distOrder[a.d]||9)-(distOrder[b.d]||9);});}
  else if(sortMode==='finishers'){f.sort(function(a,b){var va=(a.hist||{})[2025]||0,vb=(b.hist||{})[2025]||0;if(va===0&&vb===0)return 0;if(va===0)return 1;if(vb===0)return-1;return vb-va;});}
  else if(sortMode==='trend'){f.sort(function(a,b){function getTrend(r){var vals=globalYears.map(function(y){return(r.hist||{})[y]||null;}).filter(function(v){return v&&!isNaN(v);});return vals.length>=2?delta(vals[0],vals[vals.length-1]):null;}var ta=getTrend(a),tb=getTrend(b);if(ta===null&&tb===null)return 0;if(ta===null)return 1;if(tb===null)return-1;return tb-ta;});}
  var frozen=globalYears.length>4;
  if(tbl){tbl.classList.toggle('tbl-frozen',frozen);if(!frozen)tbl.style.tableLayout='';tbl.querySelectorAll('.frozen-cell').forEach(function(c){c.classList.remove('frozen-cell');c.style.position='';c.style.left='';c.style.zIndex='';c.style.minWidth='';c.style.width='';c.style.boxShadow='';});}
  var yrTh=globalYears.map(function(y){return frozen?'<th style="min-width:58px;width:58px;text-align:center;padding:7px 6px">'+y+'</th>':'<th>'+y+'</th>';}).join('');
  if(thead)thead.innerHTML='<th>Mois</th><th>Ville</th><th>Distance</th><th>Epreuve</th>'+yrTh+'<th>Tendance</th>';
  var html='';
  f.forEach(function(r){
    var vals=globalYears.map(function(y){return(r.hist||{})[y]||null;}).filter(function(v){return v&&v>0&&!isNaN(v);});
    var t=vals.length>=2?delta(vals[0],vals[vals.length-1]):null;
    var tc=t===null?csVar('--text3'):t>=0?lc('#22C55E'):lc('#FF4A6B');
    var tStr=t===null?'-':(t>=0?'+':'')+t.toFixed(1)+'%';
    var yrKeys=globalYears.filter(function(y){var v=(r.hist||{})[y];return v&&v>0;});
    var firstYr=yrKeys[0],lastYr=yrKeys[yrKeys.length-1];
    var tSub=firstYr&&lastYr&&firstYr!==lastYr?'<div style="font-size:9px;color:var(--text3);margin-top:1px">'+firstYr+'\u2192'+lastYr+'</div>':'';
    var bl=r.d==='MARATHON'?'Marathon':r.d==='SEMI'?'Semi':r.d==='AUTRE'?'Autre':'10 km';
    var raceColor=colDist(r);
    var cBadges=circBadges(r);
    html+='<tr><td>'+r.p+'</td><td>'+r.c+'</td>'
      +'<td><span class="badge" style="background:'+raceColor+'18;color:'+raceColor+'">'+bl+'</span>'+cBadges+'</td>'
      +'<td style="color:'+raceColor+'" title="'+r.r+'">'+r.r+'</td>'
      +globalYears.map(function(y){var v=(r.hist||{})[y];var isFirst=r.fy&&y===r.fy;var starHtml=isFirst?'<span style="position:absolute;top:1px;left:2px;font-size:7px;color:'+raceColor+';opacity:0.7">\u2605</span>':'';if(v===-3)return'<td style="color:var(--text3);opacity:0.2">\u00b7</td>';if(v===-1)return'<td style="color:#FF4A6B;font-size:10px;font-style:italic;position:relative">'+starHtml+'Annul\u00e9</td>';if(v===-2)return'<td style="color:'+raceColor+';font-size:10px;font-style:italic;position:relative">'+starHtml+'Elite Only</td>';return'<td style="'+(v?'color:var(--text)':'')+';position:relative">'+starHtml+(v?fmtFull(v):'\u2014')+'</td>';}).join('')
      +'<td style="color:'+tc+'">'+tStr+tSub+'</td></tr>';
  });
  document.getElementById('table-body').innerHTML=html;
  if(frozen)applyFrozen(tbl);
  var cnt=f.length;
  // Count active filters
  var activeFilters=0;
  if(q)activeFilters++;
  if(dist!=='ALL')activeFilters++;
  if(month!=='ALL')activeFilters++;
  if(badge!=='ALL')activeFilters++;
  if(sizeFilter!=='ALL')activeFilters++;
  if(periode!=='all'&&periode!=='3')activeFilters++;
  var resetBtn=document.getElementById('reset-filters');
  if(resetBtn)resetBtn.style.display=activeFilters>0?'inline-flex':'none';
  var dataCount=0,totalCells=0;
  f.forEach(function(r){globalYears.forEach(function(y){totalCells++;var v=(r.hist||{})[y];if(v&&v>0&&!isNaN(v))dataCount++;});});
  var pct=totalCells>0?Math.round(100*dataCount/totalCells):0;
  document.getElementById('table-count').textContent=cnt+' epreuve'+(cnt>1?'s':'')+' affichee'+(cnt>1?'s':'')+' \u2022 '+dataCount.toLocaleString('fr-FR')+' donnees'+(activeFilters>0?' \u2022 '+activeFilters+' filtre'+(activeFilters>1?'s':'')+' actif'+(activeFilters>1?'s':''):'');
}
function resetFilters(){
  document.getElementById('search-data').value='';
  document.getElementById('dist-data').value='ALL';
  document.getElementById('month-data').value='ALL';
  document.getElementById('badge-data').value='ALL';
  document.getElementById('size-data').value='ALL';
  document.getElementById('sort-data').value='finishers';
  document.getElementById('afficher-data').value='3';
  filterTable();
}
// Keyboard shortcut Ctrl+K / Cmd+K to focus search
document.addEventListener('keydown',function(e){
  if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();var s=document.getElementById('search-data');if(s){s.focus();s.select();var dataTab=document.getElementById('panel-data');if(dataTab&&!dataTab.classList.contains('active'))switchTab('data');}}
  if(e.key==='Escape'){var s=document.getElementById('search-data');if(s&&document.activeElement===s){s.value='';s.blur();filterTable();}}
});

// ── SPONSORING ──────────────────────────────────────────────────────────────
var spChartBrands=null,spChartSectors=null,spChartEquip=null,spChartTypes=null;
var _spPeriod='2026';
function getExposure(eventName,years){
  // Find ALL distances for this event (same name, different dist)
  var evs=RAW.filter(function(r){return r.r===eventName;});
  if(!evs.length)return 0;
  var now=new Date().getFullYear();
  var minYr=_spPeriod==='5'?now-4:_spPeriod==='3'?now-2:parseInt(_spPeriod)||now;
  var maxYr=_spPeriod==='5'||_spPeriod==='3'?now:minYr;
  var total=0;
  (years||[]).forEach(function(y){
    if(y>=minYr&&y<=maxYr){
      var yearTotal=0,hasFallback=false;
      evs.forEach(function(ev){
        if(!ev.hist)return;
        var v=ev.hist[y];
        if(v&&v>0){yearTotal+=v;}
        else{
          var fallback=0;
          for(var fy=y-1;fy>=y-5;fy--){
            var fv=ev.hist[fy];
            if(fv&&fv>0){fallback=fv;break;}
          }
          if(fallback>0){yearTotal+=fallback;hasFallback=true;}
        }
      });
      total+=yearTotal;
    }
  });
  return total;
}
var _spBS={},_spActiveSector='ALL',_spActiveBrand=null,_spPillSectors=[],_spRegion='ALL',_spListMode='brands';
function spBuildData(){
  _spBS={};
  var now=new Date().getFullYear();
  var pMinYr=_spPeriod==='5'?now-4:_spPeriod==='3'?now-2:parseInt(_spPeriod)||now;
  var pMaxYr=_spPeriod==='5'||_spPeriod==='3'?now:pMinYr;
  _spRegion=document.getElementById('sp-region')?document.getElementById('sp-region').value:'ALL';
  SP_PARTNERSHIPS.forEach(function(p){
    // Region filter on event
    if(_spRegion!=='ALL'&&raceRegion(p.event)!==_spRegion)return;
    // Only include partnerships active in the selected period
    var active=(p.years||[]).some(function(y){return y>=pMinYr&&y<=pMaxYr;});
    if(!active)return;
    if(!_spBS[p.brand])_spBS[p.brand]={events:[],exposure:0,types:[],sector:(SP_BRANDS[p.brand]||{}).sector||'Autre',partnerships:[]};
    var exp=getExposure(p.event,p.years||[]);
    var evKey=p.event;
    if(_spBS[p.brand].events.indexOf(evKey)<0)_spBS[p.brand].events.push(evKey);
    _spBS[p.brand].exposure+=exp;
    _spBS[p.brand].partnerships.push({event:p.event,years:p.years||[],type:p.type,exposure:exp});
    if(_spBS[p.brand].types.indexOf(p.type)<0)_spBS[p.brand].types.push(p.type);
  });
}
function spPrevPeriodStats(){
  var saved=_spPeriod;
  var yr=parseInt(_spPeriod);
  if(isNaN(yr)||yr<2001)return null;
  _spPeriod=String(yr-1);
  spBuildData();
  var prevBrands=Object.keys(_spBS).length;
  var prevEvSet={};SP_PARTNERSHIPS.forEach(function(p){prevEvSet[p.event]=1;});
  var prevExp=Object.values(_spBS).reduce(function(s,b){return s+b.exposure;},0);
  _spPeriod=saved;
  spBuildData();
  return{brands:prevBrands,events:Object.keys(prevEvSet).length,exp:prevExp};
}
function spRenderKpis(){
  var totalExp=Object.values(_spBS).reduce(function(s,b){return s+b.exposure;},0);
  var evSet={};Object.values(_spBS).forEach(function(b){b.events.forEach(function(e){evSet[e]=1;});});
  var nBrands=Object.keys(_spBS).length;
  var nEvents=Object.keys(evSet).length;
  var prev=spPrevPeriodStats();
  var yr=parseInt(_spPeriod);
  var prevYrLabel=isNaN(yr)?'':'vs '+(yr-1);
  function trendHtml(cur,prv,col){
    if(!prev||!prevYrLabel)return'';
    var d=cur-prv;
    if(d===0)return'';
    var sign=d>0?'\\u2191 +':'\\u2193 ';
    var c=d>0?'#22C55E':'#FF4A6B';
    return'<div style="font-size:9px;color:'+c+';margin-top:2px">'+sign+(Math.abs(d)>=1e6?(Math.abs(d)/1e6).toFixed(1)+'M':Math.abs(d)>=1e3?Math.round(Math.abs(d)/1e3)+'k':Math.abs(d))+' '+prevYrLabel+'</div>';
  }
  var kpis=[
    [nBrands,'Marques','#22C55E',''],
    [nEvents,'\\u00c9v\\u00e9nements','#38BDF8',''],
    [(totalExp/1e6).toFixed(1)+'M','Finishers expos\\u00e9s','#F472B6',prev?trendHtml(totalExp,prev.exp,'#F472B6'):'']
  ];
  document.getElementById('sp-kpis').innerHTML=kpis.map(function(k){return'<div class="sp-kpi"><div class="sp-kpi-num" style="color:'+k[2]+'">'+k[0]+'</div><div class="sp-kpi-lbl">'+k[1]+'</div>'+k[3]+'</div>';}).join('')+'<div class="sp-kpi" id="sp-kpi-sector" style="display:none;transition:all .2s"><div class="sp-kpi-num" id="sp-kpi-sector-num"></div><div class="sp-kpi-lbl" id="sp-kpi-sector-lbl"></div></div>';
  var secExp={};Object.values(_spBS).forEach(function(b){secExp[b.sector]=(secExp[b.sector]||0)+b.exposure;});
  _spSecExp=secExp;_spSecExp['ALL']=totalExp;
}
function initSponsoring(){
  spBuildData();
  _spActiveSector='ALL';_spActiveBrand=null;
  spRenderKpis();
  var secSorted=Object.entries(_spSecExp).filter(function(s){return s[0]!=='ALL';}).sort(function(a,b){return b[1]-a[1];});
  _spPillSectors=['ALL'].concat(secSorted.map(function(s){return s[0];}));
  document.getElementById('sp-pills').innerHTML=_spPillSectors.map(function(s,i){
    var col=i===0?null:(_spCols[s]||'#EF4444');
    var st=col?(' style="border-color:'+col+'55;color:'+col+'"'):'';
    return '<div class="sp-pill'+(i===0?' spc-active':'')+'"'+st+' data-si="'+i+'">'+s+'</div>';
  }).join('');
  document.getElementById('sp-pills').addEventListener('click',function(e){
    var el=e.target.closest('.sp-pill');
    if(!el)return;
    var i=parseInt(el.getAttribute('data-si')||'0');
    spSetSector(_spPillSectors[i]||'ALL');
  });
  document.getElementById('sp-search-inp').oninput=function(){spRenderList();spRenderTreemap();};
  spRenderList();
  setTimeout(function(){spRenderTreemap();spAutoSelect();},50);
}
function spSetListMode(mode){
  _spListMode=mode;
  document.querySelectorAll('.sp-sort-btn').forEach(function(b){
    b.classList.toggle('spc-active',b.dataset.sort===mode);
    b.style.color=b.dataset.sort===mode?'var(--text)':'var(--text3)';
  });
  spRenderList();
}
function spSetSector(s){
  _spActiveSector=s;
  document.querySelectorAll('.sp-pill').forEach(function(el){
    el.classList.remove('spc-active');
    el.style.removeProperty('background');
    var pillText=el.textContent.split(String.fromCharCode(10))[0].trim();
    if(pillText===s||(s==='ALL'&&pillText==='ALL')){
      el.classList.add('spc-active');
      var col=s==='ALL'?null:(_spCols[s]||'#EF4444');
      if(col)el.style.background=col;
    }
  });
  // Show sector exposure KPI in header
  var kpiSec=document.getElementById('sp-kpi-sector');
  if(kpiSec){
    if(s==='ALL'){kpiSec.style.display='none';}
    else{
      var sExp=_spSecExp[s]||0;
      var col=_spCols[s]||'#EF4444';
      document.getElementById('sp-kpi-sector-num').style.color=col;
      document.getElementById('sp-kpi-sector-num').textContent=spFmt(sExp);
      document.getElementById('sp-kpi-sector-lbl').textContent=s;
      kpiSec.style.display='';
    }
  }
  spRenderList();spRenderTreemap();
}
function spFiltered(){
  var q=(document.getElementById('sp-search-inp').value||'').toLowerCase();
  var list=Object.entries(_spBS).filter(function(e){
    if(_spActiveSector!=='ALL'&&e[1].sector!==_spActiveSector)return false;
    if(q&&e[0].toLowerCase().indexOf(q)<0)return false;
    return true;
  });
  list.sort(function(a,b){return b[1].exposure-a[1].exposure;});
  return list;
}
function spFmt(n){return n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?Math.round(n/1e3)+'k':String(n);}
var _spBrandKeys=[];
function spRenderList(){
  var bl=document.getElementById('sp-blist');
  if(_spListMode==='categories'){
    // Categories view
    var secData={};
    Object.entries(_spBS).forEach(function(e){
      var sec=e[1].sector;
      if(!secData[sec])secData[sec]={brands:0,exposure:0};
      secData[sec].brands++;
      secData[sec].exposure+=e[1].exposure;
    });
    var secList=Object.entries(secData).sort(function(a,b){return b[1].exposure-a[1].exposure;});
    bl.innerHTML=secList.map(function(e,i){
      var col=_spCols[e[0]]||'#EF4444';
      var act=_spActiveSector===e[0]?' spc-active':'';
      return '<div class="sp-bitem'+act+'" data-sec="'+e[0]+'">'
        +'<div class="sp-bdot" style="background:'+col+'"></div>'
        +'<div class="sp-bname">'+e[0]+'</div>'
        +'<div class="sp-bexp" style="text-align:right"><div>'+spFmt(e[1].exposure)+'</div><div style="font-size:9px;color:var(--text3)">'+e[1].brands+' marques</div></div></div>';
    }).join('');
    bl.onclick=function(e){
      var el=e.target.closest('.sp-bitem');
      if(!el)return;
      var sec=el.getAttribute('data-sec');
      if(sec)spSetSector(sec);
    };
    return;
  }
  // Brands view (default)
  var items=spFiltered().slice(0,50);
  _spBrandKeys=items.map(function(e){return e[0];});
  bl.innerHTML=items.map(function(e,i){
    var col=_spCols[e[1].sector]||'#EF4444';
    var act=_spActiveBrand===e[0]?' spc-active':'';
    return '<div class="sp-bitem'+act+'" data-bi="'+i+'">'
      +'<div class="sp-bdot" style="background:'+col+'"></div>'
      +'<div class="sp-bname">'+e[0]+'</div>'
      +'<div class="sp-bexp">'+spFmt(e[1].exposure)+'</div></div>';
  }).join('');
  bl.onclick=function(e){
    var el=e.target.closest('.sp-bitem');
    if(!el)return;
    var i=parseInt(el.getAttribute('data-bi')||'0');
    if(_spBrandKeys[i])spSelect(_spBrandKeys[i]);
  };
}
function spAutoSelect(){
  var items=spFiltered();
  if(items.length)spSelect(items[0][0]);
}
function spRenderTreemap(){
  var container=document.getElementById('sp-treemap');
  var hint=document.getElementById('sp-treemap-hint');
  Array.from(container.children).forEach(function(c){if(c!==hint)container.removeChild(c);});
  var items=spFiltered().slice(0,50);
  if(!items.length)return;
  var W=container.clientWidth||700,H=container.clientHeight||350;
  var nodes=items.map(function(e){return {id:e[0],v:Math.max(e[1].exposure,1),sec:e[1].sector};});
  var totalV=nodes.reduce(function(s,n){return s+n.v;},0)||1;
  function layout(ns,x,y,w,h,tv){
    if(!ns.length||w<2||h<2)return;
    if(ns.length===1){place(ns[0],x,y,w,h);return;}
    var horiz=w>=h,row=[],rowV=0,prevWorst=Infinity;
    for(var i=0;i<ns.length;i++){
      row.push(ns[i]);rowV+=ns[i].v;
      var dim=horiz?(rowV/tv)*w:(rowV/tv)*h;
      var fixd=horiz?h:w;
      var worst=row.reduce(function(mx,n){var a=(n.v/rowV)*fixd;var b=dim;var r=a>b?a/b:b/a;return Math.max(mx,r);},0);
      if(i>0&&worst>prevWorst){row.pop();rowV-=ns[i].v;break;}
      prevWorst=worst;
    }
    if(!row.length){row=[ns[0]];rowV=ns[0].v;}
    var usedDim=horiz?(rowV/tv)*w:(rowV/tv)*h;
    var off=0;
    row.forEach(function(n){
      var frac=n.v/rowV;
      var pw=horiz?usedDim:w*frac;var ph=horiz?h*frac:usedDim;
      place(n,x+(horiz?0:off),y+(horiz?off:0),pw,ph);
      off+=horiz?ph:pw;
    });
    var rem=ns.slice(row.length);
    if(rem.length){var remV=rem.reduce(function(s,n){return s+n.v;},0);layout(rem,horiz?x+usedDim:x,horiz?y:y+usedDim,horiz?w-usedDim:w,horiz?h:h-usedDim,remV);}
  }
  function place(n,x,y,w,h){
    var col=_spCols[n.sec]||'#EF4444';
    var act=_spActiveBrand===n.id;
    var bg=act?'var(--bg3)':'var(--bg2)';
    var brd=act?'1px solid '+col:'1px solid var(--border)';
    var d=document.createElement('div');
    var tw=Math.max(0,w-3),th=Math.max(0,h-3);
    d.style.cssText='position:absolute;left:'+(x+1.5)+'px;top:'+(y+1.5)+'px;width:'+tw+'px;height:'+th+'px;border-radius:6px;background:'+bg+';border:'+brd+';cursor:pointer;transition:all .15s;overflow:hidden;box-sizing:border-box;';
    var inner='<div style="position:absolute;bottom:0;left:0;right:0;height:3px;background:'+col+';border-radius:0 0 5px 5px"></div>';
    var label=n.id;
    var labelColor=act?col:'var(--text)';
    // Three tiers:
    //  - big  : w>=80 et h>=42  -> label + nombre
    //  - small: w>=55 et h>=26  -> label seul (tronque si besoin)
    //  - tiny : plus petit      -> aucun texte
    if(tw>=80&&th>=42){
      var fs=Math.max(10,Math.min(13,Math.min(tw,th)/7));
      inner+='<span style="position:absolute;bottom:22px;left:8px;right:6px;font-size:'+fs+'px;font-weight:600;color:'+labelColor+';white-space:nowrap;overflow:hidden;text-overflow:ellipsis;pointer-events:none">'+label+'</span>';
      inner+='<span style="position:absolute;bottom:7px;left:8px;font-size:10px;font-weight:500;color:var(--text3);pointer-events:none">'+spFmt(n.v)+'</span>';
    }else if(tw>=55&&th>=26){
      var short=(label.length>8&&tw<85)?label.substring(0,8)+'.':label;
      var fs=Math.max(9,Math.min(11,Math.min(tw,th)/6));
      inner+='<span style="position:absolute;bottom:8px;left:6px;right:4px;font-size:'+fs+'px;font-weight:600;color:'+labelColor+';white-space:nowrap;overflow:hidden;text-overflow:ellipsis;pointer-events:none">'+short+'</span>';
    }
    d.innerHTML=inner;
    d.setAttribute('data-sp-id',n.id);
    d.setAttribute('data-sp-col',col);
    d.addEventListener('mouseenter',function(){if(_spActiveBrand===n.id)return;this.style.background='var(--bg3)';this.style.borderColor=col+'88';});
    d.addEventListener('mouseleave',function(){if(_spActiveBrand===n.id)return;this.style.background='var(--bg2)';this.style.borderColor='var(--border)';});
    d.addEventListener('click',function(){spSelect(n.id);});
    d.title=n.id+' \\u2022 '+n.sec+' \\u2022 '+spFmt(n.v)+' finishers';
    container.appendChild(d);
  }
  layout(nodes,0,0,W,H,totalV);
  if(hint)hint.style.opacity=_spActiveBrand?'0':'1';
}
function spChangePeriod(val){
  _spPeriod=val;
  spBuildData();
  spRenderKpis();
  _spActiveBrand=null;
  document.getElementById('sp-detail').style.display='none';
  spRenderList();spRenderTreemap();
  spAutoSelect();
}
function spHighlight(brandId){
  // Update list selection
  document.querySelectorAll('.sp-bitem').forEach(function(el){
    var i=parseInt(el.getAttribute('data-bi')||'0');
    el.classList.toggle('spc-active',_spBrandKeys[i]===brandId);
  });
  // Update treemap borders
  var container=document.getElementById('sp-treemap');
  container.querySelectorAll('[data-sp-id]').forEach(function(el){
    var id=el.getAttribute('data-sp-id');
    var col=el.getAttribute('data-sp-col')||'var(--border)';
    if(id===brandId){
      el.style.borderColor=col;
      el.style.background='var(--bg3)';
    }else{
      el.style.borderColor='var(--border)';
      el.style.background='var(--bg2)';
    }
  });
}
function spSelect(brandId){
  _spActiveBrand=brandId;
  spHighlight(brandId);
  var bs=_spBS[brandId];var info=SP_BRANDS[brandId]||{};
  var col=_spCols[bs.sector]||'#EF4444';
  var tConf={
    title:{label:'Partenaire Titre',bg:col,text:'#fff'},
    premium:{label:'Partenaire Premium',bg:col+'90',text:'#fff'},
    major:{label:'Partenaire Majeur',bg:col+'60',text:'#fff'},
    official:{label:'Partenaire Officiel',bg:col+'30',text:col},
    partner:{label:'Fournisseur Officiel',bg:'var(--bg3)',text:'var(--text2)'}
  };
  // Group partnerships by type, filtered by active period
  var now=new Date().getFullYear();
  var pMinYr=_spPeriod==='5'?now-4:_spPeriod==='3'?now-2:parseInt(_spPeriod)||now;
  var pMaxYr=_spPeriod==='5'||_spPeriod==='3'?now:pMinYr;
  var byType={title:[],premium:[],major:[],official:[],partner:[]};
  bs.partnerships.forEach(function(pp){
    var active=pp.years.some(function(y){return y>=pMinYr&&y<=pMaxYr;});
    if(active)(byType[pp.type]||byType.partner).push(pp);
  });
  var evHtml='';
  ['title','premium','major','official','partner'].forEach(function(t){
    var items=byType[t]||[];if(!items.length)return;
    var tc=tConf[t];
    evHtml+='<div style="margin-bottom:8px">'
      +'<span style="display:inline-block;font-size:10px;padding:2px 8px;border-radius:3px;background:'+tc.bg+';color:'+tc.text+';font-weight:600;margin-bottom:4px">'+tc.label+'</span>'
      +'<div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:3px">';
    items.sort(function(a,b){return b.exposure-a.exposure;}).forEach(function(pp){
      var shortName=pp.event.replace(/Marathon/g,'M.').replace(/Half Marathon/g,'HM').replace(/presented by.*/i,'').trim();
      var yrRange=pp.years.length?pp.years[0]+(pp.years.length>1?'-'+pp.years[pp.years.length-1]:''):'';
      evHtml+='<span class="sp-evtag" title="'+pp.event+' ('+yrRange+') : '+spFmt(pp.exposure)+' finishers">'+shortName+(pp.exposure>0?' <span style="color:var(--text3);font-size:9px">'+spFmt(pp.exposure)+'</span>':'')+'</span>';
    });
    evHtml+='</div></div>';
  });
  var det=document.getElementById('sp-detail');
  det.innerHTML='<div style="min-width:130px">'
    +'<div class="sp-detail-name">'+brandId+'</div>'
    +'<div class="sp-detail-badge" style="background:'+col+'25;color:'+col+'">'+bs.sector+'</div>'
    +(info.country?'<div style="font-size:11px;color:var(--text3);margin-top:4px">'+info.country+'</div>':'')
    +'</div>'
    +'<div style="display:flex;gap:20px;align-items:center">'
    +'<div class="sp-detail-stat"><div class="sp-detail-stat-num" style="color:'+col+'">'+spFmt(bs.exposure)+'</div><div class="sp-detail-stat-lbl">Finishers expos\u00e9s</div></div>'
    +'<div class="sp-detail-stat"><div class="sp-detail-stat-num" style="color:'+col+'">'+bs.events.length+'</div><div class="sp-detail-stat-lbl">\u00c9v\u00e9nements</div></div>'
    +'</div>'
    +'<div style="flex:1;min-width:180px">'+evHtml+'</div>';
  det.style.display='flex';
}

initBiggestYears();
filterTable();

// ── COMPARE ──────────────────────────────────────────────────────────────────
var cmpSelectedA = null;
var cmpSelectedB = null;

function cmpSearch(side){
  var inputId='cmp-input-'+side;
  var dropId='cmp-drop-'+side;
  var q=document.getElementById(inputId).value.toLowerCase().trim();
  var drop=document.getElementById(dropId);
  if(q.length<2){drop.style.display='none';return;}
  var matches=RAW.filter(function(r){return r.r.toLowerCase().indexOf(q)>=0||r.c.toLowerCase().indexOf(q)>=0;});
  if(!matches.length){drop.style.display='none';return;}
  var dc={MARATHON:'#60A5FA18',SEMI:'#FF8A5018','10KM':'#5CDFA018'};
  var dt={MARATHON:'#60A5FA',SEMI:'#FF8A50','10KM':'#5CDFA0'};
  drop.innerHTML='';
  drop.style.display='block';
  matches.slice(0,10).forEach(function(r){
    var rawIdx=RAW.indexOf(r);
    var dl=r.d==='10KM'?'10 km':r.d==='SEMI'?'Semi':r.d==='AUTRE'?'Autre':'Marathon';
    var item=document.createElement('div');
    item.className='cmp-drop-item';
    item.innerHTML='<span class="cmp-dist-pill" style="background:'+dc[r.d]+';color:'+dt[r.d]+'">'+dl+'</span>'+r.r;
    item.addEventListener('click',(function(i,s){return function(){cmpSelect(i,s);};})(rawIdx,side));
    drop.appendChild(item);
  });
}
function cmpSelectEl(el){
  cmpSelect(parseInt(el.dataset.idx), el.dataset.side);
}
function cmpSelect(idx, side){
  var ev = RAW[idx];
  if(side==='a'){
    cmpSelectedA = ev;
    document.getElementById('cmp-input-a').value = ev.r;
  } else {
    cmpSelectedB = ev;
    document.getElementById('cmp-input-b').value = ev.r;
  }
  document.getElementById('cmp-drop-'+side).style.display='none';
  if(cmpSelectedA && cmpSelectedB) renderCompare();
}

function cmpTimeToMin(t){
  if(!t)return null;
  var p=String(t).split(':');
  if(p.length===3)return parseInt(p[0])*60+parseInt(p[1])+parseInt(p[2])/60;
  return null;
}

function cmpMeasureText(text, fontStr){
  var c=document.createElement('canvas');
  var ctx=c.getContext('2d');
  ctx.font=fontStr;
  return ctx.measureText(text).width;
}

function cmpRow(labelA, labelB, catLabel, winA){
  // winA: true=A wins, false=B wins, null=draw/no data
  var cellA, cellB;
  if(winA === true){
    cellA = '<div class="cmp-cell"><div><div class="cmp-val-win" id="cmpbar-txt-'+catLabel.replace(/[^a-z]/gi,'')+'">'+labelA+'</div>'
           +'<div class="cmp-bar" id="cmpbar-'+catLabel.replace(/[^a-z]/gi,'')+'"></div></div><div class="cmp-dot"></div></div>';
    cellB = '<div class="cmp-cell r"><div style="text-align:right"><div class="cmp-val-lose">'+labelB+'</div></div></div>';
  } else if(winA === false){
    cellA = '<div class="cmp-cell"><div><div class="cmp-val-lose">'+labelA+'</div></div></div>';
    cellB = '<div class="cmp-cell r"><div class="cmp-dot"></div><div><div class="cmp-val-win" id="cmpbar-txt-'+catLabel.replace(/[^a-z]/gi,'')+'">'+labelB+'</div>'
           +'<div class="cmp-bar" id="cmpbar-'+catLabel.replace(/[^a-z]/gi,'')+'"></div></div></div>';
  } else {
    cellA = '<div class="cmp-cell"><div><div class="cmp-val-lose">'+labelA+'</div></div></div>';
    cellB = '<div class="cmp-cell r"><div style="text-align:right"><div class="cmp-val-lose">'+labelB+'</div></div></div>';
  }
  var midLabel = catLabel.replace(/([A-Z])/g,' $1').trim();
  return '<div class="cmp-row">'+cellA
    +'<div class="cmp-mid"><div class="cmp-mid-label">'+catLabel+'</div></div>'
    +cellB+'</div>';
}

function renderCompare(){
  var a = cmpSelectedA, b = cmpSelectedB;
  var colA=colDist(a), colB=colDist(b);
  var tdA=getTimeData(a.r), tdB=getTimeData(b.r);
  var wrA=getWinnersRecords(a.r), wrB=getWinnersRecords(b.r);

  var lfA=lastFin(a),lfB=lastFin(b);
  var fA=lfA?lfA.v:null,fB=lfB?lfB.v:null;
  var fYrA=lfA?lfA.yr:0,fYrB=lfB?lfB.yr:0;

  // Evolution
  function calcEvo(r){
    var ks=Object.keys(r.hist||{}).map(Number).filter(function(y){var v=(r.hist||{})[y];return v&&v>0;}).sort(function(x,y){return x-y;});
    if(ks.length<2)return{pct:null,str:'-',sub:''};
    var first=ks[0],last=ks[ks.length-1],fv=(r.hist||{})[first],lv=(r.hist||{})[last];
    var p=((lv-fv)/fv*100);
    return{pct:p,str:(p>=0?'+':'')+p.toFixed(1)+'%',sub:first+' \u2192 '+last};
  }
  var eA=calcEvo(a),eB=calcEvo(b);

  var distA=a.d==='MARATHON'?'Marathon':a.d==='SEMI'?'Semi-marathon':a.d==='AUTRE'?'Autre':'10 km';
  var distB=b.d==='MARATHON'?'Marathon':b.d==='SEMI'?'Semi-marathon':b.d==='AUTRE'?'Autre':'10 km';
  var statA=(a.ci||[]).length?(a.ci||[]).join(' / '):'\u2014';
  var statB=(b.ci||[]).length?(b.ci||[]).join(' / '):'\u2014';

  var avgA=tdA?tdA.avg:null, avgB=tdB?tdB.avg:null;
  var menA=wrA&&wrA.men?wrA.men:(tdA?tdA.men:null);
  var menB=wrB&&wrB.men?wrB.men:(tdB?tdB.men:null);
  var wmA=wrA&&wrA.women?wrA.women:(tdA?tdA.women:null);
  var wmB=wrB&&wrB.women?wrB.women:(tdB?tdB.women:null);

  var winFin=fA&&fB?(fA>fB?true:fA<fB?false:null):null;
  var winAvg=avgA&&avgB?(cmpTimeToMin(avgA)<cmpTimeToMin(avgB)?true:cmpTimeToMin(avgA)>cmpTimeToMin(avgB)?false:null):null;
  var winMen=menA&&menB?(cmpTimeToMin(menA)<cmpTimeToMin(menB)?true:cmpTimeToMin(menA)>cmpTimeToMin(menB)?false:null):null;
  var winWm=wmA&&wmB?(cmpTimeToMin(wmA)<cmpTimeToMin(wmB)?true:cmpTimeToMin(wmA)>cmpTimeToMin(wmB)?false:null):null;
  var winEvo=eA.pct!==null&&eB.pct!==null?(eA.pct>eB.pct?true:eA.pct<eB.pct?false:null):null;

  function winCol(winA){return winA===true?colA:winA===false?colB:'var(--text3)';}
  function cmpR(valA,valB,label,winA,subA,subB){
    var wc=winCol(winA);
    var clsA=winA===true?'cmp-val-win':'cmp-val-lose';
    var clsB=winA===false?'cmp-val-win':'cmp-val-lose';
    var styleA=winA===true?'style="color:'+colA+'"':'';
    var styleB=winA===false?'style="color:'+colB+'"':'';
    var dotA=winA===true?'<div class="cmp-dot" style="background:'+colA+'"></div>':'';
    var dotB=winA===false?'<div class="cmp-dot" style="background:'+colB+'"></div>':'';
    var blA=winA===true?'border-left:2px solid '+colA:'';
    var brB=winA===false?'border-right:2px solid '+colB:'';
    return'<div class="cmp-row">'
      +'<div class="cmp-cell" style="'+blA+'"><div><div class="'+clsA+'" '+styleA+'>'+valA+'</div>'+(subA?'<div class="cmp-sub">'+subA+'</div>':'')+'</div>'+dotA+'</div>'
      +'<div class="cmp-mid"><div class="cmp-mid-label">'+label+'</div></div>'
      +'<div class="cmp-cell r" style="'+brB+'">'+dotB+'<div style="text-align:right"><div class="'+clsB+'" '+styleB+'>'+valB+'</div>'+(subB?'<div class="cmp-sub">'+subB+'</div>':'')+'</div></div>'
      +'</div>';
  }

  var finLblA=fA?fmtFull(fA)+' ('+fYrA+')':'-';
  var finLblB=fB?fmtFull(fB)+' ('+fYrB+')':'-';

  var html='<div class="cmp-wrap" style="--cmp-col-a:'+colA+';--cmp-col-b:'+colB+';">'
    +'<div class="cmp-header">'
    +'<div class="cmp-header-cell"><div class="cmp-race-name" style="color:'+colA+'">'+a.r+'</div><div class="cmp-race-meta">'+a.c+' &middot; '+a.p+' &middot; '+distA+circBadges(a)+'</div></div>'
    +'<div class="cmp-header-cell ctr"><div class="cmp-mid-label">Categorie</div></div>'
    +'<div class="cmp-header-cell" style="text-align:right"><div class="cmp-race-name" style="color:'+colB+'">'+b.r+'</div><div class="cmp-race-meta">'+b.c+' &middot; '+b.p+' &middot; '+distB+circBadges(b)+'</div></div>'
    +'</div>';

  html+=cmpR(finLblA,finLblB,'Finishers',winFin,'','');
  html+=cmpR(avgA||'-',avgB||'-','Temps moyen',winAvg,'','');
  html+=cmpR(menA||'-',menB||'-','Record homme',winMen,'','');
  html+=cmpR(wmA||'-',wmB||'-','Record femme',winWm,'','');
  html+=cmpR(eA.str,eB.str,'Evolution',winEvo,eA.sub,eB.sub);
  html+=cmpR(statA,statB,'Statut',null,'','');

  html+='</div>';
  // Chart
  html+='<div style="margin-top:1.5rem;"><div class="ov-chart-label" style="margin-bottom:8px">Evolution comparee des finishers</div><div style="position:relative;height:200px;"><canvas id="cmp-chart"></canvas></div></div>';

  document.getElementById('cmp-result').innerHTML=html;

  // Render compare chart
  if(window._cmpChart)window._cmpChart.destroy();
  var cc=document.getElementById('cmp-chart');
  if(cc){
    var aHist=Object.keys(a.hist||{}).map(Number).filter(function(y){var v=(a.hist||{})[y];return v&&v>0;});
    var bHist=Object.keys(b.hist||{}).map(Number).filter(function(y){var v=(b.hist||{})[y];return v&&v>0;});
    var allYrs=[].concat(aHist,bHist);allYrs=allYrs.filter(function(v,i,s){return s.indexOf(v)===i;}).sort(function(x,y){return x-y;});
    window._cmpChart=new Chart(cc,{type:'line',
      data:{labels:allYrs.map(String),datasets:[
        {label:a.r,data:allYrs.map(function(yr){var v=(a.hist||{})[yr];return v&&v>0?v:null;}),borderColor:colA,backgroundColor:'transparent',tension:0.3,pointRadius:4,pointBackgroundColor:colA,borderWidth:2,spanGaps:true},
        {label:b.r,data:allYrs.map(function(yr){var v=(b.hist||{})[yr];return v&&v>0?v:null;}),borderColor:colB,backgroundColor:'transparent',tension:0.3,pointRadius:4,pointBackgroundColor:colB,borderWidth:2,borderDash:[6,4],spanGaps:true}
      ]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:true,labels:{color:mkTICK().color,font:{size:11},usePointStyle:true,pointStyle:'line',boxWidth:20}},
          tooltip:mkTT({label:function(ctx){return' '+ctx.dataset.label+': '+fmtFull(ctx.parsed.y);}})},
        scales:{x:{grid:{display:false},ticks:{color:'#555',font:{size:10},maxRotation:0,minRotation:0,autoSkip:true,maxTicksLimit:12},border:{display:false}},
          y:{beginAtZero:true,grid:{color:mkGRID()},ticks:{color:'#555',font:{size:10},callback:function(v){return fmt(v);}},border:{display:false}}}
      }
    });
  }
}

function buildCmpRow(valA, valB, label, winA, subA, subB){
  var idKey = label.replace(/[^a-zA-Z]/g,'');
  var cellA, cellB;
  if(winA===true){
    cellA='<div class="cmp-cell"><div><div class="cmp-val-win" id="cmptxt-'+idKey+'">'+valA+'</div>'
      +'<div class="cmp-bar" id="cmpbar-'+idKey+'"></div>'+(subA?'<div class="cmp-sub">'+subA+'</div>':'')+'</div><div class="cmp-dot"></div></div>';
    cellB='<div class="cmp-cell r"><div style="text-align:right"><div class="cmp-val-lose">'+valB+'</div>'+(subB?'<div class="cmp-sub">'+subB+'</div>':'')+'</div></div>';
  } else if(winA===false){
    cellA='<div class="cmp-cell"><div><div class="cmp-val-lose">'+valA+'</div>'+(subA?'<div class="cmp-sub">'+subA+'</div>':'')+'</div></div>';
    cellB='<div class="cmp-cell r"><div class="cmp-dot"></div><div><div class="cmp-val-win" id="cmptxt-'+idKey+'">'+valB+'</div>'
      +'<div class="cmp-bar" id="cmpbar-'+idKey+'"></div>'+(subB?'<div class="cmp-sub">'+subB+'</div>':'')+'</div></div>';
  } else {
    cellA='<div class="cmp-cell"><div><div class="cmp-val-lose">'+valA+'</div>'+(subA?'<div class="cmp-sub">'+subA+'</div>':'')+'</div></div>';
    cellB='<div class="cmp-cell r"><div style="text-align:right"><div class="cmp-val-lose">'+valB+'</div>'+(subB?'<div class="cmp-sub">'+subB+'</div>':'')+'</div></div>';
  }
  return '<div class="cmp-row">'+cellA
    +'<div class="cmp-mid"><div class="cmp-mid-label">'+label+'</div></div>'
    +cellB+'</div>';
}

function buildCmpRowEvo(valA, valB, label, winA, subA, subB){
  var cellA, cellB;
  if(winA===true){
    cellA='<div class="cmp-cell" style="align-items:flex-start;padding-top:14px;padding-bottom:14px;">'
      +'<div style="display:inline-flex;align-items:center;gap:6px;">'
      +'<div><span class="cmp-val-win" id="cmptxt-evo-a">'+valA+'</span>'
      +'<div class="cmp-bar" id="cmpbar-evo-a" style="width:10px"></div>'
      +(subA?'<div class="cmp-sub">'+subA+'</div>':'')+'</div>'
      +'<div class="cmp-dot" style="align-self:center;margin-top:-8px"></div>'
      +'</div></div>';
    cellB='<div class="cmp-cell r"><div style="text-align:right"><div class="cmp-val-lose">'+valB+'</div>'+(subB?'<div class="cmp-sub">'+subB+'</div>':'')+'</div></div>';
  } else if(winA===false){
    cellA='<div class="cmp-cell"><div><div class="cmp-val-lose">'+valA+'</div>'+(subA?'<div class="cmp-sub">'+subA+'</div>':'')+'</div></div>';
    cellB='<div class="cmp-cell r" style="align-items:flex-start;padding-top:14px;padding-bottom:14px;">'
      +'<div style="display:inline-flex;align-items:center;gap:6px;">'
      +'<div class="cmp-dot" style="align-self:center;margin-bottom:-8px"></div>'
      +'<div><span class="cmp-val-win" id="cmptxt-evo-b">'+valB+'</span>'
      +'<div class="cmp-bar" id="cmpbar-evo-b" style="width:10px"></div>'
      +(subB?'<div class="cmp-sub">'+subB+'</div>':'')+'</div>'
      +'</div></div>';
  } else {
    cellA='<div class="cmp-cell"><div><div class="cmp-val-lose">'+valA+'</div>'+(subA?'<div class="cmp-sub">'+subA+'</div>':'')+'</div></div>';
    cellB='<div class="cmp-cell r"><div style="text-align:right"><div class="cmp-val-lose">'+valB+'</div>'+(subB?'<div class="cmp-sub">'+subB+'</div>':'')+'</div></div>';
  }
  return '<div class="cmp-row">'+cellA
    +'<div class="cmp-mid"><div class="cmp-mid-label">'+label+'</div></div>'
    +cellB+'</div>';
}

function fixCmpBar(idKey, winA){
  var txtEl = document.getElementById('cmptxt-'+idKey);
  var barEl = document.getElementById('cmpbar-'+idKey);
  if(!txtEl||!barEl) return;
  var st = window.getComputedStyle(txtEl);
  var font = st.fontWeight+' '+st.fontSize+' '+st.fontFamily;
  var c = document.createElement('canvas');
  var ctx = c.getContext('2d');
  ctx.font = font;
  barEl.style.width = Math.ceil(ctx.measureText(txtEl.textContent).width)+'px';
}

function fixCmpBarEvo(winA){
  var side = winA===true?'a':(winA===false?'b':null);
  if(!side) return;
  var txtEl = document.getElementById('cmptxt-evo-'+side);
  var barEl = document.getElementById('cmpbar-evo-'+side);
  if(!txtEl||!barEl) return;
  var st = window.getComputedStyle(txtEl);
  var font = st.fontWeight+' '+st.fontSize+' '+st.fontFamily;
  var c = document.createElement('canvas');
  var ctx = c.getContext('2d');
  ctx.font = font;
  barEl.style.width = Math.ceil(ctx.measureText(txtEl.textContent).width)+'px';
}

// Bar tooltip
var barTipEl=null;
function initBarTips(){
  if(!barTipEl){barTipEl=document.createElement('div');barTipEl.style.cssText='position:fixed;background:#111;border:1px solid #333;border-radius:6px;padding:10px 14px;pointer-events:none;z-index:100;font-size:12px;display:none;max-width:320px;';document.body.appendChild(barTipEl);}
  document.querySelectorAll('.bt-row').forEach(function(el){
    el.addEventListener('mouseenter',function(){
      var city=el.dataset.city||'';
      barTipEl.innerHTML='<div style="color:#fff;font-size:12px;font-weight:500;margin-bottom:2px">'+el.dataset.name+'</div>'+(city?'<div style="color:#888;font-size:11px;margin-bottom:4px">'+city+'</div>':'')+'<div style="color:#ccc;font-size:13px;font-weight:600">'+el.dataset.val+'</div>';
      barTipEl.style.display='block';
      var rect=el.getBoundingClientRect();
      barTipEl.style.left=(rect.left+rect.width/2-80)+'px';
      barTipEl.style.top=(rect.top-70)+'px';
    });
    el.addEventListener('mouseleave',function(){barTipEl.style.display='none';});
  });
}

// Close dropdowns on outside click
document.addEventListener('click', function(e){
  if(!e.target.closest('.cmp-search-box')){
    var da=document.getElementById('cmp-drop-a');
    var db=document.getElementById('cmp-drop-b');
    if(da)da.style.display='none';
    if(db)db.style.display='none';
  }
});

// ── WINNERS TIMES ─────────────────────────────────────────────────────────────
var cW=null;
function winToSec(t){if(!t)return null;var p=t.split(':');if(p.length===3)return+p[0]*3600+(+p[1])*60+(+p[2]);if(p.length===2)return+p[0]*60+(+p[1]);return null;}
function secToTime(s){if(s==null)return'-';var h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sc=Math.round(s%60);return(h?h+':':'')+(h?String(m).padStart(2,'0'):m)+':'+String(sc).padStart(2,'0');}
function secToMin(s){return s!=null?s/60:null;}

function updateWinners(){
  var dist=document.getElementById('win-dist').value;
  var gender=document.getElementById('win-gender').value;
  var sortMode=document.getElementById('win-sort').value;
  var topN=+document.getElementById('win-topn').value;
  var region=document.getElementById('region-winners').value;
  var filtered=WINNERS.filter(function(w){if(w.d!==dist)return false;if(region!=='ALL'&&raceRegion(w.r)!==region)return false;return true;});
  var races={};
  filtered.forEach(function(w){if(!races[w.r])races[w.r]={name:w.r,years:[]};races[w.r].years.push({y:w.y,m:winToSec(w.m),w:winToSec(w.w),ms:w.m,ws:w.w});});
  var raceList=Object.values(races).filter(function(r){return r.years.length>0;});
  raceList.forEach(function(r){r.years.sort(function(a,b){return a.y-b.y;});});
  if(sortMode==='fastest'){raceList.sort(function(a,b){var la=a.years[a.years.length-1],lb=b.years[b.years.length-1];var va=gender==='w'?(la.w||9999):(la.m||9999),vb=gender==='w'?(lb.w||9999):(lb.m||9999);return va-vb;});}
  else if(sortMode==='alpha'){raceList.sort(function(a,b){return a.name.localeCompare(b.name);});}
  else if(sortMode==='progress'){raceList.sort(function(a,b){function prog(r){if(r.years.length<2)return 0;var f=r.years[0],l=r.years[r.years.length-1];var fv=gender==='w'?f.w:f.m,lv=gender==='w'?l.w:l.m;if(!fv||!lv)return 0;return fv-lv;}return prog(b)-prog(a);});}
  if(topN<999)raceList=raceList.slice(0,topN);
  var allYears=[];
  raceList.forEach(function(r){r.years.forEach(function(y){if(allYears.indexOf(y.y)<0)allYears.push(y.y);});});
  allYears.sort();
  var palette=['#EF4444','#FF8A50','#5CDFA0','#FCDB00','#FF6B9D','#00D4AA','#FF4444','#44AAFF','#FFD700','#FF69B4','#00CED1','#FFA07A','#98FB98','#DDA0DD','#87CEEB','#F0E68C','#CD853F','#8FBC8F','#E6E6FA','#FFDAB9'];
  var datasets=[];
  raceList.forEach(function(r,i){var c=palette[i%palette.length];
    if(gender!=='w'){var mData=allYears.map(function(yr){var yd=r.years.find(function(y){return y.y===yr;});return yd&&yd.m?secToMin(yd.m):null;});datasets.push({label:r.name+(gender==='both'?' (H)':''),data:mData,borderColor:c,backgroundColor:c+'33',pointBackgroundColor:c,pointRadius:4,pointHoverRadius:6,tension:.3,borderWidth:2,spanGaps:true});}
    if(gender!=='m'){var wData=allYears.map(function(yr){var yd=r.years.find(function(y){return y.y===yr;});return yd&&yd.w?secToMin(yd.w):null;});datasets.push({label:r.name+(gender==='both'?' (F)':''),data:wData,borderColor:c,backgroundColor:c+'33',pointBackgroundColor:c,pointRadius:4,pointHoverRadius:6,tension:.3,borderWidth:gender==='both'?1:2,borderDash:gender==='both'?[5,3]:[],spanGaps:true});}
  });
  var allM=[],allW=[];
  filtered.forEach(function(w){var ms=winToSec(w.m),ws=winToSec(w.w);if(ms)allM.push(ms);if(ws)allW.push(ws);});
  allM.sort(function(a,b){return a-b;});allW.sort(function(a,b){return a-b;});
  var mH='';
  if(allM.length){mH+='<div class="metric"><div class="metric-label">Record Homme</div><div class="metric-value" style="color:#60A5FA">'+secToTime(allM[0])+'</div><div class="metric-sub">sur '+allM.length+' courses</div></div>';}
  if(allW.length){mH+='<div class="metric"><div class="metric-label">Record Femme</div><div class="metric-value" style="color:#FF8A50">'+secToTime(allW[0])+'</div><div class="metric-sub">sur '+allW.length+' courses</div></div>';}
  if(allM.length){var avg=allM.reduce(function(a,b){return a+b;},0)/allM.length;mH+='<div class="metric"><div class="metric-label">Moy. Homme</div><div class="metric-value">'+secToTime(avg)+'</div></div>';}
  if(allW.length){var avg=allW.reduce(function(a,b){return a+b;},0)/allW.length;mH+='<div class="metric"><div class="metric-label">Moy. Femme</div><div class="metric-value">'+secToTime(avg)+'</div></div>';}
  mH+='<div class="metric"><div class="metric-label">Courses</div><div class="metric-value">'+raceList.length+'</div><div class="metric-sub">'+filtered.length+' resultats</div></div>';
  document.getElementById('win-metrics').innerHTML=mH;
  var distLabel=dist==='42K'?'Marathon':dist==='21K'?'Semi-marathon':'10 km';
  document.getElementById('win-section-lbl').textContent='Temps des vainqueurs - '+distLabel;
  var legH='';
  raceList.forEach(function(r,i){legH+='<span class="leg-item"><span class="leg-dot" style="background:'+palette[i%palette.length]+'"></span>'+r.name+'</span>';});
  if(gender==='both')legH+='<span class="leg-item" style="margin-left:12px;font-style:italic;color:var(--text3)">&mdash; plein = Homme &middot; - - - = Femme</span>';
  document.getElementById('win-legend').innerHTML=legH;
  if(cW){cW.destroy();cW=null;}
  var ctx=document.getElementById('chart-winners').getContext('2d');
  cW=new Chart(ctx,{type:'line',data:{labels:allYears.map(String),datasets:datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:true},plugins:{legend:{display:false},tooltip:mkTT({title:function(items){return items.length?items[0].dataset.label:'';},label:function(ctx){var v=ctx.parsed.y;if(v==null)return null;var h=Math.floor(v/60),m=Math.floor(v%60),s=Math.round((v*60)%60);return' '+(h?h+':':'')+String(m).padStart(h?2:1,'0')+':'+String(s).padStart(2,'0');}})},scales:{x:{ticks:{color:mkTICK().color,font:{size:11}},grid:{color:mkGRID()}},y:{reverse:true,ticks:{color:mkTICK().color,font:{size:11},callback:function(v){var h=Math.floor(v/60),m=Math.round(v%60);return(h?h+'h':'')+(h?String(m).padStart(2,'0'):m)+'min';}},grid:{color:mkGRID()}}}}});
  // Populate year filter
  var yrSel=document.getElementById('win-year');
  var prevYr=yrSel.value;
  var availYears=[];
  filtered.forEach(function(w){if(availYears.indexOf(w.y)<0)availYears.push(w.y);});
  availYears.sort(function(a,b){return b-a;});
  yrSel.innerHTML=availYears.map(function(y){return'<option value="'+y+'">'+y+'</option>';}).join('');
  if(prevYr&&availYears.indexOf(+prevYr)>=0)yrSel.value=prevYr;
  updateWinnersTable();
}

function updateWinnersTable(){
  var dist=document.getElementById('win-dist').value;
  var yr=+document.getElementById('win-year').value;
  if(!yr)return;
  var filtered=WINNERS.filter(function(w){return w.d===dist&&w.y===yr;});
  filtered.sort(function(a,b){
    var ma=winToSec(a.m)||9999,mb=winToSec(b.m)||9999;
    return ma-mb;
  });
  var tbody=document.getElementById('win-tbody');
  tbody.innerHTML=filtered.map(function(w){
    var ms=winToSec(w.m),ws=winToSec(w.w);
    var gap=(ms&&ws)?secToTime(ws-ms):'\\u2014';
    return'<tr><td>'+w.r+'</td><td style="text-align:center;color:#60A5FA">'+(w.m||'\\u2014')+'</td><td style="text-align:center;color:#FF8A50">'+(w.w||'\\u2014')+'</td><td style="text-align:center;color:var(--text3)">'+gap+'</td></tr>';
  }).join('');
  document.getElementById('win-count').textContent=filtered.length+' courses - '+yr;
}
'''


CSS = """*{box-sizing:border-box;margin:0;padding:0;scrollbar-width:thin;scrollbar-color:#ffffff18 transparent;}
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:#ffffff18;border-radius:999px;}
::-webkit-scrollbar-thumb:hover{background:#DC2626;}
::-webkit-scrollbar-corner{background:transparent;}
:root{--bg:#13131a;--bg2:#1a1a24;--bg3:#1f1f2e;--bg4:#25253a;--border:#25253a;--border2:#303048;--text:#f0f0f5;--text2:#8a8a9a;--text3:#55555f;--purple:#DC2626;--purple2:#EF4444;--yellow:#FCDB00;--accent:#DC2626;}
[data-theme="light"]{--bg:#f8f8f8;--bg2:#ffffff;--bg3:#f0f0f0;--bg4:#e8e8e8;--border:rgba(0,0,0,0.08);--border2:rgba(0,0,0,0.12);--text:#0a0a0a;--text2:#444;--text3:#888;--purple:#DC2626;--purple2:#991B1B;--yellow:#A88F00;--accent:#DC2626;}
[data-theme="light"]{scrollbar-color:rgba(0,0,0,0.15) transparent;}
[data-theme="light"] ::-webkit-scrollbar-thumb{background:rgba(0,0,0,0.15);}
[data-theme="light"] ::-webkit-scrollbar-thumb:hover{background:#DC2626;}
body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,-apple-system,sans-serif;padding:0;-webkit-font-smoothing:antialiased;}
.dash-nav{position:fixed;top:0;left:0;right:0;z-index:200;height:56px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;background:rgba(8,8,8,.75);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-bottom:1px solid var(--border);}
.dash-nav-left{display:flex;align-items:center;gap:14px;}
.dash-nav-logo{height:28px;border-radius:50%;}
.dash-nav-logo-svg{height:40px;width:auto;display:block;color:var(--text);flex-shrink:0;}
[data-theme="light"] .dash-nav-logo-svg{color:#111;}

.dash-nav-sep{width:1px;height:22px;background:var(--border2);}
.dash-nav-title{font-size:15px;font-weight:600;color:var(--text);letter-spacing:0.2px;}
.dash-nav-right{display:flex;align-items:center;gap:12px;}
.dash-body{padding:72px 24px 24px;}
.dp-footer{padding:32px 24px;border-top:1px solid var(--border);text-align:center;margin-top:2rem;}
.dp-footer-logo{height:24px;border-radius:50%;margin:0 auto 12px;}
.dp-footer-links{display:flex;justify-content:center;gap:20px;font-size:12px;color:var(--text3);flex-wrap:wrap;margin-bottom:10px;}
.dp-footer-links a{color:var(--text3);text-decoration:none;transition:color .2s;}
.dp-footer-links a:hover{color:var(--text);}
.dp-footer-copy{font-size:11px;color:var(--text3);}
.ins-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;}
@media(max-width:700px){.ins-grid{grid-template-columns:1fr;}}
.ins-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:1.25rem;}
.ins-card-title{font-size:14px;font-weight:600;margin-bottom:1rem;display:flex;align-items:center;gap:8px;}
.ins-row{display:flex;justify-content:space-between;align-items:center;font-size:13px;transition:background .15s;}
.ins-row:hover{background:rgba(255,255,255,.03);}
.ins-pct-up{color:#22C55E;font-weight:600;}
.ins-pct-down{color:#EF4444;font-weight:600;}
.tabs{display:flex;gap:4px;padding:4px;background:var(--bg2);border-radius:10px;border:1px solid var(--border);overflow-x:auto;scrollbar-width:none;-ms-overflow-style:none;margin-bottom:1.5rem;}
.tabs::-webkit-scrollbar{display:none;}
.tab{padding:8px 16px;font-size:12px;font-weight:500;color:var(--text3);cursor:pointer;border-radius:6px;white-space:nowrap;transition:all .2s;letter-spacing:.02em;}
.tab.active{background:var(--purple);color:#fff;}
.tab:hover:not(.active){color:var(--text);background:var(--bg3);}
.panel{display:none;}.panel.active{display:block;}
.controls{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:1.5rem;align-items:flex-end;}
.ctrl-group{display:flex;flex-direction:column;gap:5px;}
.ctrl-label{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;}
select{font-family:'Inter',system-ui,sans-serif;font-size:12px;padding:7px 12px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text2);cursor:pointer;outline:none;transition:border-color .2s,box-shadow .2s;}
select:focus{border-color:var(--purple);color:var(--text);box-shadow:0 0 0 3px rgba(220,38,38,.1);}
.section-title{font-size:10px;color:var(--text3);margin-bottom:12px;text-transform:uppercase;letter-spacing:.1em;}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;}
.leg-item{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text3);}
.leg-clickable:hover{opacity:0.8;text-decoration:underline;}
.leg-dot{width:8px;height:8px;border-radius:1px;flex-shrink:0;}
.chart-wrap{position:relative;width:100%;margin-bottom:1.5rem;}
.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:10px;}
table{width:100%;border-collapse:collapse;font-size:12px;}
th{background:var(--bg2);padding:7px 12px;text-align:left;font-weight:400;color:var(--text3);font-size:10px;text-transform:uppercase;letter-spacing:.08em;border-bottom:.5px solid var(--border);}
td{padding:7px 12px;border-bottom:.5px solid var(--border);color:var(--text2);height:36px;}
tr:last-child td{border-bottom:none;}
tr:hover td{background:var(--bg2);color:var(--text);}
.badge{font-size:10px;font-weight:500;padding:3px 10px;border-radius:100px;}
.badge-world{background:#DC262618;color:#EF4444;}
.badge-wmm{background:#38BDF818;color:#38BDF8;margin-left:4px;}
.search-wrap{position:relative;flex:1;min-width:160px;}
.search-wrap input{width:100%;font-family:'Inter',system-ui,sans-serif;font-size:13px;padding:8px 12px 8px 30px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text);outline:none;transition:border-color .2s,box-shadow .2s;}
.search-wrap input:focus{border-color:var(--purple);box-shadow:0 0 0 3px rgba(220,38,38,.1);}
.search-wrap input::placeholder{color:var(--text3);}
.search-icon{position:absolute;left:8px;top:50%;transform:translateY(-50%);color:var(--text3);font-size:12px;pointer-events:none;}
.count{font-size:11px;color:var(--text3);margin-top:8px;}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:1.5rem;}
.metric{background:var(--bg2);border-radius:10px;padding:14px 16px;border:1px solid var(--border);}
.metric-label{font-size:10px;font-weight:500;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;}
.metric-value{font-size:22px;font-weight:700;color:var(--text);margin-top:4px;}
.metric-sub{font-size:11px;color:var(--text3);margin-top:2px;}
.time-bar-wrap{margin-bottom:1.5rem;max-height:360px;overflow-y:auto;}
.time-bar-row{display:flex;align-items:center;gap:10px;margin-bottom:5px;cursor:pointer;transition:background .1s;border-radius:4px;padding:2px 4px;}
.time-bar-row:hover{background:var(--bg2);}
.time-bar-rank{font-size:11px;color:#555;font-family:'Courier New',monospace;}
.time-bar-label{font-size:11px;color:var(--text2);width:280px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.time-bar-track{flex:1;background:var(--bg2);border-radius:4px;height:18px;}
.time-bar-fill{height:100%;border-radius:4px;display:flex;align-items:center;justify-content:flex-end;padding-right:6px;font-size:10px;color:#fff;font-weight:500;white-space:nowrap;}
.time-bar-val{font-size:11px;color:var(--text3);min-width:56px;flex-shrink:0;text-align:right;white-space:nowrap;}
.ov-search-wrap{position:relative;margin-bottom:1rem;}
.ov-search-wrap input{width:100%;font-size:13px;padding:8px 12px 8px 32px;border:.5px solid var(--border2);border-radius:4px;background:var(--bg2);color:var(--text);outline:none;}
.ov-search-wrap input:focus{border-color:var(--purple);}
.ov-search-wrap input::placeholder{color:var(--text3);}
.ov-search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--text3);font-size:14px;pointer-events:none;}
.ov-results{border:.5px solid var(--border);border-radius:4px;overflow:hidden;margin-bottom:1.5rem;max-height:220px;overflow-y:auto;}
.ov-result-item{padding:8px 14px;font-size:12px;color:var(--text2);cursor:pointer;border-bottom:.5px solid var(--border);display:flex;align-items:center;gap:10px;transition:background .1s;}
.ov-result-item:last-child{border-bottom:none;}
.ov-result-item:hover,.ov-result-item.selected{background:var(--bg2);color:var(--text);}
.ov-result-item.selected{border-left:2px solid var(--purple);}
.ov-result-dist{font-size:10px;padding:1px 6px;border-radius:2px;flex-shrink:0;}
.ov-placeholder{color:var(--text3);font-size:12px;padding:1.5rem;text-align:center;}
.ov-card{border:1px solid var(--border);border-radius:10px;padding:1.25rem;margin-bottom:1.5rem;background:var(--bg2);}
.ov-card-header{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:1.25rem;flex-wrap:wrap;}
.ov-card-title{font-size:16px;font-weight:500;letter-spacing:-.2px;}
.ov-card-meta{font-size:12px;color:var(--text3);margin-top:4px;display:flex;gap:12px;flex-wrap:wrap;}
.ov-badge{font-size:10px;padding:2px 8px;border-radius:2px;font-weight:400;flex-shrink:0;}
.ov-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:1.25rem;}
.ov-stat{background:var(--bg3);border-radius:4px;padding:10px 12px;border:.5px solid var(--border);}
.ov-stat-label{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.07em;}
.ov-stat-value{font-size:16px;font-weight:500;margin-top:3px;}
.ov-charts{display:grid;grid-template-columns:1fr 1fr;gap:1rem;}
@media(max-width:560px){.ov-charts{grid-template-columns:1fr;}}
.ov-chart-box{background:var(--bg3);border:.5px solid var(--border);border-radius:4px;padding:12px;}
.ov-chart-label{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;}
.cmp-search-row{display:grid;grid-template-columns:1fr 48px 1fr;gap:12px;align-items:flex-start;margin-bottom:1.5rem;}
.cmp-vs{text-align:center;font-size:11px;font-weight:500;color:var(--text3);letter-spacing:.1em;padding-top:8px;}
.cmp-search-box{position:relative;}
.cmp-input{width:100%;font-size:12px;padding:7px 10px 7px 28px;border:.5px solid var(--border2);border-radius:4px;background:var(--bg2);color:var(--text);outline:none;}
.cmp-input:focus{border-color:var(--purple);}
.cmp-input::placeholder{color:var(--text3);}
.cmp-search-icon{position:absolute;left:9px;top:9px;color:var(--text3);font-size:12px;pointer-events:none;z-index:1;}
.cmp-dropdown{border:.5px solid var(--border2);border-radius:4px;background:var(--bg2);margin-top:4px;overflow:hidden;max-height:180px;overflow-y:auto;position:absolute;width:100%;z-index:10;}
.cmp-drop-item{padding:7px 10px;font-size:12px;color:var(--text2);cursor:pointer;display:flex;align-items:center;gap:8px;border-bottom:.5px solid var(--border);}
.cmp-drop-item:last-child{border-bottom:none;}
.cmp-drop-item:hover{background:var(--bg3);color:var(--text);}
.cmp-dist-pill{font-size:10px;padding:1px 6px;border-radius:2px;flex-shrink:0;}
.cmp-wrap{border:.5px solid var(--border2);border-radius:6px;overflow:hidden;}
.cmp-header{display:grid;grid-template-columns:1fr 160px 1fr;background:var(--bg2);}
.cmp-header-cell{padding:14px 16px;}
.cmp-header-cell.ctr{text-align:center;border-left:.5px solid var(--border);border-right:.5px solid var(--border);}
.cmp-race-name{font-size:13px;font-weight:500;color:var(--text);line-height:1.3;}
.cmp-race-meta{font-size:11px;color:var(--text3);margin-top:3px;}
.cmp-row{display:grid;grid-template-columns:1fr 160px 1fr;border-top:.5px solid var(--border);}
.cmp-row:hover .cmp-cell,.cmp-row:hover .cmp-mid{background:var(--bg3);}
.cmp-cell{padding:12px 16px;display:flex;align-items:center;gap:6px;}
.cmp-cell.r{justify-content:flex-end;}
.cmp-mid{padding:12px 16px;display:flex;align-items:center;justify-content:center;border-left:.5px solid var(--border);border-right:.5px solid var(--border);background:var(--bg2);}
.cmp-mid-label{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;text-align:center;}
.cmp-val-win{font-size:16px;font-weight:700;}
.cmp-val-lose{font-size:14px;font-weight:500;color:var(--text3);}
.cmp-bar{display:none;}
.cmp-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0;}
.cmp-row-win-a .cmp-cell:first-child{border-left:2px solid var(--cmp-col-a,var(--purple));}
.cmp-row-win-b .cmp-cell:last-child{border-right:2px solid var(--cmp-col-b,var(--purple));}
.cmp-input{height:34px;font-size:13px;padding:6px 10px 6px 28px;}
.cmp-sub{font-size:11px;color:var(--text3);margin-top:2px;}
.cmp-placeholder{color:var(--text3);font-size:12px;padding:2rem;text-align:center;border:.5px solid var(--border);border-radius:6px;}
#data-table.tbl-frozen{table-layout:fixed;width:max-content;min-width:100%;}
#data-table.tbl-frozen td.frozen-cell,#data-table.tbl-frozen th.frozen-cell{background:var(--bg);}
#data-table.tbl-frozen tr:hover td.frozen-cell{background:var(--bg2);}
#data-table.tbl-frozen th:not(.frozen-cell),#data-table.tbl-frozen td:not(.frozen-cell){min-width:58px;width:58px;text-align:center;font-size:11px;padding:7px 6px;}
#data-table.tbl-frozen td:not(.frozen-cell){white-space:nowrap;}
.theme-toggle{background:var(--bg2);border:.5px solid var(--border);border-radius:20px;padding:4px 10px;cursor:pointer;font-size:13px;display:flex;align-items:center;gap:6px;color:var(--text2);transition:all .2s;user-select:none;}
.theme-toggle:hover{color:var(--text);border-color:var(--purple);}
.export-btn-wrap{position:relative;}
.export-menu{position:absolute;top:34px;right:0;background:var(--bg2);border:.5px solid var(--border);border-radius:8px;padding:4px 0;min-width:140px;box-shadow:0 4px 16px rgba(0,0,0,0.25);z-index:1000;}
.export-menu-item{padding:8px 14px;cursor:pointer;font-size:13px;color:var(--text2);transition:all .15s;user-select:none;}
.export-menu-item:hover{background:var(--bg3);color:var(--text);}
[data-theme="light"] .export-menu{box-shadow:0 4px 16px rgba(0,0,0,0.1);}
/* ── Light mode: global ── */
[data-theme="light"] body{background:var(--bg);}
[data-theme="light"] .dash-nav{background:rgba(248,248,248,0.85);border-bottom-color:var(--border);}
[data-theme="light"] .dash-nav-logo{filter:none;}
[data-theme="light"] .dash-nav-sep{background:var(--border2);}
[data-theme="light"] .theme-toggle{background:var(--bg3);border-color:var(--border);color:var(--text2);}
/* ── Light mode: tabs ── */
[data-theme="light"] .tabs{background:var(--bg3);border-color:var(--border);}
[data-theme="light"] .tab:hover:not(.active){background:var(--bg4);}
/* ── Light mode: inputs ── */
[data-theme="light"] select{background:var(--bg2);border-color:var(--border);color:var(--text2);}
[data-theme="light"] .search-wrap input,[data-theme="light"] .ov-search-wrap input,[data-theme="light"] .cmp-input{background:var(--bg2);border-color:var(--border);color:var(--text);}
/* ── Light mode: table ── */
[data-theme="light"] th{background:var(--bg3);}
[data-theme="light"] tr:hover td{background:var(--bg3);}
[data-theme="light"] #data-table.tbl-frozen td.frozen-cell,[data-theme="light"] #data-table.tbl-frozen th.frozen-cell{background:var(--bg);}
[data-theme="light"] #data-table.tbl-frozen tr:hover td.frozen-cell{background:var(--bg3);}
/* ── Light mode: metrics ── */
[data-theme="light"] .metric{background:var(--bg2);border-color:var(--border);}
[data-theme="light"] .ov-stat{background:var(--bg2) !important;border-color:var(--border);}
/* ── Light mode: cards ── */
[data-theme="light"] .ov-card{background:var(--bg2);border-color:var(--border);}
[data-theme="light"] .ov-chart-box{background:var(--bg3);border-color:var(--border);}
[data-theme="light"] .ins-card{background:var(--bg2);border-color:var(--border);}
/* ── Light mode: compare ── */
[data-theme="light"] .cmp-mid{background:var(--bg3);}
[data-theme="light"] .cmp-dropdown{background:var(--bg2);}
/* ── Light mode: bars ── */
[data-theme="light"] .time-bar-track{background:var(--bg3);}
[data-theme="light"] .leg-item{color:var(--text2);}
/* ── Light mode: badges ── */
[data-theme="light"] .badge-world{background:#DC262615;color:#991B1B;}
[data-theme="light"] .badge-wmm{background:#0284C715;color:#025E87;}
.sp-kpis{display:flex;gap:12px;margin-bottom:18px;}
.sp-kpi{flex:1;background:var(--bg2);border-radius:10px;padding:14px 18px;border:.5px solid var(--border);}
.sp-kpi-num{font-size:1.8rem;font-weight:700;line-height:1;}
.sp-kpi-lbl{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;margin-top:4px;}
.sp-layout{display:grid;grid-template-columns:300px 1fr;gap:12px;height:calc(100vh - 240px);min-height:460px;}
.sp-sidebar{display:flex;flex-direction:column;gap:7px;overflow:hidden;background:var(--bg2);border-radius:10px;padding:12px;border:.5px solid var(--border);min-height:0;}
.sp-search-inp{width:100%;padding:7px 10px;background:var(--bg);border:1px solid var(--border);border-radius:7px;color:var(--text);font-size:12px;outline:none;}
.sp-search-inp:focus{border-color:var(--purple);}
.sp-pills{display:flex;flex-wrap:wrap;gap:3px;flex-shrink:0;max-height:200px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border) transparent;}
.sp-pills::-webkit-scrollbar{width:3px;}
.sp-pills::-webkit-scrollbar-track{background:transparent;}
.sp-pills::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
.sp-pill{padding:3px 8px;border-radius:20px;font-size:10px;cursor:pointer;background:var(--bg);color:var(--text3);border:1px solid var(--border);transition:.15s;white-space:nowrap;}
.sp-pill:hover{color:var(--text);}
.sp-pill.spc-active{color:#fff!important;border-color:transparent!important;}
[data-theme="light"] .sp-pill[data-si="0"].spc-active{background:#000!important;}
.sp-list-title{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;}
.sp-blist{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:1px;scrollbar-width:thin;scrollbar-color:var(--border) transparent;}
.sp-blist::-webkit-scrollbar{width:4px;}
.sp-blist::-webkit-scrollbar-track{background:transparent;}
.sp-blist::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px;}
.sp-blist::-webkit-scrollbar-thumb:hover{background:var(--text3);}
.sp-bitem{display:flex;align-items:center;gap:7px;padding:6px 8px;border-radius:7px;cursor:pointer;transition:.12s;}
.sp-bitem:hover,.sp-bitem.spc-active{background:var(--bg);}
.sp-bdot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.sp-bname{flex:1;font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sp-bexp{font-size:11px;color:var(--text3);flex-shrink:0;}
.sp-right{display:flex;flex-direction:column;gap:10px;overflow-y:auto;overflow-x:hidden;scrollbar-width:thin;scrollbar-color:var(--border) transparent;}
.sp-treemap{position:relative;border-radius:10px;overflow:hidden;background:var(--bg2);border:.5px solid var(--border);min-height:280px;height:calc(100vh - 420px);flex-shrink:0;}
.sp-treemap-hint{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:12px;color:var(--text3);pointer-events:none;transition:opacity .3s;}
.sp-detail{background:var(--bg2);border-radius:10px;padding:16px 20px;display:none;gap:20px;align-items:flex-start;flex-wrap:wrap;border:.5px solid var(--border);min-height:110px;flex-shrink:0;}
.sp-detail-name{font-size:1.3rem;font-weight:700;margin-bottom:4px;}
.sp-detail-badge{font-size:11px;padding:2px 10px;border-radius:20px;display:inline-block;margin-bottom:6px;}
.sp-detail-stat{text-align:center;}
.sp-detail-stat-num{font-size:1.5rem;font-weight:700;}
.sp-detail-stat-lbl{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;}
.sp-evtag{font-size:10px;padding:2px 7px;background:var(--bg);border-radius:4px;color:var(--text2);}
/* ── Light mode: sponsoring ── */
[data-theme="light"] .sp-kpi{background:var(--bg2);border-color:var(--border);}
[data-theme="light"] .sp-sidebar{background:var(--bg3);border-color:var(--border);}
[data-theme="light"] .sp-search-inp{background:var(--bg2);border-color:var(--border);}
[data-theme="light"] .sp-treemap{border-color:var(--border);background:var(--bg3);}
[data-theme="light"] .sp-detail{border-color:var(--border);background:var(--bg3);}
[data-theme="light"] .sp-pill{background:var(--bg2);border-color:var(--border);}
[data-theme="light"] .sp-bitem:hover,[data-theme="light"] .sp-bitem.spc-active{background:var(--bg2);}
/* ── Light mode: footer ── */
[data-theme="light"] .dp-footer{border-color:var(--border);}
[data-theme="light"] .dp-footer-logo{filter:none;}
/* ── Light mode: insights ── */
[data-theme="light"] .ins-row:hover{background:rgba(0,0,0,0.03);}"""

HTML_BODY = """
<nav class="dash-nav">
  <div class="dash-nav-left">
    <svg class="dash-nav-logo-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 88" role="img" aria-label="A.S.O. Amaury Sport Organisation">
      <text x="4" y="60" font-family="'Arial Black', Impact, Arial, sans-serif" font-weight="900" font-style="italic" font-size="64" letter-spacing="-2" fill="#E30613">A.S.O.</text>
      <text x="4" y="80" font-family="'Arial Black', Arial, sans-serif" font-weight="900" font-size="11" letter-spacing="0.5" fill="currentColor"><tspan fill="#E30613">A</tspan>MAURY <tspan fill="#E30613">S</tspan>PORT <tspan fill="#E30613">O</tspan>RGANISATION</text>
    </svg>
    <span class="dash-nav-sep"></span>
    <span class="dash-nav-title">Dashboard Running</span>
  </div>
  <div class="dash-nav-right">
    <div class="export-btn-wrap">
      <div class="theme-toggle" onclick="toggleExportMenu(event)" id="export-btn" title="Exporter la vue actuelle en PNG ou PDF">&#x2913; Exporter</div>
      <div id="export-menu" class="export-menu" style="display:none">
        <div class="export-menu-item" onclick="exportPanel('png')">Image PNG</div>
        <div class="export-menu-item" onclick="exportPanel('pdf')">Document PDF</div>
      </div>
    </div>
    <div class="theme-toggle" onclick="toggleTheme()" id="theme-btn" title="Changer le theme">&#x263E; Dark</div>
  </div>
</nav>
<div class="dash-body">
<div class="tabs">
  <div class="tab active" onclick="switchTab('data')">Tableau</div>
  <div class="tab" onclick="switchTab('overview')">Vue d'ensemble</div>
  <div class="tab" onclick="switchTab('compare')">Comparer</div>
  <div class="tab" onclick="switchTab('trends')">Evolution</div>
  <div class="tab" onclick="switchTab('biggest')">Top evenements</div>
  <div class="tab" onclick="switchTab('temps')">Temps moyen</div>
  <div class="tab" onclick="switchTab('winners')">Winners Times</div>
  <div class="tab" onclick="switchTab('sponsoring')">Sponsoring</div>
</div>
<!-- Insights panel removed (ASO version) -->
<div id="panel-overview" class="panel">
  <div class="ov-search-wrap"><span class="ov-search-icon">&#x2315;</span>
    <input type="text" id="ov-search" placeholder="Rechercher un evenement..." oninput="ovSearch()" autocomplete="off">
  </div>
  <div id="ov-results" class="ov-results"><div class="ov-placeholder">Tapez le nom d'un evenement pour commencer</div></div>
  <div id="ov-card-wrap"></div>
</div>
<div id="panel-compare" class="panel">
  <div class="cmp-search-row">
    <div class="cmp-search-box">
      <span class="cmp-search-icon">&#x2315;</span>
      <input type="text" id="cmp-input-a" class="cmp-input" placeholder="Rechercher evenement A..." oninput="cmpSearch('a')" autocomplete="off">
      <div id="cmp-drop-a" class="cmp-dropdown" style="display:none"></div>
    </div>
    <div class="cmp-vs">VS</div>
    <div class="cmp-search-box">
      <span class="cmp-search-icon">&#x2315;</span>
      <input type="text" id="cmp-input-b" class="cmp-input" placeholder="Rechercher evenement B..." oninput="cmpSearch('b')" autocomplete="off">
      <div id="cmp-drop-b" class="cmp-dropdown" style="display:none"></div>
    </div>
  </div>
  <div id="cmp-result"></div>
</div>
<div id="panel-trends" class="panel">
  <div class="controls">
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="dist-trends" onchange="updateTrends()">
        <option value="ALL">Toutes distances</option>
        <option value="MARATHON">Marathon</option><option value="SEMI">Semi-marathon</option><option value="10KM">10 km</option><option value="AUTRE">Autre</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">R&eacute;gion</span>
      <select id="region-trends" onchange="updateTrends()">
        <option value="ALL">Toutes</option><option>Europe</option><option>Am&eacute;rique du Nord</option><option>Asie</option><option>Oc&eacute;anie</option><option>Moyen-Orient</option><option>Am&eacute;rique du Sud</option><option>Afrique</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Top evenements</span>
      <select id="topn-trends" onchange="updateTrends()">
        <option value="8">Top 8</option><option value="12">Top 12</option><option value="16">Top 16</option><option value="20">Top 20</option>
      </select>
    </div>
  </div>
  <div class="section-title" id="trends-section-lbl">EVOLUTION</div>
  <div class="legend" id="trends-legend">
    <span class="leg-item"><span class="leg-dot" style="background:#60A5FA"></span>Marathon</span>
    <span class="leg-item"><span class="leg-dot" style="background:#FF8A50"></span>Semi-marathon</span>
    <span class="leg-item"><span class="leg-dot" style="background:#5CDFA0"></span>10 km</span>
    <span class="leg-item"><span class="leg-dot" style="background:#F472B6"></span>Autre</span>
  </div>
  <div class="chart-wrap" style="height:380px;"><canvas id="chart-trends"></canvas></div>
</div>
<div id="panel-biggest" class="panel">
  <div class="controls">
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="dist-biggest" onchange="initBiggestYears();updateBiggest()">
        <option value="ALL">Toutes distances</option>
        <option value="MARATHON">Marathon</option><option value="SEMI">Semi-marathon</option><option value="10KM">10 km</option><option value="AUTRE">Autre</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">R&eacute;gion</span>
      <select id="region-biggest" onchange="initBiggestYears();updateBiggest()">
        <option value="ALL">Toutes</option><option>Europe</option><option>Am&eacute;rique du Nord</option><option>Asie</option><option>Oc&eacute;anie</option><option>Moyen-Orient</option><option>Am&eacute;rique du Sud</option><option>Afrique</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Top N</span>
      <select id="topn-biggest" onchange="updateBiggest()">
        <option value="10">Top 10</option><option value="15">Top 15</option><option value="20">Top 20</option><option value="999">Tous</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Annee</span>
      <select id="year-biggest" onchange="updateBiggest()"></select>
    </div>
  </div>
  <div class="section-title">Top evenements par nombre de finishers</div>
  <div class="legend">
    <span class="leg-item"><span class="leg-dot" style="background:#2563EB"></span>Marathon</span>
    <span class="leg-item"><span class="leg-dot" style="background:#FF8A50"></span>Semi-marathon</span>
    <span class="leg-item"><span class="leg-dot" style="background:#5CDFA0"></span>10 km</span>
    <span class="leg-item"><span class="leg-dot" style="background:#F472B6"></span>Autre</span>
  </div>
  <div class="time-bar-wrap" id="biggest-bars" style="max-height:none"></div>
</div>
<div id="panel-temps" class="panel">
  <div class="controls">
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="dist-temps" onchange="updateTempsYears();updateTemps()">
        <option value="MARATHON">Marathon</option><option value="SEMI">Semi-marathon</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">R&eacute;gion</span>
      <select id="region-temps" onchange="updateTemps()">
        <option value="ALL">Toutes</option><option>Europe</option><option>Am&eacute;rique du Nord</option><option>Asie</option><option>Oc&eacute;anie</option><option>Moyen-Orient</option><option>Am&eacute;rique du Sud</option><option>Afrique</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Annee</span>
      <select id="year-temps" onchange="updateTemps()">
        <option value="2025">2025</option><option value="2024">2024</option><option value="2026">2026</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Tri</span>
      <select id="sort-temps" onchange="updateTemps()">
        <option value="avg">Temps moyen (croissant)</option><option value="finishers">Finishers (decroissant)</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Top N</span>
      <select id="topn-temps" onchange="updateTemps()">
        <option value="15">Top 15</option><option value="25">Top 25</option><option value="999">Tous</option>
      </select>
    </div>
  </div>
  <div class="metrics" id="metrics-temps"></div>
  <div class="section-title">Temps moyen par course</div>
  <div style="font-size:10px;color:var(--text3);margin-bottom:12px">Barre la plus longue = course la plus rapide</div>
  <div class="time-bar-wrap" id="time-bars"></div>
</div>
<div id="panel-winners" class="panel">
  <div class="controls">
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="win-dist" onchange="updateWinners()">
        <option value="42K">Marathon (42K)</option><option value="21K">Semi-marathon (21K)</option><option value="10K">10 km</option><option value="AUTRE">Autre</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">R&eacute;gion</span>
      <select id="region-winners" onchange="updateWinners()">
        <option value="ALL">Toutes</option><option>Europe</option><option>Am&eacute;rique du Nord</option><option>Asie</option><option>Oc&eacute;anie</option><option>Moyen-Orient</option><option>Am&eacute;rique du Sud</option><option>Afrique</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Genre</span>
      <select id="win-gender" onchange="updateWinners()">
        <option value="both">Homme &amp; Femme</option><option value="m">Homme</option><option value="w">Femme</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Tri</span>
      <select id="win-sort" onchange="updateWinners()">
        <option value="fastest">Plus rapide (derniere annee)</option><option value="alpha">Alphabetique</option><option value="progress">Meilleure progression</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Nb courses</span>
      <select id="win-topn" onchange="updateWinners()">
        <option value="8">8</option><option value="12" selected>12</option><option value="16">16</option><option value="999">Toutes</option>
      </select>
    </div>
  </div>
  <div class="metrics" id="win-metrics"></div>
  <div class="section-title" id="win-section-lbl">Temps des vainqueurs - Marathon</div>
  <div class="legend" id="win-legend"></div>
  <div class="chart-wrap" style="height:420px;"><canvas id="chart-winners"></canvas></div>
  <div style="display:flex;align-items:center;gap:12px;margin-top:1.5rem;margin-bottom:12px">
    <span class="section-title" style="margin:0">Classement detaille</span>
    <select id="win-year" onchange="updateWinnersTable()" style="font-size:11px;padding:3px 8px;"></select>
  </div>
  <div class="table-wrap" style="max-height:400px;overflow-y:auto">
    <table><thead><tr><th>Course</th><th>Homme</th><th>Femme</th><th>Ecart H/F</th></tr></thead>
    <tbody id="win-tbody"></tbody></table>
  </div>
  <div class="count" id="win-count"></div>
</div>
<div id="panel-sponsoring" class="panel">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px">
    <div class="sp-kpis" id="sp-kpis" style="margin-bottom:0"></div>
    <div class="ctrl-group"><span class="ctrl-label">Periode</span>
      <select id="sp-period" onchange="spChangePeriod(this.value)" style="font-size:11px;padding:4px 8px;">
        <option value="2026">2026</option>
        <option value="2025">2025</option>
        <option value="3">3 dernieres annees</option>
        <option value="5">5 dernieres annees</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">R&eacute;gion</span>
      <select id="sp-region" onchange="spChangePeriod(document.getElementById('sp-period').value)" style="font-size:11px;padding:4px 8px;">
        <option value="ALL">Toutes</option><option>Europe</option><option>Am&eacute;rique du Nord</option><option>Asie</option><option>Oc&eacute;anie</option><option>Moyen-Orient</option><option>Am&eacute;rique du Sud</option><option>Afrique</option>
      </select>
    </div>
  </div>
  <div class="sp-layout">
    <div class="sp-sidebar">
      <input class="sp-search-inp" id="sp-search-inp" type="text" placeholder="&#x2315; Rechercher une marque...">
      <div class="sp-pills" id="sp-pills"></div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:4px;margin-bottom:2px">
        <div class="sp-list-title">Marques</div>
        <div style="display:flex;gap:1px;font-size:9px">
          <span class="sp-sort-btn spc-active" data-sort="brands" onclick="spSetListMode('brands')" style="cursor:pointer;padding:1px 5px;border-radius:3px">Marques</span>
          <span class="sp-sort-btn" data-sort="categories" onclick="spSetListMode('categories')" style="cursor:pointer;padding:1px 5px;border-radius:3px;color:var(--text3)">Cat&eacute;gories</span>
        </div>
      </div>
      <div class="sp-blist" id="sp-blist"></div>
    </div>
    <div class="sp-right">
      <div class="sp-treemap" id="sp-treemap">
        <div class="sp-treemap-hint" id="sp-treemap-hint"></div>
      </div>
      <div class="sp-detail" id="sp-detail"></div>
    </div>
  </div>
</div>
<div id="panel-data" class="panel active">
  <div class="controls">
    <div class="search-wrap"><span class="search-icon">&#x2315;</span>
      <input type="text" id="search-data" placeholder="Rechercher... (Ctrl+K)" oninput="filterTable()">
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="dist-data" onchange="filterTable()">
        <option value="ALL">Toutes</option><option value="MARATHON">Marathon</option><option value="SEMI">Semi</option><option value="10KM">10 km</option><option value="AUTRE">Autre</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Mois</span>
      <select id="month-data" onchange="filterTable()">
        <option value="ALL">Tous</option>
        <option>Janvier</option><option>Fevrier</option><option>Mars</option><option>Avril</option>
        <option>Mai</option><option>Juin</option><option>Juillet</option><option>Aout</option>
        <option>Septembre</option><option>Octobre</option><option>Novembre</option><option>Decembre</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">R&eacute;gion</span>
      <select id="region-data" onchange="filterTable()">
        <option value="ALL">Toutes</option><option>Europe</option><option>Am&eacute;rique du Nord</option><option>Asie</option><option>Oc&eacute;anie</option><option>Moyen-Orient</option><option>Am&eacute;rique du Sud</option><option>Afrique</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Circuit</span>
      <select id="badge-data" onchange="filterTable()">
        <option value="ALL">Tous</option><option value="WMM">WMM</option><option value="EMC">EMC</option><option value="RNR">RNR</option><option value="L5G">L5G</option><option value="NONE">Sans circuit</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Taille</span>
      <select id="size-data" onchange="filterTable()">
        <option value="ALL">Toutes</option><option value="20000">20 000+</option><option value="10000">10-20k</option><option value="5000">5-10k</option><option value="0">&lt; 5 000</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Tri</span>
      <select id="sort-data" onchange="filterTable()">
        <option value="finishers" selected>Finishers (decroissant)</option>
        <option value="default">Par defaut</option>
        <option value="month">Par mois</option>
        <option value="distance">Par distance</option>
        <option value="trend">Meilleure tendance</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Periode</span>
      <select id="afficher-data" onchange="filterTable()">
        <option value="3">3 dernieres annees</option>
        <option value="5">5 dernieres annees</option>
        <option value="10">10 dernieres annees</option>
        <option value="all">Historique complet</option>
      </select>
    </div>
  </div>
  <div class="table-wrap">
    <table id="data-table">
      <thead><tr id="table-head-row"><th>Mois</th><th>Ville</th><th>Distance</th><th>Epreuve</th><th>Tendance</th></tr></thead>
      <tbody id="table-body"></tbody>
    </table>
  </div>
  <div class="count" style="display:flex;align-items:center;gap:10px"><span id="table-count"></span><a id="reset-filters" href="javascript:void(0)" onclick="resetFilters()" style="display:none;align-items:center;gap:4px;font-size:11px;color:var(--accent);text-decoration:none;cursor:pointer">\u21BA Reinitialiser les filtres</a></div>
</div>
</div><!-- /dash-body -->
<footer class="dp-footer">
  <div class="dp-footer-links"><!-- ASO internal -->
  </div>
  <div class="dp-footer-copy">ASO &middot; Running Data &middot; 2026</div>
</footer>"""


def load_sponsoring():
    """Load sponsoring data from JSON file."""
    path = SCRIPT_DIR / "sponsoring_data.json"
    if not path.exists():
        return {"brands": {}, "partnerships": []}
    import json as jlib
    with open(path, "r", encoding="utf-8") as f:
        return jlib.load(f)


def generate_html(finishers, biggest, md, sd, tdb, winners):
    now = datetime.datetime.now().strftime("%d/%m/%Y a %H:%M")
    tmjs = {str(yr): [{"race": r["race"], "city": r["city"], "finishers": r["finishers"] or 0, "avg": r["avg"] or ""}
                       for r in rows if r.get("avg")] for yr, rows in md.items()}
    tsjs = {str(yr): [{"race": r["race"], "city": r["city"], "finishers": r["finishers"] or 0, "avg": r["avg"] or ""}
                       for r in rows if r.get("avg")] for yr, rows in sd.items()}
    tdbjs = {k: {"men": v["men"], "women": v["women"], "avg": v["avg"], "yr": v["yr"]} for k, v in tdb.items()}
    # Load Sporthive average times
    sp_avg = load_sporthive_avg()
    sp_avg_js = [{"race": r["race"], "yr": r["year"], "avg": r["avg"]} for r in sp_avg]
    # Load sponsoring data
    spdata = load_sponsoring()
    js_data = ("const RAW=" + j(finishers) + ";\nconst BIGGEST=" + j(biggest) + ";\n"
               "const TEMPS_MARATHON=" + j(tmjs) + ";\nconst TEMPS_SEMI=" + j(tsjs) + ";\n"
               "const TEMPS_AVG=" + j(sp_avg_js) + ";\n"
               "const TIMES_DB=" + j(tdbjs) + ";\n"
               "const WMM_KEYWORDS=" + j(WMM_KEYWORDS) + ";\n"
               "const WINNERS=" + j(winners) + ";\n"
               "const SP_BRANDS=" + j(spdata.get("brands", {})) + ";\n"
               "const SP_PARTNERSHIPS=" + j(spdata.get("partnerships", [])) + ";\n")
    body = HTML_BODY.format(now=now)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ASO &mdash; Running Data Dashboard</title>
<meta name="description" content="Dashboard interactif de 186+ evenements running mondiaux : finishers, temps moyens, chronos vainqueurs, sponsoring. 2000-2026.">
<meta property="og:title" content="ASO — Running Data Dashboard">
<meta property="og:description" content="Dashboard interne ASO : finishers, temps moyens, chronos vainqueurs, sponsoring.">
<meta property="og:type" content="website">
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="X-Frame-Options" content="SAMEORIGIN">
<meta name="referrer" content="strict-origin-when-cross-origin">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
{body}
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js" integrity="sha384-dug+JxfBvklEQdJ4AYuBBAIScUz0bVN73xpy273gcAwHjb3qI0fXmuYNaNfdyYJG" crossorigin="anonymous"></script>
<script>
{js_data}
{JS_LOGIC}
</script>
</body>
</html>"""


def main():
    print("\nASO Dashboard Generator (internal)")
    print("-" * 40)

    use_db = _DB_PATH.exists() and _DB_PATH.stat().st_size > 0

    if use_db:
        print(f"Source : SQLite ({_DB_PATH.name})")
        from datapace.data_loader import load_all
        print("\nLecture des donnees (SQLite)...")
        finishers, biggest, md, sd, tdb, winners, sp_avg = load_all(_DB_PATH)
        # Add region and circuit fields to finishers and biggest
        for row in finishers:
            row["rg"] = get_region(row.get("c", ""))
            row["ci"] = compute_circuits(row.get("r", ""), row.get("d", ""), row.get("c", ""))
        for row in biggest:
            row["rg"] = get_region(row.get("c", ""))
            row["ci"] = compute_circuits(row.get("r", ""), row.get("d", ""), row.get("c", ""))
    else:
        print("Source : fichiers Excel (pas de BDD trouvee)")
        check_files()
        print("\nLecture des donnees (Excel)...")
        finishers = load_finishers()
        biggest = load_biggest()
        md = {yr: load_marathon(yr) for yr in [2024, 2025, 2026]}
        sd = load_semi()
        tdb = build_times_db(md, sd)
        winners = load_winners()

    print("\nGeneration du HTML...")
    html = generate_html(finishers, biggest, md, sd, tdb, winners)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"\nDashboard genere : {OUTPUT_FILE.name}  ({OUTPUT_FILE.stat().st_size // 1024} Ko)")
    print("Ouvre ce fichier dans le navigateur via http://localhost:8000/datapace_dashboard.html\n")


if __name__ == "__main__":
    main()

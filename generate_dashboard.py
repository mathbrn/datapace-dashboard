#!/usr/bin/env python3
"""
DataPace Dashboard Generator
=============================
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

ASO_KEYWORDS = [
    "schneider electric", "hoka semi de paris", "semi de paris",
    "run in lyon", "beaujolais", "adidas 10k paris", "10k montmartre",
    "cancer research", "asics ldnx", "adidas manchester",
]

WMM_KEYWORDS = [
    "tcs new york city marathon", "tcs london marathon", "boston marathon",
    "tcs sydney marathon", "bmw berlin marathon",
    "bank of america chicago marathon", "tokyo marathon",
]


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
        rows.append({"p": str(r.get("Période", "")).strip(), "c": str(r.get("City", "")).strip(),
                     "d": str(r.get("Distance", "")).strip(), "r": race,
                     "y3": gv(2023), "y4": gv(2024), "y5": gv(2025), "y6": gv(2026),
                     "hist": hist, "fy": first_yr})
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
        rows.append({"c": str(r.get("City", "")).strip(), "r": race,
                     "y3": gv(2023), "y4": gv(2024), "y5": gv(2025), "y6": gv(2026),
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


JS_LOGIC = '''function isAso(r){var l=r.toLowerCase();return ASO_KEYWORDS.some(function(k){return l.indexOf(k)>=0;});}
function isWmm(r){var l=r.toLowerCase();return WMM_KEYWORDS.some(function(k){return l.indexOf(k)>=0;});}
function isLight(){return document.documentElement.hasAttribute('data-theme');}
var LIGHT_MAP={'#38BDF8':'#0B7BC0','#FCDB00':'#A88F00','#5C00D4':'#4800A8','#9B6FFF':'#6B3FCC','#FF8A50':'#CC5A20','#5CDFA0':'#2BA368','#F472B6':'#C04080','#FF4A6B':'#CC2040','#22C55E':'#1A8A42','#2DBF7E':'#1F8A5A','#FF6B9D':'#CC3870'};
function lc(c){return isLight()?(LIGHT_MAP[c]||c):c;}
function col(r){return lc(isWmm(r)?'#38BDF8':isAso(r)?'#FCDB00':'#5C00D4');}
function colDist(r){return lc(isWmm(r.r)?'#38BDF8':isAso(r.r)?'#FCDB00':r.d==='10KM'?'#5CDFA0':r.d==='SEMI'?'#FF8A50':r.d==='AUTRE'?'#F472B6':'#9B6FFF');}
function colByName(name){var r=RAW.find(function(x){return x.r===name;});return r?colDist(r):lc('#9B6FFF');}
function toMin(t){if(!t)return null;var p=String(t).split(':');if(p.length===3)return parseInt(p[0])*60+parseInt(p[1])+parseInt(p[2])/60;return null;}
function fmt(n){if(n===-1)return'Annul\u00e9';if(n===-2)return'Elite';if(n===-3)return'';if(!n||isNaN(n))return'\u2014';return n>=1000?(n/1000).toFixed(1)+'k':n.toString();}
function fmtFull(n){if(n===-1)return'Annul\u00e9';if(n===-2)return'Elite Only';if(n===-3)return'';if(!n||isNaN(n))return'\u2014';return Math.round(n).toLocaleString('fr-FR');}
function delta(a,b){if(!a||!b||isNaN(a)||isNaN(b))return null;return((b-a)/a*100);}
function fmtHM(mins){var h=Math.floor(mins/60),m=Math.round(mins%60);return h+'h'+String(m).padStart(2,'0');}
function fmtHMMin(mins){return fmtHM(mins)+'min';}
function csVar(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim();}
function mkGRID(){return isLight()?csVar('--border'):'rgba(255,255,255,0.04)';}
function mkTICK(){return{color:csVar('--text3'),font:{size:11}};}
function mkTT(){var isDark=!document.documentElement.hasAttribute('data-theme');return{backgroundColor:isDark?'#161b22':'#ffffff',borderColor:csVar('--border'),borderWidth:1,titleColor:csVar('--text2'),bodyColor:csVar('--text'),padding:10};}
function mkBorder(){return isLight()?csVar('--border'):'rgba(255,255,255,0.03)';}
var GRID=mkGRID();
var TICK=mkTICK();
var TT=mkTT();


function getTimeData(rn){
  var l=rn.toLowerCase();
  var keys=Object.keys(TIMES_DB);
  for(var i=0;i<keys.length;i++){var k=keys[i];if(l.indexOf(k)>=0||k.indexOf(l.substring(0,12))>=0)return TIMES_DB[k];}
  return null;
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
  if(name==='sponsoring'&&!window._spInit){window._spInit=true;initSponsoring();}
}

function ovSearch(){
  var q=document.getElementById('ov-search').value.toLowerCase().trim();
  var box=document.getElementById('ov-results');
  if(q.length<2){box.innerHTML='<div class="ov-placeholder">Tapez au moins 2 caracteres</div>';return;}
  var matches=RAW.filter(function(r){return r.r.toLowerCase().indexOf(q)>=0||r.c.toLowerCase().indexOf(q)>=0;});
  if(!matches.length){box.innerHTML='<div class="ov-placeholder">Aucun resultat</div>';return;}
  var dc={MARATHON:'#9B6FFF18',SEMI:'#FF8A5018','10KM':'#5CDFA018'};
  var dt={MARATHON:'#9B6FFF',SEMI:'#FF8A50','10KM':'#5CDFA0'};
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
  var ac=colDist(ev),aso=isAso(ev.r);
  var dl=ev.d==='MARATHON'?'Marathon':ev.d==='SEMI'?'Semi-marathon':ev.d==='AUTRE'?'Autre':'10 km';
  var histKeys=Object.keys(ev.hist||{}).map(Number).sort(function(a,b){return a-b;});
  var finHistory=histKeys.map(function(yr){return{yr:yr,v:(ev.hist||{})[yr]};}).filter(function(e){return e.v&&!isNaN(e.v);});
  if(!finHistory.length)finHistory=[{yr:2023,v:ev.y3},{yr:2024,v:ev.y4},{yr:2025,v:ev.y5},{yr:2026,v:ev.y6}].filter(function(e){return e.v&&!isNaN(e.v);});
  var lastEd=finHistory[finHistory.length-1];
  var td=getTimeData(ev.r);
  var wr=getWinnersRecords(ev.r);
  var finStr=lastEd?fmtFull(lastEd.v):'-';
  var finLbl='Finishers'+(lastEd?' ('+lastEd.yr+')':'');
  var avgLbl='Temps moyen'+(td?' ('+td.yr+')':'');
  var menVal=wr&&wr.men?wr.men:(td&&td.men?td.men:'-');
  var menYrVal=wr&&wr.menYr?wr.menYr:(td?td.yr:null);
  var wmVal=wr&&wr.women?wr.women:(td&&td.women?td.women:'-');
  var wmYrVal=wr&&wr.womenYr?wr.womenYr:(td?td.yr:null);
  var menLbl='Record homme'+(menYrVal?' ('+menYrVal+')':'');
  var wmLbl='Record femme'+(wmYrVal?' ('+wmYrVal+')':'');
  var badgeBg=ac+'18';
  var badgeCol=ac;
  var html='<div class="ov-card">'
    +'<div class="ov-card-header"><div>'
    +'<div class="ov-card-title">'+ev.r+'</div>'
    +'<div class="ov-card-meta"><span>&#x1F4CD; '+ev.c+'</span><span>&#x1F4C5; '+ev.p+'</span></div>'
    +'</div>'
    +(isWmm(ev.r)?'<span class="ov-badge" style="background:#38BDF818;color:#38BDF8">'+dl+' - World Marathon Majors</span>':'<span class="ov-badge" style="background:'+badgeBg+';color:'+badgeCol+'">'+dl+' - '+(aso?'ASO':'Autre')+'</span>')
    +'</div>'
    +'<div class="ov-stats">'
    +'<div class="ov-stat"><div class="ov-stat-label">'+finLbl+'</div><div class="ov-stat-value">'+finStr+'</div></div>'
    +'<div class="ov-stat"><div class="ov-stat-label">'+avgLbl+'</div><div class="ov-stat-value" style="font-size:14px">'+(td&&td.avg?td.avg:'-')+'</div></div>'
    +'<div class="ov-stat"><div class="ov-stat-label">'+menLbl+'</div><div class="ov-stat-value" style="font-size:14px;color:#9B6FFF">'+menVal+'</div></div>'
    +'<div class="ov-stat"><div class="ov-stat-label">'+wmLbl+'</div><div class="ov-stat-value" style="font-size:14px;color:#FF8A50">'+wmVal+'</div></div>'
    +'</div>'
    +'<div class="ov-charts">'
    +'<div class="ov-chart-box"><div class="ov-chart-label">Finishers par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-fin"></canvas></div></div>'
    +'<div class="ov-chart-box"><div class="ov-chart-label">Temps moyen par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-time"></canvas></div></div>'
    +'</div>'
    +'<div class="ov-charts">'
    +'<div class="ov-chart-box"><div class="ov-chart-label">Record Homme par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-men"></canvas></div></div>'
    +'<div class="ov-chart-box"><div class="ov-chart-label">Record Femme par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-women"></canvas></div></div>'
    +'</div>'
    +'</div>';
  document.getElementById('ov-card-wrap').innerHTML=html;

  if(ovChartF)ovChartF.destroy();
  var fc=document.getElementById('ov-chart-fin');
  if(fc&&finHistory.length){
    var finCfg={
      type:'bar',
      data:{labels:finHistory.map(function(e){return e.yr;}),datasets:[{data:finHistory.map(function(e){return e.v;}),backgroundColor:ac+'99',borderRadius:3,borderSkipped:false}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{backgroundColor:mkTT().backgroundColor,borderColor:mkTT().borderColor,borderWidth:1,titleColor:mkTT().titleColor,bodyColor:mkTT().bodyColor,padding:10,callbacks:{label:function(ctx){return' '+fmtFull(ctx.parsed.y)+' finishers';}}}},
        scales:{x:{grid:{display:false},ticks:TICK,border:{color:mkBorder()}},y:{grid:{color:mkGRID()},ticks:{color:mkTICK().color,font:{size:11},callback:function(v){return fmt(v);}},border:{color:mkBorder()}}}
      }
    };
    ovChartF=new Chart(fc,finCfg);
  }
  if(ovChartT)ovChartT.destroy();
  var th=buildTimeHistory(ev.r);
  var tc=document.getElementById('ov-chart-time');
  if(tc&&th.length>1){
    var timeCfg={
      type:'line',
      data:{labels:th.map(function(e){return e.yr;}),datasets:[{data:th.map(function(e){return e.min;}),borderColor:ac,backgroundColor:'transparent',tension:0.3,pointRadius:4,pointBackgroundColor:ac,borderWidth:2}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{backgroundColor:mkTT().backgroundColor,borderColor:mkTT().borderColor,borderWidth:1,titleColor:mkTT().titleColor,bodyColor:mkTT().bodyColor,padding:10,callbacks:{label:function(ctx){return' '+fmtHMMin(ctx.parsed.y);}}}},
        scales:{x:{grid:{display:false},ticks:TICK,border:{color:mkBorder()}},y:{grid:{color:mkGRID()},ticks:{color:mkTICK().color,font:{size:11},callback:function(v){return fmtHM(v);}},border:{color:mkBorder()}}}
      }
    };
    ovChartT=new Chart(tc,timeCfg);
  }
  // Winner time charts (men + women)
  if(ovChartM)ovChartM.destroy();
  if(ovChartW)ovChartW.destroy();
  var wh=buildWinnerHistory(ev.r);
  var mcv=document.getElementById('ov-chart-men');
  if(mcv&&wh.men.length>1){
    ovChartM=new Chart(mcv,{type:'line',
      data:{labels:wh.men.map(function(e){return e.yr;}),datasets:[{data:wh.men.map(function(e){return e.sec/60;}),borderColor:'#9B6FFF',backgroundColor:'#9B6FFF22',tension:0.3,pointRadius:4,pointBackgroundColor:'#9B6FFF',borderWidth:2,fill:true}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{backgroundColor:mkTT().backgroundColor,borderColor:mkTT().borderColor,borderWidth:1,titleColor:mkTT().titleColor,bodyColor:mkTT().bodyColor,padding:10,callbacks:{label:function(ctx){var i=ctx.dataIndex;return' '+wh.men[i].time;}}}},
        scales:{x:{grid:{display:false},ticks:TICK,border:{color:mkBorder()}},y:{grid:{color:mkGRID()},ticks:{color:mkTICK().color,font:{size:11},callback:function(v){return fmtHM(v);}},border:{color:mkBorder()}}}
      }
    });
  }
  var wcv=document.getElementById('ov-chart-women');
  if(wcv&&wh.women.length>1){
    ovChartW=new Chart(wcv,{type:'line',
      data:{labels:wh.women.map(function(e){return e.yr;}),datasets:[{data:wh.women.map(function(e){return e.sec/60;}),borderColor:'#FF8A50',backgroundColor:'#FF8A5022',tension:0.3,pointRadius:4,pointBackgroundColor:'#FF8A50',borderWidth:2,fill:true}]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{backgroundColor:mkTT().backgroundColor,borderColor:mkTT().borderColor,borderWidth:1,titleColor:mkTT().titleColor,bodyColor:mkTT().bodyColor,padding:10,callbacks:{label:function(ctx){var i=ctx.dataIndex;return' '+wh.women[i].time;}}}},
        scales:{x:{grid:{display:false},ticks:TICK,border:{color:mkBorder()}},y:{grid:{color:mkGRID()},ticks:{color:mkTICK().color,font:{size:11},callback:function(v){return fmtHM(v);}},border:{color:mkBorder()}}}
      }
    });
  }
}

function updateTrends(){
  var dist=document.getElementById('dist-trends').value;
  var topn=parseInt(document.getElementById('topn-trends').value);
  var src=dist==='ALL'?RAW:RAW.filter(function(r){return r.d===dist;});
  if(cT)cT.destroy();
  var lbl=document.getElementById('trends-section-lbl');
  var sorted=src.slice().sort(function(a,b){
    var ka=Object.keys(a.hist||{}).map(Number).sort(function(x,y){return y-x;});
    var kb=Object.keys(b.hist||{}).map(Number).sort(function(x,y){return y-x;});
    return((a.hist||{})[ka[0]]||0)<((b.hist||{})[kb[0]]||0)?1:-1;
  }).slice(0,topn);
  var allYears=[];
  sorted.forEach(function(r){Object.keys(r.hist||{}).map(Number).forEach(function(y){if(allYears.indexOf(y)<0)allYears.push(y);});});
  allYears.sort(function(a,b){return a-b;});
  var datasets=sorted.map(function(r){return{label:r.r,data:allYears.map(function(yr){var v=(r.hist||{})[yr];return v&&v>0?v:null;}),borderColor:colDist(r),backgroundColor:'transparent',tension:0.35,fill:false,pointRadius:3,pointHoverRadius:7,spanGaps:true,borderWidth:2,pointBackgroundColor:colDist(r)};});
  var minYr=allYears.length?allYears[0]:'';var maxYr=allYears.length?allYears[allYears.length-1]:'';
  if(lbl)lbl.textContent='Evolution par evenement '+minYr+'-'+maxYr;
  var trendCfg={type:'line',data:{labels:allYears.map(String),datasets:datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:true},plugins:{legend:{display:false},tooltip:{backgroundColor:mkTT().backgroundColor,borderColor:mkTT().borderColor,borderWidth:1,titleColor:mkTT().titleColor,bodyColor:mkTT().bodyColor,padding:10,callbacks:{title:function(items){return items.length?items[0].dataset.label:'';},label:function(ctx){return' '+fmtFull(ctx.parsed.y)+' finishers';}}}},scales:{x:{grid:{color:mkGRID()},ticks:TICK,border:{color:mkBorder()}},y:{grid:{color:mkGRID()},ticks:{color:mkTICK().color,font:{size:11},callback:function(v){return fmt(v);}},border:{color:mkBorder()}}}}};
  cT=new Chart(document.getElementById('chart-trends'),trendCfg);
}

function getBiggestSrc(){
  var dist=document.getElementById('dist-biggest').value;
  return dist==='ALL'?RAW:RAW.filter(function(r){return r.d===dist;});
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

function updateBiggest(){
  var n=parseInt(document.getElementById('topn-biggest').value);
  var yr=parseInt(document.getElementById('year-biggest').value);
  var src=getBiggestSrc();
  var sorted=src.filter(function(r){var v=(r.hist||{})[yr];return v&&!isNaN(v);}).sort(function(a,b){return((b.hist||{})[yr]||0)-((a.hist||{})[yr]||0);}).slice(0,n);
  var maxVal=sorted.length?((sorted[0].hist||{})[yr]||1):1;
  var html='';
  sorted.forEach(function(r){
    var v=(r.hist||{})[yr];
    var pct=(v/maxVal*80+5).toFixed(1);
    var barCol=colDist(r);
    html+='<div class="time-bar-row bt-row" data-name="'+r.r.replace(/"/g,'&quot;')+'" data-val="'+fmtFull(v)+' finishers"><div class="time-bar-label" title="'+r.r+'">'+r.r+'</div><div class="time-bar-track"><div class="time-bar-fill" style="width:'+pct+'%;background:'+barCol+'88"></div></div><div class="time-bar-val">'+fmt(v)+'</div></div>';
  });
  document.getElementById('biggest-bars').innerHTML=html;
  initBarTips();
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

function updateTemps(){
  var dist=document.getElementById('dist-temps').value;
  var yr=parseInt(document.getElementById('year-temps').value);
  var sortMode=document.getElementById('sort-temps').value;
  var topn=parseInt(document.getElementById('topn-temps').value);
  var src=dist==='SEMI'?(TEMPS_SEMI[String(yr)]||[]):(TEMPS_MARATHON[String(yr)]||[]);
  var data=src.slice();
  if(sortMode==='avg'){data.sort(function(a,b){var ma=toMin(a.avg),mb=toMin(b.avg);if(!ma)return 1;if(!mb)return -1;return ma-mb;});}
  else{data.sort(function(a,b){return b.finishers-a.finishers;});}
  var withAvg=data.filter(function(d){return toMin(d.avg);});
  var displayed=data.slice(0,topn);
  var displayedWithAvg=displayed.filter(function(d){return toMin(d.avg);});
  var fastest=withAvg.length?withAvg.reduce(function(a,b){return toMin(a.avg)<toMin(b.avg)?a:b;}):null;
  var slowest=withAvg.length?withAvg.reduce(function(a,b){return toMin(a.avg)>toMin(b.avg)?a:b;}):null;
  var avgAll=withAvg.length?withAvg.reduce(function(s,d){return s+toMin(d.avg);},0)/withAvg.length:0;
  var avgH=Math.floor(avgAll/60),avgM=Math.floor(avgAll%60),avgS=Math.round((avgAll-Math.floor(avgAll))*60);
  var distLabel=dist==='SEMI'?'Semi-marathon':'Marathon';
  var yrLabel=dist==='SEMI'?2025:yr;
  document.getElementById('metrics-temps').innerHTML=
    '<div class="metric"><div class="metric-label">Courses</div><div class="metric-value">'+src.length+'</div><div class="metric-sub">'+distLabel+' '+yrLabel+'</div></div>'
    +'<div class="metric"><div class="metric-label">Temps moyen</div><div class="metric-value" style="font-size:16px">'+avgH+'h'+String(avgM).padStart(2,'0')+'m'+String(avgS).padStart(2,'0')+'</div></div>'
    +'<div class="metric"><div class="metric-label">Plus rapide</div><div class="metric-value" style="font-size:14px;color:#FCDB00">'+(fastest?fastest.avg:'-')+'</div></div>'
    +'<div class="metric"><div class="metric-label">Plus lent</div><div class="metric-value" style="font-size:14px">'+(slowest?slowest.avg:'-')+'</div></div>';
  var minM=withAvg.length?Math.min.apply(null,withAvg.map(function(d){return toMin(d.avg);})):0;
  var maxM=withAvg.length?Math.max.apply(null,withAvg.map(function(d){return toMin(d.avg);})):1;
  var barsHtml='';
  displayed.forEach(function(d){
    var m=toMin(d.avg);var pct=m?((m-minM)/(maxM-minM+0.001)*75+5).toFixed(1):'0';
    var barCol=isWmm(d.race)?'#38BDF8':isAso(d.race)?'#FCDB00':dist==='SEMI'?'#FF8A50':'#9B6FFF';
    barsHtml+='<div class="time-bar-row"><div class="time-bar-label">'+d.race+'</div><div class="time-bar-track"><div class="time-bar-fill" style="width:'+(m?pct:0)+'%;background:'+barCol+'88"></div></div><div class="time-bar-val">'+(d.avg||'-')+'</div></div>';
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
    if(q&&r.r.toLowerCase().indexOf(q)<0&&r.c.toLowerCase().indexOf(q)<0)return false;
    // Badge filter
    if(badge!=='ALL'){
      var w=isWmm(r.r),a=isAso(r.r);
      if(badge==='WMM'&&!w)return false;
      if(badge==='ASO'&&!a)return false;
      if(badge==='OTHER'&&(w||a))return false;
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
  else if(sortMode==='finishers'){f.sort(function(a,b){var va=(a.hist||{})[lastYr]||0,vb=(b.hist||{})[lastYr]||0;return vb-va;});}
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
    var wmm=isWmm(r.r);var aso=isAso(r.r);
    var bl=r.d==='MARATHON'?'Marathon':r.d==='SEMI'?'Semi':r.d==='AUTRE'?'Autre':'10 km';
    var raceColor=colDist(r);
    var badgeLabel=wmm?bl+' - WMM':aso?bl+' - ASO':bl;
    html+='<tr><td>'+r.p+'</td><td>'+r.c+'</td>'
      +'<td><span class="badge" style="background:'+raceColor+'18;color:'+raceColor+'">'+badgeLabel+'</span></td>'
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
  document.getElementById('sort-data').value='default';
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
function getExposure(eventName){
  var ev=RAW.find(function(r){return r.r===eventName;});
  if(!ev||!ev.hist)return 0;
  var vals=Object.values(ev.hist).filter(function(v){return v&&v>0;});
  return vals.length?Math.max.apply(null,vals):0;
}
var _spBS={},_spActiveSector='ALL',_spActiveBrand=null,_spPillSectors=[];
var _spCols={'Equipementier sport':'#22C55E','Banque/Finance':'#38BDF8','Assurance/Finance':'#9B6FFF','Finance/Investissement':'#38BDF8','Automobile':'#FF8A50','Tech/IT':'#F472B6','Energie':'#FCDB00','Industrie/Energie':'#FCDB00','Sante/Pharma':'#2DBF7E','Caritatif/Sante':'#2DBF7E','Fondation/Mecenat':'#FF6B9D','Aviation/Transport':'#5CDFA0','Nutrition/Alimentaire':'#FF9F45','Audio/Wearables':'#C084FC','Paiement/Finance':'#34D399','Retail/Mode':'#FB923C','Conglomeral/Tech':'#94A3B8','Transport':'#60A5FA','Boisson/Brasserie':'#FCD34D','Hydratation/Consommation':'#FB923C','Horlogerie/Luxe':'#E2E8F0','Assurance/Mutuelle':'#818CF8'};
function initSponsoring(){
  _spBS={};
  SP_PARTNERSHIPS.forEach(function(p){
    if(!_spBS[p.brand])_spBS[p.brand]={events:[],exposure:0,types:[],sector:(SP_BRANDS[p.brand]||{}).sector||'Autre'};
    var exp=getExposure(p.event);
    if(_spBS[p.brand].events.indexOf(p.event)<0){_spBS[p.brand].events.push(p.event);_spBS[p.brand].exposure+=exp;}
    if(_spBS[p.brand].types.indexOf(p.type)<0)_spBS[p.brand].types.push(p.type);
  });
  _spActiveSector='ALL';_spActiveBrand=null;
  var totalExp=Object.values(_spBS).reduce(function(s,b){return s+b.exposure;},0);
  var evSet={};SP_PARTNERSHIPS.forEach(function(p){evSet[p.event]=1;});
  var secExp={};Object.values(_spBS).forEach(function(b){secExp[b.sector]=(secExp[b.sector]||0)+b.exposure;});
  var topS=Object.entries(secExp).sort(function(a,b){return b[1]-a[1];})[0];
  var kpis=[[Object.keys(_spBS).length,'Marques','#22C55E'],[Object.keys(evSet).length,'\u00c9v\u00e9nements','#38BDF8'],[(totalExp/1e6).toFixed(1)+'M','Finishers expos\u00e9s','#F472B6'],[topS?topS[0].split('/')[0].trim():'-','Secteur #1','#FCDB00']];
  document.getElementById('sp-kpis').innerHTML=kpis.map(function(k){return '<div class="sp-kpi"><div class="sp-kpi-num" style="color:'+k[2]+'">'+k[0]+'</div><div class="sp-kpi-lbl">'+k[1]+'</div></div>';}).join('');
  var secSorted=Object.entries(secExp).sort(function(a,b){return b[1]-a[1];});
  _spPillSectors=['ALL'].concat(secSorted.map(function(s){return s[0];}));
  document.getElementById('sp-pills').innerHTML=_spPillSectors.map(function(s,i){
    var col=i===0?null:(_spCols[s]||'#9B6FFF');
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
  spRenderList();spRenderTreemap();
}
function spSetSector(s){
  _spActiveSector=s;
  document.querySelectorAll('.sp-pill').forEach(function(el){
    el.classList.remove('spc-active');
    el.style.removeProperty('background');
    if(el.textContent===s||(s==='ALL'&&el.textContent==='ALL')){
      el.classList.add('spc-active');
      var col=s==='ALL'?null:(_spCols[s]||'#9B6FFF');
      if(col)el.style.background=col;
    }
  });
  spRenderList();spRenderTreemap();
}
function spFiltered(){
  var q=(document.getElementById('sp-search-inp').value||'').toLowerCase();
  return Object.entries(_spBS).filter(function(e){
    if(_spActiveSector!=='ALL'&&e[1].sector!==_spActiveSector)return false;
    if(q&&e[0].toLowerCase().indexOf(q)<0)return false;
    return true;
  }).sort(function(a,b){return b[1].exposure-a[1].exposure;});
}
function spFmt(n){return n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?Math.round(n/1e3)+'k':String(n);}
var _spBrandKeys=[];
function spRenderList(){
  var items=spFiltered();
  _spBrandKeys=items.map(function(e){return e[0];});
  document.getElementById('sp-blist').innerHTML=items.map(function(e,i){
    var col=_spCols[e[1].sector]||'#9B6FFF';
    var act=_spActiveBrand===e[0]?' spc-active':'';
    return '<div class="sp-bitem'+act+'" data-bi="'+i+'">'
      +'<div class="sp-bdot" style="background:'+col+'"></div>'
      +'<div class="sp-bname">'+e[0]+'</div>'
      +'<div class="sp-bexp">'+spFmt(e[1].exposure)+'</div></div>';
  }).join('');
  var bl=document.getElementById('sp-blist');
  bl.onclick=function(e){
    var el=e.target.closest('.sp-bitem');
    if(!el)return;
    var i=parseInt(el.getAttribute('data-bi')||'0');
    if(_spBrandKeys[i])spSelect(_spBrandKeys[i]);
  };
}
function spRenderTreemap(){
  var container=document.getElementById('sp-treemap');
  var hint=document.getElementById('sp-treemap-hint');
  var items=spFiltered();
  Array.from(container.children).forEach(function(c){if(c!==hint)container.removeChild(c);});
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
    var col=_spCols[n.sec]||'#9B6FFF';
    var act=_spActiveBrand===n.id;
    var d=document.createElement('div');
    d.style.cssText='position:absolute;left:'+(x+1.5)+'px;top:'+(y+1.5)+'px;width:'+(w-3)+'px;height:'+(h-3)+'px;border-radius:6px;background:'+(act?col:col+'50')+';cursor:pointer;transition:background .15s;overflow:hidden;box-sizing:border-box;';
    if(w>55&&h>28){var fs=Math.max(9,Math.min(13,Math.min(w,h)/6));d.innerHTML='<span style="position:absolute;bottom:5px;left:6px;right:4px;font-size:'+fs+'px;font-weight:600;color:#fff;text-shadow:0 1px 4px #0009;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;pointer-events:none">'+n.id+'</span>';}
    d.addEventListener('mouseenter',function(){if(_spActiveBrand!==n.id)this.style.background=col+'88';});
    d.addEventListener('mouseleave',function(){if(_spActiveBrand!==n.id)this.style.background=col+'50';});
    d.addEventListener('click',function(){spSelect(n.id);});
    d.title=n.id;container.appendChild(d);
  }
  layout(nodes,0,0,W,H,totalV);
  if(hint)hint.style.opacity=_spActiveBrand?'0':'1';
}
function spSelect(brandId){
  _spActiveBrand=brandId;
  spRenderList();spRenderTreemap();
  var bs=_spBS[brandId];var info=SP_BRANDS[brandId]||{};
  var col=_spCols[bs.sector]||'#9B6FFF';
  var tL={title:'\u2605 Title Sponsor',official:'\u25cf Officiel',partner:'\u25cb Partenaire'};
  var typeStr=bs.types.map(function(t){return tL[t]||t;}).join(' \u00b7 ');
  var evTags=bs.events.slice(0,14).map(function(ev){return '<span class="sp-evtag">'+ev.replace(/Marathon/g,'M.').replace(/Half Marathon/g,'HM').replace(/presented by.*/i,'').trim()+'</span>';}).join('');
  if(bs.events.length>14)evTags+='<span class="sp-evtag" style="color:var(--text3)">+'+(bs.events.length-14)+'</span>';
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
    +'<div style="flex:1;min-width:180px">'
    +'<div style="font-size:10px;color:var(--text3);text-transform:uppercase;margin-bottom:6px">'+typeStr+'</div>'
    +'<div style="display:flex;flex-wrap:wrap;gap:3px">'+evTags+'</div>'
    +'</div>';
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
  var dc={MARATHON:'#9B6FFF18',SEMI:'#FF8A5018','10KM':'#5CDFA018'};
  var dt={MARATHON:'#9B6FFF',SEMI:'#FF8A50','10KM':'#5CDFA0'};
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
  var a = cmpSelectedA;
  var b = cmpSelectedB;
  var tdA = getTimeData(a.r);
  var tdB = getTimeData(b.r);
  var wrA = getWinnersRecords(a.r);
  var wrB = getWinnersRecords(b.r);

  // Last finishers
  var fA = a.y6||a.y5||a.y4||a.y3;
  var fB = b.y6||b.y5||b.y4||b.y3;
  var fYrA = a.y6?2026:a.y5?2025:a.y4?2024:2023;
  var fYrB = b.y6?2026:b.y5?2025:b.y4?2024:2023;

  // Evolution premiere annee disponible -> derniere
  var evoA = null, evoB = null;
  var evoStrA = '-', evoStrB = '-';
  var evoSubA = '', evoSubB = '';
  var haKeys=Object.keys(a.hist||{}).map(Number).sort(function(x,y){return x-y;});
  var haFirst=haKeys.length?haKeys[0]:null;
  var haFirstV=haFirst?(a.hist||{})[haFirst]:null;
  if(haFirstV&&fA){evoA=((fA-haFirstV)/haFirstV*100);evoStrA=(evoA>=0?'+':'')+evoA.toFixed(1)+'%';evoSubA=fmtFull(haFirstV)+' ('+haFirst+') \u2192 '+fmtFull(fA)+' ('+fYrA+')';}
  else if(a.y3&&fA){evoA=((fA-a.y3)/a.y3*100);evoStrA=(evoA>=0?'+':'')+evoA.toFixed(1)+'%';evoSubA=fmtFull(a.y3)+' \u2192 '+fmtFull(fA);}
  var hbKeys=Object.keys(b.hist||{}).map(Number).sort(function(x,y){return x-y;});
  var hbFirst=hbKeys.length?hbKeys[0]:null;
  var hbFirstV=hbFirst?(b.hist||{})[hbFirst]:null;
  if(hbFirstV&&fB){evoB=((fB-hbFirstV)/hbFirstV*100);evoStrB=(evoB>=0?'+':'')+evoB.toFixed(1)+'%';evoSubB=fmtFull(hbFirstV)+' ('+hbFirst+') \u2192 '+fmtFull(fB)+' ('+fYrB+')';}
  else if(b.y3&&fB){evoB=((fB-b.y3)/b.y3*100);evoStrB=(evoB>=0?'+':'')+evoB.toFixed(1)+'%';evoSubB=fmtFull(b.y3)+' \u2192 '+fmtFull(fB);}

  var distA = a.d==='MARATHON'?'Marathon':a.d==='SEMI'?'Semi-marathon':a.d==='AUTRE'?'Autre':'10 km';
  var distB = b.d==='MARATHON'?'Marathon':b.d==='SEMI'?'Semi-marathon':b.d==='AUTRE'?'Autre':'10 km';
  var asoA = isWmm(a.r)?'WMM':isAso(a.r)?'ASO':'Autre';
  var asoB = isWmm(b.r)?'WMM':isAso(b.r)?'ASO':'Autre';

  var avgA = tdA?tdA.avg:null;
  var avgB = tdB?tdB.avg:null;
  var menA = wrA&&wrA.men?wrA.men:(tdA?tdA.men:null);
  var menB = wrB&&wrB.men?wrB.men:(tdB?tdB.men:null);
  var wmA  = wrA&&wrA.women?wrA.women:(tdA?tdA.women:null);
  var wmB  = wrB&&wrB.women?wrB.women:(tdB?tdB.women:null);

  // Win conditions
  var winFin   = fA&&fB ? (fA>fB?true:fA<fB?false:null) : null;
  var winAvg   = avgA&&avgB ? (cmpTimeToMin(avgA)<cmpTimeToMin(avgB)?true:cmpTimeToMin(avgA)>cmpTimeToMin(avgB)?false:null) : null;
  var winMen   = menA&&menB ? (cmpTimeToMin(menA)<cmpTimeToMin(menB)?true:cmpTimeToMin(menA)>cmpTimeToMin(menB)?false:null) : null;
  var winWm    = wmA&&wmB  ? (cmpTimeToMin(wmA)<cmpTimeToMin(wmB)?true:cmpTimeToMin(wmA)>cmpTimeToMin(wmB)?false:null) : null;
  var winEvo   = evoA!==null&&evoB!==null ? (evoA>evoB?true:evoA<evoB?false:null) : null;

  var finLblA = fA?fmtFull(fA)+' ('+fYrA+')':'-';
  var finLblB = fB?fmtFull(fB)+' ('+fYrB+')':'-';

  var html = '<div class="cmp-wrap">'
    +'<div class="cmp-header">'
    +'<div class="cmp-header-cell"><div class="cmp-race-name">'+a.r+'</div><div class="cmp-race-meta">'+a.c+' &middot; '+a.p+' &middot; '+distA+'</div></div>'
    +'<div class="cmp-header-cell ctr"><div class="cmp-mid-label">Categorie</div></div>'
    +'<div class="cmp-header-cell" style="text-align:right"><div class="cmp-race-name">'+b.r+'</div><div class="cmp-race-meta">'+b.c+' &middot; '+b.p+' &middot; '+distB+'</div></div>'
    +'</div>';

  // Finishers row
  html += buildCmpRow(finLblA, finLblB, 'Finishers', winFin, '', '');
  // Temps moyen
  html += buildCmpRow(avgA||'-', avgB||'-', 'Temps moyen', winAvg, '', '');
  // Record homme
  html += buildCmpRow(menA||'-', menB||'-', 'Record homme', winMen, '', '');
  // Record femme
  html += buildCmpRow(wmA||'-', wmB||'-', 'Record femme', winWm, '', '');
  // Evolution
  html += buildCmpRowEvo(evoStrA, evoStrB, 'Evolution', winEvo, evoSubA, evoSubB);
  // Statut
  html += buildCmpRow(asoA, asoB, 'Statut', null, '', '');

  html += '</div>';
  document.getElementById('cmp-result').innerHTML = html;

  // Fix bar widths after render
  setTimeout(function(){
    fixCmpBar('Finishers', winFin);
    fixCmpBar('Tempsmoyen', winAvg);
    fixCmpBar('Recordhomme', winMen);
    fixCmpBar('Recordfemme', winWm);
    fixCmpBarEvo(winEvo);
  }, 50);
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
  if(!barTipEl){barTipEl=document.createElement('div');barTipEl.style.cssText='position:fixed;background:#111;border:1px solid #333;border-radius:4px;padding:8px 12px;pointer-events:none;z-index:100;font-size:12px;display:none;';document.body.appendChild(barTipEl);}
  document.querySelectorAll('.bt-row').forEach(function(el){
    el.addEventListener('mouseenter',function(){
      barTipEl.innerHTML='<div style="color:#888;font-size:11px;margin-bottom:3px">'+el.dataset.name+'</div><div style="color:#ccc">'+el.dataset.val+'</div>';
      barTipEl.style.display='block';
      var rect=el.getBoundingClientRect();
      barTipEl.style.left=(rect.left+rect.width/2-60)+'px';
      barTipEl.style.top=(rect.top-50)+'px';
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
  var filtered=WINNERS.filter(function(w){return w.d===dist;});
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
  var palette=['#9B6FFF','#FF8A50','#5CDFA0','#FCDB00','#FF6B9D','#00D4AA','#FF4444','#44AAFF','#FFD700','#FF69B4','#00CED1','#FFA07A','#98FB98','#DDA0DD','#87CEEB','#F0E68C','#CD853F','#8FBC8F','#E6E6FA','#FFDAB9'];
  var datasets=[];
  raceList.forEach(function(r,i){var c=palette[i%palette.length];
    if(gender!=='w'){var mData=allYears.map(function(yr){var yd=r.years.find(function(y){return y.y===yr;});return yd&&yd.m?secToMin(yd.m):null;});datasets.push({label:r.name+(gender==='both'?' (H)':''),data:mData,borderColor:c,backgroundColor:c+'33',pointBackgroundColor:c,pointRadius:4,pointHoverRadius:6,tension:.3,borderWidth:2,spanGaps:true});}
    if(gender!=='m'){var wData=allYears.map(function(yr){var yd=r.years.find(function(y){return y.y===yr;});return yd&&yd.w?secToMin(yd.w):null;});datasets.push({label:r.name+(gender==='both'?' (F)':''),data:wData,borderColor:c,backgroundColor:c+'33',pointBackgroundColor:c,pointRadius:4,pointHoverRadius:6,tension:.3,borderWidth:gender==='both'?1:2,borderDash:gender==='both'?[5,3]:[],spanGaps:true});}
  });
  var allM=[],allW=[];
  filtered.forEach(function(w){var ms=winToSec(w.m),ws=winToSec(w.w);if(ms)allM.push(ms);if(ws)allW.push(ws);});
  allM.sort(function(a,b){return a-b;});allW.sort(function(a,b){return a-b;});
  var mH='';
  if(allM.length){mH+='<div class="metric"><div class="metric-label">Record Homme</div><div class="metric-value" style="color:#9B6FFF">'+secToTime(allM[0])+'</div><div class="metric-sub">sur '+allM.length+' courses</div></div>';}
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
  cW=new Chart(ctx,{type:'line',data:{labels:allYears.map(String),datasets:datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:true},plugins:{legend:{display:false},tooltip:{backgroundColor:mkTT().backgroundColor,borderColor:mkTT().borderColor,borderWidth:1,titleColor:mkTT().titleColor,bodyColor:mkTT().bodyColor,padding:10,callbacks:{title:function(items){return items.length?items[0].dataset.label:'';},label:function(ctx){var v=ctx.parsed.y;if(v==null)return null;var h=Math.floor(v/60),m=Math.floor(v%60),s=Math.round((v*60)%60);return' '+(h?h+':':'')+String(m).padStart(h?2:1,'0')+':'+String(s).padStart(2,'0');}}}},scales:{x:{ticks:{color:mkTICK().color,font:{size:11}},grid:{color:mkGRID()}},y:{reverse:true,ticks:{color:mkTICK().color,font:{size:11},callback:function(v){var h=Math.floor(v/60),m=Math.round(v%60);return(h?h+'h':'')+(h?String(m).padStart(2,'0'):m)+'min';}},grid:{color:mkGRID()}}}}});
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
    return'<tr><td>'+w.r+'</td><td style="text-align:center;color:#9B6FFF">'+(w.m||'\\u2014')+'</td><td style="text-align:center;color:#FF8A50">'+(w.w||'\\u2014')+'</td><td style="text-align:center;color:var(--text3)">'+gap+'</td></tr>';
  }).join('');
  document.getElementById('win-count').textContent=filtered.length+' courses - '+yr;
}
'''


CSS = """*{box-sizing:border-box;margin:0;padding:0;}
:root{--bg:#0d1117;--bg2:#161b22;--bg3:#1c2128;--border:#30363d;--border2:#30363d;--text:#e6edf3;--text2:#8b949e;--text3:#6e7681;--purple:#7B2FFF;--yellow:#FCDB00;}
[data-theme="light"]{--bg:#f8f9fb;--bg2:#eef1f5;--bg3:#e4e8ee;--border:#c8ced6;--border2:#c8ced6;--text:#1a1d21;--text2:#3d454e;--text3:#636d78;--purple:#5C00D4;--yellow:#B8920A;}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:1.5rem;}
.dp-header{padding-bottom:1.25rem;border-bottom:.5px solid var(--border);margin-bottom:1.5rem;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:.5rem;}
.dp-title{font-size:15px;font-weight:500;letter-spacing:.02em;}
.dp-sub{font-size:12px;color:var(--text3);margin-top:4px;}
.dp-updated{font-size:11px;color:var(--text3);}
.tabs{display:flex;border-bottom:.5px solid var(--border);margin-bottom:1.5rem;overflow-x:auto;scrollbar-width:none;-ms-overflow-style:none;}
.tabs::-webkit-scrollbar{display:none;}
.tab{padding:8px 14px;font-size:12px;color:var(--text3);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;letter-spacing:.04em;text-transform:uppercase;transition:color .15s,border-color .15s;white-space:nowrap;}
.tab.active{color:var(--text);border-bottom-color:var(--purple);}
.tab:hover:not(.active){color:var(--text2);}
.panel{display:none;}.panel.active{display:block;}
.controls{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:1.5rem;align-items:flex-end;}
.ctrl-group{display:flex;flex-direction:column;gap:5px;}
.ctrl-label{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;}
select{font-size:12px;padding:5px 10px;border:.5px solid var(--border2);border-radius:4px;background:var(--bg2);color:var(--text2);cursor:pointer;outline:none;}
select:focus{border-color:var(--purple);color:var(--text);}
.section-title{font-size:10px;color:var(--text3);margin-bottom:12px;text-transform:uppercase;letter-spacing:.1em;}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;}
.leg-item{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text3);}
.leg-dot{width:8px;height:8px;border-radius:1px;flex-shrink:0;}
.chart-wrap{position:relative;width:100%;margin-bottom:1.5rem;}
.table-wrap{overflow-x:auto;border:.5px solid var(--border);border-radius:4px;}
table{width:100%;border-collapse:collapse;font-size:12px;}
th{background:var(--bg2);padding:7px 12px;text-align:left;font-weight:400;color:var(--text3);font-size:10px;text-transform:uppercase;letter-spacing:.08em;border-bottom:.5px solid var(--border);}
td{padding:7px 12px;border-bottom:.5px solid var(--border);color:var(--text2);}
tr:last-child td{border-bottom:none;}
tr:hover td{background:var(--bg2);color:var(--text);}
.badge{font-size:10px;padding:2px 7px;border-radius:2px;font-weight:400;}
.badge-aso{background:#FCDB0018;color:#FCDB00;}
.badge-world{background:#5C00D418;color:#9B6FFF;}
.badge-wmm{background:#38BDF818;color:#38BDF8;margin-left:4px;}
.search-wrap{position:relative;flex:1;min-width:160px;}
.search-wrap input{width:100%;font-size:12px;padding:5px 10px 5px 26px;border:.5px solid var(--border2);border-radius:4px;background:var(--bg2);color:var(--text);}
.search-wrap input::placeholder{color:var(--text3);}
.search-icon{position:absolute;left:8px;top:50%;transform:translateY(-50%);color:var(--text3);font-size:12px;pointer-events:none;}
.count{font-size:11px;color:var(--text3);margin-top:8px;}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:1.5rem;}
.metric{background:var(--bg2);border-radius:4px;padding:12px 14px;border:.5px solid var(--border);}
.metric-label{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;}
.metric-value{font-size:20px;font-weight:500;color:var(--text);margin-top:4px;}
.metric-sub{font-size:11px;color:var(--text3);margin-top:2px;}
.time-bar-wrap{margin-bottom:1.5rem;max-height:360px;overflow-y:auto;}
.time-bar-row{display:flex;align-items:center;gap:10px;margin-bottom:5px;}
.time-bar-label{font-size:11px;color:var(--text2);width:210px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.time-bar-track{flex:1;background:var(--bg2);border-radius:2px;height:5px;}
.time-bar-fill{height:100%;border-radius:2px;}
.time-bar-val{font-size:11px;color:var(--text3);width:56px;flex-shrink:0;text-align:right;}
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
.ov-card{border:.5px solid var(--border2);border-radius:6px;padding:1.25rem;margin-bottom:1.5rem;background:var(--bg2);}
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
.cmp-val-win{font-size:16px;font-weight:500;color:#22C55E;}
.cmp-val-lose{font-size:14px;font-weight:500;color:var(--text2);}
.cmp-bar{height:2px;background:#22C55E;border-radius:1px;margin-top:3px;}
.cmp-dot{width:5px;height:5px;border-radius:50%;background:#22C55E;flex-shrink:0;}
.cmp-sub{font-size:11px;color:var(--text3);margin-top:2px;}
.cmp-placeholder{color:var(--text3);font-size:12px;padding:2rem;text-align:center;border:.5px solid var(--border);border-radius:6px;}
#data-table.tbl-frozen{table-layout:fixed;width:max-content;min-width:100%;}
#data-table.tbl-frozen td.frozen-cell,#data-table.tbl-frozen th.frozen-cell{background:var(--bg);}
#data-table.tbl-frozen tr:hover td.frozen-cell{background:var(--bg2);}
#data-table.tbl-frozen th:not(.frozen-cell),#data-table.tbl-frozen td:not(.frozen-cell){min-width:58px;width:58px;text-align:center;font-size:11px;padding:7px 6px;}
#data-table.tbl-frozen td:not(.frozen-cell){white-space:nowrap;}
.theme-toggle{background:var(--bg2);border:.5px solid var(--border);border-radius:20px;padding:4px 10px;cursor:pointer;font-size:13px;display:flex;align-items:center;gap:6px;color:var(--text2);transition:all .2s;user-select:none;}
.theme-toggle:hover{color:var(--text);border-color:var(--purple);}
[data-theme="light"] .badge-aso{background:#FCDB0030;color:#7A6200;}
[data-theme="light"] .badge-world{background:#5C00D420;color:#4800A8;}
[data-theme="light"] .badge-wmm{background:#0284C728;color:#025E87;}
[data-theme="light"] .time-bar-track{background:var(--bg3);}
[data-theme="light"] .metric{border-color:var(--border);}
[data-theme="light"] .ov-card{border-color:var(--border);}
[data-theme="light"] .ov-chart-box{background:var(--bg2);border-color:var(--border);}
[data-theme="light"] .cmp-mid{background:var(--bg2);}
[data-theme="light"] .leg-item{color:var(--text2);}
[data-theme="light"] select{background:var(--bg);border-color:var(--border);}
[data-theme="light"] .search-wrap input,[data-theme="light"] .ov-search-wrap input,[data-theme="light"] .cmp-input{background:var(--bg);border-color:var(--border);}
[data-theme="light"] .cmp-dropdown{background:var(--bg);}
[data-theme="light"] #data-table.tbl-frozen td.frozen-cell,[data-theme="light"] #data-table.tbl-frozen th.frozen-cell{background:var(--bg);}
[data-theme="light"] #data-table.tbl-frozen tr:hover td.frozen-cell{background:var(--bg2);}
.sp-kpis{display:flex;gap:12px;margin-bottom:18px;}
.sp-kpi{flex:1;background:var(--bg2);border-radius:10px;padding:14px 18px;border:.5px solid var(--border);}
.sp-kpi-num{font-size:1.8rem;font-weight:700;line-height:1;}
.sp-kpi-lbl{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;margin-top:4px;}
.sp-layout{display:grid;grid-template-columns:220px 1fr;gap:12px;height:calc(100vh - 240px);min-height:460px;}
.sp-sidebar{display:flex;flex-direction:column;gap:7px;overflow:hidden;background:var(--bg2);border-radius:10px;padding:12px;border:.5px solid var(--border);}
.sp-search-inp{width:100%;padding:7px 10px;background:var(--bg);border:1px solid var(--border);border-radius:7px;color:var(--text);font-size:12px;outline:none;}
.sp-search-inp:focus{border-color:var(--purple);}
.sp-pills{display:flex;flex-wrap:wrap;gap:3px;}
.sp-pill{padding:3px 8px;border-radius:20px;font-size:10px;cursor:pointer;background:var(--bg);color:var(--text3);border:1px solid var(--border);transition:.15s;white-space:nowrap;}
.sp-pill:hover{color:var(--text);}
.sp-pill.spc-active{color:#fff!important;border-color:transparent!important;}
.sp-list-title{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.06em;}
.sp-blist{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:1px;}
.sp-bitem{display:flex;align-items:center;gap:7px;padding:6px 8px;border-radius:7px;cursor:pointer;transition:.12s;}
.sp-bitem:hover,.sp-bitem.spc-active{background:var(--bg);}
.sp-bdot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.sp-bname{flex:1;font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sp-bexp{font-size:11px;color:var(--text3);flex-shrink:0;}
.sp-right{display:flex;flex-direction:column;gap:10px;overflow:hidden;}
.sp-treemap{flex:1;position:relative;border-radius:10px;overflow:hidden;background:var(--bg2);border:.5px solid var(--border);}
.sp-treemap-hint{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:12px;color:var(--text3);pointer-events:none;transition:opacity .3s;}
.sp-detail{background:var(--bg2);border-radius:10px;padding:16px 20px;display:none;gap:20px;align-items:flex-start;flex-wrap:wrap;border:.5px solid var(--border);min-height:110px;}
.sp-detail-name{font-size:1.3rem;font-weight:700;margin-bottom:4px;}
.sp-detail-badge{font-size:11px;padding:2px 10px;border-radius:20px;display:inline-block;margin-bottom:6px;}
.sp-detail-stat{text-align:center;}
.sp-detail-stat-num{font-size:1.5rem;font-weight:700;}
.sp-detail-stat-lbl{font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:.05em;}
.sp-evtag{font-size:10px;padding:2px 7px;background:var(--bg);border-radius:4px;color:var(--text2);}
[data-theme="light"] .sp-kpi{border-color:var(--border);}
[data-theme="light"] .sp-sidebar{border-color:var(--border);}
[data-theme="light"] .sp-search-inp{background:var(--bg);border-color:var(--border);}
[data-theme="light"] .sp-treemap{border-color:var(--border);}
[data-theme="light"] .sp-detail{border-color:var(--border);}"""

HTML_BODY = """
<div class="dp-header">
  <div><div class="dp-title">Dashboard Running</div><div class="dp-sub">Grands evenements running mondiaux &middot; 2007-2026</div></div>
  <div style="display:flex;align-items:center;gap:12px;">
    <div class="theme-toggle" onclick="toggleTheme()" id="theme-btn" title="Changer le theme">&#x263E; Dark</div>
    <div class="dp-updated">Genere le {now}</div>
  </div>
</div>
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
    <div class="ctrl-group"><span class="ctrl-label">Top evenements</span>
      <select id="topn-trends" onchange="updateTrends()">
        <option value="8">Top 8</option><option value="12">Top 12</option><option value="16">Top 16</option><option value="20">Top 20</option>
      </select>
    </div>
  </div>
  <div class="section-title" id="trends-section-lbl">Evolution par evenement 2023-2025</div>
  <div class="legend">
    <span class="leg-item"><span class="leg-dot" style="background:#9B6FFF"></span>Marathon</span>
    <span class="leg-item"><span class="leg-dot" style="background:#FF8A50"></span>Semi-marathon</span>
    <span class="leg-item"><span class="leg-dot" style="background:#5CDFA0"></span>10 km</span>
    <span class="leg-item"><span class="leg-dot" style="background:#F472B6"></span>Autre</span>
    <span class="leg-item"><span class="leg-dot" style="background:#FCDB00"></span>Evenements ASO</span>
    <span class="leg-item"><span class="leg-dot" style="background:#38BDF8"></span>World Marathon Majors</span>
  </div>
  <div class="chart-wrap" style="height:320px;"><canvas id="chart-trends"></canvas></div>
</div>
<div id="panel-biggest" class="panel">
  <div class="controls">
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="dist-biggest" onchange="initBiggestYears();updateBiggest()">
        <option value="ALL">Toutes distances</option>
        <option value="MARATHON">Marathon</option><option value="SEMI">Semi-marathon</option><option value="10KM">10 km</option><option value="AUTRE">Autre</option>
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
    <span class="leg-item"><span class="leg-dot" style="background:#5C00D4"></span>Autre</span>
    <span class="leg-item"><span class="leg-dot" style="background:#FCDB00"></span>Evenements ASO</span>
    <span class="leg-item"><span class="leg-dot" style="background:#38BDF8"></span>World Marathon Majors</span>
  </div>
  <div class="time-bar-wrap" id="biggest-bars" style="max-height:520px"></div>
</div>
<div id="panel-temps" class="panel">
  <div class="controls">
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="dist-temps" onchange="updateTempsYears();updateTemps()">
        <option value="MARATHON">Marathon</option><option value="SEMI">Semi-marathon</option>
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
  <div class="legend">
    <span class="leg-item"><span class="leg-dot" style="background:#5C00D4"></span>Autre</span>
    <span class="leg-item"><span class="leg-dot" style="background:#FCDB00"></span>Evenements ASO</span>
    <span class="leg-item"><span class="leg-dot" style="background:#38BDF8"></span>World Marathon Majors</span>
  </div>
  <div class="time-bar-wrap" id="time-bars"></div>
</div>
<div id="panel-winners" class="panel">
  <div class="controls">
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="win-dist" onchange="updateWinners()">
        <option value="42K">Marathon (42K)</option><option value="21K">Semi-marathon (21K)</option><option value="10K">10 km</option><option value="AUTRE">Autre</option>
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
  <div class="sp-kpis" id="sp-kpis"></div>
  <div class="sp-layout">
    <div class="sp-sidebar">
      <input class="sp-search-inp" id="sp-search-inp" type="text" placeholder="&#x2315; Rechercher une marque...">
      <div class="sp-pills" id="sp-pills"></div>
      <div class="sp-list-title" style="margin-top:4px;margin-bottom:2px">Marques</div>
      <div class="sp-blist" id="sp-blist"></div>
    </div>
    <div class="sp-right">
      <div class="sp-treemap" id="sp-treemap">
        <div class="sp-treemap-hint" id="sp-treemap-hint">&#x2190; Cliquer sur une marque pour voir le detail</div>
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
    <div class="ctrl-group"><span class="ctrl-label">Badge</span>
      <select id="badge-data" onchange="filterTable()">
        <option value="ALL">Tous</option><option value="WMM">WMM</option><option value="ASO">ASO</option><option value="OTHER">Autre</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Taille</span>
      <select id="size-data" onchange="filterTable()">
        <option value="ALL">Toutes</option><option value="20000">20 000+</option><option value="10000">10-20k</option><option value="5000">5-10k</option><option value="0">&lt; 5 000</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Tri</span>
      <select id="sort-data" onchange="filterTable()">
        <option value="default">Par defaut</option>
        <option value="month">Par mois</option>
        <option value="distance">Par distance</option>
        <option value="finishers">Finishers (decroissant)</option>
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
      <thead><tr id="table-head-row"><th>Mois</th><th>Ville</th><th>Distance</th><th>Epreuve</th><th>2023</th><th>2024</th><th>2025</th><th>2026</th><th>Tendance</th></tr></thead>
      <tbody id="table-body"></tbody>
    </table>
  </div>
  <div class="count" style="display:flex;align-items:center;gap:10px"><span id="table-count"></span><a id="reset-filters" href="javascript:void(0)" onclick="resetFilters()" style="display:none;align-items:center;gap:4px;font-size:11px;color:var(--accent);text-decoration:none;cursor:pointer">\u21BA Reinitialiser les filtres</a></div>
</div>"""


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
               "const TIMES_DB=" + j(tdbjs) + ";\nconst ASO_KEYWORDS=" + j(ASO_KEYWORDS) + ";\n"
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
<title>Dashboard Running</title>
<style>{CSS}</style>
</head>
<body>
{body}
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
{js_data}
{JS_LOGIC}
</script>
</body>
</html>"""


def main():
    print("\nDataPace Dashboard Generator")
    print("-" * 40)

    use_db = _DB_PATH.exists() and _DB_PATH.stat().st_size > 0

    if use_db:
        print(f"Source : SQLite ({_DB_PATH.name})")
        from datapace.data_loader import load_all
        print("\nLecture des donnees (SQLite)...")
        finishers, biggest, md, sd, tdb, winners, sp_avg = load_all(_DB_PATH)
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

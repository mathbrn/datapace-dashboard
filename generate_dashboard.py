#!/usr/bin/env python3
"""
DataPace Dashboard Generator
=============================
Lit les fichiers Excel et génère datapace_dashboard.html.

Usage :
    python generate_dashboard.py

Fichiers Excel requis (même dossier que ce script) :
    - Suivi_Finishers_Monde_10k_-_21k_-_42k.xlsx
    - Temps_moyen_par_marathon_2024.xlsx
    - Temps_moyen_par_marathon_2025.xlsx
    - Temps_moyen_par_marathon_2026.xlsx
    - Temps_moyen_semi-marathon_2025.xlsx

Sortie :
    - datapace_dashboard.html  (ouvrir dans le navigateur)
"""

import pandas as pd
import json
import datetime
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

FILES = {
    "finishers":     SCRIPT_DIR / "Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx",
    "marathon_2024": SCRIPT_DIR / "Temps_moyen_par_marathon_2024.xlsx",
    "marathon_2025": SCRIPT_DIR / "Temps_moyen_par_marathon_2025.xlsx",
    "marathon_2026": SCRIPT_DIR / "Temps_moyen_par_marathon_2026.xlsx",
    "semi_2025":     SCRIPT_DIR / "Temps_moyen_semi-marathon_2025.xlsx",
}
OUTPUT_FILE = SCRIPT_DIR / "datapace_dashboard.html"

ASO_KEYWORDS = [
    "schneider electric", "hoka semi de paris", "semi de paris",
    "run in lyon", "beaujolais", "adidas 10k paris", "10k montmartre",
    "cancer research", "asics ldnx", "adidas manchester",
]


def fmt_time(val):
    if val is None or (isinstance(val, float) and pd.isna(val)): return None
    if isinstance(val, datetime.time): return val.strftime("%H:%M:%S")
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
            try: iv = int(float(v)); return iv if iv > 0 else None
            except: return None
        hist = {yr: v for yr in year_cols if (v := gv(yr)) is not None}
        rows.append({"p": str(r.get("Période", "")).strip(), "c": str(r.get("City", "")).strip(),
                     "d": str(r.get("Distance", "")).strip(), "r": race,
                     "y3": gv(2023), "y4": gv(2024), "y5": gv(2025), "y6": gv(2026),
                     "hist": hist})
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
    df = pd.read_excel(FILES["semi_2025"], sheet_name="2025", header=None)
    df.columns = ["_", "city", "race", "finishers", "avg_time", "men_time", "women_time", "top10_avg"]
    rows = []
    for _, r in df.iloc[4:].iterrows():
        race = str(r["race"]).strip() if pd.notna(r["race"]) else ""
        if not race or race in ("nan", "Race"): continue
        rows.append({"race": race,
                     "city": str(r["city"]).strip() if pd.notna(r["city"]) else "",
                     "finishers": safe_int(r["finishers"]),
                     "avg": fmt_time(r["avg_time"]), "men": fmt_time(r["men_time"]),
                     "women": fmt_time(r["women_time"]), "year": 2025})
    print(f"  Semi 2025  : {len(rows)} courses")
    return rows


def build_times_db(md, sd):
    db = {}; all_e = []
    for rows in md.values(): all_e.extend(rows)
    all_e.extend(sd); all_e.sort(key=lambda x: x.get("year", 0))
    for row in all_e:
        if row.get("avg") or row.get("men"):
            db[row["race"].lower()] = {
                "men": row.get("men") or "", "women": row.get("women") or "",
                "avg": row.get("avg") or "", "yr": row.get("year")}
    return db


JS_LOGIC = '''function isAso(r){var l=r.toLowerCase();return ASO_KEYWORDS.some(function(k){return l.indexOf(k)>=0;});}
function col(r){return isAso(r)?'#FCDB00':'#5C00D4';}
function colDist(r){return isAso(r.r)?'#FCDB00':r.d==='10KM'?'#5CDFA0':r.d==='SEMI'?'#79AAFF':'#9B6FFF';}
function toMin(t){if(!t)return null;var p=String(t).split(':');if(p.length===3)return parseInt(p[0])*60+parseInt(p[1])+parseInt(p[2])/60;return null;}
function fmt(n){if(!n||isNaN(n))return'\u2014';return n>=1000?(n/1000).toFixed(1)+'k':n.toString();}
function fmtFull(n){if(!n||isNaN(n))return'\u2014';return Math.round(n).toLocaleString('fr-FR');}
function delta(a,b){if(!a||!b||isNaN(a)||isNaN(b))return null;return((b-a)/a*100);}
function fmtHM(mins){var h=Math.floor(mins/60),m=Math.round(mins%60);return h+'h'+String(m).padStart(2,'0');}
function fmtHMMin(mins){return fmtHM(mins)+'min';}
var GRID='rgba(255,255,255,0.04)';
var TICK={color:'#555',font:{size:11}};
var TT={backgroundColor:'#111',borderColor:'#ffffff18',borderWidth:1,titleColor:'#888',bodyColor:'#ccc',padding:10};


function getTimeData(rn){
  var l=rn.toLowerCase();
  var keys=Object.keys(TIMES_DB);
  for(var i=0;i<keys.length;i++){var k=keys[i];if(l.indexOf(k)>=0||k.indexOf(l.substring(0,12))>=0)return TIMES_DB[k];}
  return null;
}
function buildTimeHistory(rn){
  var l=rn.toLowerCase(),hist=[];
  [2024,2025,2026].forEach(function(yr){
    var rows=TEMPS_MARATHON[String(yr)]||[];
    for(var i=0;i<rows.length;i++){var rl=rows[i].race.toLowerCase();if(l.indexOf(rl.substring(0,10))>=0||rl.indexOf(l.substring(0,10))>=0){if(toMin(rows[i].avg))hist.push({yr:String(yr),min:toMin(rows[i].avg)});break;}}
  });
  if(!hist.length){for(var i=0;i<TEMPS_SEMI_2025.length;i++){var rl=TEMPS_SEMI_2025[i].race.toLowerCase();if(l.indexOf(rl.substring(0,10))>=0||rl.indexOf(l.substring(0,10))>=0){if(toMin(TEMPS_SEMI_2025[i].avg))hist.push({yr:'2025',min:toMin(TEMPS_SEMI_2025[i].avg)});break;}}}
  return hist;
}
var cT=null,cB=null,cTm=null,ovChartF=null,ovChartT=null;

function switchTab(name){
  var names=['overview','compare','trends','biggest','temps','data'];
  document.querySelectorAll('.tab').forEach(function(t,i){t.classList.toggle('active',names[i]===name);});
  document.querySelectorAll('.panel').forEach(function(p){p.classList.remove('active');});
  document.getElementById('panel-'+name).classList.add('active');
  if(name==='trends')updateTrends();
  if(name==='biggest')updateBiggest();
  if(name==='temps')updateTemps();
  if(name==='data')filterTable();
}

function ovSearch(){
  var q=document.getElementById('ov-search').value.toLowerCase().trim();
  var box=document.getElementById('ov-results');
  if(q.length<2){box.innerHTML='<div class="ov-placeholder">Tapez au moins 2 caracteres</div>';return;}
  var matches=RAW.filter(function(r){return r.r.toLowerCase().indexOf(q)>=0||r.c.toLowerCase().indexOf(q)>=0;});
  if(!matches.length){box.innerHTML='<div class="ov-placeholder">Aucun resultat</div>';return;}
  var dc={MARATHON:'#5C00D418',SEMI:'#2563eb18','10KM':'#2DBF7E18'};
  var dt={MARATHON:'#9B6FFF',SEMI:'#79AAFF','10KM':'#5CDFA0'};
  var html='';
  matches.forEach(function(r){
    var idx=RAW.indexOf(r);
    var dl=r.d==='10KM'?'10 km':r.d==='SEMI'?'Semi':'Marathon';
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
  var ac=col(ev.r),aso=isAso(ev.r);
  var dl=ev.d==='MARATHON'?'Marathon':ev.d==='SEMI'?'Semi-marathon':'10 km';
  var histKeys=Object.keys(ev.hist||{}).map(Number).sort(function(a,b){return a-b;});
  var finHistory=histKeys.map(function(yr){return{yr:yr,v:(ev.hist||{})[yr]};}).filter(function(e){return e.v&&!isNaN(e.v);});
  if(!finHistory.length)finHistory=[{yr:2023,v:ev.y3},{yr:2024,v:ev.y4},{yr:2025,v:ev.y5},{yr:2026,v:ev.y6}].filter(function(e){return e.v&&!isNaN(e.v);});
  var lastEd=finHistory[finHistory.length-1];
  var td=getTimeData(ev.r);
  var finStr=lastEd?fmtFull(lastEd.v):'-';
  var finLbl='Finishers'+(lastEd?' ('+lastEd.yr+')':'');
  var avgLbl='Temps moyen'+(td?' ('+td.yr+')':'');
  var menLbl='Record homme'+(td?' ('+td.yr+')':'');
  var wmLbl='Record femme'+(td?' ('+td.yr+')':'');
  var badgeBg=aso?'#FCDB0018':'#5C00D418';
  var badgeCol=aso?'#FCDB00':'#9B6FFF';
  var html='<div class="ov-card">'
    +'<div class="ov-card-header"><div>'
    +'<div class="ov-card-title">'+ev.r+'</div>'
    +'<div class="ov-card-meta"><span>&#x1F4CD; '+ev.c+'</span><span>&#x1F4C5; '+ev.p+'</span></div>'
    +'</div>'
    +'<span class="ov-badge" style="background:'+badgeBg+';color:'+badgeCol+'">'+dl+' - '+(aso?'ASO':'Mondial')+'</span>'
    +'</div>'
    +'<div class="ov-stats">'
    +'<div class="ov-stat"><div class="ov-stat-label">'+finLbl+'</div><div class="ov-stat-value">'+finStr+'</div></div>'
    +'<div class="ov-stat"><div class="ov-stat-label">'+avgLbl+'</div><div class="ov-stat-value" style="font-size:14px">'+(td&&td.avg?td.avg:'-')+'</div></div>'
    +'<div class="ov-stat"><div class="ov-stat-label">'+menLbl+'</div><div class="ov-stat-value" style="font-size:14px;color:var(--yellow)">'+(td&&td.men?td.men:'-')+'</div></div>'
    +'<div class="ov-stat"><div class="ov-stat-label">'+wmLbl+'</div><div class="ov-stat-value" style="font-size:14px;color:var(--yellow)">'+(td&&td.women?td.women:'-')+'</div></div>'
    +'</div>'
    +'<div class="ov-charts">'
    +'<div class="ov-chart-box"><div class="ov-chart-label">Finishers par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-fin"></canvas></div></div>'
    +'<div class="ov-chart-box"><div class="ov-chart-label">Temps moyen par edition</div><div style="position:relative;height:150px"><canvas id="ov-chart-time"></canvas></div></div>'
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
        plugins:{legend:{display:false},tooltip:{backgroundColor:'#111',borderColor:'#ffffff18',borderWidth:1,titleColor:'#888',bodyColor:'#ccc',padding:10,callbacks:{label:function(ctx){return' '+fmtFull(ctx.parsed.y)+' finishers';}}}},
        scales:{x:{grid:{display:false},ticks:TICK,border:{color:'#ffffff08'}},y:{grid:{color:GRID},ticks:{color:'#555',font:{size:11},callback:function(v){return fmt(v);}},border:{color:'#ffffff08'}}}
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
        plugins:{legend:{display:false},tooltip:{backgroundColor:'#111',borderColor:'#ffffff18',borderWidth:1,titleColor:'#888',bodyColor:'#ccc',padding:10,callbacks:{label:function(ctx){return' '+fmtHMMin(ctx.parsed.y);}}}},
        scales:{x:{grid:{display:false},ticks:TICK,border:{color:'#ffffff08'}},y:{grid:{color:GRID},ticks:{color:'#555',font:{size:11},callback:function(v){return fmtHM(v);}},border:{color:'#ffffff08'}}}
      }
    };
    ovChartT=new Chart(tc,timeCfg);
  }
}

function updateTrends(){
  var dist=document.getElementById('dist-trends').value;
  var topn=parseInt(document.getElementById('topn-trends').value);
  var periode=document.getElementById('periode-trends').value;
  var src=dist==='ALL'?RAW:RAW.filter(function(r){return r.d===dist;});
  if(cT)cT.destroy();
  var lbl=document.getElementById('trends-section-lbl');
  if(periode==='hist'){
    var histSrc=src.filter(function(r){return r.hist&&Object.keys(r.hist).some(function(y){return parseInt(y)<2023;});});
    var sorted=histSrc.slice().sort(function(a,b){
      var ka=Object.keys(a.hist||{}).map(Number).sort(function(x,y){return y-x;});
      var kb=Object.keys(b.hist||{}).map(Number).sort(function(x,y){return y-x;});
      return((a.hist||{})[ka[0]]||0)<((b.hist||{})[kb[0]]||0)?1:-1;
    }).slice(0,topn);
    var allYears=[];
    sorted.forEach(function(r){Object.keys(r.hist||{}).map(Number).forEach(function(y){if(allYears.indexOf(y)<0)allYears.push(y);});});
    allYears.sort(function(a,b){return a-b;});
    var datasets=sorted.map(function(r){return{label:r.r,data:allYears.map(function(yr){return(r.hist||{})[yr]||null;}),borderColor:colDist(r),backgroundColor:'transparent',tension:0.35,fill:false,pointRadius:4,pointHoverRadius:7,spanGaps:true,borderWidth:2,pointBackgroundColor:colDist(r)};});
    if(lbl)lbl.textContent='Tendances historiques - grands evenements';
    var trendCfg={type:'line',data:{labels:allYears.map(String),datasets:datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:true},plugins:{legend:{display:false},tooltip:{backgroundColor:'#111',borderColor:'#ffffff18',borderWidth:1,titleColor:'#888',bodyColor:'#ccc',padding:10,callbacks:{title:function(items){return items.length?items[0].dataset.label:'';},label:function(ctx){return' '+fmtFull(ctx.parsed.y)+' finishers';}}}},scales:{x:{grid:{color:GRID},ticks:TICK,border:{color:'#ffffff08'}},y:{grid:{color:GRID},ticks:{color:'#555',font:{size:11},callback:function(v){return fmt(v);}},border:{color:'#ffffff08'}}}}};
    cT=new Chart(document.getElementById('chart-trends'),trendCfg);
  }else{
    var sorted=src.filter(function(r){return r.y5&&!isNaN(r.y5);}).sort(function(a,b){return(b.y5||0)-(a.y5||0);}).slice(0,topn);
    var datasets=sorted.map(function(r){return{label:r.r,data:[r.y3||null,r.y4||null,r.y5||null],borderColor:colDist(r),backgroundColor:'transparent',tension:0.35,fill:false,pointRadius:3,pointHoverRadius:6,spanGaps:true,borderWidth:1.5,pointBackgroundColor:colDist(r)};});
    if(lbl)lbl.textContent='Evolution par evenement 2023-2025';
    var trendCfg={type:'line',data:{labels:['2023','2024','2025'],datasets:datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:true},plugins:{legend:{display:false},tooltip:{backgroundColor:'#111',borderColor:'#ffffff18',borderWidth:1,titleColor:'#888',bodyColor:'#ccc',padding:10,callbacks:{title:function(items){return items.length?items[0].dataset.label:'';},label:function(ctx){return' '+fmtFull(ctx.parsed.y)+' finishers';}}}},scales:{x:{grid:{color:GRID},ticks:TICK,border:{color:'#ffffff08'}},y:{grid:{color:GRID},ticks:{color:'#555',font:{size:11},callback:function(v){return fmt(v);}},border:{color:'#ffffff08'}}}}};
    cT=new Chart(document.getElementById('chart-trends'),trendCfg);
  }
}

function initBiggestYears(){
  var allYears=[];
  BIGGEST.forEach(function(r){Object.keys(r.hist||{}).forEach(function(y){var yi=parseInt(y);if(allYears.indexOf(yi)<0)allYears.push(yi);});});
  allYears.sort(function(a,b){return b-a;});
  var sel=document.getElementById('year-biggest');
  sel.innerHTML='';
  allYears.forEach(function(y){var o=document.createElement('option');o.value=y;o.textContent=y;sel.appendChild(o);});
}

function updateBiggest(){
  var n=parseInt(document.getElementById('topn-biggest').value);
  var yr=parseInt(document.getElementById('year-biggest').value);
  var sorted=BIGGEST.filter(function(r){var v=(r.hist||{})[yr];return v&&!isNaN(v);}).sort(function(a,b){return((b.hist||{})[yr]||0)-((a.hist||{})[yr]||0);}).slice(0,n);
  document.getElementById('biggest-wrap').style.height=Math.max(300,n*44+80)+'px';
  if(cB)cB.destroy();
  var bigCfg={
    type:'bar',
    data:{labels:sorted.map(function(r){return r.r;}),datasets:[{data:sorted.map(function(r){return(r.hist||{})[yr];}),backgroundColor:sorted.map(function(r){return col(r.r)+'CC';}),borderRadius:2,borderSkipped:false}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{backgroundColor:'#111',borderColor:'#ffffff18',borderWidth:1,titleColor:'#888',bodyColor:'#ccc',padding:10,callbacks:{title:function(items){return sorted[items[0].dataIndex].r;},label:function(ctx){return' '+fmtFull(ctx.parsed.y)+' finishers';}}}},
      scales:{x:{grid:{display:false},ticks:{color:'#555',font:{size:10},maxRotation:45,autoSkip:false},border:{color:'#ffffff08'}},y:{grid:{color:GRID},ticks:{color:'#555',font:{size:11},callback:function(v){return fmt(v);}},border:{color:'#ffffff08'}}}
    }
  };
  cB=new Chart(document.getElementById('chart-biggest'),bigCfg);
}

function updateTemps(){
  var dist=document.getElementById('dist-temps').value;
  var yr=parseInt(document.getElementById('year-temps').value);
  var sortMode=document.getElementById('sort-temps').value;
  var topn=parseInt(document.getElementById('topn-temps').value);
  if(dist==='SEMI'&&yr!==2025){document.getElementById('year-temps').value='2025';updateTemps();return;}
  var src=dist==='SEMI'?TEMPS_SEMI_2025:(TEMPS_MARATHON[String(yr)]||[]);
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
    barsHtml+='<div class="time-bar-row"><div class="time-bar-label">'+d.race+'</div><div class="time-bar-track"><div class="time-bar-fill" style="width:'+(m?pct:0)+'%;background:'+col(d.race)+'88"></div></div><div class="time-bar-val">'+(d.avg||'-')+'</div></div>';
  });
  document.getElementById('time-bars').innerHTML=barsHtml;
  var chartH=Math.max(260,displayedWithAvg.length*28+80);
  document.getElementById('chart-temps-wrap').style.height=chartH+'px';
  if(cTm)cTm.destroy();
  var minY=dist==='SEMI'?90:200;
  var tempsCfg={
    type:'bar',
    data:{
      labels:displayedWithAvg.map(function(d){return d.race.length>22?d.race.substring(0,22)+'...':d.race;}),
      datasets:[{data:displayedWithAvg.map(function(d){return parseFloat(toMin(d.avg).toFixed(1));}),backgroundColor:displayedWithAvg.map(function(d){return col(d.race)+'BB';}),borderRadius:2,borderSkipped:false}]
    },
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{backgroundColor:'#111',borderColor:'#ffffff18',borderWidth:1,titleColor:'#888',bodyColor:'#ccc',padding:10,callbacks:{
        title:function(items){return displayedWithAvg[items[0].dataIndex].race;},
        label:function(ctx){return' '+displayedWithAvg[ctx.dataIndex].avg+' ('+fmtHM(ctx.parsed.y)+')';}
      }}},
      scales:{
        x:{grid:{display:false},ticks:{color:'#555',font:{size:10},maxRotation:45,autoSkip:false},border:{color:'#ffffff08'}},
        y:{grid:{color:GRID},ticks:{color:'#555',font:{size:11},callback:function(v){return fmtHM(v);}},border:{color:'#ffffff08'},min:minY}
      }
    }
  };
  cTm=new Chart(document.getElementById('chart-temps'),tempsCfg);
}

function applyFrozen(tbl){
  if(!tbl)return;
  var ths=tbl.querySelectorAll('thead tr th');
  if(ths.length<4)return;
  var left=0;
  for(var i=0;i<4;i++){
    var w=ths[i].offsetWidth;
    tbl.querySelectorAll('tr th:nth-child('+(i+1)+'),tr td:nth-child('+(i+1)+')').forEach(function(c){
      c.classList.add('frozen-cell');
      c.style.position='sticky';
      c.style.left=left+'px';
      c.style.zIndex=c.tagName==='TH'?'3':'2';
      c.style.minWidth=w+'px';
      c.style.maxWidth=w+'px';
      if(i===3)c.style.boxShadow='2px 0 6px rgba(0,0,0,0.45)';
    });
    left+=w;
  }
  tbl.querySelectorAll('tbody td:nth-child(4)').forEach(function(c){
    c.style.overflow='hidden';c.style.textOverflow='ellipsis';c.style.whiteSpace='nowrap';
  });
}

function filterTable(){
  var q=(document.getElementById('search-data').value||'').toLowerCase();
  var dist=document.getElementById('dist-data').value;
  var month=document.getElementById('month-data').value;
  var afficher=document.getElementById('afficher-data').value;
  var thead=document.getElementById('table-head-row');
  var f=RAW.filter(function(r){
    if(dist!=='ALL'&&r.d!==dist)return false;
    if(month!=='ALL'&&r.p!==month)return false;
    if(q&&r.r.toLowerCase().indexOf(q)<0&&r.c.toLowerCase().indexOf(q)<0)return false;
    if(afficher==='hist'&&!Object.keys(r.hist||{}).some(function(y){return parseInt(y)<2023;}))return false;
    return true;
  });
  var tbl=document.getElementById('data-table');
  var html='';
  if(afficher==='hist'){
    if(tbl)tbl.classList.add('tbl-frozen');
    var allYears=[];
    f.forEach(function(r){Object.keys(r.hist||{}).map(Number).forEach(function(y){if(allYears.indexOf(y)<0)allYears.push(y);});});
    allYears.sort(function(a,b){return a-b;});
    if(thead)thead.innerHTML='<th>Mois</th><th>Ville</th><th>Distance</th><th>Epreuve</th>'+allYears.map(function(y){return'<th>'+y+'</th>';}).join('')+'<th>Tendance</th>';
    f.forEach(function(r){
      var hkeys=Object.keys(r.hist||{}).map(Number).sort(function(a,b){return a-b;});
      var hvals=hkeys.map(function(y){return(r.hist||{})[y];}).filter(function(v){return v&&!isNaN(v);});
      var t=hvals.length>=2?delta(hvals[0],hvals[hvals.length-1]):null;
      var tc=t===null?'#555':t>=0?'#2DBF7E':'#FF4A6B';
      var tStr=t===null?'-':(t>=0?'+':'')+t.toFixed(1)+'%';
      var firstYr=hkeys[0],lastYr=hkeys[hkeys.length-1];
      var tSub=firstYr&&lastYr?'<div style="font-size:9px;color:#555;margin-top:1px">'+firstYr+'\u2192'+lastYr+'</div>':'';
      var aso=isAso(r.r);
      var bl=r.d==='MARATHON'?'Marathon':r.d==='SEMI'?'Semi':'10 km';
      var raceColor=col(r.r)==='#FCDB00'?'#FCDB00':'var(--text2)';
      html+='<tr><td>'+r.p+'</td><td>'+r.c+'</td>'
        +'<td><span class="badge '+(aso?'badge-aso':'badge-world')+'">'+bl+' - '+(aso?'ASO':'Monde')+'</span></td>'
        +'<td style="color:'+raceColor+'" title="'+r.r+'">'+r.r+'</td>'
        +allYears.map(function(y){var v=(r.hist||{})[y];return'<td style="'+(v?'color:var(--text)':'')+'">'+(v?fmtFull(v):'\u2014')+'</td>';}).join('')
        +'<td style="color:'+tc+'">'+tStr+tSub+'</td></tr>';
    });
    document.getElementById('table-body').innerHTML=html;
    applyFrozen(tbl);
    var cnt=f.length;
    document.getElementById('table-count').textContent=cnt+' epreuve'+(cnt>1?'s':'')+' affichee'+(cnt>1?'s':'');
    return;
  }else{
    if(tbl)tbl.classList.remove('tbl-frozen');
    if(thead)thead.innerHTML='<th>Mois</th><th>Ville</th><th>Distance</th><th>Epreuve</th><th>2023</th><th>2024</th><th>2025</th><th>2026</th><th>Tendance</th>';
    f.forEach(function(r){
      var hkeys=Object.keys(r.hist||{}).map(Number).sort(function(a,b){return a-b;});
      var hvals=hkeys.map(function(y){return(r.hist||{})[y];}).filter(function(v){return v&&!isNaN(v);});
      var t=hvals.length>=2?delta(hvals[0],hvals[hvals.length-1]):null;
      var firstYr=hkeys.length>=2?hkeys[0]:null;
      var lastYr=hkeys.length>=2?hkeys[hkeys.length-1]:null;
      var tc=t===null?'#555':t>=0?'#2DBF7E':'#FF4A6B';
      var tStr=t===null?'-':(t>=0?'+':'')+t.toFixed(1)+'%';
      var tSub=firstYr&&lastYr&&(lastYr-firstYr>3)?'<div style="font-size:9px;color:#555;margin-top:1px">'+firstYr+'\u2192'+lastYr+'</div>':'';
      var raceColor=col(r.r)==='#FCDB00'?'#FCDB00':'var(--text2)';
      var aso=isAso(r.r);
      var bl=r.d==='MARATHON'?'Marathon':r.d==='SEMI'?'Semi':'10 km';
      html+='<tr><td>'+r.p+'</td><td>'+r.c+'</td>'
        +'<td><span class="badge '+(aso?'badge-aso':'badge-world')+'">'+bl+' - '+(aso?'ASO':'Monde')+'</span></td>'
        +'<td style="max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:'+raceColor+'">'+r.r+'</td>'
        +'<td>'+fmtFull(r.y3)+'</td><td>'+fmtFull(r.y4)+'</td><td>'+fmtFull(r.y5)+'</td><td>'+fmtFull(r.y6)+'</td>'
        +'<td style="color:'+tc+'">'+tStr+tSub+'</td></tr>';
    });
  }
  document.getElementById('table-body').innerHTML=html;
  var cnt=f.length;
  document.getElementById('table-count').textContent=cnt+' epreuve'+(cnt>1?'s':'')+' affichee'+(cnt>1?'s':'');
}

updateTrends();
initBiggestYears();

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
  var dc={MARATHON:'#5C00D418',SEMI:'#2563eb18','10KM':'#2DBF7E18'};
  var dt={MARATHON:'#9B6FFF',SEMI:'#79AAFF','10KM':'#5CDFA0'};
  drop.innerHTML='';
  drop.style.display='block';
  matches.slice(0,10).forEach(function(r){
    var rawIdx=RAW.indexOf(r);
    var dl=r.d==='10KM'?'10 km':r.d==='SEMI'?'Semi':'Marathon';
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

  var distA = a.d==='MARATHON'?'Marathon':a.d==='SEMI'?'Semi-marathon':'10 km';
  var distB = b.d==='MARATHON'?'Marathon':b.d==='SEMI'?'Semi-marathon':'10 km';
  var asoA = isAso(a.r)?'ASO':'Mondial';
  var asoB = isAso(b.r)?'ASO':'Mondial';

  var avgA = tdA?tdA.avg:null;
  var avgB = tdB?tdB.avg:null;
  var menA = tdA?tdA.men:null;
  var menB = tdB?tdB.men:null;
  var wmA  = tdA?tdA.women:null;
  var wmB  = tdB?tdB.women:null;

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

// Close dropdowns on outside click
document.addEventListener('click', function(e){
  if(!e.target.closest('.cmp-search-box')){
    var da=document.getElementById('cmp-drop-a');
    var db=document.getElementById('cmp-drop-b');
    if(da)da.style.display='none';
    if(db)db.style.display='none';
  }
});
'''


CSS = """*{box-sizing:border-box;margin:0;padding:0;}
:root{--bg:#0a0a0a;--bg2:#111;--bg3:#161616;--border:#ffffff0f;--border2:#ffffff18;--text:#f0f0f0;--text2:#888;--text3:#555;--purple:#5C00D4;--yellow:#FCDB00;}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:1.5rem;}
.dp-header{padding-bottom:1.25rem;border-bottom:.5px solid var(--border);margin-bottom:1.5rem;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:.5rem;}
.dp-title{font-size:15px;font-weight:500;letter-spacing:.02em;}
.dp-sub{font-size:12px;color:var(--text3);margin-top:4px;}
.dp-updated{font-size:11px;color:var(--text3);}
.tabs{display:flex;border-bottom:.5px solid var(--border);margin-bottom:1.5rem;overflow-x:auto;}
.tab{padding:8px 14px;font-size:12px;color:var(--text3);cursor:pointer;border-bottom:1px solid transparent;margin-bottom:-1px;letter-spacing:.04em;text-transform:uppercase;transition:color .15s;white-space:nowrap;}
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
#data-table.tbl-frozen td.frozen-cell{background:var(--bg);}
#data-table.tbl-frozen tr:hover td.frozen-cell{background:var(--bg2);}"""

HTML_BODY = """
<div class="dp-header">
  <div><div class="dp-title">Finishers Monde - 10K &middot; 21K &middot; 42K</div><div class="dp-sub">Grands evenements running mondiaux &middot; 2007-2026</div></div>
  <div class="dp-updated">Genere le {now}</div>
</div>
<div class="tabs">
  <div class="tab" onclick="switchTab('overview')">Vue d'ensemble</div>
  <div class="tab" onclick="switchTab('compare')">Comparer</div>
  <div class="tab active" onclick="switchTab('trends')">Evolution</div>
  <div class="tab" onclick="switchTab('biggest')">Top evenements</div>
  <div class="tab" onclick="switchTab('temps')">Temps moyen</div>
  <div class="tab" onclick="switchTab('data')">Tableau</div>
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
<div id="panel-trends" class="panel active">
  <div class="controls">
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="dist-trends" onchange="updateTrends()">
        <option value="ALL">Toutes distances</option>
        <option value="MARATHON">Marathon</option><option value="SEMI">Semi-marathon</option><option value="10KM">10 km</option>
      </select>
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Periode</span>
      <select id="periode-trends" onchange="updateTrends()">
        <option value="recent">Recent (2023-2025)</option>
        <option value="hist">Historique (2007-2026)</option>
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
    <span class="leg-item"><span class="leg-dot" style="background:#79AAFF"></span>Semi-marathon</span>
    <span class="leg-item"><span class="leg-dot" style="background:#5CDFA0"></span>10 km</span>
    <span class="leg-item"><span class="leg-dot" style="background:#FCDB00"></span>Evenements ASO</span>
  </div>
  <div class="chart-wrap" style="height:320px;"><canvas id="chart-trends"></canvas></div>
</div>
<div id="panel-biggest" class="panel">
  <div class="controls">
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
    <span class="leg-item"><span class="leg-dot" style="background:#5C00D4"></span>Mondial</span>
    <span class="leg-item"><span class="leg-dot" style="background:#FCDB00"></span>Evenements ASO</span>
  </div>
  <div class="chart-wrap" id="biggest-wrap" style="height:300px;"><canvas id="chart-biggest"></canvas></div>
</div>
<div id="panel-temps" class="panel">
  <div class="controls">
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="dist-temps" onchange="updateTemps()">
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
    <span class="leg-item"><span class="leg-dot" style="background:#5C00D4"></span>Mondial</span>
    <span class="leg-item"><span class="leg-dot" style="background:#FCDB00"></span>Evenements ASO</span>
  </div>
  <div class="time-bar-wrap" id="time-bars"></div>
  <div class="section-title" style="margin-top:.5rem">Comparaison graphique (minutes)</div>
  <div class="chart-wrap" id="chart-temps-wrap" style="height:280px;"><canvas id="chart-temps"></canvas></div>
</div>
<div id="panel-data" class="panel">
  <div class="controls">
    <div class="search-wrap"><span class="search-icon">&#x2315;</span>
      <input type="text" id="search-data" placeholder="Rechercher course, ville..." oninput="filterTable()">
    </div>
    <div class="ctrl-group"><span class="ctrl-label">Distance</span>
      <select id="dist-data" onchange="filterTable()">
        <option value="ALL">Toutes</option><option value="MARATHON">Marathon</option><option value="SEMI">Semi</option><option value="10KM">10 km</option>
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
    <div class="ctrl-group"><span class="ctrl-label">Donnees</span>
      <select id="afficher-data" onchange="filterTable()">
        <option value="recent">Recentes (2023-2026)</option>
        <option value="hist">Historiques (2007-2026)</option>
      </select>
    </div>
  </div>
  <div class="table-wrap">
    <table id="data-table">
      <thead><tr id="table-head-row"><th>Mois</th><th>Ville</th><th>Distance</th><th>Epreuve</th><th>2023</th><th>2024</th><th>2025</th><th>2026</th><th>Tendance</th></tr></thead>
      <tbody id="table-body"></tbody>
    </table>
  </div>
  <div class="count" id="table-count"></div>
</div>"""


def generate_html(finishers, biggest, md, sd, tdb):
    now = datetime.datetime.now().strftime("%d/%m/%Y a %H:%M")
    tmjs = {str(yr): [{"race": r["race"], "city": r["city"], "finishers": r["finishers"] or 0, "avg": r["avg"] or ""}
                       for r in rows if r.get("avg")] for yr, rows in md.items()}
    tsjs = [{"race": r["race"], "city": r["city"], "finishers": r["finishers"] or 0, "avg": r["avg"] or ""}
            for r in sd if r.get("avg")]
    tdbjs = {k: {"men": v["men"], "women": v["women"], "avg": v["avg"], "yr": v["yr"]} for k, v in tdb.items()}
    js_data = ("const RAW=" + j(finishers) + ";\nconst BIGGEST=" + j(biggest) + ";\n"
               "const TEMPS_MARATHON=" + j(tmjs) + ";\nconst TEMPS_SEMI_2025=" + j(tsjs) + ";\n"
               "const TIMES_DB=" + j(tdbjs) + ";\nconst ASO_KEYWORDS=" + j(ASO_KEYWORDS) + ";\n")
    body = HTML_BODY.format(now=now)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DataPace - Finishers Monde</title>
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
    check_files()
    print("\nLecture des donnees...")
    finishers = load_finishers()
    biggest = load_biggest()
    md = {yr: load_marathon(yr) for yr in [2024, 2025, 2026]}
    sd = load_semi()
    tdb = build_times_db(md, sd)
    print("\nGeneration du HTML...")
    html = generate_html(finishers, biggest, md, sd, tdb)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"\nDashboard genere : {OUTPUT_FILE.name}  ({OUTPUT_FILE.stat().st_size // 1024} Ko)")
    print("Ouvre ce fichier dans le navigateur via http://localhost:8000/datapace_dashboard.html\n")


if __name__ == "__main__":
    main()

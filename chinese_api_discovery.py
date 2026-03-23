#!/usr/bin/env python3
"""
Agent automatise pour decouvrir les APIs des apps chinoises de resultats de courses.

Workflow complet :
1. Lance mitmweb (proxy d'interception HTTPS)
2. Demarre l'emulateur Android avec proxy
3. Telecharge et installe les APK chinoises
4. Navigue automatiquement dans les apps vers les pages de resultats
5. Collecte et analyse les requetes API interceptees par mitmproxy

Usage :
    python chinese_api_discovery.py              # Workflow complet
    python chinese_api_discovery.py download      # Telecharger les APK seulement
    python chinese_api_discovery.py monitor       # Surveiller mitmproxy seulement
    python chinese_api_discovery.py analyze       # Analyser les flows captures
    python chinese_api_discovery.py browse        # Ouvrir les sites chinois dans l'emulateur
"""

import subprocess
import sys
import os
import time
import json
import re
import io
import signal
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# === CONFIGURATION ===
SCRIPT_DIR = Path(__file__).parent
ANDROID_SDK = Path(os.environ.get("ANDROID_HOME",
    Path.home() / "AppData" / "Local" / "Android" / "Sdk"))
ADB = ANDROID_SDK / "platform-tools" / "adb.exe"
EMULATOR = ANDROID_SDK / "emulator" / "emulator.exe"
MITMPROXY_CERT = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.cer"
APK_DIR = SCRIPT_DIR / "apk_chinois"
FLOWS_DIR = SCRIPT_DIR / "mitmproxy_flows"
DISCOVERED_APIS_FILE = SCRIPT_DIR / "chinese_apis_discovered.json"

PROXY_HOST = "10.0.2.2"
PROXY_PORT = 8080
MITMWEB_PORT = 8081

# Apps chinoises a tester et leurs URLs de resultats
CHINESE_APPS = {
    "geexek": {
        "name": "Saike (赛客)",
        "package": "com.geexek.app",
        "urls": [
            "https://www.geexek.com/score",
            "https://www.geexek.com/score/search?keyword=马拉松",
            "https://www.geexek.com/cmpt",
        ],
        "api_patterns": ["geexek.com", "api.geexek.com", "timer.geexek.com"],
    },
    "mararun": {
        "name": "Mararun (马拉马拉)",
        "package": "com.mararun.app",
        "urls": [
            "https://beijing-registration.mararun.com/score.html",
            "https://m.mararun.com/",
        ],
        "api_patterns": ["mararun.com", "saas-user-gw.mararun.com"],
    },
    "zuicool": {
        "name": "Zuicool (最酷)",
        "package": "com.zuicool.app",
        "urls": [
            "https://www.zuicool.com/",
        ],
        "api_patterns": ["zuicool.com", "api.zuicool.com"],
    },
    "iranshao": {
        "name": "iranshao (爱燃烧)",
        "package": "com.iranshao.app",
        "urls": [
            "https://iranshao.com/",
        ],
        "api_patterns": ["iranshao.com", "api.iranshao.com"],
    },
    "runchina": {
        "name": "CAA (中国田径协会)",
        "package": "org.runchina.app",
        "urls": [
            "https://www.runchina.org.cn/",
        ],
        "api_patterns": ["runchina.org.cn"],
    },
}

# Sites web chinois de resultats (pas besoin d'APK)
CHINESE_WEBSITES = [
    {"url": "https://www.geexek.com/score/search?keyword=北京马拉松", "name": "Geexek - Beijing Marathon"},
    {"url": "https://www.geexek.com/score/search?keyword=上海马拉松", "name": "Geexek - Shanghai Marathon"},
    {"url": "https://www.geexek.com/score/search?keyword=厦门马拉松", "name": "Geexek - Xiamen Marathon"},
    {"url": "https://beijing-registration.mararun.com/score.html", "name": "Mararun - Beijing Marathon"},
    {"url": "https://www.zuicool.com/", "name": "Zuicool - Results"},
]


def log(msg, level="INFO"):
    """Affiche un message avec timestamp."""
    ts = time.strftime("%H:%M:%S")
    prefix = {"INFO": " ", "OK": "+", "WARN": "!", "ERR": "x", "STEP": "#"}
    print(f"[{ts}] [{prefix.get(level, ' ')}] {msg}")


def run_cmd(cmd, check=False, timeout=60):
    """Execute une commande shell."""
    result = subprocess.run(
        [str(c) for c in cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result


def is_mitmweb_running():
    """Verifie si mitmweb tourne deja (check port binding)."""
    import socket
    for port in [PROXY_PORT, MITMWEB_PORT]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            s.close()
            if result == 0:
                return True
        except Exception:
            pass
    return False


def start_mitmweb():
    """Demarre mitmweb en arriere-plan avec l'addon de capture."""
    if is_mitmweb_running():
        log("mitmweb deja en cours (ports 8080/8081 ouverts)", "OK")
        return True

    log("Demarrage de mitmweb...")
    import shutil
    mitmweb_path = shutil.which("mitmweb") or shutil.which("mitmweb.exe")

    if not mitmweb_path:
        log("mitmweb non trouve ! Installe-le : pip install mitmproxy", "ERR")
        return False

    # Addon de capture
    addon_path = SCRIPT_DIR / "mitmproxy_capture.py"

    # Demarrer mitmweb avec l'addon
    cmd = [mitmweb_path,
           "--listen-port", str(PROXY_PORT),
           "--web-port", str(MITMWEB_PORT),
           "--set", "connection_strategy=lazy"]
    if addon_path.exists():
        cmd.extend(["-s", str(addon_path)])

    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Attendre qu'il soit pret
    for i in range(20):
        time.sleep(1)
        if is_mitmweb_running():
            log(f"mitmweb demarre (proxy:{PROXY_PORT}, web:{MITMWEB_PORT})", "OK")
            if addon_path.exists():
                log(f"Addon de capture actif -> {FLOWS_DIR / 'live_capture.jsonl'}", "OK")
            return True

    log("mitmweb n'a pas demarre dans les 20s", "ERR")
    return False


def is_emulator_running():
    """Verifie si l'emulateur Android tourne."""
    result = run_cmd([ADB, "devices"])
    return "emulator-" in result.stdout


def start_emulator():
    """Demarre l'emulateur avec proxy."""
    if is_emulator_running():
        log("Emulateur deja en cours", "OK")
        return True

    # Lister les AVDs
    result = run_cmd([EMULATOR, "-list-avds"])
    avds = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
    if not avds:
        log("Aucun AVD trouve ! Cree-en un dans Android Studio.", "ERR")
        return False

    avd = avds[0]
    log(f"Demarrage de l'emulateur '{avd}' avec proxy {PROXY_HOST}:{PROXY_PORT}...")

    subprocess.Popen(
        [str(EMULATOR), "-avd", avd,
         "-http-proxy", f"http://{PROXY_HOST}:{PROXY_PORT}",
         "-no-snapshot-load"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Attendre le boot
    for i in range(90):
        time.sleep(2)
        result = run_cmd([ADB, "shell", "getprop", "sys.boot_completed"])
        if result.stdout.strip() == "1":
            log(f"Emulateur pret apres {(i+1)*2}s", "OK")
            # Configurer le proxy global
            run_cmd([ADB, "shell", "settings", "put", "global", "http_proxy",
                     f"{PROXY_HOST}:{PROXY_PORT}"])
            return True
        if i % 10 == 0 and i > 0:
            log(f"  ...{(i+1)*2}s")

    log("Timeout demarrage emulateur", "ERR")
    return False


def install_cert():
    """Installe le certificat mitmproxy dans l'emulateur."""
    if not MITMPROXY_CERT.exists():
        log("Certificat mitmproxy absent. Lance mitmweb d'abord.", "WARN")
        return False

    log("Installation du certificat mitmproxy...")
    run_cmd([ADB, "push", str(MITMPROXY_CERT), "/sdcard/mitmproxy-ca-cert.cer"])

    # Ouvrir les settings de securite
    run_cmd([ADB, "shell", "am", "start", "-a", "android.settings.SECURITY_SETTINGS"])
    time.sleep(2)

    log("Certificat copie sur /sdcard/mitmproxy-ca-cert.cer", "OK")
    log("ACTION MANUELLE : Settings > Security > Install CA certificate", "WARN")
    log("  OU ouvre Chrome > http://mitm.it dans l'emulateur", "WARN")
    return True


def download_apk(app_key):
    """Telecharge un APK depuis apkpure.com."""
    APK_DIR.mkdir(exist_ok=True)
    app = CHINESE_APPS.get(app_key)
    if not app:
        log(f"App inconnue : {app_key}", "ERR")
        return None

    apk_path = APK_DIR / f"{app_key}.apk"
    if apk_path.exists():
        log(f"APK deja telecharge : {apk_path}", "OK")
        return apk_path

    log(f"Telecharge l'APK manuellement pour {app['name']}:", "WARN")
    log(f"  1. Va sur https://apkpure.com et recherche '{app_key}'", "WARN")
    log(f"  2. Telecharge l'APK", "WARN")
    log(f"  3. Place-le dans : {apk_path}", "WARN")
    return None


def install_apk(apk_path):
    """Installe un APK dans l'emulateur."""
    if not Path(apk_path).exists():
        log(f"APK non trouve : {apk_path}", "ERR")
        return False

    log(f"Installation de {apk_path}...")
    result = run_cmd([ADB, "install", "-r", str(apk_path)], timeout=120)
    if "Success" in result.stdout:
        log("APK installe", "OK")
        return True
    else:
        log(f"Echec installation : {result.stdout} {result.stderr}", "ERR")
        return False


def open_url_in_emulator(url, wait=3):
    """Ouvre une URL dans Chrome de l'emulateur."""
    run_cmd([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url])
    log(f"Ouvert : {url}")
    time.sleep(wait)


def browse_chinese_sites():
    """Ouvre tous les sites chinois dans l'emulateur pour capturer le traffic."""
    if not is_emulator_running():
        log("Emulateur non demarre !", "ERR")
        return

    log("Navigation automatique sur les sites chinois...", "STEP")
    log("Surveille mitmweb sur http://localhost:8081 pendant la navigation", "WARN")
    print()

    for site in CHINESE_WEBSITES:
        log(f">>> {site['name']}")
        open_url_in_emulator(site["url"], wait=5)

    print()
    log("Navigation terminee. Verifie mitmweb pour les requetes capturees.", "OK")
    log("Filtre utile dans mitmweb : ~d geexek.com | ~d mararun.com | ~d zuicool.com", "INFO")


def get_mitmproxy_flows():
    """Recupere les flows captures depuis le fichier live_capture.jsonl."""
    capture_file = FLOWS_DIR / "live_capture.jsonl"
    if not capture_file.exists():
        log("Aucun fichier de capture trouve.", "WARN")
        log(f"  Attendu : {capture_file}", "INFO")
        log("  mitmweb doit tourner avec l'addon mitmproxy_capture.py", "INFO")
        return []

    flows = []
    with open(capture_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    flows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return flows


def analyze_flows():
    """Analyse les flows captures (deja pre-filtres par l'addon)."""
    log("Analyse des flows mitmproxy...", "STEP")

    api_calls = get_mitmproxy_flows()
    if not api_calls:
        log("Aucun flow capture. Assure-toi que mitmweb tourne et que du traffic passe.", "WARN")
        return []

    log(f"{len(api_calls)} requetes API capturees")

    # Afficher les resultats
    log(f"{len(api_calls)} requetes API trouvees :", "OK")
    print()

    # Grouper par domaine
    by_domain = {}
    for call in api_calls:
        domain = call.get("host", "unknown")
        by_domain.setdefault(domain, []).append(call)

    for domain, calls in sorted(by_domain.items()):
        print(f"  === {domain} ({len(calls)} calls) ===")
        # Deduplicate by path
        seen_paths = set()
        shown = 0
        for call in calls:
            path_key = call.get("path", "").split("?")[0]
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)
            auth = " [AUTH]" if call.get("auth_headers") else ""
            json_tag = " [JSON]" if call.get("is_json") else ""
            body = ""
            if call.get("body_preview"):
                body = f" ({len(call['body_preview'])} chars)"
            print(f"    {call.get('method','?')} {call.get('path','')[:80]} "
                  f"-> {call.get('status','?')}{auth}{json_tag}{body}")
            if call.get("auth_headers"):
                for k, v in call["auth_headers"].items():
                    print(f"      {k}: {v[:80]}...")
            shown += 1
            if shown >= 15:
                remaining = len(seen_paths.symmetric_difference(
                    {c.get("path","").split("?")[0] for c in calls}))
                if remaining > 0:
                    print(f"    ... et d'autres requetes")
                break
        print()

    # Sauvegarder le resume consolide
    FLOWS_DIR.mkdir(exist_ok=True)
    save_discovered_apis(api_calls)

    return api_calls


def save_discovered_apis(api_calls):
    """Sauvegarde les APIs decouvertes dans un fichier consolide."""
    existing = {}
    if DISCOVERED_APIS_FILE.exists():
        with open(DISCOVERED_APIS_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)

    apis = existing.get("apis", {})
    for call in api_calls:
        key = f"{call['method']} {call['host']}{call['path'].split('?')[0]}"
        if key not in apis:
            apis[key] = {
                "method": call["method"],
                "url": call["url"].split("?")[0],
                "host": call["host"],
                "auth_headers": call["auth_headers"],
                "is_json": call["is_json"],
                "first_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
                "hit_count": 1,
            }
        else:
            apis[key]["hit_count"] += 1
            if call["auth_headers"] and not apis[key]["auth_headers"]:
                apis[key]["auth_headers"] = call["auth_headers"]

    output = {
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_apis": len(apis),
        "apis": apis,
    }
    with open(DISCOVERED_APIS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    log(f"APIs consolidees : {len(apis)} endpoints dans {DISCOVERED_APIS_FILE}", "OK")


def full_workflow():
    """Workflow complet : mitmweb + emulateur + navigation + analyse."""
    print("=" * 60)
    print("  DECOUVERTE D'APIs CHINOISES DE RESULTATS DE COURSES")
    print("=" * 60)
    print()

    # Etape 1 : mitmweb
    log("ETAPE 1/5 : Demarrage de mitmweb", "STEP")
    if not start_mitmweb():
        return False
    print()

    # Etape 2 : Emulateur
    log("ETAPE 2/5 : Demarrage de l'emulateur Android", "STEP")
    if not start_emulator():
        return False
    print()

    # Etape 3 : Certificat
    log("ETAPE 3/5 : Installation du certificat SSL", "STEP")
    if MITMPROXY_CERT.exists():
        install_cert()
        # Verifier si le certificat est deja installe en testant mitm.it
        log("Verification : ouvre http://mitm.it dans Chrome de l'emulateur", "INFO")
        open_url_in_emulator("http://mitm.it", wait=3)
    else:
        log("Certificat pas encore genere, mitmweb vient de demarrer.", "WARN")
        log("Le certificat sera genere au premier traffic intercepte.", "INFO")
    print()

    # Etape 4 : APK et navigation
    log("ETAPE 4/5 : Installation des APK et navigation", "STEP")

    # Verifier les APK disponibles
    APK_DIR.mkdir(exist_ok=True)
    installed_any = False
    for app_key, app_info in CHINESE_APPS.items():
        apk_path = APK_DIR / f"{app_key}.apk"
        if apk_path.exists():
            log(f"Installation de {app_info['name']}...")
            if install_apk(apk_path):
                installed_any = True

    if not installed_any:
        log("Aucun APK trouve. Navigation web a la place.", "INFO")
        log(f"Pour ajouter des APK, place-les dans : {APK_DIR}", "INFO")
        for app_key in CHINESE_APPS:
            log(f"  - {APK_DIR / app_key}.apk", "INFO")

    # Naviguer sur les sites web chinois
    print()
    browse_chinese_sites()
    print()

    # Etape 5 : Analyse
    log("ETAPE 5/5 : Analyse des requetes capturees", "STEP")
    log("Attente de 5s pour laisser les dernieres requetes arriver...")
    time.sleep(5)
    api_calls = analyze_flows()
    print()

    # Resume
    print("=" * 60)
    print("  RESUME")
    print("=" * 60)
    print()
    if api_calls:
        log(f"{len(api_calls)} endpoints API decouverts !", "OK")
        log(f"Details dans : {DISCOVERED_APIS_FILE}", "INFO")
        print()
        log("Prochaines etapes :", "INFO")
        log("  1. Examine les APIs decouvertes dans le fichier JSON", "INFO")
        log("  2. Teste les endpoints avec curl", "INFO")
        log("  3. Navigue manuellement dans l'emulateur pour decouvrir plus d'APIs", "INFO")
        log("  4. Relance 'python chinese_api_discovery.py analyze' apres navigation", "INFO")
    else:
        log("Aucune API detectee. Causes possibles :", "WARN")
        log("  - Certificat SSL pas installe (ouvre http://mitm.it dans l'emulateur)", "WARN")
        log("  - Les sites chinois sont bloques ou redirigent vers WeChat", "WARN")
        log("  - Navigue manuellement et relance 'analyze'", "WARN")

    print()
    log(f"mitmweb reste actif sur http://localhost:{MITMWEB_PORT}", "INFO")
    log("Navigue manuellement dans l'emulateur pour decouvrir plus d'APIs.", "INFO")
    log("Puis relance : python chinese_api_discovery.py analyze", "INFO")

    return True


def main():
    if len(sys.argv) < 2:
        full_workflow()
        return

    command = sys.argv[1].lower()

    if command == "download":
        log("Telechargement des APK chinoises", "STEP")
        for app_key in CHINESE_APPS:
            download_apk(app_key)
    elif command == "monitor" or command == "watch":
        log("Surveillance continue des flows mitmproxy (Ctrl+C pour arreter)", "STEP")
        seen = set()
        while True:
            try:
                flows = get_mitmproxy_flows()
                for flow in flows:
                    fid = flow.get("id", "")
                    if fid in seen:
                        continue
                    seen.add(fid)
                    req = flow.get("request", {})
                    host = req.get("host", "")
                    path = req.get("path", "")
                    # Filtrer les domaines chinois
                    target_domains = set()
                    for app in CHINESE_APPS.values():
                        target_domains.update(app["api_patterns"])
                    if any(d in host for d in target_domains):
                        resp = flow.get("response", {})
                        status = resp.get("status_code", "?")
                        print(f"  [{status}] {req.get('method','?')} https://{host}{path[:80]}")
                time.sleep(2)
            except KeyboardInterrupt:
                print("\nArret de la surveillance.")
                break
    elif command == "analyze":
        analyze_flows()
    elif command == "browse":
        if not is_emulator_running():
            log("Emulateur non demarre ! Lance 'full' d'abord.", "ERR")
            return
        browse_chinese_sites()
    elif command == "status":
        print(f"mitmweb : {'actif' if is_mitmweb_running() else 'inactif'}")
        print(f"Emulateur : {'actif' if is_emulator_running() else 'inactif'}")
        print(f"Certificat : {'present' if MITMPROXY_CERT.exists() else 'absent'}")
        apks = list(APK_DIR.glob("*.apk")) if APK_DIR.exists() else []
        print(f"APK disponibles : {len(apks)} dans {APK_DIR}")
        for apk in apks:
            print(f"  - {apk.name}")
        if DISCOVERED_APIS_FILE.exists():
            with open(DISCOVERED_APIS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"APIs decouvertes : {data.get('total_apis', 0)}")
    elif command == "stop":
        log("Arret de l'emulateur...")
        run_cmd([ADB, "emu", "kill"])
        log("Emulateur arrete", "OK")
    else:
        print(f"Commande inconnue : {command}")
        print("Commandes : download, monitor, analyze, browse, status, stop")
        print("Sans argument : workflow complet")


if __name__ == "__main__":
    main()

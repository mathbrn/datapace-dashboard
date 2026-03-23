#!/usr/bin/env python3
"""
Script d'automatisation pour configurer l'émulateur Android avec mitmproxy.

Étapes automatisées :
1. Démarrer l'émulateur avec proxy HTTP pointant vers mitmproxy
2. Attendre que l'émulateur soit prêt
3. Installer le certificat CA de mitmproxy
4. Installer des APK (si fournis en argument)

Usage :
    python setup_android_emulator.py                    # Démarre l'émulateur avec proxy
    python setup_android_emulator.py install app.apk    # Installe un APK
    python setup_android_emulator.py cert               # Installe le certificat mitmproxy
    python setup_android_emulator.py full                # Setup complet (start + cert)
    python setup_android_emulator.py stop                # Arrête l'émulateur

Prérequis :
    - Android Studio installé avec un AVD créé
    - mitmproxy installé (pip install mitmproxy)
"""

import subprocess
import sys
import time
import os
import shutil
from pathlib import Path

# === CONFIGURATION ===
ANDROID_SDK = Path(os.environ.get("ANDROID_HOME",
    Path.home() / "AppData" / "Local" / "Android" / "Sdk"))
EMULATOR = ANDROID_SDK / "emulator" / "emulator.exe"
ADB = ANDROID_SDK / "platform-tools" / "adb.exe"
MITMPROXY_CERT = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.cer"
PROXY_HOST = "10.0.2.2"  # Adresse spéciale de l'émulateur pour accéder au host
PROXY_PORT = 8080


def run(cmd, check=True, capture=True, timeout=60):
    """Exécute une commande et retourne le résultat."""
    print(f"  > {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(
        [str(c) for c in cmd],
        capture_output=capture,
        text=True,
        timeout=timeout
    )
    if check and result.returncode != 0:
        stderr = result.stderr if capture else ""
        print(f"  ERREUR: {stderr}")
    return result


def list_avds():
    """Liste les AVDs disponibles."""
    result = run([EMULATOR, "-list-avds"], check=False)
    avds = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    return avds


def is_emulator_running():
    """Vérifie si un émulateur est déjà en cours."""
    result = run([ADB, "devices"], check=False)
    return "emulator-" in result.stdout


def start_emulator(avd_name=None):
    """Démarre l'émulateur avec le proxy HTTP configuré."""
    if is_emulator_running():
        print("✓ Émulateur déjà en cours d'exécution")
        return True

    avds = list_avds()
    if not avds:
        print("ERREUR: Aucun AVD trouvé. Créez-en un dans Android Studio.")
        print("  Tools → Device Manager → Create Virtual Device")
        return False

    avd = avd_name or avds[0]
    print(f"Démarrage de l'émulateur '{avd}' avec proxy {PROXY_HOST}:{PROXY_PORT}...")

    # Démarrer l'émulateur en arrière-plan avec proxy
    subprocess.Popen(
        [str(EMULATOR), "-avd", avd,
         "-http-proxy", f"http://{PROXY_HOST}:{PROXY_PORT}",
         "-no-snapshot-load"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Attendre que l'émulateur soit prêt
    print("Attente du démarrage de l'émulateur...")
    for i in range(90):  # 90 secondes max
        time.sleep(2)
        result = run([ADB, "shell", "getprop", "sys.boot_completed"], check=False)
        if result.stdout.strip() == "1":
            print(f"✓ Émulateur prêt après {(i+1)*2}s")
            return True
        if i % 5 == 0:
            print(f"  ...{(i+1)*2}s")

    print("ERREUR: Timeout - l'émulateur n'a pas démarré dans les 180s")
    return False


def configure_proxy():
    """Configure le proxy WiFi dans l'émulateur."""
    print("Configuration du proxy WiFi...")

    # Configurer le proxy global via settings
    run([ADB, "shell", "settings", "put", "global", "http_proxy",
         f"{PROXY_HOST}:{PROXY_PORT}"], check=False)

    print(f"✓ Proxy configuré : {PROXY_HOST}:{PROXY_PORT}")
    return True


def install_mitmproxy_cert():
    """Installe le certificat CA de mitmproxy dans l'émulateur."""
    if not MITMPROXY_CERT.exists():
        print("Le certificat mitmproxy n'existe pas encore.")
        print("Lance d'abord mitmproxy/mitmweb pour le générer :")
        print("  mitmweb")
        print(f"Certificat attendu : {MITMPROXY_CERT}")
        return False

    print("Installation du certificat mitmproxy...")

    # Calculer le hash du certificat pour le nom de fichier système
    # Android utilise le hash du sujet comme nom de fichier
    import hashlib

    # Copier le certificat sur l'émulateur
    remote_cert = "/sdcard/mitmproxy-ca-cert.cer"
    run([ADB, "push", str(MITMPROXY_CERT), remote_cert])

    # Installer le certificat utilisateur via intent
    # L'utilisateur devra confirmer manuellement dans l'UI
    run([ADB, "shell", "am", "start", "-a", "android.settings.SECURITY_SETTINGS"], check=False)

    print("✓ Certificat copié sur l'émulateur")
    print("")
    print("=== ACTION MANUELLE REQUISE ===")
    print("Dans l'émulateur, va dans :")
    print("  Settings → Security → Encryption & credentials")
    print("  → Install a certificate → CA certificate")
    print("  → Sélectionne 'mitmproxy-ca-cert.cer'")
    print("")
    print("OU ouvre Chrome dans l'émulateur et va sur http://mitm.it")
    print("pour télécharger et installer le certificat automatiquement.")

    return True


def install_apk(apk_path):
    """Installe un APK sur l'émulateur."""
    if not os.path.exists(apk_path):
        print(f"ERREUR: Fichier APK non trouvé : {apk_path}")
        return False

    print(f"Installation de {apk_path}...")
    result = run([ADB, "install", "-r", apk_path], timeout=120)

    if "Success" in result.stdout:
        print(f"✓ APK installé avec succès")
        return True
    else:
        print(f"ERREUR: {result.stdout}")
        return False


def stop_emulator():
    """Arrête l'émulateur."""
    print("Arrêt de l'émulateur...")
    run([ADB, "emu", "kill"], check=False)
    print("✓ Émulateur arrêté")


def open_browser(url="http://mitm.it"):
    """Ouvre une URL dans Chrome de l'émulateur."""
    run([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW",
         "-d", url], check=False)
    print(f"✓ Ouvert : {url}")


def check_proxy():
    """Vérifie que le proxy fonctionne."""
    print("Vérification du proxy...")
    result = run([ADB, "shell", "settings", "get", "global", "http_proxy"], check=False)
    proxy = result.stdout.strip()
    if proxy and proxy != "null" and proxy != ":0":
        print(f"✓ Proxy actif : {proxy}")
    else:
        print("⚠ Proxy non configuré, configuration...")
        configure_proxy()

    # Tester la connectivité
    result = run([ADB, "shell", "ping", "-c", "1", "-W", "3", PROXY_HOST], check=False)
    if result.returncode == 0:
        print(f"✓ Host {PROXY_HOST} accessible")
    else:
        print(f"⚠ Host {PROXY_HOST} non accessible (normal si mitmproxy pas démarré)")


def full_setup():
    """Setup complet : démarrer + proxy + certificat."""
    print("=" * 50)
    print("SETUP COMPLET ÉMULATEUR ANDROID + MITMPROXY")
    print("=" * 50)
    print()

    # Vérifier que mitmproxy est disponible
    mitmweb = shutil.which("mitmweb")
    if not mitmweb:
        print("⚠ mitmweb non trouvé dans le PATH")
        print("  Installe-le : pip install mitmproxy")
    else:
        print(f"✓ mitmweb trouvé : {mitmweb}")
    print()

    # Étape 1 : Démarrer l'émulateur
    print("[1/4] Démarrage de l'émulateur...")
    if not start_emulator():
        return False
    print()

    # Étape 2 : Configurer le proxy
    print("[2/4] Configuration du proxy...")
    configure_proxy()
    print()

    # Étape 3 : Vérifier la connectivité
    print("[3/4] Vérification...")
    check_proxy()
    print()

    # Étape 4 : Installer le certificat
    print("[4/4] Installation du certificat...")
    install_mitmproxy_cert()
    print()

    print("=" * 50)
    print("SETUP TERMINÉ")
    print("=" * 50)
    print()
    print("Prochaines étapes :")
    print("1. Lance mitmweb sur le PC (si pas déjà fait)")
    print("2. Installe le certificat dans l'émulateur (voir instructions ci-dessus)")
    print("3. Ouvre Chrome dans l'émulateur → http://mitm.it pour vérifier")
    print("4. Navigue sur les sites/apps chinoises et observe les requêtes dans mitmweb")
    print()
    print("Pour installer un APK :")
    print("  python setup_android_emulator.py install chemin/vers/app.apk")
    print()
    print("Pour des apps chinoises, télécharge les APK depuis :")
    print("  - apkpure.com")
    print("  - apkcombo.com")
    print("  Recherche : geexek (赛客), iranshao (爱燃烧), gudong (咕咚)")

    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAVDs disponibles :")
        for avd in list_avds():
            print(f"  - {avd}")
        print(f"\nÉmulateur en cours : {'Oui' if is_emulator_running() else 'Non'}")
        return

    command = sys.argv[1].lower()

    if command == "start":
        avd = sys.argv[2] if len(sys.argv) > 2 else None
        start_emulator(avd)
    elif command == "stop":
        stop_emulator()
    elif command == "cert":
        install_mitmproxy_cert()
    elif command == "proxy":
        configure_proxy()
    elif command == "check":
        check_proxy()
    elif command == "install":
        if len(sys.argv) < 3:
            print("Usage: python setup_android_emulator.py install <apk_path>")
            return
        install_apk(sys.argv[2])
    elif command == "open":
        url = sys.argv[2] if len(sys.argv) > 2 else "http://mitm.it"
        open_browser(url)
    elif command == "full":
        full_setup()
    elif command == "list":
        print("AVDs disponibles :")
        for avd in list_avds():
            print(f"  - {avd}")
    else:
        print(f"Commande inconnue : {command}")
        print("Commandes : start, stop, cert, proxy, check, install, open, full, list")


if __name__ == "__main__":
    main()

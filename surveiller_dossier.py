"""
DataPace - Surveillant automatique
====================================
Lance generer_dashboard.bat automatiquement
dès qu'un fichier Excel est modifié.

Usage :
    Double-clique sur ce fichier, ou lance :
    python surveiller_dossier.py

Laisse la fenêtre ouverte en arrière-plan.
Pour arrêter : ferme la fenêtre ou Ctrl+C
"""

import time
import os
import subprocess
from pathlib import Path

DOSSIER = Path(__file__).parent
BAT_FILE = DOSSIER / "generer_dashboard.bat"
DELAI_SECONDES = 5  # Attendre 5s après la dernière modif avant de lancer

def get_excel_dates():
    """Retourne un dict {fichier: date_modification} pour tous les Excel du dossier."""
    return {
        f: f.stat().st_mtime
        for f in DOSSIER.glob("*.xlsx")
    }

def lancer_bat():
    print("\n>>> Modification detectee ! Lancement de generer_dashboard.bat...")
    subprocess.run(str(BAT_FILE), shell=True)
    print(">>> Dashboard mis a jour et pousse sur GitHub.\n")
    print("En surveillance... (Ctrl+C pour arreter)\n")

def main():
    print("=" * 50)
    print("  DataPace - Surveillance automatique")
    print("=" * 50)
    print(f"\nDossier surveille : {DOSSIER}")
    print(f"Fichiers surveilles : {len(list(DOSSIER.glob('*.xlsx')))} fichiers Excel")
    print("\nEn attente de modifications...\n")

    dates_precedentes = get_excel_dates()
    derniere_modif = 0

    while True:
        try:
            dates_actuelles = get_excel_dates()

            # Vérifie si un fichier a changé
            modifie = False
            for fichier, mtime in dates_actuelles.items():
                if fichier not in dates_precedentes or mtime != dates_precedentes[fichier]:
                    print(f"  Changement detecte : {fichier.name}")
                    modifie = True
                    derniere_modif = time.time()

            # Attend que les modifications se stabilisent (ex: sauvegarde Excel en cours)
            if modifie:
                dates_precedentes = dates_actuelles

            # Lance le bat seulement si un changement a eu lieu
            # et qu'il n'y a plus eu de modif depuis DELAI_SECONDES
            if derniere_modif > 0 and (time.time() - derniere_modif) >= DELAI_SECONDES:
                lancer_bat()
                derniere_modif = 0

            time.sleep(2)  # Vérifie toutes les 2 secondes

        except KeyboardInterrupt:
            print("\nSurveillance arretee.")
            break
        except Exception as e:
            print(f"Erreur : {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()

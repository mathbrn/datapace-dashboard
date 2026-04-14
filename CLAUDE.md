# Dashboard Running - Consignes de projet

## Architecture des donnees

### Source de verite pour le dashboard
`generate_dashboard.py` utilise **SQLite en priorite** si `datapace.db` existe, sinon les fichiers Excel.
- Si `datapace.db` existe → lit depuis SQLite (tables `events`, `finishers`, `winners`, `avg_times`)
- Sinon → lit depuis les fichiers Excel

### Ou sont stockes les noms d'evenements (TOUS a modifier lors d'un renommage)
1. **`datapace.db`** (SQLite) : table `events` colonne `name` — **SOURCE PRIMAIRE du dashboard**. Les tables `finishers`, `winners`, `avg_times` referencent par `event_id` (FK).
2. **`Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx`** : onglet ALL, colonne D (Race)
3. **`Chronos_Vainqueurs.xlsx`** : colonne Race (genere par `create_chronos.py`, verifier aussi le .py)
4. **`_event_list.json`** : liste plate des noms d'evenements
5. **`event_websites.json`** : cles = noms d'evenements
6. **`sponsoring_data.json`** : champ `event` dans chaque entree
7. **`scraped_partners.json`** : champ `event`
8. **`compile_websites.py`** : appels `add("NomEvenement", ...)`
9. **`_scrape_queue.json`** : champ `event`

### Ou sont stockees les donnees de finishers
1. **`datapace.db`** : table `finishers` (event_id, year, count, source)
2. **`Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx`** : onglet ALL (colonnes annees 2000-2026), onglet BIGGEST EVENTS
3. **`avg_times_sporthive.json`** : temps moyens calcules depuis APIs

### Ou sont stockes les temps vainqueurs
1. **`datapace.db`** : table `winners` (event_id, year, men_time, women_time)
2. **`Chronos_Vainqueurs.xlsx`** : genere par `create_chronos.py` (donnees en dur dans le script)

### Ou sont stockes les temps moyens
1. **`datapace.db`** : table `avg_times`
2. **`Temps_moyen_semi-marathon.xlsx`** : multi-feuilles par annee
3. **`Temps_moyen_par_marathon_{2024,2025,2026}.xlsx`** : une feuille par annee
4. **`avg_times_sporthive.json`** : temps moyens calcules depuis APIs (Sporthive + Tracx)

### Fichiers principaux

- `generate_dashboard.py` : Generateur du dashboard HTML (lit SQLite ou Excel + JSON)
- `datapace.db` : Base SQLite (source primaire si presente)
- `Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx` : Donnees finishers (onglet ALL + BIGGEST EVENTS)
- `Chronos_Vainqueurs.xlsx` : Temps vainqueurs H/F (genere par `create_chronos.py`)
- `Temps_moyen_semi-marathon.xlsx` : Temps moyens semi (multi-feuilles par annee)
- `Temps_moyen_par_marathon_{2024,2025,2026}.xlsx` : Temps moyens marathon
- `avg_times_sporthive.json` : Temps moyens calcules depuis APIs (Sporthive + Tracx)
- `datapace_dashboard.html` : Dashboard genere (ouvrir dans navigateur)

## Regles strictes

### Validation permanente (onglet Temps moyen)
- `generate_dashboard.py` execute `validate_data()` apres chaque `load_marathon()`, `load_semi()` et `load_sporthive_avg()`
- La validation detecte : encodage casse (Ã), noms generiques (Marathon, 42.2 KM...), annees residuelles dans les noms, chronos sans zero initial
- **Regle** : apres chaque ajout de donnees dans les fichiers Excel Temps_moyen_*, relancer `python generate_dashboard.py` et verifier qu'aucun avertissement VALIDATION n'apparait avant de pusher
- Les noms invalides sont filtres par `is_invalid_race_name()` et `INVALID_RACE_NAMES`
- L'encodage est corrige iterativement par `fix_encoding()` (cp1252→UTF-8, latin-1→UTF-8, jusqu'a 5 passes)

### Donnees finishers
- **JAMAIS ecraser une cellule deja remplie** dans le fichier Excel finishers. Le script `update_finishers.py` a une protection [SKIP].
- **ZERO tolerance pour les chiffres ronds** (10000, 20000, 30000...). Ce sont des estimations ou des caps d'inscription, pas des finishers exacts.
- **Exclure les finishers VIRTUAL** des comptages. Toujours filtrer "virtual" dans les APIs.
- **Exclure les courses de plus de 42.195km** (pas d'ultras, pas de trail).
- Cellules speciales dans le Excel : `-` = edition annulee, `Elite` = edition elite uniquement, `x` = evenement n'existait pas encore.

### Distances
- `MARATHON` : 42.195km
- `SEMI` : ~21.1km (half marathon)
- `10KM` : 10km
- `AUTRE` : distances non-standard (10 miles, 12K, 15K, etc.)

### Badges evenements
- `WMM` (bleu #38BDF8) : World Marathon Majors (NYC, London, Boston, Sydney, Berlin, Chicago, Tokyo)
- `ASO` (jaune #FCDB00) : Evenements ASO (Paris, Lyon, 10K Paris, Montmartre, Manchester, London Winter Run, ASICS LDNX)
- `Autre` (violet #9B6FFF) : Tous les autres

### Premiere edition
- Marquer `x` dans le Excel pour toutes les annees AVANT la premiere edition d'un evenement
- Dashboard : petite etoile dans la couleur de l'evenement sur la cellule de la premiere edition (uniquement si >= 2000)
- Pas d'etoile pour les evenements crees avant 2000

## APIs decouvertes et exploitees

### 1. Sporthive/MYLAPS (MEILLEURE SOURCE)
- **API** : `https://eventresults-api.speedhive.com/sporthive/events/{eventId}/races`
- **Auth** : Aucune
- **Donnees** : `classificationsCount` = finishers, `raceStatistics.averageSpeedInKmh` = vitesse moyenne reelle
- **Decouverte IDs** : `site:results.sporthive.com` sur Google, ou Playwright
- **Calcul temps moyen** : `temps = distance / vitesse`

### 2. Tracx Events
- **API** : `https://api.tracx.events/v1/`
- **Auth** : `Authorization: Bearer 40496C26-9BEF-4266-8A27-43C78540F669`
- **Events** : `GET /events?page=1&per_page=100` (860 events total)
- **Races** : `GET /events/{id}/races` → `participant_count` direct
- **Results** : `GET /events/{id}/races/{raceId}/rankings/{rankingId}/results?page=1` → resultats individuels avec temps
- **Temps vainqueur** : premier resultat male + premier resultat female dans les rankings

### 3. Athlinks (US races)
- **Metadata** : `https://reignite-api.athlinks.com/master/{masterEventId}/metadata`
- **Course** : `https://alaska.athlinks.com/Events/Race/Api/{eventId}/Course/0`
- **Finishers** : `EventCoursesDropDown[].Value` = `courseId:raceId:FINISHER_COUNT:??` (3eme champ)
- **Auth** : Aucune
- **Decouverte IDs** : `site:athlinks.com/event "Event Name"`

### 4. RTRT.me (Great Run events)
- **API** : `https://api.rtrt.me/`
- **Auth** : `appid=623f2dd5e7847810bb1f0a07&token=9FA560A93CFC014488AB`
- **Total** : `GET /events/{code}` → `finishers` = total
- **Par course** : `GET /events/{code}/stats` → `stats.tags.{course}.FINISH-*.valid_count`
- **Codes** : `GR-NORTH-{YYYY}`, `GR-SCOTTISH-{YYYY}`, `GR-MANCHESTER-{YYYY}`, `GR-BRISTOL-{YYYY}`, `GR-BIRMINGHAM-{YYYY}`, `GR-SOUTH-{YYYY}`
- **Couverture** : 2022-2025 uniquement

### 5. TimeTo / SportInnovation (ASO France + resultats individuels)
- **Events** : `https://sportinnovation.fr/api/events`
- **Races** : `https://sportinnovation.fr/api/events/{id}/races`
- **Resultats individuels** : `GET https://sportinnovation.fr/api/races/{raceId}/results` → tableau complet (jusqu'a 57000+ resultats en une requete)
- **Champs** : `sex`, `nationality`, `firstName`, `realTime`, `officialTime`, `generalRanking`, `sexRanking`
- **Finishers** : `totals.maxGeneralRanking` (ou compter les resultats)
- **Auth** : Aucune
- **Couverture** : Marathon de Paris, Semi de Paris, 10K Paris, Run in Lyon, Run in Marseille

### 5b. ACN Timing / ChronoRace (Rotterdam, etc.)
- **Event view** : `GET https://prod.chronorace.be/api/Event/view/{eventId}`
- **Resultats** : `GET https://results.chronorace.be/api/results/table/search/{db}/{tableName}?fromRecord={offset}&pageSize={limit}`
- **Parametres** : `db` = contexte (ex: `20260411_rotterdam`), `tableName` = `LIVE{n}` (scanner LIVE1..LIVE60 pour trouver la bonne table)
- **Structure** : reponse paginee, `Groups[].SlaveRows[]` = tableau de tableaux, colonnes definies dans `TableDefinition.Columns`
- **Colonnes marathon** : Col2=Gender, Col3=Name(HTML), Col14=Location(Finish-), Col15=NetTime(HTML), Col16=GrossTime
- **Astuce** : la table avec le plus de resultats est generalement la table complete (ex: LIVE9=16542 pour Rotterdam vs LIVE31=941 elites)
- **Auth** : Aucune
- **Couverture** : NN Marathon Rotterdam, et potentiellement d'autres evenements ChronoRace

### 6. Active.com (ASO events anciens)
- **Events** : `https://sportinnovation.fr/api/events`
- **Races** : `https://sportinnovation.fr/api/events/{id}/races`
- **Finishers** : `totals.maxGeneralRanking`
- **Auth** : Aucune
- **Couverture** : Marathon de Paris, Semi de Paris, 10K Paris, Run in Lyon, Run in Marseille

### 6. Active.com (ASO events anciens)
- **Events** : `https://resultscui.active.com/api/results/events/{appName}`
- **Count** : `GET /events/{appName}/participants?groupId={overallId}&routeId={id}&offset=0&limit=1` → `meta.totalCount`
- **Auth** : Aucune
- **Noms d'app** : `{Sponsor}{EventName}{Year}` (ex: `SchneiderElectricMarathondeParis2019`, `RunInLyon2018`, `Adidas10KParis2022`)

### 7. Mikatiming (scraping)
- **URL** : `https://{event}.r.mikatiming.com/{year}/?pid=list&event={code}`
- **Codes** : HML=Half Marathon, MAL=Marathon
- **Extraction** : regex `(\d[\d.]*)\s*(?:Ergebnisse|Results)` dans le texte de la page
- **Couverture** : Berlin HM, Frankfurt Marathon, Stockholm

### 8. MarathonView.net (scraping)
- **URL** : `https://marathonview.net/series/{id}`
- **Donnees** : finishers par annee dans le JSON embarque
- **WebFetch** fonctionne
- **Couverture** : 500+ series de marathons mondiaux

### 9. World Athletics GraphQL (catalogue)
- **Endpoint** : `https://graphql-prod-4860.edge.aws.worldathletics.org/graphql`
- **API Key** : `da2-5eqvkoavsnhjxfqd47jvjteray`
- **Operation** : `getCalendarEvents` avec variables startDate/endDate/regionType/limit/offset
- **Donnees** : Catalogue de 807 road races/an (pas de resultats de masse)

### 10. SportTimingSolutions (Inde)
- **API** : `https://sportstimingsolutions.in/frontend/api/`
- **Races** : `GET /event-races?event_id={id}` (base64-encoded)
- **Finishers** : `GET /event/bib/result?event_id={id}&bibNo={bib}` → `brackets[].bracket_participants`
- **Necessite** un bib valide

### 11. Njuko (inscription uniquement)
- **API** : `https://front-api.njuko.com/`
- **Donnees** : Details evenement, competitions, places restantes
- **PAS de resultats** — renvoie vers les plateformes de chronometrage

## Scripts utilitaires

- `update_finishers.py "Race Name" DISTANCE YEAR COUNT` : Met a jour une cellule (avec protection SKIP)
- `add_event.py "Period" "City" "Distance" "Race Name" [YEAR COUNT ...]` : Ajoute un nouvel evenement
- `create_chronos.py` : Genere Chronos_Vainqueurs.xlsx depuis les donnees en dur
- `mark_first_editions.py` : Marque les cellules pre-premiere-edition avec 'x'
- `scrape_finishers.py` : Scraper generique via Playwright (interception reseau)
- `crawl_sporthive.py` : Crawler Sporthive par decouverte d'IDs
- `crawl_tracx.py` : Crawler exhaustif des 860 events Tracx
- `crawl_athlinks.py` : Scanner Athlinks par range d'IDs
- `aggregate_all.py` : Fusionneur de toutes les sources → `unified_race_database.json`

## Auto Update 4D — Systeme automatique

- **Script** : `auto_update_4d.py`
- **Declencheur** : GitHub Actions cron 06h00 UTC quotidien (`.github/workflows/auto_update_4d.yml`)
- **Logs** : `logs/update_4d_{date}.json` (artifact GitHub Actions, retention 30j)
- **Couverture** : 88 evenements mappes sur 202 (via `event_platform_map.json`)
- **Plateformes supportees** : TimeTo, Sporthive, Tracx, ChronoRace, Mikatiming, Sportmaniacs, Endu, RTRT, Athlinks, RunSignup, Ultimate, STS-Timing, RunCzech, MyRunResults, PSE, Splittime, Smartchip, Mararun
- **Sans couverture API** : Tokyo, Valencia, Mexico, Taipei, Singapore (plateformes custom fermees) → **Update 4D manuel requis**
- **WMM avec API identifiee mais non-implementee** : Chicago (mikatiming `results.chicagomarathon.com`), NYC (API POST `rmsprodapi.nyrr.org/api/v2`), Boston (HTML `results.baa.org/{yyyy}/`) → necessite scraper/fetcher dedie dans `auto_update_4d.py`
- **MarathonView.net** : IDs documentes pour les 7 WMM (54=NYC, 55=Berlin, 56=Boston, 57=London, 59=Chicago, 108=Tokyo, 113=Sydney) — API `/api/series` retourne 401, necessite auth ou browser-rendering
- **Protection stricte** : aucune donnee existante ne peut etre ecrasee
  - `[SKIP]` automatique sur `update_finishers.py` (Excel finishers)
  - `[SKIP]` automatique sur `avg_times_sporthive.json` si avg_time deja rempli
  - `[SKIP]` automatique sur `temp_chronos_1.json` si chronos deja remplis
- **Fenetre de date** : ±1 jour autour de la cible (capture les courses dont les resultats sont publies le lendemain)
- **Matching pays** : extraction ISO code depuis WA venue "Paris (FRA)", bonus +5 si match, **malus -10 si mismatch** (evite les faux positifs geographiques)
- **Test manuel** : `python auto_update_4d.py --date YYYY-MM-DD --dry-run`

## Workflow de mise a jour

1. Rechercher les donnees (APIs, web search, scraping)
2. Appliquer via `update_finishers.py` (ne modifie que les cellules vides)
3. Executer `python generate_dashboard.py`
4. **Verifier que les nouvelles donnees apparaissent dans TOUS les onglets du dashboard** : extraire les JSON `RAW`, `TEMPS_MARATHON`, `TEMPS_SEMI`, `TEMPS_AVG`, `TIMES_DB`, `WINNERS` du HTML genere et confirmer que les valeurs ajoutees/modifiees sont presentes dans chaque onglet concerne (Tableau, Vue d'ensemble, Temps moyen, Winners Times...). Ne pas considerer la tache comme terminee tant que cette verification n'est pas faite.
   - **Temps moyens** : doivent apparaitre dans Vue d'ensemble ET dans l'onglet Temps moyen. `generate_dashboard.py` fusionne automatiquement les donnees `avg_times_sporthive.json` dans `TEMPS_MARATHON`/`TEMPS_SEMI` pour les courses absentes des Excel.
   - **Chronos vainqueurs** : doivent apparaitre dans Vue d'ensemble ET dans l'onglet Winners Times. Mettre a jour `create_chronos.py` (donnees en dur) ET `temp_chronos_1.json` (donnees recentes).
   - **Finishers** : doivent apparaitre dans Tableau ET Vue d'ensemble ET Top Evenements.
5. **Toujours commit + push automatiquement** apres chaque modification (ne pas attendre que l'utilisateur le demande)
   `git add -A && git commit && git push`
6. **OBLIGATOIRE : Pousser sur `main`** (meme depuis une branche de feature : merge fast-forward vers main puis push). Le dashboard est heberge sur GitHub Pages : https://mathbrn.github.io/datapace-dashboard/ et sert depuis `main`. Si on travaille sur une branche de feature, faire : `git checkout main && git merge <branche> --ff-only && git push origin main && git checkout <branche>`.

### Update 4D (competence standard pour chaque evenement)
Pour chaque evenement, recuperer les **4 donnees** et les repercuter dans **tous les onglets** :

| Donnee               | Onglets concernes                              |
|----------------------|------------------------------------------------|
| 1. Finishers         | Tableau, Vue d'ensemble, Top Evenements        |
| 2. Temps moyen       | Vue d'ensemble, Temps moyen                    |
| 3. Chrono vainqueur H| Vue d'ensemble, Winners Times                  |
| 4. Chrono vainqueur F| Vue d'ensemble, Winners Times                  |

**Procedure :**
1. **Decouvrir l'API** : identifier la plateforme (TimeTo, ACN/ChronoRace, Sporthive, Tracx, Athlinks...) et ses endpoints
2. **Recuperer les 4D** : finishers, temps moyen, chrono vainqueur H, chrono vainqueur F
3. **Mettre a jour TOUS les fichiers** :
   - `update_finishers.py "NomCourse" DISTANCE ANNEE COUNT` → finishers dans Excel
   - `create_chronos.py` → ajouter la ligne de chronos vainqueurs (donnees en dur)
   - `avg_times_sporthive.json` → ajouter le temps moyen
   - `Temps_moyen_par_marathon_{ANNEE}.xlsx` ou `Temps_moyen_semi-marathon.xlsx` → remplir la ligne
4. **Regenerer** : `python create_chronos.py && python generate_dashboard.py`
5. **Verifier** : confirmer la presence dans RAW, WINNERS, TEMPS_MARATHON/SEMI, TIMES_DB, TEMPS_AVG
6. **Commit + push**

### Renommer un evenement
Modifier le nom dans TOUS les emplacements listes dans "Ou sont stockes les noms d'evenements" ci-dessus (9 fichiers). **Ne pas oublier `datapace.db`** (table `events`), c'est la source primaire du dashboard.

## Structure du dashboard (onglets)

1. **Tableau** : Grille evenements x annees avec finishers, badges, premieres editions
2. **Vue d'ensemble** : Fiche identite par evenement (finishers, temps moyen, records H/F, 4 graphiques)
3. **Comparer** : Comparaison cote a cote de 2 evenements
4. **Evolution** : Graphique d'evolution des finishers par evenement
5. **Top Evenements** : Barres horizontales des plus gros evenements
6. **Temps moyen** : Comparaison des temps moyens par distance et annee
7. **Winners Times** : Graphique des temps vainqueurs H/F par distance

## Etat actuel

- 180 evenements, 57.8% de remplissage total (48.3% pertinent)
- 906 lignes de chronos vainqueurs (84% avec au moins 1 temps)
- 137 temps moyens (Sporthive + Tracx)
- Base unifiee : 979 courses, 4.56M finishers
- Dashboard : 229 Ko

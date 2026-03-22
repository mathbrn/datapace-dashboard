# Dashboard Running - Consignes de projet

## Fichiers principaux

- `generate_dashboard.py` : Generateur du dashboard HTML (lit tous les Excel + JSON)
- `Suivi_Finishers_Monde_10k_-_21k_-_42k_HISTORIQUE.xlsx` : Donnees finishers (onglet ALL)
- `Chronos_Vainqueurs.xlsx` : Temps vainqueurs H/F (genere par `create_chronos.py`)
- `Temps_moyen_semi-marathon.xlsx` : Temps moyens semi (multi-feuilles par annee)
- `Temps_moyen_par_marathon_{2024,2025,2026}.xlsx` : Temps moyens marathon
- `avg_times_sporthive.json` : Temps moyens calcules depuis APIs (Sporthive + Tracx)
- `datapace_dashboard.html` : Dashboard genere (ouvrir dans navigateur)

## Regles strictes

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

### 5. TimeTo / SportInnovation (ASO France)
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

## Workflow de mise a jour

1. Rechercher les donnees (APIs, web search, scraping)
2. Appliquer via `update_finishers.py` (ne modifie que les cellules vides)
3. Executer `python generate_dashboard.py`
4. `git add -A && git commit && git push`

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

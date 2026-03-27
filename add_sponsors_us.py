#!/usr/bin/env python3
"""Add US sponsors from research."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('sponsoring_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

new_brands = {
    "Chevron": {"full_name": "Chevron Corporation", "sector": "Energie/Petrole", "country": "US"},
    "Aramco": {"full_name": "Saudi Aramco", "sector": "Energie/Petrole", "country": "SA"},
    "IU Health": {"full_name": "Indiana University Health", "sector": "Sante/Hopital", "country": "US"},
    "Delta Dental": {"full_name": "Delta Dental", "sector": "Assurance/Sante", "country": "US"},
    "JAL": {"full_name": "Japan Airlines", "sector": "Aviation/Transport", "country": "JP"},
    "St. Jude": {"full_name": "St. Jude Children's Research Hospital", "sector": "Sante/Hopital", "country": "US"},
    "CELSIUS": {"full_name": "Celsius Holdings", "sector": "Nutrition/Boisson", "country": "US"},
    "GEICO": {"full_name": "GEICO (Berkshire Hathaway)", "sector": "Assurance/Finance", "country": "US"},
    "State Farm": {"full_name": "State Farm Insurance", "sector": "Assurance/Finance", "country": "US"},
    "CORKCICLE": {"full_name": "CORKCICLE", "sector": "Hydratation/Consommation", "country": "US"},
    "Cigna": {"full_name": "Cigna Healthcare", "sector": "Assurance/Sante", "country": "US"},
    "Dick's Sporting Goods": {"full_name": "Dick's Sporting Goods", "sector": "Retail/Distribution sport", "country": "US"},
    "Skechers": {"full_name": "Skechers USA", "sector": "Equipementier sport", "country": "US"},
    "Nuun": {"full_name": "Nuun Hydration", "sector": "Nutrition/Boisson", "country": "US"},
    "Northside Hospital": {"full_name": "Northside Hospital", "sector": "Sante/Hopital", "country": "US"},
}

data['brands'].update(new_brands)

new_partnerships = [
    # Houston
    {"event": "Chevron Houston Marathon", "brand": "Chevron", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Aramco Houston Half Marathon", "brand": "Aramco", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Peachtree
    {"event": "Atlanta Journal-Constitution Peachtree Road Race", "brand": "Mizuno", "type": "official", "years": [2023, 2024, 2025, 2026]},
    {"event": "Atlanta Journal-Constitution Peachtree Road Race", "brand": "Northside Hospital", "type": "title", "years": [2026]},
    # Brooklyn Half
    {"event": "NYRR RBC Brooklyn Half", "brand": "RBC", "type": "title", "years": [2022, 2023, 2024, 2025, 2026]},
    {"event": "NYRR RBC Brooklyn Half", "brand": "New Balance", "type": "official", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Marine Corps
    {"event": "Marine Corps Marathon", "brand": "GEICO", "type": "official", "years": [2023, 2024, 2025, 2026]},
    # Rock n Roll series
    {"event": "Rock 'n' Roll Running Series Las Vegas", "brand": "St. Jude", "type": "partner", "years": [2023, 2024, 2025, 2026]},
    {"event": "Rock 'n' Roll Running Series Las Vegas", "brand": "CELSIUS", "type": "official", "years": [2025, 2026]},
    {"event": "Rock 'n' Roll Running Series San Diego", "brand": "St. Jude", "type": "partner", "years": [2023, 2024, 2025, 2026]},
    {"event": "St. Jude Rock 'n' Roll Series Nashville", "brand": "St. Jude", "type": "title", "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "St. Jude Rock 'n' Roll Running Series Washington DC", "brand": "St. Jude", "type": "title", "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Rock 'n' Roll Arizona Marathon", "brand": "St. Jude", "type": "partner", "years": [2023, 2024, 2025, 2026]},
    # Indy Mini
    {"event": "IU Health 500 Festival Mini-Marathon", "brand": "IU Health", "type": "title", "years": [2023, 2024, 2025, 2026]},
    {"event": "IU Health 500 Festival Mini-Marathon", "brand": "Delta Dental", "type": "official", "years": [2023, 2024, 2025, 2026]},
    # Disney
    {"event": "Disney Princess Half Marathon", "brand": "CORKCICLE", "type": "title", "years": [2025, 2026]},
    {"event": "Walt Disney World Marathon Weekend", "brand": "State Farm", "type": "title", "years": [2025, 2026]},
    # Honolulu
    {"event": "Honolulu Marathon", "brand": "JAL", "type": "title", "years": [2025, 2026]},
    # San Francisco
    {"event": "San Francisco Marathon", "brand": "Biofreeze", "type": "title", "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "San Francisco Marathon", "brand": "Nuun", "type": "official", "years": [2025, 2026]},
    # Twin Cities
    {"event": "Medtronic Twin Cities Marathon", "brand": "Medtronic", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Pittsburgh
    {"event": "Dick's Pittsburgh Marathon", "brand": "Dick's Sporting Goods", "type": "title", "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Dallas
    {"event": "BMW Dallas Marathon", "brand": "BMW", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Denver Colfax
    {"event": "Denver Colfax Marathon", "brand": "Cigna", "type": "title", "years": [2022, 2023, 2024, 2025, 2026]},
    {"event": "Denver Colfax Marathon", "brand": "ASICS", "type": "official", "years": [2025, 2026]},
    # BOLDERBoulder
    {"event": "BOLDERBoulder 10K", "brand": "Nike", "type": "official", "years": [2025, 2026]},
    # Cherry Blossom
    {"event": "Credit Union Cherry Blossom", "brand": "ASICS", "type": "official", "years": [2025, 2026]},
    # Bay to Breakers
    {"event": "Bay to Breakers", "brand": "Skechers", "type": "official", "years": [2025, 2026]},
]

data['partnerships'].extend(new_partnerships)

with open('sponsoring_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Brands: {len(data['brands'])}")
print(f"Partnerships: {len(data['partnerships'])}")
print(f"Added: {len(new_brands)} brands, {len(new_partnerships)} partnerships")

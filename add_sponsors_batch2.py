#!/usr/bin/env python3
"""Add sponsors from batch 2 research (Asia-Pacific + Europe)."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('sponsoring_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

new_brands = {
    "Mizuno": data['brands'].get("Mizuno", {"full_name": "Mizuno Corporation", "sector": "Equipementier sport", "country": "JP"}),
    "Bank of China": {"full_name": "Bank of China", "sector": "Banque/Finance", "country": "CN"},
    "Fubon": {"full_name": "Fubon Financial Holdings", "sector": "Banque/Finance", "country": "TW"},
    "OPAP": {"full_name": "OPAP S.A.", "sector": "Jeux/Divertissement", "country": "GR"},
    "SAB": {"full_name": "Saudi Awwal Bank", "sector": "Banque/Finance", "country": "SA"},
    "Tawuniya": {"full_name": "Tawuniya Insurance", "sector": "Assurance/Finance", "country": "SA"},
    "Porvenir": {"full_name": "Porvenir S.A.", "sector": "Finance/Investissement", "country": "CO"},
    "Telcel": {"full_name": "Telcel (America Movil)", "sector": "Telecom", "country": "MX"},
    "BBVA": {"full_name": "BBVA", "sector": "Banque/Finance", "country": "ES"},
    "Dong-A Ilbo": {"full_name": "Dong-A Ilbo", "sector": "Media/Presse", "country": "KR"},
    "KB Financial": {"full_name": "KB Financial Group", "sector": "Banque/Finance", "country": "KR"},
    "Voltaren City2Surf": {"full_name": "placeholder", "sector": "skip", "country": "skip"},
    "China Airlines": {"full_name": "China Airlines", "sector": "Aviation/Transport", "country": "TW"},
    # European
    "Acea": {"full_name": "Acea S.p.A.", "sector": "Energie", "country": "IT"},
    "Joma": {"full_name": "Joma Sport S.A.", "sector": "Equipementier sport", "country": "ES"},
    "Eurospin": {"full_name": "Eurospin Italia", "sector": "Grande distribution", "country": "IT"},
    "Wizz Air": {"full_name": "Wizz Air Holdings", "sector": "Aviation/Transport", "country": "HU"},
    "Volkswagen": {"full_name": "Volkswagen AG", "sector": "Automobile", "country": "DE"},
    "Boozt": {"full_name": "Boozt.com", "sector": "Retail/Mode", "country": "SE"},
    "Wiener Stadtische": {"full_name": "Wiener Stadtische Versicherung", "sector": "Assurance/Finance", "country": "AT"},
    "N Kolay": {"full_name": "N Kolay (Aktif Bank)", "sector": "Fintech/Paiement", "country": "TR"},
    "Haspa": {"full_name": "Hamburger Sparkasse", "sector": "Banque/Finance", "country": "DE"},
    "Irish Life": {"full_name": "Irish Life Group", "sector": "Assurance/Finance", "country": "IE"},
    "Vitality": {"full_name": "Vitality Group", "sector": "Assurance/Sante", "country": "GB"},
    "Oysho": {"full_name": "Oysho (Inditex)", "sector": "Retail/Mode", "country": "ES"},
    "Movistar": {"full_name": "Movistar (Telefonica)", "sector": "Telecom", "country": "ES"},
    "Sprinter": {"full_name": "Sprinter (Grupo Sprinter)", "sector": "Retail/Distribution sport", "country": "ES"},
    "i-Run": {"full_name": "i-Run.fr", "sector": "Retail/Distribution sport", "country": "FR"},
    "RBC": {"full_name": "Royal Bank of Canada", "sector": "Banque/Finance", "country": "CA"},
    "Sweaty Betty": {"full_name": "Sweaty Betty", "sector": "Equipementier sport", "country": "GB"},
}

# Remove placeholder
del new_brands["Voltaren City2Surf"]

data['brands'].update(new_brands)

new_partnerships = [
    # === ASIA-PACIFIC ===
    # Osaka
    {"event": "Osaka Marathon", "brand": "Mizuno", "type": "official", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Seoul
    {"event": "Seoul Marathon", "brand": "Dong-A Ilbo", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Seoul Marathon", "brand": "Adidas", "type": "official", "years": [2025, 2026]},
    {"event": "Seoul Marathon", "brand": "KB Financial", "type": "official", "years": [2025, 2026]},
    # Beijing
    {"event": "Beijing Marathon", "brand": "Bank of China", "type": "title", "years": [2025, 2026]},
    {"event": "Beijing Marathon", "brand": "Adidas", "type": "official", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Shanghai
    {"event": "Shanghai Marathon", "brand": "Nike", "type": "official", "years": [2025, 2026]},
    # Taipei
    {"event": "Taipei Marathon", "brand": "Fubon", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Taipei Marathon", "brand": "Adidas", "type": "official", "years": [2025, 2026]},
    # Gold Coast
    {"event": "Gold Coast Marathon", "brand": "ASICS", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Athens
    {"event": "Athens Marathon", "brand": "OPAP", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Riyadh
    {"event": "Riyadh Marathon", "brand": "SAB", "type": "title", "years": [2025, 2026]},
    {"event": "Riyadh Marathon", "brand": "ASICS", "type": "official", "years": [2025, 2026]},
    {"event": "Riyadh Marathon", "brand": "Tawuniya", "type": "official", "years": [2025, 2026]},
    # Bogota
    {"event": "Media Maraton de Bogota", "brand": "Porvenir", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Media Maraton de Bogota", "brand": "Samsung", "type": "official", "years": [2024, 2025, 2026]},
    # Mexico City
    {"event": "Maratón de la Ciudad de México Telcel", "brand": "Telcel", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Vedanta Delhi
    {"event": "Vedanta Delhi Half Marathon", "brand": "Vedanta", "type": "title", "years": [2022, 2023, 2024, 2025, 2026]},
    # KL
    {"event": "Standard Chartered KL Marathon", "brand": "ASICS", "type": "official", "years": [2025, 2026]},
    {"event": "Standard Chartered KL Half Marathon", "brand": "ASICS", "type": "official", "years": [2025, 2026]},
    # Run Melbourne
    {"event": "Asics Run Melbourne", "brand": "ASICS", "type": "title", "years": [2023, 2024, 2025, 2026]},

    # === EUROPE ===
    # Rome
    {"event": "Acea Run Rome The Marathon", "brand": "Acea", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Acea Run Rome The Marathon", "brand": "Joma", "type": "official", "years": [2025, 2026]},
    {"event": "Eurospin RomaOstia Half Marathon", "brand": "Eurospin", "type": "title", "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Eurospin RomaOstia Half Marathon", "brand": "Adidas", "type": "official", "years": [2025, 2026]},
    {"event": "Wizz Air Rome Half Marathon by Brooks", "brand": "Wizz Air", "type": "title", "years": [2024, 2025, 2026]},
    {"event": "Wizz Air Rome Half Marathon by Brooks", "brand": "Brooks", "type": "official", "years": [2024, 2025, 2026]},
    {"event": "Milano Marathon", "brand": "Wizz Air", "type": "title", "years": [2024, 2025, 2026]},
    {"event": "Milano Marathon", "brand": "ASICS", "type": "official", "years": [2025, 2026]},
    # Prague
    {"event": "Generali Prague Half Marathon", "brand": "Generali", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Generali Prague Half Marathon", "brand": "Adidas", "type": "official", "years": [2025, 2026]},
    {"event": "Prague International Marathon", "brand": "Volkswagen", "type": "title", "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Gothenburg
    {"event": "Göteborgsvarvet", "brand": "Boozt", "type": "title", "years": [2023, 2024, 2025, 2026]},
    {"event": "Göteborgsvarvet", "brand": "Maurten", "type": "official", "years": [2025, 2026]},
    # Stockholm
    {"event": "Stockholm Marathon", "brand": "Adidas", "type": "title", "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Copenhagen
    {"event": "Copenhagen Half Marathon", "brand": "Zalando", "type": "title", "years": [2025, 2026]},
    {"event": "Copenhagen Marathon", "brand": "Zalando", "type": "title", "years": [2026]},
    # Vienna
    {"event": "Vienna City Half Marathon", "brand": "Wiener Stadtische", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Istanbul
    {"event": "Istanbul Marathon", "brand": "N Kolay", "type": "title", "years": [2022, 2023, 2024, 2025, 2026]},
    # Warsaw
    {"event": "NN Maraton Warszawski", "brand": "NN", "type": "title", "years": [2023, 2024, 2025, 2026]},
    {"event": "Warsaw Half Marathon", "brand": "NN", "type": "title", "years": [2025, 2026]},
    # Hamburg
    {"event": "Haspa Marathon Hamburg", "brand": "Haspa", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Amsterdam
    {"event": "TCS Amsterdam Marathon", "brand": "TCS", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "TCS Amsterdam Marathon", "brand": "Mizuno", "type": "official", "years": [2025, 2026]},
    # Dublin
    {"event": "Irish Life Dublin Marathon", "brand": "Irish Life", "type": "title", "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    # Big Half
    {"event": "The Big Half", "brand": "Vitality", "type": "title", "years": [2025, 2026]},
    # Cardiff
    {"event": "Cardiff Half Marathon", "brand": "Oysho", "type": "title", "years": [2025, 2026]},
    # London Landmarks
    {"event": "London Landmarks Half Marathon", "brand": "RBC", "type": "official", "years": [2025, 2026]},
    # Royal Parks
    {"event": "Royal Parks Half Marathon", "brand": "Sweaty Betty", "type": "official", "years": [2022, 2023, 2024, 2025]},
    # Dam tot Damloop
    {"event": "Dam tot Damloop", "brand": "NN", "type": "title", "years": [2022, 2023, 2024, 2025, 2026]},
    # Sevilla Marathon
    {"event": "Zurich Maratón de Sevilla", "brand": "Zurich", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Zurich Maratón de Sevilla", "brand": "ASICS", "type": "official", "years": [2025, 2026]},
    # Sevilla Half
    {"event": "Medio Maraton de Sevilla", "brand": "Sprinter", "type": "title", "years": [2025, 2026]},
    {"event": "Medio Maraton de Sevilla", "brand": "Hoka", "type": "official", "years": [2025, 2026]},
    # Madrid Half
    {"event": "Movistar Madrid Medio Maraton", "brand": "Movistar", "type": "title", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]},
    {"event": "Movistar Madrid Medio Maraton", "brand": "Joma", "type": "official", "years": [2025, 2026]},
    # Boulogne
    {"event": "Semi-Marathon de Boulogne-Billancourt", "brand": "i-Run", "type": "official", "years": [2025, 2026]},
    # Run in Lyon
    {"event": "Run in Lyon", "brand": "Harmonie Mutuelle", "type": "title", "years": [2025, 2026]},
    {"event": "Run in Lyon", "brand": "ASICS", "type": "official", "years": [2025, 2026]},
]

data['partnerships'].extend(new_partnerships)

with open('sponsoring_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Brands: {len(data['brands'])}")
print(f"Partnerships: {len(data['partnerships'])}")
print(f"Added: {len(new_brands)} brands, {len(new_partnerships)} partnerships")

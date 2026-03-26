#!/usr/bin/env python3
"""Update sponsoring_data.json with 2026 partnerships."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('sponsoring_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1. Extend existing partnerships to 2026 (confirmed or assumed continuations)
extended = 0
for p in data['partnerships']:
    if 2025 in p.get('years', []) and 2026 not in p.get('years', []):
        p['years'].append(2026)
        extended += 1

print(f"Extended {extended} existing partnerships to 2026")

# 2. Add new brands
new_brands = {
    "Ford": {"full_name": "Ford Motor Company", "sector": "Automobile", "country": "US"},
    "Flora": {"full_name": "Flora (Upfield)", "sector": "Alimentaire", "country": "GB"},
    "Revolut": {"full_name": "Revolut Ltd.", "sector": "Fintech/Paiement", "country": "GB"},
    "Kia": {"full_name": "Kia Corporation", "sector": "Automobile", "country": "KR"},
    "McDonald's": {"full_name": "McDonald's Corporation", "sector": "Restauration", "country": "US"},
    "Culligan": {"full_name": "Culligan International", "sector": "Eau/Boisson", "country": "US"},
    "JetBlue": {"full_name": "JetBlue Airways", "sector": "Aviation/Transport", "country": "US"},
    "Dick's Sporting Goods": {"full_name": "Dick's Sporting Goods", "sector": "Retail/Distribution sport", "country": "US"},
    "Dai-ichi Life": {"full_name": "Dai-ichi Life Holdings", "sector": "Assurance/Finance", "country": "JP"},
    "Kao": {"full_name": "Kao Corporation", "sector": "Hygiene/Cosmetique", "country": "JP"},
    "STARTS": {"full_name": "STARTS Corporation", "sector": "Immobilier", "country": "JP"},
    "MSC": {"full_name": "MSC Cruises", "sector": "Transport/Croisiere", "country": "CH"},
    "BUFF": {"full_name": "BUFF S.A.", "sector": "Equipementier sport", "country": "ES"},
    "Compressport": {"full_name": "Compressport International", "sector": "Equipementier sport", "country": "CH"},
    "AA Drink": {"full_name": "AA Drink", "sector": "Nutrition/Boisson", "country": "NL"},
    "COMPEED": {"full_name": "COMPEED (HRA Pharma)", "sector": "Sante/Pharma", "country": "FR"},
    "Ekosport": {"full_name": "Ekosport SAS", "sector": "Retail/Distribution sport", "country": "FR"},
    "AMARON": {"full_name": "AMARON (Amara Raja)", "sector": "Industrie/Batteries", "country": "IN"},
    "Snickers": {"full_name": "Snickers (Mars Inc.)", "sector": "Alimentaire", "country": "US"},
    "Red Bull": {"full_name": "Red Bull GmbH", "sector": "Nutrition/Boisson", "country": "AT"},
    "Nayara Energy": {"full_name": "Nayara Energy Ltd.", "sector": "Energie/Petrole", "country": "IN"},
    "Coopah": {"full_name": "Coopah Ltd.", "sector": "Tech/App sport", "country": "GB"},
}
data['brands'].update(new_brands)
print(f"Added {len(new_brands)} new brands")

# 3. Add new 2026 partnerships
new_partnerships = [
    # London 2026 new
    {"event": "TCS London Marathon", "brand": "Ford", "type": "official", "years": [2026]},
    {"event": "TCS London Marathon", "brand": "Flora", "type": "official", "years": [2026]},
    {"event": "TCS London Marathon", "brand": "Coopah", "type": "partner", "years": [2026]},
    {"event": "TCS London Marathon", "brand": "Clif Bar", "type": "partner", "years": [2026]},
    # Berlin 2026 new
    {"event": "BMW Berlin Marathon", "brand": "Revolut", "type": "partner", "years": [2026]},
    {"event": "BMW Berlin Marathon", "brand": "Shokz", "type": "partner", "years": [2026]},
    {"event": "BMW Berlin Marathon", "brand": "Clif Bar", "type": "partner", "years": [2026]},
    # Chicago 2026 new
    {"event": "Bank of America Chicago Marathon", "brand": "Kia", "type": "official", "years": [2026]},
    {"event": "Bank of America Chicago Marathon", "brand": "McDonald's", "type": "partner", "years": [2026]},
    {"event": "Bank of America Chicago Marathon", "brand": "Culligan", "type": "partner", "years": [2026]},
    {"event": "Bank of America Chicago Marathon", "brand": "Shokz", "type": "partner", "years": [2026]},
    {"event": "Bank of America Chicago Marathon", "brand": "Maurten", "type": "partner", "years": [2026]},
    # Boston 2026 new
    {"event": "Boston Marathon", "brand": "JetBlue", "type": "official", "years": [2026]},
    {"event": "Boston Marathon", "brand": "Dick's Sporting Goods", "type": "official", "years": [2026]},
    {"event": "Boston Marathon", "brand": "Shokz", "type": "partner", "years": [2026]},
    {"event": "Boston Marathon", "brand": "Maurten", "type": "partner", "years": [2026]},
    {"event": "Boston Marathon", "brand": "Runna", "type": "partner", "years": [2026]},
    # Tokyo 2026 confirmed
    {"event": "Tokyo Marathon", "brand": "Dai-ichi Life", "type": "official", "years": [2026]},
    {"event": "Tokyo Marathon", "brand": "McDonald's", "type": "official", "years": [2026]},
    {"event": "Tokyo Marathon", "brand": "Kao", "type": "partner", "years": [2026]},
    {"event": "Tokyo Marathon", "brand": "STARTS", "type": "official", "years": [2025, 2026]},
    {"event": "Tokyo Marathon", "brand": "Seiko", "type": "official", "years": [2026]},
    # Barcelona 2026 new
    {"event": "Zurich Marato de Barcelona", "brand": "Hoka", "type": "official", "years": [2026]},
    {"event": "Zurich Marato de Barcelona", "brand": "BUFF", "type": "partner", "years": [2026]},
    {"event": "Zurich Marato de Barcelona", "brand": "Compressport", "type": "partner", "years": [2026]},
    # Semi de Paris 2026
    {"event": "HOKA Semi de Paris", "brand": "Ekosport", "type": "partner", "years": [2026]},
    # Rotterdam 2026 new
    {"event": "NN Marathon Rotterdam", "brand": "Shokz", "type": "official", "years": [2026]},
    {"event": "NN Marathon Rotterdam", "brand": "Zalando", "type": "partner", "years": [2026]},
    {"event": "NN Marathon Rotterdam", "brand": "Chiquita", "type": "partner", "years": [2026]},
    {"event": "NN Marathon Rotterdam", "brand": "AA Drink", "type": "partner", "years": [2026]},
    {"event": "NN Marathon Rotterdam", "brand": "COMPEED", "type": "partner", "years": [2026]},
    # Valencia 2026
    {"event": "Valencia Marathon Trinidad Alfonso Zurich", "brand": "MSC", "type": "official", "years": [2025, 2026]},
    # Singapore 2026 - major change
    {"event": "Standard Chartered Singapore Marathon", "brand": "Adidas", "type": "official", "years": [2026]},
    # Cape Town 2026
    {"event": "Sanlam Cape Town Marathon", "brand": "Adidas", "type": "official", "years": [2026]},
    # Sydney 2026
    {"event": "TCS Sydney Marathon presented by ASICS", "brand": "Powerade", "type": "official", "years": [2026]},
    # Mumbai 2026 new
    {"event": "Tata Mumbai Marathon", "brand": "AMARON", "type": "official", "years": [2026]},
    {"event": "Tata Mumbai Marathon", "brand": "Snickers", "type": "partner", "years": [2026]},
    {"event": "Tata Mumbai Marathon", "brand": "Red Bull", "type": "partner", "years": [2026]},
    {"event": "Tata Mumbai Marathon", "brand": "Nayara Energy", "type": "official", "years": [2026]},
    {"event": "Tata Mumbai Marathon", "brand": "ASICS", "type": "official", "years": [2025, 2026]},
    # Great North Run 2026
    {"event": "AJ Bell Great North Run", "brand": "Maurten", "type": "partner", "years": [2026]},
]

data['partnerships'].extend(new_partnerships)
print(f"Added {len(new_partnerships)} new 2026 partnerships")

with open('sponsoring_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\nTotal: {len(data['brands'])} brands, {len(data['partnerships'])} partnerships")

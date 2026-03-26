#!/usr/bin/env python3
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('sponsoring_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

new_brands = {
    "Buxton": {"full_name": "Buxton (Nestle Waters)", "sector": "Eau/Boisson", "country": "GB"},
    "Radox": {"full_name": "Radox (Unilever)", "sector": "Hygiene/Cosmetique", "country": "GB"},
    "Voltarol": {"full_name": "Voltarol/Voltaren (GSK)", "sector": "Sante/Pharma", "country": "GB"},
    "HubSpot": {"full_name": "HubSpot Inc.", "sector": "Tech/SaaS", "country": "US"},
    "Biotherm": {"full_name": "Biotherm (L'Oreal)", "sector": "Cosmetique", "country": "FR"},
    "BLACKROLL": {"full_name": "BLACKROLL AG", "sector": "Equipement sport/Recovery", "country": "DE"},
    "Chiquita": {"full_name": "Chiquita Brands", "sector": "Alimentaire", "country": "US"},
    "Biofreeze": {"full_name": "Biofreeze (Reckitt)", "sector": "Sante/Recovery", "country": "US"},
    "Athletico": {"full_name": "Athletico Physical Therapy", "sector": "Sante/Physiotherapie", "country": "US"},
    "CITGO": {"full_name": "CITGO Petroleum", "sector": "Energie/Petrole", "country": "US"},
    "Poland Spring": {"full_name": "Poland Spring (Nestle)", "sector": "Eau/Boisson", "country": "US"},
    "Clif Bar": {"full_name": "Clif Bar (Mondelez)", "sector": "Nutrition sport", "country": "US"},
    "Citizens": {"full_name": "Citizens Financial Group", "sector": "Banque/Finance", "country": "US"},
    "CookUnity": {"full_name": "CookUnity Inc.", "sector": "Alimentaire/Livraison", "country": "US"},
    "GetYourGuide": {"full_name": "GetYourGuide GmbH", "sector": "Tech/Tourisme", "country": "DE"},
    "Dunkin'": {"full_name": "Dunkin' Brands", "sector": "Restauration/Boisson", "country": "US"},
    "Peloton": {"full_name": "Peloton Interactive", "sector": "Fitness/Tech", "country": "US"},
    "Otsuka Pharmaceutical": {"full_name": "Otsuka Pharmaceutical", "sector": "Pharma/Nutrition", "country": "JP"},
    "Mizuho Bank": {"full_name": "Mizuho Financial Group", "sector": "Banque/Finance", "country": "JP"},
    "Hisamitsu": {"full_name": "Hisamitsu Pharmaceutical", "sector": "Sante/Pharma", "country": "JP"},
    "Luanvi": {"full_name": "Luanvi S.A.", "sector": "Equipementier sport", "country": "ES"},
    "OK Mobility": {"full_name": "OK Mobility Group", "sector": "Mobilite/Location", "country": "ES"},
    "Vodafone": {"full_name": "Vodafone Group", "sector": "Telecom", "country": "GB"},
    "Powerade": {"full_name": "Powerade (Coca-Cola)", "sector": "Nutrition/Boisson", "country": "US"},
    "T. Rowe Price": {"full_name": "T. Rowe Price Group", "sector": "Finance/Investissement", "country": "US"},
    "PowerBar": {"full_name": "PowerBar (Post Holdings)", "sector": "Nutrition sport", "country": "US"},
    "Rosbacher": {"full_name": "Rosbacher Brunnen", "sector": "Eau/Boisson", "country": "DE"},
    "Krombacher": {"full_name": "Krombacher Brauerei", "sector": "Boisson/Brasserie", "country": "DE"},
    "Applied Nutrition": {"full_name": "Applied Nutrition Ltd.", "sector": "Nutrition sport", "country": "GB"},
    "100PLUS": {"full_name": "100PLUS (F&N)", "sector": "Nutrition/Boisson", "country": "MY"},
    "OATSIDE": {"full_name": "OATSIDE", "sector": "Nutrition/Boisson", "country": "SG"},
    "Ethiopian Airlines": {"full_name": "Ethiopian Airlines", "sector": "Aviation/Transport", "country": "ET"},
    "BYD": {"full_name": "BYD Company", "sector": "Automobile", "country": "CN"},
    "Solgar": {"full_name": "Solgar (Nestle Health)", "sector": "Sante/Supplements", "country": "US"},
    "Aqua Pura": {"full_name": "Aqua Pura", "sector": "Eau/Boisson", "country": "GB"},
    "IDFC FIRST Bank": {"full_name": "IDFC FIRST Bank", "sector": "Banque/Finance", "country": "IN"},
    "Bisleri": {"full_name": "Bisleri International", "sector": "Eau/Boisson", "country": "IN"},
    "VIDA": {"full_name": "VIDA (Hero MotoCorp)", "sector": "Automobile/EV", "country": "IN"},
    "Fast&Up": {"full_name": "Fast&Up (Fullife)", "sector": "Nutrition sport", "country": "IN"},
    "Vedanta": {"full_name": "Vedanta Limited", "sector": "Industrie/Ressources", "country": "IN"},
    "RBC Capital Markets": {"full_name": "RBC Capital Markets", "sector": "Finance/Investissement", "country": "CA"},
    "YoPRO": {"full_name": "YoPRO (Danone)", "sector": "Nutrition/Alimentaire", "country": "FR"},
    "SriLankan Airlines": {"full_name": "SriLankan Airlines", "sector": "Aviation/Transport", "country": "LK"},
    "Coinbase": {"full_name": "Coinbase Global", "sector": "Crypto/Fintech", "country": "US"},
    "Chobani": {"full_name": "Chobani LLC", "sector": "Nutrition/Alimentaire", "country": "US"},
    "Chemist Warehouse": {"full_name": "Chemist Warehouse Group", "sector": "Retail/Pharmacie", "country": "AU"},
    "Bupa": {"full_name": "Bupa Group", "sector": "Assurance/Sante", "country": "GB"},
    "ECOTIC": {"full_name": "ECOTIC Envases", "sector": "Environnement/Recyclage", "country": "ES"},
    "Infront": {"full_name": "Infront Sports & Media", "sector": "Marketing sportif", "country": "CH"},
}

data['brands'].update(new_brands)

new_partnerships = [
    # London
    {"event": "TCS London Marathon", "brand": "Buxton", "type": "official", "years": [2024, 2025]},
    {"event": "TCS London Marathon", "brand": "Radox", "type": "official", "years": [2024, 2025]},
    {"event": "TCS London Marathon", "brand": "Voltarol", "type": "official", "years": [2024, 2025]},
    {"event": "TCS London Marathon", "brand": "HubSpot", "type": "official", "years": [2025]},
    # Berlin
    {"event": "BMW Berlin Marathon", "brand": "Biotherm", "type": "partner", "years": [2025]},
    {"event": "BMW Berlin Marathon", "brand": "BLACKROLL", "type": "partner", "years": [2025]},
    {"event": "BMW Berlin Marathon", "brand": "Chiquita", "type": "partner", "years": [2025]},
    # Chicago
    {"event": "Bank of America Chicago Marathon", "brand": "Biofreeze", "type": "partner", "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]},
    {"event": "Bank of America Chicago Marathon", "brand": "Chiquita", "type": "partner", "years": [2025]},
    {"event": "Bank of America Chicago Marathon", "brand": "Athletico", "type": "partner", "years": [2025]},
    # Boston
    {"event": "Boston Marathon", "brand": "CITGO", "type": "official", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]},
    {"event": "Boston Marathon", "brand": "Poland Spring", "type": "official", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]},
    {"event": "Boston Marathon", "brand": "Clif Bar", "type": "official", "years": [2025]},
    # NYC
    {"event": "TCS New York City Marathon", "brand": "Citizens", "type": "official", "years": [2023, 2024, 2025]},
    {"event": "TCS New York City Marathon", "brand": "CookUnity", "type": "partner", "years": [2025]},
    {"event": "TCS New York City Marathon", "brand": "GetYourGuide", "type": "partner", "years": [2025]},
    {"event": "TCS New York City Marathon", "brand": "Dunkin'", "type": "partner", "years": [2019, 2020, 2021, 2022, 2023, 2024, 2025]},
    {"event": "TCS New York City Marathon", "brand": "Peloton", "type": "partner", "years": [2024, 2025]},
    # Tokyo
    {"event": "Tokyo Marathon", "brand": "Otsuka Pharmaceutical", "type": "official", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]},
    {"event": "Tokyo Marathon", "brand": "Mizuho Bank", "type": "official", "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]},
    {"event": "Tokyo Marathon", "brand": "Hisamitsu", "type": "partner", "years": [2020, 2021, 2022, 2023, 2024, 2025]},
    # Rotterdam
    {"event": "NN Marathon Rotterdam", "brand": "Voltarol", "type": "official", "years": [2025]},
    # Valencia
    {"event": "Valencia Marathon Trinidad Alfonso Zurich", "brand": "Luanvi", "type": "official", "years": [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]},
    # Barcelona
    {"event": "Zurich Marato de Barcelona", "brand": "OK Mobility", "type": "official", "years": [2025]},
    {"event": "Zurich Marato de Barcelona", "brand": "ECOTIC", "type": "partner", "years": [2025]},
    # Lisbon
    {"event": "EDP Maratona de Lisboa", "brand": "Vodafone", "type": "official", "years": [2025]},
    {"event": "EDP Maratona de Lisboa", "brand": "Powerade", "type": "partner", "years": [2025]},
    # Frankfurt
    {"event": "Mainova Frankfurt Marathon", "brand": "T. Rowe Price", "type": "official", "years": [2025]},
    {"event": "Mainova Frankfurt Marathon", "brand": "PowerBar", "type": "official", "years": [2025]},
    {"event": "Mainova Frankfurt Marathon", "brand": "Rosbacher", "type": "partner", "years": [2025]},
    {"event": "Mainova Frankfurt Marathon", "brand": "Krombacher", "type": "partner", "years": [2025]},
    # Manchester
    {"event": "Adidas Manchester Marathon", "brand": "Applied Nutrition", "type": "partner", "years": [2025]},
    # Singapore
    {"event": "Standard Chartered Singapore Marathon", "brand": "BYD", "type": "title", "years": [2026]},
    {"event": "Standard Chartered Singapore Marathon", "brand": "100PLUS", "type": "official", "years": [2025]},
    {"event": "Standard Chartered Singapore Marathon", "brand": "OATSIDE", "type": "partner", "years": [2025]},
    {"event": "Standard Chartered Singapore Marathon", "brand": "Ethiopian Airlines", "type": "partner", "years": [2025]},
    # Great North Run
    {"event": "AJ Bell Great North Run", "brand": "Solgar", "type": "partner", "years": [2025]},
    {"event": "AJ Bell Great North Run", "brand": "Aqua Pura", "type": "partner", "years": [2025]},
    # Cape Town
    {"event": "Sanlam Cape Town Marathon", "brand": "Infront", "type": "partner", "years": [2025]},
    # Mumbai
    {"event": "Tata Mumbai Marathon", "brand": "IDFC FIRST Bank", "type": "official", "years": [2025]},
    {"event": "Tata Mumbai Marathon", "brand": "Bisleri", "type": "official", "years": [2025]},
    {"event": "Tata Mumbai Marathon", "brand": "VIDA", "type": "partner", "years": [2025]},
    {"event": "Tata Mumbai Marathon", "brand": "Fast&Up", "type": "partner", "years": [2025]},
    {"event": "Tata Mumbai Marathon", "brand": "Vedanta", "type": "partner", "years": [2025]},
    # Sydney
    {"event": "TCS Sydney Marathon presented by ASICS", "brand": "HubSpot", "type": "partner", "years": [2025]},
    {"event": "TCS Sydney Marathon presented by ASICS", "brand": "RBC Capital Markets", "type": "partner", "years": [2025]},
    {"event": "TCS Sydney Marathon presented by ASICS", "brand": "YoPRO", "type": "partner", "years": [2025]},
    # Melbourne
    {"event": "Nike Melbourne Marathon Festival", "brand": "SriLankan Airlines", "type": "official", "years": [2025]},
    {"event": "Nike Melbourne Marathon Festival", "brand": "Coinbase", "type": "partner", "years": [2024, 2025]},
    {"event": "Nike Melbourne Marathon Festival", "brand": "Gatorade", "type": "official", "years": [2025]},
    {"event": "Nike Melbourne Marathon Festival", "brand": "Bupa", "type": "partner", "years": [2025]},
    {"event": "Nike Melbourne Marathon Festival", "brand": "Garmin", "type": "partner", "years": [2025]},
    {"event": "Nike Melbourne Marathon Festival", "brand": "Chemist Warehouse", "type": "partner", "years": [2025]},
    {"event": "Nike Melbourne Marathon Festival", "brand": "Chobani", "type": "partner", "years": [2025]},
]

data['partnerships'].extend(new_partnerships)

with open('sponsoring_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Brands: {len(data['brands'])}")
print(f"Partnerships: {len(data['partnerships'])}")
print(f"Added: {len(new_brands)} brands, {len(new_partnerships)} partnerships")

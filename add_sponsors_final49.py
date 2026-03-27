#!/usr/bin/env python3
"""Add sponsors for the remaining 49 events."""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('sponsoring_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

new_brands = {
    "Beneva": {"full_name": "Beneva (La Capitale + SSQ)", "sector": "Assurance", "country": "CA"},
    "AUSA": {"full_name": "Association of the U.S. Army", "sector": "Institutionnel", "country": "US"},
    "Ascension Seton": {"full_name": "Ascension Seton", "sector": "Sante", "country": "US"},
    "Under Armour": {"full_name": "Under Armour Inc.", "sector": "Equipementier sport", "country": "US"},
    "Excellus BCBS": {"full_name": "Excellus BlueCross BlueShield", "sector": "Assurance", "country": "US"},
    "Emirates NBD": {"full_name": "Emirates NBD Bank", "sector": "Banque/Finance", "country": "AE"},
    "Sutter Health": {"full_name": "Sutter Health", "sector": "Sante", "country": "US"},
    "Nationwide": {"full_name": "Nationwide Insurance", "sector": "Assurance", "country": "US"},
    "Independence Blue Cross": {"full_name": "Independence Blue Cross", "sector": "Assurance", "country": "US"},
    "LCMC Health": {"full_name": "LCMC Health", "sector": "Sante", "country": "US"},
    "Detroit Free Press": {"full_name": "Detroit Free Press (Gannett)", "sector": "Media/Presse", "country": "US"},
    "OCCU": {"full_name": "Oregon Community Credit Union", "sector": "Banque/Finance", "country": "US"},
    "Essentia Health": {"full_name": "Essentia Health", "sector": "Sante", "country": "US"},
    "Prysmian": {"full_name": "Prysmian Group", "sector": "Industrie/Energie", "country": "IT"},
    "Publix": {"full_name": "Publix Super Markets", "sector": "Grande distribution", "country": "US"},
    "Gate Petroleum": {"full_name": "Gate Petroleum", "sector": "Energie/Petrole", "country": "US"},
    "Coca-Cola": {"full_name": "The Coca-Cola Company", "sector": "Nutrition/Boisson", "country": "US"},
    "Hoag": {"full_name": "Hoag Memorial Hospital", "sector": "Sante", "country": "US"},
    "CNO Financial": {"full_name": "CNO Financial Group", "sector": "Assurance", "country": "US"},
    "2XU": {"full_name": "2XU Pty Ltd", "sector": "Equipementier sport", "country": "AU"},
    "Puma": {"full_name": "Puma SE", "sector": "Equipementier sport", "country": "DE"},
    "Devon Energy": {"full_name": "Devon Energy", "sector": "Energie/Petrole", "country": "US"},
    "Paycom": {"full_name": "Paycom Software", "sector": "Tech/SaaS", "country": "US"},
    "OHSU Health": {"full_name": "OHSU Health", "sector": "Sante", "country": "US"},
    "Allianz": {"full_name": "Allianz SE", "sector": "Assurance", "country": "DE"},
    "Nordea Foundation": {"full_name": "Nordea Foundation", "sector": "Fondation/Mecenat", "country": "DK"},
    "Yuengling": {"full_name": "Yuengling Brewery", "sector": "Boisson/Brasserie", "country": "US"},
    "Toyota": {"full_name": "Toyota Motor", "sector": "Automobile", "country": "JP"},
    "Applied Materials": {"full_name": "Applied Materials", "sector": "Tech/Electronique", "country": "US"},
    "Juice Plus+": {"full_name": "Juice Plus+ (NSA)", "sector": "Nutrition sport", "country": "US"},
    "Transurban": {"full_name": "Transurban Group", "sector": "Transport", "country": "AU"},
    "Ukrop's": {"full_name": "Ukrop's Homestyle Foods", "sector": "Alimentaire", "country": "US"},
    "Kroger": {"full_name": "The Kroger Co.", "sector": "Grande distribution", "country": "US"},
    "Herbaland": {"full_name": "Herbaland Naturals", "sector": "Nutrition sport", "country": "CA"},
    "Baylor Scott & White": {"full_name": "Baylor Scott & White Health", "sector": "Sante", "country": "US"},
}

data['brands'].update(new_brands)

existing = set((p['event'], p['brand']) for p in data['partnerships'])

new_partnerships = [
    # 1. Montreal
    ("21K de Montréal", "Beneva", "title", [2023, 2024, 2025, 2026]),
    # 2. Army Ten Miler
    ("Army Ten Miler", "AUSA", "title", [2025, 2026]),
    # 3. Austin Marathon
    ("Austin Marathon", "Ascension Seton", "title", [2025, 2026]),
    # 4. Baltimore
    ("Baltimore Running Festival", "Under Armour", "official", [2025, 2026]),
    # 6. Boilermaker
    ("Boilermaker Road Race", "Excellus BCBS", "title", [2025, 2026]),
    # 8. Broad Street Run
    ("Broad Street Run", "Independence Blue Cross", "title", [2025, 2026]),
    # 9. Brolobet
    ("Broløbet - The Bridge Run", "Boozt", "title", [2025]),
    # 10. Burj2Burj
    ("Burj2Burj Half Marathon", "Emirates NBD", "title", [2024, 2025, 2026]),
    # 11. California International Marathon
    ("California International Marathon", "Sutter Health", "title", [2025, 2026]),
    ("California International Marathon", "ASICS", "official", [2025, 2026]),
    # 12. Columbus Marathon
    ("Columbus Marathon", "Nationwide", "official", [2025, 2026]),
    # 13. Cooper River Bridge Run
    ("Cooper River Bridge Run", "Publix", "title", [2025, 2026]),
    # 14. Cowtown Marathon
    ("Cowtown Marathon", "Baylor Scott & White", "title", [2025, 2026]),
    # 15. Crescent City Classic
    ("Crescent City Classic", "LCMC Health", "title", [2023, 2024, 2025, 2026]),
    ("Crescent City Classic", "Michelob Ultra", "partner", [2025, 2026]),
    # 16. Detroit Marathon
    ("Detroit Marathon", "Detroit Free Press", "title", [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 17. Eugene Marathon
    ("Eugene Marathon", "OCCU", "title", [2025, 2026]),
    ("Eugene Marathon", "Nike", "official", [2025, 2026]),
    # 18. Falmouth Road Race
    ("Falmouth Road Race", "ASICS", "title", [2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 19. Fargo Marathon
    ("Fargo Marathon", "Essentia Health", "title", [2025, 2026]),
    # 20. Flying Pig Marathon
    ("Flying Pig Marathon", "Prysmian", "title", [2023, 2024, 2025, 2026]),
    # 21. Gasparilla
    ("Gasparilla Distance Classic", "Publix", "title", [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 22. Gate River Run
    ("Gate River Run", "Gate Petroleum", "title", [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    ("Gate River Run", "Brooks", "official", [2025, 2026]),
    # 23. Grandma's Marathon
    ("Grandma's Marathon", "Coca-Cola", "title", [2024, 2025, 2026]),
    ("Grandma's Marathon", "ASICS", "official", [2025, 2026]),
    ("Grandma's Marathon", "Toyota", "official", [2025, 2026]),
    # 24. Hoag OC Marathon
    ("Hoag OC Marathon", "Hoag", "title", [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 25. Indianapolis Monumental Marathon
    ("Indianapolis Monumental Marathon", "CNO Financial", "title", [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    ("Indianapolis Monumental Marathon", "Brooks", "official", [2025, 2026]),
    # 27. Lilac Bloomsday Run (no title sponsor)
    # 28. Long Beach Marathon
    ("Long Beach Marathon", "2XU", "title", [2025, 2026]),
    # 29. Manchester Half Marathon (UK)
    ("Manchester Half Marathon", "Puma", "title", [2024, 2025, 2026]),
    ("Manchester Half Marathon", "Runna", "official", [2025, 2026]),
    ("Manchester Half Marathon", "ERDINGER", "partner", [2025, 2026]),
    # 31. Miami Marathon
    ("Miami Marathon", "Life Time", "title", [2025, 2026]),
    ("Miami Marathon", "Garmin", "official", [2025, 2026]),
    # 33. Oklahoma City Memorial Marathon
    ("Oklahoma City Memorial Marathon", "Devon Energy", "title", [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    ("Oklahoma City Memorial Marathon", "Paycom", "official", [2025, 2026]),
    # 34. Portland Marathon
    ("Portland Marathon", "OHSU Health", "title", [2024, 2025, 2026]),
    ("Portland Marathon", "Nike", "official", [2025, 2026]),
    # 35. Richmond Marathon
    ("Richmond Marathon", "Allianz", "title", [2022, 2023, 2024, 2025, 2026]),
    # 36. Royal Parks (RBC already exists as Sweaty Betty, add RBC title)
    ("Royal Parks Half Marathon", "RBC", "title", [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 37. Royal Run
    ("Royal Run", "Nordea Foundation", "title", [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 39. Shamrock Marathon
    ("Shamrock Marathon", "Yuengling", "title", [2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 40. Shamrock Run Portland
    ("Shamrock Run Portland", "Toyota", "title", [2025, 2026]),
    # 41. Silicon Valley Turkey Trot
    ("Silicon Valley Turkey Trot", "Applied Materials", "title", [2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 42. St. Jude Memphis Marathon
    ("St. Jude Memphis Marathon", "St. Jude", "title", [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    ("St. Jude Memphis Marathon", "Juice Plus+", "official", [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 43. Statesman Cap10K
    ("Statesman Capitol 10K", "Baylor Scott & White", "official", [2025, 2026]),
    # 45. Transurban Bridge to Brisbane
    ("Transurban Bridge to Brisbane", "Transurban", "title", [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 46. Ukrop's Monument Ave 10K
    ("Ukrop's Monument Avenue 10K", "Ukrop's", "title", [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    ("Ukrop's Monument Avenue 10K", "Kroger", "official", [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]),
    # 47. Vancouver Sun Run
    ("Vancouver Sun Run", "Herbaland", "title", [2025, 2026]),
]

added = 0
for ev, brand, typ, years in new_partnerships:
    if (ev, brand) not in existing:
        data['partnerships'].append({"event": ev, "brand": brand, "type": typ, "years": years})
        added += 1

with open('sponsoring_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Added {len(new_brands)} brands, {added} partnerships")
print(f"Total: {len(data['brands'])} brands, {len(data['partnerships'])} partnerships")

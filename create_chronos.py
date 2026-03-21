import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# All collected data: (Course, Distance, Année, Temps Homme, Temps Femme)
data = []

# ============================================================
# MARATHONS (42K)
# ============================================================

marathon_data = [
    # ============================================================
    # HISTORICAL DATA (2015-2022)
    # ============================================================
    # BMW Berlin Marathon
    ("BMW Berlin Marathon", "42K", 2015, "2:04:00", "2:19:25"),
    ("BMW Berlin Marathon", "42K", 2016, "2:03:03", "N/A"),
    ("BMW Berlin Marathon", "42K", 2017, "2:03:32", "2:20:53"),
    ("BMW Berlin Marathon", "42K", 2018, "2:01:39", "2:18:11"),
    ("BMW Berlin Marathon", "42K", 2019, "2:01:41", "N/A"),
    ("BMW Berlin Marathon", "42K", 2021, "2:05:45", "N/A"),
    ("BMW Berlin Marathon", "42K", 2022, "2:01:09", "N/A"),
    # Bank of America Chicago Marathon
    ("Bank of America Chicago Marathon", "42K", 2015, "2:09:25", "2:23:33"),
    ("Bank of America Chicago Marathon", "42K", 2016, "2:11:23", "2:21:32"),
    ("Bank of America Chicago Marathon", "42K", 2017, "2:09:20", "2:18:31"),
    ("Bank of America Chicago Marathon", "42K", 2018, "2:05:11", "2:18:35"),
    ("Bank of America Chicago Marathon", "42K", 2019, "2:05:45", "2:14:04"),
    ("Bank of America Chicago Marathon", "42K", 2021, "2:06:12", "2:22:31"),
    ("Bank of America Chicago Marathon", "42K", 2022, "2:04:24", "2:14:18"),
    # TCS London Marathon
    ("TCS London Marathon", "42K", 2015, "2:04:42", "N/A"),
    ("TCS London Marathon", "42K", 2016, "2:03:05", "N/A"),
    ("TCS London Marathon", "42K", 2017, "2:05:48", "2:17:01"),
    ("TCS London Marathon", "42K", 2018, "2:04:17", "2:18:31"),
    ("TCS London Marathon", "42K", 2019, "2:02:37", "N/A"),
    ("TCS London Marathon", "42K", 2020, "2:05:41", "2:18:58"),
    ("TCS London Marathon", "42K", 2021, "2:04:01", "N/A"),
    ("TCS London Marathon", "42K", 2022, "2:04:39", "2:17:26"),
    # TCS New York City Marathon
    ("TCS New York City Marathon", "42K", 2015, "2:10:34", "2:24:25"),
    ("TCS New York City Marathon", "42K", 2016, "2:07:51", "2:24:26"),
    ("TCS New York City Marathon", "42K", 2017, "2:10:53", "N/A"),
    ("TCS New York City Marathon", "42K", 2018, "2:05:59", "2:22:48"),
    ("TCS New York City Marathon", "42K", 2019, "2:08:13", "2:22:38"),
    ("TCS New York City Marathon", "42K", 2021, "2:08:22", "2:22:39"),
    ("TCS New York City Marathon", "42K", 2022, "2:08:41", "2:23:23"),
    # Boston Marathon
    ("Boston Marathon", "42K", 2015, "2:09:17", "2:24:55"),
    ("Boston Marathon", "42K", 2016, "2:12:45", "2:29:19"),
    ("Boston Marathon", "42K", 2017, "2:09:37", "2:21:52"),
    ("Boston Marathon", "42K", 2018, "2:15:58", "2:39:54"),
    ("Boston Marathon", "42K", 2019, "2:07:57", "2:23:31"),
    ("Boston Marathon", "42K", 2021, "2:09:51", "N/A"),
    ("Boston Marathon", "42K", 2022, "2:06:51", "2:21:01"),
    # Tokyo Marathon
    ("Tokyo Marathon", "42K", 2015, "2:06:00", "2:23:15"),
    ("Tokyo Marathon", "42K", 2016, "2:06:56", "2:21:27"),
    ("Tokyo Marathon", "42K", 2017, "2:03:58", "N/A"),
    ("Tokyo Marathon", "42K", 2018, "2:05:30", "2:19:51"),
    ("Tokyo Marathon", "42K", 2019, "2:04:15", "N/A"),
    ("Tokyo Marathon", "42K", 2020, "2:04:15", "2:17:45"),
    ("Tokyo Marathon", "42K", 2021, "2:02:40", "2:16:02"),
    # Schneider Electric Marathon de Paris
    ("Schneider Electric Marathon de Paris", "42K", 2017, "2:06:10", "N/A"),
    ("Schneider Electric Marathon de Paris", "42K", 2018, "2:06:25", "2:22:56"),
    ("Schneider Electric Marathon de Paris", "42K", 2019, "2:07:05", "2:22:47"),
    ("Schneider Electric Marathon de Paris", "42K", 2022, "2:05:00", "2:19:48"),
    # NN Marathon Rotterdam
    ("NN Marathon Rotterdam", "42K", 2015, "2:06:47", "2:26:30"),
    ("NN Marathon Rotterdam", "42K", 2016, "2:06:11", "2:26:15"),
    ("NN Marathon Rotterdam", "42K", 2017, "2:06:04", "2:24:18"),
    ("NN Marathon Rotterdam", "42K", 2018, "2:04:11", "2:22:55"),
    ("NN Marathon Rotterdam", "42K", 2021, "2:03:36", "N/A"),
    ("NN Marathon Rotterdam", "42K", 2022, "2:04:45", "N/A"),
    # TCS Amsterdam Marathon
    ("TCS Amsterdam Marathon", "42K", 2015, "2:06:19", "2:24:11"),
    ("TCS Amsterdam Marathon", "42K", 2016, "2:05:20", "2:23:20"),
    ("TCS Amsterdam Marathon", "42K", 2017, "2:05:09", "2:21:53"),
    ("TCS Amsterdam Marathon", "42K", 2018, "2:04:06", "N/A"),
    ("TCS Amsterdam Marathon", "42K", 2021, "2:03:38", "2:17:57"),
    ("TCS Amsterdam Marathon", "42K", 2022, "N/A", "2:17:20"),
    # Valencia Marathon Trinidad Alfonso Zurich
    ("Valencia Marathon Trinidad Alfonso Zurich", "42K", 2015, "2:06:13", "N/A"),
    ("Valencia Marathon Trinidad Alfonso Zurich", "42K", 2020, "2:03:00", "N/A"),
    ("Valencia Marathon Trinidad Alfonso Zurich", "42K", 2022, "2:01:53", "2:14:57"),
    # Irish Life Dublin Marathon
    ("Irish Life Dublin Marathon", "42K", 2015, "2:14:01", "2:30:00"),
    ("Irish Life Dublin Marathon", "42K", 2016, "2:12:18", "2:32:32"),
    ("Irish Life Dublin Marathon", "42K", 2017, "2:15:52", "2:28:57"),
    ("Irish Life Dublin Marathon", "42K", 2018, "2:13:23", "2:33:48"),
    ("Irish Life Dublin Marathon", "42K", 2019, "2:08:06", "2:27:48"),
    ("Irish Life Dublin Marathon", "42K", 2022, "2:11:30", "2:28:32"),
    # Vienna City Marathon
    ("Vienna City Marathon", "42K", 2015, "2:07:31", "2:30:09"),
    ("Vienna City Marathon", "42K", 2017, "2:08:40", "2:24:20"),
    ("Vienna City Marathon", "42K", 2019, "2:06:56", "2:22:12"),
    ("Vienna City Marathon", "42K", 2021, "2:09:25", "2:24:29"),
    ("Vienna City Marathon", "42K", 2022, "2:06:53", "2:20:59"),
    # Honolulu Marathon
    ("Honolulu Marathon", "42K", 2015, "2:11:43", "2:28:34"),
    ("Honolulu Marathon", "42K", 2016, "2:09:37", "2:31:10"),
    ("Honolulu Marathon", "42K", 2017, "2:08:27", "2:22:15"),
    ("Honolulu Marathon", "42K", 2018, "2:09:01", "2:36:22"),
    ("Honolulu Marathon", "42K", 2019, "2:07:59", "2:31:09"),
    ("Honolulu Marathon", "42K", 2021, "2:14:30", "2:41:24"),
    ("Honolulu Marathon", "42K", 2022, "2:14:40", "2:30:58"),
    # ============================================================
    # RECENT DATA (2023-2026)
    # ============================================================
    # Chevron Houston Marathon
    ("Chevron Houston Marathon", "42K", 2023, "2:10:26", "2:19:24"),
    ("Chevron Houston Marathon", "42K", 2024, "2:06:39", "2:19:33"),
    ("Chevron Houston Marathon", "42K", 2025, "2:08:17", "2:20:54"),
    ("Chevron Houston Marathon", "42K", 2026, "2:05:45", "2:24:17"),
    # Tata Mumbai Marathon
    ("Tata Mumbai Marathon", "42K", 2023, "2:07:32", "2:24:15"),
    ("Tata Mumbai Marathon", "42K", 2024, "2:07:50", "2:26:06"),
    ("Tata Mumbai Marathon", "42K", 2025, "2:11:44", "2:24:56"),
    ("Tata Mumbai Marathon", "42K", 2026, "2:09:55", "2:25:13"),
    # Zurich Maratón de Sevilla
    ("Zurich Maratón de Sevilla", "42K", 2023, "2:04:59", "2:20:29"),
    ("Zurich Maratón de Sevilla", "42K", 2024, "2:03:27", "2:22:13"),
    ("Zurich Maratón de Sevilla", "42K", 2025, "2:05:15", "2:22:17"),
    ("Zurich Maratón de Sevilla", "42K", 2026, "2:03:59", "2:20:39"),
    # Seoul Marathon
    ("Seoul Marathon", "42K", 2023, "2:05:27", "2:28:32"),
    ("Seoul Marathon", "42K", 2024, "2:06:08", "2:21:32"),
    ("Seoul Marathon", "42K", 2025, "2:05:42", "2:21:36"),
    # Tokyo Marathon
    ("Tokyo Marathon", "42K", 2023, "2:05:22", "2:16:28"),
    ("Tokyo Marathon", "42K", 2024, "2:02:16", "2:15:55"),
    ("Tokyo Marathon", "42K", 2025, "2:03:23", "2:16:31"),
    ("Tokyo Marathon", "42K", 2026, "2:03:37", "2:14:29"),
    # Zurich Marató de Barcelona
    ("Zurich Marató de Barcelona", "42K", 2023, "2:05:06", "2:19:44"),
    ("Zurich Marató de Barcelona", "42K", 2024, "2:05:01", "2:19:52"),
    ("Zurich Marató de Barcelona", "42K", 2025, "2:04:13", "2:19:33"),
    ("Zurich Marató de Barcelona", "42K", 2026, "2:04:57", "2:10:53"),
    # Acea Run Rome The Marathon
    ("Acea Run Rome The Marathon", "42K", 2023, "2:07:43", "2:23:01"),
    ("Acea Run Rome The Marathon", "42K", 2024, "2:06:23", "2:24:35"),
    ("Acea Run Rome The Marathon", "42K", 2025, "2:07:35", "2:26:16"),
    # ASICS Los Angeles Marathon
    ("ASICS Los Angeles Marathon", "42K", 2023, "2:13:13", "2:31:00"),
    ("ASICS Los Angeles Marathon", "42K", 2024, "2:11:00", "2:25:29"),
    ("ASICS Los Angeles Marathon", "42K", 2025, "2:07:56", "2:30:16"),
    ("ASICS Los Angeles Marathon", "42K", 2026, "2:11:18", "2:25:20"),
    # Boston Marathon
    ("Boston Marathon", "42K", 2023, "2:05:54", "2:21:38"),
    ("Boston Marathon", "42K", 2024, "2:06:17", "2:22:37"),
    ("Boston Marathon", "42K", 2025, "2:04:45", "2:17:22"),
    # TCS London Marathon
    ("TCS London Marathon", "42K", 2023, "2:01:25", "2:18:33"),
    ("TCS London Marathon", "42K", 2024, "2:04:01", "2:16:16"),
    ("TCS London Marathon", "42K", 2025, "2:02:27", "2:15:50"),
    # Zurich Rock 'n' Roll Running Series Madrid
    ("Zurich Rock 'n' Roll Running Series Madrid", "42K", 2023, "2:10:29", "2:26:31"),
    ("Zurich Rock 'n' Roll Running Series Madrid", "42K", 2024, "2:08:05", "2:26:19"),
    ("Zurich Rock 'n' Roll Running Series Madrid", "42K", 2025, "2:09:11", "2:25:55"),
    # Adidas Manchester Marathon
    ("Adidas Manchester Marathon", "42K", 2023, "2:16:27", "2:31:26"),
    ("Adidas Manchester Marathon", "42K", 2024, "2:16:29", "2:37:14"),
    ("Adidas Manchester Marathon", "42K", 2025, "2:16:56", "2:34:53"),
    # Schneider Electric Marathon de Paris
    ("Schneider Electric Marathon de Paris", "42K", 2023, "2:07:15", "2:23:19"),
    ("Schneider Electric Marathon de Paris", "42K", 2024, "2:05:33", "2:20:45"),
    ("Schneider Electric Marathon de Paris", "42K", 2025, "2:05:25", "2:20:45"),
    # NN Marathon Rotterdam
    ("NN Marathon Rotterdam", "42K", 2023, "2:03:47", "2:20:31"),
    ("NN Marathon Rotterdam", "42K", 2024, "2:04:45", "2:19:30"),
    ("NN Marathon Rotterdam", "42K", 2025, "2:04:33", "2:21:15"),
    # Vienna City Marathon
    ("Vienna City Marathon", "42K", 2023, "2:05:08", "2:24:12"),
    ("Vienna City Marathon", "42K", 2024, "2:06:35", "2:24:08"),
    ("Vienna City Marathon", "42K", 2025, "2:08:28", "2:24:14"),
    # Copenhagen Marathon
    ("Copenhagen Marathon", "42K", 2023, "2:09:12", "2:23:14"),
    ("Copenhagen Marathon", "42K", 2024, "2:09:11", "2:23:19"),
    ("Copenhagen Marathon", "42K", 2025, "2:09:09", "2:23:19"),
    # Prague International Marathon
    ("Prague International Marathon", "42K", 2023, "2:05:09", "2:20:42"),
    ("Prague International Marathon", "42K", 2024, "2:08:43", "2:23:41"),
    ("Prague International Marathon", "42K", 2025, "2:05:14", "2:20:55"),
    # Sanlam Cape Town Marathon
    ("Sanlam Cape Town Marathon", "42K", 2023, "2:11:28", "2:24:17"),
    ("Sanlam Cape Town Marathon", "42K", 2024, "2:08:16", "2:22:22"),
    ("Sanlam Cape Town Marathon", "42K", 2025, "Annulé", "Annulé"),
    # Maratón de la Ciudad de México Telcel
    ("Maratón de la Ciudad de México Telcel", "42K", 2023, "2:08:23", "2:27:17"),
    ("Maratón de la Ciudad de México Telcel", "42K", 2024, "2:10:36", "2:29:19"),
    ("Maratón de la Ciudad de México Telcel", "42K", 2025, "2:11:14", "2:23:22"),
    # TCS Sydney Marathon
    ("TCS Sydney Marathon presented by ASICS", "42K", 2023, "2:08:20", "2:26:47"),
    ("TCS Sydney Marathon presented by ASICS", "42K", 2024, "2:06:17", "2:21:40"),
    ("TCS Sydney Marathon presented by ASICS", "42K", 2025, "2:06:06", "2:18:22"),
    # BMW Berlin Marathon
    ("BMW Berlin Marathon", "42K", 2023, "2:02:42", "2:11:53"),
    ("BMW Berlin Marathon", "42K", 2024, "2:03:17", "2:16:42"),
    ("BMW Berlin Marathon", "42K", 2025, "2:02:16", "2:21:05"),
    # NN Maraton Warszawski
    ("NN Maraton Warszawski", "42K", 2023, "2:15:29", "2:34:41"),
    ("NN Maraton Warszawski", "42K", 2024, "2:10:43", "2:31:24"),
    ("NN Maraton Warszawski", "42K", 2025, "2:11:21", "2:33:41"),
    # TCS Amsterdam Marathon
    ("TCS Amsterdam Marathon", "42K", 2023, "2:04:18", "2:18:21"),
    ("TCS Amsterdam Marathon", "42K", 2024, "2:05:38", "2:16:52"),
    ("TCS Amsterdam Marathon", "42K", 2025, "2:03:31", "2:17:37"),
    # Bank of America Chicago Marathon
    ("Bank of America Chicago Marathon", "42K", 2023, "2:00:35", "2:13:44"),
    ("Bank of America Chicago Marathon", "42K", 2024, "2:02:43", "2:09:56"),
    ("Bank of America Chicago Marathon", "42K", 2025, "2:02:21", "2:14:56"),
    # EDP Maratona de Lisboa
    ("EDP Maratona de Lisboa", "42K", 2023, "N/A", "N/A"),
    ("EDP Maratona de Lisboa", "42K", 2024, "N/A", "N/A"),
    ("EDP Maratona de Lisboa", "42K", 2025, "2:05:43", "2:24:17"),
    # TCS Toronto Waterfront Marathon
    ("TCS Toronto Waterfront Marathon", "42K", 2023, "2:09:20", "2:23:11"),
    ("TCS Toronto Waterfront Marathon", "42K", 2024, "2:07:16", "2:20:44"),
    ("TCS Toronto Waterfront Marathon", "42K", 2025, "2:08:05", "2:21:04"),
    # Irish Life Dublin Marathon
    ("Irish Life Dublin Marathon", "42K", 2023, "2:06:52", "2:26:22"),
    ("Irish Life Dublin Marathon", "42K", 2024, "2:08:47", "2:24:13"),
    ("Irish Life Dublin Marathon", "42K", 2025, "2:08:51", "2:26:28"),
    # Marine Corps Marathon
    ("Marine Corps Marathon", "42K", 2023, "2:25:56", "2:50:49"),
    ("Marine Corps Marathon", "42K", 2024, "2:25:06", "2:39:36"),
    ("Marine Corps Marathon", "42K", 2025, "2:18:51", "2:34:08"),
    # Bangsaen42 Chonburi Marathon
    ("Bangsaen42 Chonburi Marathon", "42K", 2023, "N/A", "N/A"),
    ("Bangsaen42 Chonburi Marathon", "42K", 2024, "N/A", "N/A"),
    ("Bangsaen42 Chonburi Marathon", "42K", 2025, "2:17:53", "N/A"),
    # TCS New York City Marathon
    ("TCS New York City Marathon", "42K", 2023, "2:04:58", "2:27:23"),
    ("TCS New York City Marathon", "42K", 2024, "2:07:39", "2:24:35"),
    ("TCS New York City Marathon", "42K", 2025, "2:08:09", "2:19:51"),
    # Standard Chartered Singapore Marathon
    ("Standard Chartered Singapore Marathon", "42K", 2024, "2:16:06", "2:39:04"),
    ("Standard Chartered Singapore Marathon", "42K", 2025, "2:15:40", "2:41:24"),
    # Taipei Marathon
    ("Taipei Marathon", "42K", 2023, "2:11:05", "2:27:14"),
    ("Taipei Marathon", "42K", 2024, "2:11:41", "2:32:47"),
    ("Taipei Marathon", "42K", 2025, "N/A", "N/A"),  # Course en décembre 2025, pas encore de données fiables
    # Valencia Marathon Trinidad Alfonso Zurich
    ("Valencia Marathon Trinidad Alfonso Zurich", "42K", 2023, "2:01:48", "2:15:51"),
    ("Valencia Marathon Trinidad Alfonso Zurich", "42K", 2024, "2:02:05", "2:16:49"),
    ("Valencia Marathon Trinidad Alfonso Zurich", "42K", 2025, "2:02:24", "2:14:00"),
    # Honolulu Marathon
    ("Honolulu Marathon", "42K", 2023, "2:15:42", "2:33:01"),
    ("Honolulu Marathon", "42K", 2024, "2:11:59", "2:31:14"),
    ("Honolulu Marathon", "42K", 2025, "2:13:38", "2:30:43"),
    # Standard Chartered KL Marathon
    ("Standard Chartered KL Marathon", "42K", 2025, "2:17:28", "2:41:36"),
    # Standard Chartered Hong Kong Marathon
    ("Standard Chartered Hong Kong Marathon", "42K", 2026, "N/A", "N/A"),
    ("Standard Chartered Hong Kong Marathon", "42K", 2019, "2:09:20", "2:26:13"),
]

# ============================================================
# SEMI-MARATHONS (21K)
# ============================================================

half_marathon_data = [
    # HOKA Semi de Paris
    ("HOKA Semi de Paris", "21K", 2023, "0:59:38", "1:06:01"),
    ("HOKA Semi de Paris", "21K", 2024, "1:00:45", "1:06:58"),
    ("HOKA Semi de Paris", "21K", 2025, "1:00:16", "1:07:14"),
    ("HOKA Semi de Paris", "21K", 2026, "1:00:11", "1:05:12"),
    # Mitja Marato Barcelona by Brooks
    ("Mitja Marato Barcelona by Brooks", "21K", 2023, "0:58:53", "1:04:37"),
    ("Mitja Marato Barcelona by Brooks", "21K", 2024, "0:59:21", "1:04:28"),
    ("Mitja Marato Barcelona by Brooks", "21K", 2025, "0:56:42", "1:04:11"),
    ("Mitja Marato Barcelona by Brooks", "21K", 2026, "N/A", "1:04:00"),
    # Aramco Houston Half Marathon
    ("Aramco Houston Half Marathon", "21K", 2024, "1:00:42", "1:04:37"),
    ("Aramco Houston Half Marathon", "21K", 2025, "0:59:17", "N/A"),
    ("Aramco Houston Half Marathon", "21K", 2026, "0:59:01", "1:04:49"),
    # Medio Maraton de Sevilla
    ("Medio Maraton de Sevilla", "21K", 2024, "0:59:21", "1:07:59"),
    ("Medio Maraton de Sevilla", "21K", 2025, "0:59:33", "1:07:18"),
    ("Medio Maraton de Sevilla", "21K", 2026, "1:00:24", "1:06:33"),
    # Standard Chartered Hong Kong Half Marathon
    ("Standard Chartered Hong Kong Half Marathon", "21K", 2025, "N/A", "N/A"),
    # Walt Disney World Marathon Weekend (Half)
    ("Walt Disney World Marathon Weekend", "21K", 2025, "N/A", "N/A"),
    ("Walt Disney World Marathon Weekend", "21K", 2026, "N/A", "N/A"),
    # Tata Mumbai Marathon (Half)
    ("Tata Mumbai Marathon (Half)", "21K", 2025, "N/A", "N/A"),
    ("Tata Mumbai Marathon (Half)", "21K", 2026, "N/A", "N/A"),
    # Riyadh Marathon (Half)
    ("Riyadh Marathon (Half)", "21K", 2023, "N/A", "N/A"),
    ("Riyadh Marathon (Half)", "21K", 2024, "N/A", "N/A"),
    ("Riyadh Marathon (Half)", "21K", 2025, "N/A", "N/A"),
    ("Riyadh Marathon (Half)", "21K", 2026, "N/A", "N/A"),
    # Rock 'n' Roll Running Series Las Vegas
    ("Rock 'n' Roll Running Series Las Vegas", "21K", 2023, "N/A", "N/A"),
    ("Rock 'n' Roll Running Series Las Vegas", "21K", 2024, "N/A", "N/A"),
    ("Rock 'n' Roll Running Series Las Vegas", "21K", 2025, "N/A", "N/A"),
    ("Rock 'n' Roll Running Series Las Vegas", "21K", 2026, "N/A", "N/A"),
    # Burj2Burj Half Marathon
    ("Burj2Burj Half Marathon", "21K", 2024, "N/A", "N/A"),
    ("Burj2Burj Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("Burj2Burj Half Marathon", "21K", 2026, "0:59:26", "1:06:57"),
    # Generali Berlin Half Marathon
    ("Generali Berlin Half Marathon", "21K", 2023, "0:59:01", "1:05:43"),
    ("Generali Berlin Half Marathon", "21K", 2024, "0:59:30", "1:06:53"),
    ("Generali Berlin Half Marathon", "21K", 2025, "0:58:43", "1:03:35"),
    # United Airlines NYC Half
    ("United Airlines NYC Half", "21K", 2025, "1:01:31", "1:07:04"),
    ("United Airlines NYC Half", "21K", 2026, "0:59:30", "1:06:33"),
    # EDP Lisboa Meia Maratona
    ("EDP Lisboa Meia Maratona", "21K", 2024, "N/A", "N/A"),
    ("EDP Lisboa Meia Maratona", "21K", 2025, "N/A", "N/A"),
    ("EDP Lisboa Meia Maratona", "21K", 2026, "N/A", "N/A"),
    # Generali Prague Half Marathon
    ("Generali Prague Half Marathon", "21K", 2023, "0:59:43", "1:06:00"),
    ("Generali Prague Half Marathon", "21K", 2024, "0:58:24", "1:08:10"),
    ("Generali Prague Half Marathon", "21K", 2025, "0:58:54", "1:05:27"),
    # Eurospin RomaOstia Half Marathon
    ("Eurospin RomaOstia Half Marathon", "21K", 2023, "0:59:17", "1:06:21"),
    ("Eurospin RomaOstia Half Marathon", "21K", 2024, "1:01:10", "1:07:38"),
    ("Eurospin RomaOstia Half Marathon", "21K", 2025, "0:58:49", "1:08:20"),
    ("Eurospin RomaOstia Half Marathon", "21K", 2026, "0:58:00", "N/A"),
    # Copenhagen Half Marathon
    ("Copenhagen Half Marathon", "21K", 2023, "0:59:11", "1:05:53"),
    ("Copenhagen Half Marathon", "21K", 2024, "0:58:05", "1:05:11"),
    ("Copenhagen Half Marathon", "21K", 2025, "0:58:23", "1:04:44"),
    # AJ Bell Great North Run
    ("AJ Bell Great North Run", "21K", 2025, "1:00:52", "1:09:32"),
    # Valencia Half Marathon Trinidad Alfonso Zurich
    ("Valencia Half Marathon Trinidad Alfonso Zurich", "21K", 2025, "0:58:02", "1:03:08"),
    # Göteborgsvarvet
    ("Göteborgsvarvet", "21K", 2024, "N/A", "N/A"),
    ("Göteborgsvarvet", "21K", 2025, "N/A", "N/A"),
    # Run in Lyon (Semi)
    ("Run in Lyon (Semi)", "21K", 2023, "N/A", "N/A"),
    ("Run in Lyon (Semi)", "21K", 2024, "1:05:44", "1:18:34"),
    ("Run in Lyon (Semi)", "21K", 2025, "N/A", "N/A"),
    # Zurich Rock 'n' Roll Running Series Madrid (Half)
    ("Zurich Rock 'n' Roll Running Series Madrid (Half)", "21K", 2023, "N/A", "N/A"),
    ("Zurich Rock 'n' Roll Running Series Madrid (Half)", "21K", 2024, "N/A", "N/A"),
    ("Zurich Rock 'n' Roll Running Series Madrid (Half)", "21K", 2025, "N/A", "N/A"),
    # Warsaw Half Marathon
    ("Warsaw Half Marathon", "21K", 2024, "N/A", "N/A"),
    ("Warsaw Half Marathon", "21K", 2025, "N/A", "N/A"),
    # TCS Toronto Waterfront Marathon (Half)
    ("TCS Toronto Waterfront Marathon (Half)", "21K", 2023, "N/A", "N/A"),
    ("TCS Toronto Waterfront Marathon (Half)", "21K", 2024, "N/A", "N/A"),
    ("TCS Toronto Waterfront Marathon (Half)", "21K", 2025, "N/A", "N/A"),
    # Hyundai Meia Maratona (Lisbon)
    ("Hyundai Meia Maratona", "21K", 2023, "N/A", "N/A"),
    ("Hyundai Meia Maratona", "21K", 2024, "N/A", "N/A"),
    ("Hyundai Meia Maratona", "21K", 2025, "N/A", "N/A"),
    # Taipei Half Marathon
    ("Taipei Half Marathon", "21K", 2023, "N/A", "N/A"),
    ("Taipei Half Marathon", "21K", 2024, "N/A", "N/A"),
    ("Taipei Half Marathon", "21K", 2025, "N/A", "N/A"),
    # Bangsaen21
    ("Bangsaen21", "21K", 2023, "N/A", "N/A"),
    ("Bangsaen21", "21K", 2024, "N/A", "N/A"),
    ("Bangsaen21", "21K", 2025, "N/A", "N/A"),
    # Other half marathons with limited data (1 year only, 2025)
    ("Coelmo Napoli City Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("Coelmo Napoli City Half Marathon", "21K", 2026, "N/A", "N/A"),
    ("Kagawa Marugame International Half Marathon", "21K", 2026, "N/A", "N/A"),
    ("Movistar Madrid Medio Maraton", "21K", 2025, "N/A", "N/A"),
    ("NN CPC Loop Den Haag - Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("NN CPC Loop Den Haag - Half Marathon", "21K", 2026, "N/A", "N/A"),
    ("Disney Princess Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("Disney Princess Half Marathon", "21K", 2026, "N/A", "N/A"),
    ("St. Jude Rock 'n' Roll Running Series Washington DC", "21K", 2025, "N/A", "N/A"),
    ("GetPro Bath Half", "21K", 2025, "N/A", "N/A"),
    ("GetPro Bath Half", "21K", 2026, "N/A", "N/A"),
    ("NYCRUNS Brooklyn Experience Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("London Landmarks Half Marathon", "21K", 2024, "N/A", "N/A"),
    ("London Landmarks Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("Vienna City Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("21K de Montréal", "21K", 2025, "N/A", "N/A"),
    ("St. Jude Rock 'n' Roll Series Nashville", "21K", 2025, "N/A", "N/A"),
    ("NYRR RBC Brooklyn Half", "21K", 2025, "N/A", "N/A"),
    ("Hoka Runaway Sydney Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("IU Health 500 Festival Mini-Marathon", "21K", 2025, "N/A", "N/A"),
    ("Rock 'n' Roll Running Series San Diego", "21K", 2025, "N/A", "N/A"),
    ("AJ Bell Great Manchester Run", "21K", 2025, "N/A", "N/A"),
    ("AJ Bell Great Bristol Run", "21K", 2025, "N/A", "N/A"),
    ("Brølløbet - The Bridge Run", "21K", 2025, "N/A", "N/A"),
    ("Media Maraton de Bogota", "21K", 2025, "N/A", "N/A"),
    ("Asics Run Melbourne", "21K", 2025, "N/A", "N/A"),
    ("The Big Half", "21K", 2025, "N/A", "N/A"),
    ("Life Time Chicago Half Marathon & 5K", "21K", 2024, "N/A", "N/A"),
    ("Life Time Chicago Half Marathon & 5K", "21K", 2025, "N/A", "N/A"),
    ("Cardiff Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("Manchester Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("Wizz Air Rome Half Marathon by Brooks", "21K", 2025, "N/A", "N/A"),
    ("Royal Parks Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("Tokyo Legacy Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("TCS Mizuno Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("Nike Melbourne Marathon Festival", "21K", 2025, "N/A", "N/A"),
    ("Vedanta Delhi Half Marathon", "21K", 2025, "0:59:50", "1:07:20"),
    ("Half Marathon Munchen by Brooks", "21K", 2025, "N/A", "N/A"),
    ("Semi-Marathon de Boulogne-Billancourt", "21K", 2025, "N/A", "N/A"),
    ("Standard Chartered Singapore Half Marathon", "21K", 2025, "N/A", "N/A"),
    ("Rock 'n' Roll Running Series Mexico City", "21K", 2025, "N/A", "N/A"),
    # Standard Chartered KL Half Marathon
    ("Standard Chartered KL Half Marathon", "21K", 2025, "1:11:08", "1:23:55"),
    # Standard Chartered Hong Kong Half Marathon
    ("Standard Chartered Hong Kong Half Marathon", "21K", 2026, "N/A", "N/A"),
    ("Standard Chartered Hong Kong Half Marathon", "21K", 2019, "1:01:13", "1:09:28"),
]

# ============================================================
# 10K
# ============================================================

tenk_data = [
    # 10K Valencia Ibercaja by Kiprun
    ("10K Valencia Ibercaja by Kiprun", "10K", 2023, "N/A", "0:29:19"),
    ("10K Valencia Ibercaja by Kiprun", "10K", 2024, "N/A", "0:28:45"),
    ("10K Valencia Ibercaja by Kiprun", "10K", 2025, "N/A", "N/A"),
    ("10K Valencia Ibercaja by Kiprun", "10K", 2026, "0:26:45", "0:29:25"),
    # 10K Montmartre
    ("10K Montmartre", "10K", 2026, "N/A", "N/A"),
    # Cancer Research UK London Winter Run
    ("Cancer Research UK London Winter Run", "10K", 2023, "0:28:52", "0:31:59"),
    ("Cancer Research UK London Winter Run", "10K", 2024, "0:28:46", "0:32:33"),
    ("Cancer Research UK London Winter Run", "10K", 2025, "0:29:22", "0:34:32"),
    ("Cancer Research UK London Winter Run", "10K", 2026, "N/A", "N/A"),
    # EDP Meia Maratona de Lisboa - Vodafone 10K
    ("EDP Meia Maratona de Lisboa - Vodafone 10K", "10K", 2023, "N/A", "N/A"),
    ("EDP Meia Maratona de Lisboa - Vodafone 10K", "10K", 2024, "N/A", "N/A"),
    ("EDP Meia Maratona de Lisboa - Vodafone 10K", "10K", 2025, "N/A", "N/A"),
    ("EDP Meia Maratona de Lisboa - Vodafone 10K", "10K", 2026, "N/A", "N/A"),
    # Cooper River Bridge Run
    ("Cooper River Bridge Run", "10K", 2023, "N/A", "N/A"),
    ("Cooper River Bridge Run", "10K", 2024, "N/A", "N/A"),
    ("Cooper River Bridge Run", "10K", 2025, "0:28:27", "0:31:49"),
    # Vancouver Sun Run
    ("Vancouver Sun Run", "10K", 2023, "N/A", "N/A"),
    ("Vancouver Sun Run", "10K", 2024, "N/A", "N/A"),
    ("Vancouver Sun Run", "10K", 2025, "0:28:09", "0:32:54"),
    # Statesman Capitol 10K
    ("Statesman Capitol 10K", "10K", 2023, "N/A", "N/A"),
    ("Statesman Capitol 10K", "10K", 2024, "N/A", "N/A"),
    ("Statesman Capitol 10K", "10K", 2025, "N/A", "N/A"),
    # Ukrop's Monument Avenue 10K
    ("Ukrop's Monument Avenue 10K", "10K", 2023, "N/A", "N/A"),
    ("Ukrop's Monument Avenue 10K", "10K", 2024, "N/A", "N/A"),
    ("Ukrop's Monument Avenue 10K", "10K", 2025, "N/A", "N/A"),
    # Bangsaen10
    ("Bangsaen10", "10K", 2023, "N/A", "N/A"),
    ("Bangsaen10", "10K", 2024, "N/A", "N/A"),
    ("Bangsaen10", "10K", 2025, "N/A", "N/A"),
    # AJ Bell Great Manchester Run (10K)
    ("AJ Bell Great Manchester Run (10K)", "10K", 2024, "N/A", "N/A"),
    ("AJ Bell Great Manchester Run (10K)", "10K", 2025, "N/A", "N/A"),
    # BOLDERBoulder 10K
    ("BOLDERBoulder 10K", "10K", 2023, "0:29:08", "0:33:25"),
    ("BOLDERBoulder 10K", "10K", 2024, "0:29:13", "0:32:45"),
    ("BOLDERBoulder 10K", "10K", 2025, "N/A", "N/A"),
    # Adidas 10K Paris
    ("Adidas 10K Paris", "10K", 2023, "N/A", "N/A"),
    ("Adidas 10K Paris", "10K", 2024, "0:29:37", "0:32:18"),
    ("Adidas 10K Paris", "10K", 2025, "N/A", "N/A"),
    # Royal Run
    ("Royal Run", "10K", 2023, "N/A", "N/A"),
    ("Royal Run", "10K", 2024, "N/A", "N/A"),
    ("Royal Run", "10K", 2025, "N/A", "N/A"),
    # Atlanta Journal-Constitution Peachtree Road Race
    ("Atlanta Journal-Constitution Peachtree Road Race", "10K", 2023, "0:27:41", "0:30:43"),
    ("Atlanta Journal-Constitution Peachtree Road Race", "10K", 2024, "0:28:03", "0:31:12"),
    ("Atlanta Journal-Constitution Peachtree Road Race", "10K", 2025, "N/A", "0:31:29"),
    # Saucony London 10K
    ("Saucony London 10K", "10K", 2023, "N/A", "N/A"),
    ("Saucony London 10K", "10K", 2024, "0:29:41", "0:32:51"),
    ("Saucony London 10K", "10K", 2025, "0:29:33", "N/A"),
    # Transurban Bridge to Brisbane
    ("Transurban Bridge to Brisbane", "10K", 2023, "N/A", "N/A"),
    ("Transurban Bridge to Brisbane", "10K", 2024, "N/A", "N/A"),
    ("Transurban Bridge to Brisbane", "10K", 2025, "N/A", "N/A"),
    # Vitality London 10,000
    ("Vitality London 10,000", "10K", 2023, "N/A", "N/A"),
    ("Vitality London 10,000", "10K", 2024, "0:29:14", "0:31:36"),
    ("Vitality London 10,000", "10K", 2025, "N/A", "N/A"),
    # Run in Lyon (10K)
    ("Run in Lyon (10K)", "10K", 2023, "N/A", "N/A"),
    ("Run in Lyon (10K)", "10K", 2024, "N/A", "N/A"),
    ("Run in Lyon (10K)", "10K", 2025, "N/A", "N/A"),
    # ASICS LDNX
    ("ASICS LDNX", "10K", 2025, "N/A", "N/A"),
    # NN San Silvestre Vallecana
    ("NN San Silvestre Vallecana", "10K", 2023, "N/A", "N/A"),  # Aregawi / Garcia - temps exacts non trouvés
    ("NN San Silvestre Vallecana", "10K", 2024, "N/A", "0:31:18"),
    ("NN San Silvestre Vallecana", "10K", 2025, "0:27:41", "0:31:11"),
    # NN CPC Loop Den Haag - 10 KM Loop
    ("NN CPC Loop Den Haag - 10 KM Loop", "10K", 2026, "N/A", "N/A"),
]

data.extend(marathon_data)
data.extend(half_marathon_data)
data.extend(tenk_data)

# Sort by Distance (42K first, then 21K, then 10K), then Course, then Year
distance_order = {"42K": 0, "21K": 1, "10K": 2}
data.sort(key=lambda x: (distance_order.get(x[1], 9), x[0], x[2]))

# Create workbook
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Chronos Vainqueurs"

# Header style
header_font = Font(bold=True, color="FFFFFF", size=11)
header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

thin_border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

# Distance color fills
fill_42k = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")  # Blue
fill_21k = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")  # Green
fill_10k = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")  # Orange
fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

# Headers
headers = ["Course", "Distance", "Année", "Temps Vainqueur Homme", "Temps Vainqueur Femme"]
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = header_alignment
    cell.border = thin_border

# Data rows
for row_idx, (course, distance, year, men_time, women_time) in enumerate(data, 2):
    ws.cell(row=row_idx, column=1, value=course).border = thin_border
    ws.cell(row=row_idx, column=2, value=distance).border = thin_border
    ws.cell(row=row_idx, column=2).alignment = Alignment(horizontal="center")
    ws.cell(row=row_idx, column=3, value=year).border = thin_border
    ws.cell(row=row_idx, column=3).alignment = Alignment(horizontal="center")
    ws.cell(row=row_idx, column=4, value=men_time).border = thin_border
    ws.cell(row=row_idx, column=4).alignment = Alignment(horizontal="center")
    ws.cell(row=row_idx, column=5, value=women_time).border = thin_border
    ws.cell(row=row_idx, column=5).alignment = Alignment(horizontal="center")

    # Color by distance
    if distance == "42K":
        fill = fill_42k if row_idx % 2 == 0 else fill_white
    elif distance == "21K":
        fill = fill_21k if row_idx % 2 == 0 else fill_white
    else:
        fill = fill_10k if row_idx % 2 == 0 else fill_white

    for col in range(1, 6):
        ws.cell(row=row_idx, column=col).fill = fill

# Column widths
ws.column_dimensions['A'].width = 50
ws.column_dimensions['B'].width = 12
ws.column_dimensions['C'].width = 10
ws.column_dimensions['D'].width = 28
ws.column_dimensions['E'].width = 28

# Freeze panes
ws.freeze_panes = "A2"

# Auto-filter
ws.auto_filter.ref = f"A1:E{len(data) + 1}"

# Save
output_path = r"C:\Users\mathi\Documents\6. DATA PACE\0. Dashboard\Fichiers sources\Chronos_Vainqueurs.xlsx"
wb.save(output_path)

# Stats
total = len(data)
with_data = sum(1 for r in data if r[3] != "N/A" or r[4] != "N/A")
marathons = sum(1 for r in data if r[1] == "42K")
halfs = sum(1 for r in data if r[1] == "21K")
tenks = sum(1 for r in data if r[1] == "10K")
courses = len(set(r[0] for r in data))

print(f"Fichier sauvegardé: {output_path}")
print(f"Total lignes: {total}")
print(f"  - 42K: {marathons} lignes")
print(f"  - 21K: {halfs} lignes")
print(f"  - 10K: {tenks} lignes")
print(f"Courses uniques: {courses}")
print(f"Lignes avec au moins 1 chrono: {with_data}/{total} ({100*with_data//total}%)")

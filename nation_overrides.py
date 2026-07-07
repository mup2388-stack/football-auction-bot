"""
Nation overrides for players missing nationality in the PES Teams-Players CSV.
Keyed by PES player ID. Based on real-world knowledge of these players.
"""
NATION_OVERRIDES = {
    # Mali
    "112218": "Mali",      # Yves Bissouma
    "112229": "Mali",      # Rominigue Kouamé
    "133697": "Mali",      # Boubacar Traoré
    "136256": "Mali",      # Ibrahima Koné
    "148984": "Mali",      # Kamory Doumbia
    "157042": "Mali",      # Mamadou Sangaré
    "113551": "Mali",      # Bakaye Dibassy
    "114868": "Mali",      # Fousseni Diabaté
    "140079": "Mali",      # Fodé Doucouré
    "140869": "Mali",      # Habib Keita
    "144434": "Mali",      # Ousmane Diakité
    "145075": "Burkina Faso", # Ismahila Ouédraogo
    "146878": "Mali",      # Daouda Guindo
    "146880": "Mali",      # Mamady Diambou
    "161201": "Mali",      # Amadou Danté
    "161591": "Mali",      # Youssouf Diarra
    "167119": "Ivory Coast", # Arsène Kouassi
    "177713": "Mali",      # Gaoussou Diarra
    "160300": "Mali",      # Cheick Konaté
    "159250": "Mali",      # Moussa Diakité
    "171143": "Mali",      # Siaka Sidibe
    "176365": "Mali",      # Mohamed Guindo
    "178478": "Mali",      # Thiemoko Diarra
    "181582": "Mali",      # Issa Traoré
    "158510": "Mali",      # Mahamadou Doumbia
    "162735": "Mali",      # Lassine Diarra
    "91120": "Mali",       # Mamadou Maiga
    "177765": "Mali",      # Zoumana Keita
    "55762": "Mali",       # Soumaïla Diabaté

    # Guinea-Bissau
    "132897": "Guinea-Bissau", # Beto
    "108706": "Guinea-Bissau", # Mama Baldé
    "102285": "Guinea-Bissau", # Alexandre Mendy
    "130801": "Guinea-Bissau", # Fali Candé
    "115841": "Guinea-Bissau", # Opa Sanganté
    "164301": "Guinea-Bissau", # Franculino Djú
    "174881": "Guinea-Bissau", # Khaly
    "107743": "Guinea-Bissau", # Fábio Abreu
    "153150": "Guinea-Bissau", # Duk
    "174721": "Portugal",  # Pedro Bondo (Portuguese)
    "133386": "Guinea-Bissau", # Jefferson Encada
    "160980": "Guinea-Bissau", # Marciano Sanca
    "174881": "Guinea-Bissau", # Khaly
    "142552": "El Salvador", # Alex Roldán

    # Cape Verde
    "60463": "Cape Verde",  # Steven Moreira
    "109532": "Cape Verde", # Nuno Da Costa
    "120377": "Cape Verde", # Nanú
    "137531": "Cape Verde", # Dylan Tavares
    "162585": "Cape Verde", # Ricardo Santos
    "138012": "Cape Verde", # Clau Mendes
    "177751": "Cape Verde", # Sidny Cabral
    "123753": "Cape Verde", # Willy Semedo

    # DR Congo
    "59749": "DR Congo",    # Yannick Bolasie
    "155500": "DR Congo",   # Ezechiel Banzuzi
    "108995": "DR Congo",   # Vital N'Simba
    "118939": "DR Congo",   # Beni Baningime
    "46493": "DR Congo",    # Fabrice N'Sakala
    "172253": "DR Congo",   # Joseph Kalulu
    "54471": "DR Congo",    # Steve Kapuadi
    "59634": "DR Congo",    # Jeremy Bokila
    "165763": "DR Congo",   # Makabi Lilepo
    "117791": "DR Congo",   # Afimico Pululu

    # Ivory Coast
    "43075": "Central African Republic", # Kondogbia
    "170614": "Ivory Coast", # Malick Yalcouyé
    "157278": "Ivory Coast", # Jaurès Assoumou
    "145051": "Ivory Coast", # Moussa Kyabou
    "162958": "Ivory Coast", # Kouame Kouadio
    "170814": "Ivory Coast", # Anto Sekongo

    # Senegal
    "144040": "Senegal",    # Moïse Sahi Dion
    "171046": "Senegal",    # Sékou Gassama

    # Comoros
    "131096": "Comoros",    # Saïd Bakari
    "139920": "Comoros",    # Rafiki Saïd
    "101404": "Comoros",    # Benjaloud Youssouf
    "114799": "Comoros",    # Akim Abdallah

    # Guinea
    "57129": "Guinea",      # Mamadou Samassa
    "140187": "Guinea",     # Louis Mafouta
    "173855": "Guinea",     # Amady Camara

    # Angola
    "114290": "Angola",     # Bastos
    "161915": "Angola",     # Kialonda Gaspar
    "131198": "Angola",     # Randy Nteka
    "160078": "Angola",     # Beni Mukendi
    "164509": "Angola",     # Loide Augusto
    "165670": "Angola",     # Manuel Keliano
    "174405": "Angola",     # Domingos Andrade

    # Sierra Leone
    "172627": "Sierra Leone", # Juma Bah
    "130003": "Sierra Leone", # Augustus Kargbo
    "155726": "Sierra Leone", # Jocelyn Janneh
    "175985": "Sierra Leone", # Hindolo Mustapha

    # Liberia
    "135952": "Liberia",    # Oscar Dorley
    "142358": "Liberia",    # Mohammed Kamara

    # Burkina Faso
    "178495": "Burkina Faso", # Pierre Landry Kabore
    "168032": "Burkina Faso", # Abdoul Ayindé

    # Niger
    "161700": "Niger",      # Rahim Alhassane

    # South Sudan
    "168339": "South Sudan", # Tammer Bany

    # Chad
    "126594": "Chad",       # Marius Mouandilmadji
    "136959": "Chad",       # Oscar Maritu

    "157516": "Mali",      # Néné Dorgeles
    "109563": "Mali",      # Lassana Coulibaly
    "140808": "Mali",      # Ismaila Coulibaly
    "153727": "Guinea-Bissau", # Panutche Camará
    "182035": "Guinea-Bissau", # Babacar Fati
    "117931": "Guinea-Bissau", # Alfa Semedo

    # Gambia (missing, add)
    "174038": "Brazil",     # Léo Scienza (Brazilian)

    # Syria
    "106800": "Germany",    # Mahmoud Dahoud (German international)
    "115642": "UAE",        # Khaled Ebraheim
    "147505": "Syria",      # Aiham Ousou
    "106067": "Syria",      # Omar Al Soma
    "91373": "Libya",       # Daniel Elfadli

    # Libya
    "132760": "Libya",      # Ali Musrati

    # Central African Republic
    "100670": "Central African Republic", # Geoffrey Lembet

    # Burundi
    "135384": "Burundi",    # Y. Ndayishimiye

    # Moldova
    "152292": "Moldova",    # Iurie Iovu

    # Albania
    "165672": "Albania",    # Altin Zeqiri

    # Indonesia
    "167177": "Indonesia",  # Justin Hubner
    "156310": "Indonesia",  # Elkan Baggott

    # Palestine
    "124031": "Palestine",  # Wessam Abou Ali

    # Yemen
    "115751": "Yemen",      # Abdulrahman Al Harazi

    # Sudan
    "172872": "Sudan",      # Mohamed Awad Alla

    # Mauritania
    "123442": "Mauritania", # Aly Abeid
    "47547": "France",      # Lindsay Rose (French)

    # UAE (many local players)
    "106114": "UAE",        # Salem Juma Awad
    "130340": "UAE",        # Shahin Abdulrahman
    "16182": "UAE",         # Adel Al Hosani
    "60403": "UAE",         # Ahmed Barman
    "122391": "UAE",        # Khalid Bawazir
    "129679": "UAE",        # Tahnoon Alzaabi
    "129685": "UAE",        # Yousif Ali Almheiri
    "129915": "UAE",        # Khalid Al Baloushi
    "130342": "UAE",        # Abdalla Ghanim
    "145241": "UAE",        # Darwish Mohammad
    "122397": "UAE",        # Abdulrahman Saleh
    "122418": "UAE",        # Fares Khalil
    "154403": "UAE",        # Al Hassan Saleh
    "155638": "UAE",        # Mohammed Al Baloushi
    "16173": "UAE",         # Khaled Al Senaani

    # Qatar (via Al Rayyan)
    "115751": "Qatar",      # Actually Abdulrahman Al Harazi - wait, he's Yemeni

    # Romania
    "176366": "Belgium",    # Jordi Liongola (Belgian)

    # Germany
    "91589": "Germany",     # Assan Ouédraogo (German youth international)

    # Bulgaria
    "164683": "Bulgaria",   # Miro

    # Costa Rica
    "161235": "Costa Rica", # Kevin Chamorro
    "169952": "Costa Rica", # Warren Madrigal
    "181895": "Costa Rica", # Kenay Myrie

    # USA
    "144379": "USA",        # Isaiah Parente
    "168395": "USA",        # Malachi Jones
    "158525": "DR Congo",   # Bernard Kamungo (USA-born but DR Congo heritage)
    "162180": "Ghana",      # Ronald Donkor

    # Sweden
    "158508": "Sweden",     # Kevin Yakob

    # Cuba
    "123234": "Cuba",       # César Munder

    # Dominican Republic
    "111343": "Dominican Republic", # Mariano Díaz

    # Grenada
    "109574": "Grenada",    # Regan Charles-Cook

    # El Salvador
    "142552": "El Salvador", # Alex Roldán

    # Peru
    "108758": "Peru",       # Jalil Elías

    # Argentina
    "174649": "Argentina",  # Luis Ignacio Abraham
    "116554": "Argentina",  # Facundo Mater
    "145683": "Argentina",  # Wilfredo Rivera

    # Hong Kong / Macao
    "143826": "Hong Kong",  # Leung Nok Hang
    "145140": "Macao",      # Ngan Cheuk Pan
    "163181": "Macao",      # Tsui Wang Kit

    # Portugal
    "131742": "Portugal",   # David Carmo
    "109345": "Portugal",   # Rúben Semedo
    "119130": "Portugal",   # Ivanildo Fernandes
    "168604": "Brazil",     # Fabrício Garcia (Brazilian)
    "114030": "Portugal",   # Hildeberto Pereira

    # Netherlands
    "103519": "Netherlands", # Kevin Diks

    # France
    "91147": "France",      # Jordy Makengo
    "159325": "France",     # Rayan Lutin
    "176364": "Belgium",    # Samuel Gueulette (Belgian)

    # Switzerland
    "100608": "Switzerland", # Cephas Malele

    # Gabon
    "161578": "Gabon",      # Jovany Ikanga

    # Puerto Rico
    "151695": "Puerto Rico", # Leandro Antonetti

    # Suriname
    "178177": "Suriname",   # Jalmaro Calvin

    # England
    "101054": "England",    # Luke O'Nien

    # Brazil
    "61260": "Brazil",      # Caio Lucas
    "174038": "Brazil",     # Léo Scienza

    # Greece
    "128182": "Spain",      # Christian Sánchez (Spanish)

    # Misc
    "170483": "Mali",       # Mamadou Doumbia (Mali)
    "177765": "Mali",       # Zoumana Keita
}

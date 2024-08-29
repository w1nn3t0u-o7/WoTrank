from bs4 import BeautifulSoup
import requests
import json
import pandas as pd
import re
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("mode.copy_on_write", True)

urls = [
    'http://wotreplays.eu/site/6799640#ensk-iain11-grille_15',
    'http://wotreplays.eu/site/6799641#ensk-iain11-grille_15',
    'http://wotreplays.eu/site/6799644#cliff-iain11-grille_15',
    'http://wotreplays.eu/site/6799645#cliff-iain11-grille_15',
    'http://wotreplays.eu/site/6799646#studzianki-iain11-grille_15',
]

def fetch_data(url):
    result = requests.get(url)
    doc = BeautifulSoup(result.text, "html.parser")
# Czas trwania bitwy
    battle_duration = doc.find(string = re.compile('Battle duration')).next_sibling.string
# Mapa
    map_name = doc.img['alt']
# Satystyki z bitwy
    scripts = doc.find_all('script')
    roster_data = None
    for script in scripts:
        if 'var roster =' in script.text:
            script_content = script.string
            start = script_content.find('var roster =') + len('var roster =')
            end = script_content.find(';', start)
            roster_json = script_content[start:end].strip()
            roster_data = json.loads(roster_json)
            break

    df = pd.DataFrame(roster_data)
# Przekształcenie tabeli, aby kolumny red i green stały się wartościami w nowej kolumnie 'team'
    df_melted = df.melt(id_vars=[col for col in df.columns if col not in ['red', 'green']], 
                    value_vars=['red', 'green'], 
                    var_name='team', 
                    value_name='player_info')

# Rozbicie słownika 'player_info' na osobne kolumny
    player_df = df_melted['player_info'].apply(pd.Series)

# Połączenie wszystkiego razem
    df_final = pd.concat([df_melted.drop(columns=['player_info']), player_df], axis=1)
# Usunięcie pustych wierszy
    df_null = df_final.dropna(subset = ['id'])
# Odfiltrowanie obserwujących mecz
    df_filter = df_null[df_null['tank'] != 'Spectator']
# Normalizacja kolumny odpowiadającej za team kille i team damage
    df_filter[['vehicleTeamKills', 'vehicleTeamDamage']] = df_filter['vehicleTKString'].str.split('/', expand = True)
# Odfiltrowanie niepotrzebnych kolumn
    df_columns = df_filter.drop(columns=['platoon', 'achievements', 'achievementsToolTip', 'ranked', 'vehicleTKString', 'clan'])
# Dodanie kolumny z mapą
    df_columns.insert(1, 'map', map_name, False)
# Dodanie kolumny z czasem trwania bitwy
    df_columns['battleDuration'] = battle_duration
    return df_columns

#Połączenie danych z wielu linków
merge_data = [fetch_data(url) for url in urls]
all_data = pd.concat(merge_data)

# Usuwanie przypadkowych duplikatów
all_data_clean = all_data.drop_duplicates()
# Ustawienie nowego indexu
all_data_clean.reset_index(inplace = True, drop = True)

# Konwersja danych na plik Excela
#all_data_clean.to_excel('WoT_Ranking.xlsx', sheet_name = 'Baza')

# Konwersja danych na plik json 


print(all_data_clean)

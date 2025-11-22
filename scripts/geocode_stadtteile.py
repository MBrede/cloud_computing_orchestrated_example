import pandas as pd
from pathlib import Path
import requests
from time import sleep
from tqdm import tqdm

def get_coords(stadtteil):
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    area["name"="Kiel"]["admin_level"="6"]->.kiel;
    (
      node["name"="{stadtteil}"](area.kiel);
      way["name"="{stadtteil}"](area.kiel);
      relation["name"="{stadtteil}"](area.kiel);
    );
    out center 1;
    """
    try:
        response = requests.post(url, data={'data': query}, timeout=30)
        data = response.json()
        if data['elements']:
            elem = data['elements'][0]
            if 'lat' in elem and 'lon' in elem:
                return elem['lat'], elem['lon']
            elif 'center' in elem:
                return elem['center']['lat'], elem['center']['lon']
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"Error for {stadtteil}: {e}")
    return None, None

if __name__ == '__main__':
    folder = Path('./data')
    csv_files = list(folder.glob('*.csv'))

    stadtteile = set()
    for csv_file in csv_files:
        df = pd.read_csv(csv_file, sep=';')
        for col in df.columns:
            if col.lower().strip() == 'stadtteil':
                stadtteile.update([str(st).strip() for st in df[col].dropna().unique() if not str(st)[0].isdigit()])
                break

    print(f"Found {len(stadtteile)} unique Stadtteile: {stadtteile}")

    coords_map = {}
    for stadtteil in tqdm(list(stadtteile)):
        lat, lon = get_coords(stadtteil)
        coords_map[stadtteil] = (lat, lon)
        print(f"{stadtteil}: {lat}, {lon}")
        sleep(0.1)

    for csv_file in csv_files:
        df = pd.read_csv(csv_file, sep=';')
        stadtteil_col = None
        for col in df.columns:
            if 'stadtteil' in col.lower():
                stadtteil_col = col
                break

        if not stadtteil_col:
            continue

        df['lat'] = df[stadtteil_col].map(lambda x: coords_map.get(str(x).strip(), (None, None))[0] if pd.notna(x) else None)
        df['lon'] = df[stadtteil_col].map(lambda x: coords_map.get(str(x).strip(), (None, None))[1] if pd.notna(x) else None)

        df.to_csv(csv_file, sep=';', index=False)

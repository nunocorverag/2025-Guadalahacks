import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
from fac_type_lookup import fac_type_lookup

# Cargar archivos
streetNav = gpd.read_file("data/STREETS_NAV/SREETS_NAV_4815075.geojson")
streetNaming = gpd.read_file("data/STREETS_NAMING_ADDRESSING/SREETS_NAMING_ADDRESSING_4815075.geojson")
POI = pd.read_csv("data/POIs/POI_4815075.csv")

# Filtrar calles con MULTIDIGIT y sin glorieta
multiDigiStreetNav = streetNav[(streetNav['MULTIDIGIT'] == 'Y') & (streetNav['ROUNDABOUT'] == 'N')]

# Filtrar naming para links válidos
filteredNaming = streetNaming[streetNaming['link_id'].isin(multiDigiStreetNav['link_id'])]
filteredNaming = filteredNaming[filteredNaming.geometry.notnull()]

# Crear diccionario link_id → nombre de calle
linkName = {row['link_id']: row['ST_NAME'] for _, row in filteredNaming.iterrows()}

# Filtrar POIs que caen en links válidos
POIStreetConcordance = POI[POI['LINK_ID'].isin(linkName)].copy()

# Agregar descripciones
POIStreetConcordance['FAC_DESC_EN'] = POIStreetConcordance['FAC_TYPE'].map(
    lambda x: fac_type_lookup.get(x, ("Unknown", "Desconocido"))[0]
)
POIStreetConcordance['FAC_DESC_ES'] = POIStreetConcordance['FAC_TYPE'].map(
    lambda x: fac_type_lookup.get(x, ("Unknown", "Desconocido"))[1]
)

# Diccionario: link_id → geometría de calle
link_geoms = {row['link_id']: row.geometry for _, row in multiDigiStreetNav.iterrows()}

# Calcular coordenadas: inicial y por PERCFRREF
def get_coords(link_id, perc):
    geom = link_geoms.get(link_id)
    if geom and isinstance(geom, LineString):
        # Coordenada con menor latitud
        min_lat_coord = min(geom.coords, key=lambda c: c[1])
        # Coordenada por porcentaje
        perc = float(perc) if pd.notnull(perc) else 0
        perc = min(max(perc, 0), 1)  # Clamp 0-1
        point_by_perc = geom.interpolate(geom.length * perc)
        return min_lat_coord[1], min_lat_coord[0], point_by_perc.y, point_by_perc.x
    return None, None, None, None

POIStreetConcordance[['LAT_INIT', 'LON_INIT', 'LAT_PERC', 'LON_PERC']] = POIStreetConcordance.apply(
    lambda row: pd.Series(get_coords(row['LINK_ID'], row['PERCFRREF'])), axis=1
)

# Mostrar primeros 5 del tipo 4013
print(
    POIStreetConcordance[POIStreetConcordance['FAC_TYPE'] == 4013][
        ['FAC_TYPE', 'FAC_DESC_EN', 'FAC_DESC_ES', 'POI_NAME', 'LINK_ID', 'PERCFRREF',
         'LAT_INIT', 'LON_INIT', 'LAT_PERC', 'LON_PERC']
    ].head(5)
)

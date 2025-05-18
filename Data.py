import geopandas as gpd
import pandas as pd
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

# Agregar descripciones desde lookup
POIStreetConcordance['FAC_DESC_EN'] = POIStreetConcordance['FAC_TYPE'].astype(str).map(
    lambda x: fac_type_lookup.get(x, {}).get("desc_en", "Unknown")
)
POIStreetConcordance['FAC_DESC_ES'] = POIStreetConcordance['FAC_TYPE'].astype(str).map(
    lambda x: fac_type_lookup.get(x, {}).get("desc_es", "Desconocido")
)

# Agregar tamaño y between si se desea
POIStreetConcordance['FAC_SIZE'] = POIStreetConcordance['FAC_TYPE'].astype(str).map(
    lambda x: fac_type_lookup.get(x, {}).get("size", None)
)
POIStreetConcordance['FAC_BETWEEN'] = POIStreetConcordance['FAC_TYPE'].astype(str).map(
    lambda x: fac_type_lookup.get(x, {}).get("between", "N")
)

# Obtener coordenada de menor latitud (más al sur) del LINK_ID desde streets_nav
def get_min_lat_coords(link_id):
    geometries = streetNav[streetNav['link_id'] == link_id].geometry
    if geometries.empty:
        return None, None
    all_coords = []
    for geom in geometries:
        if geom.geom_type == 'LineString':
            all_coords.extend(geom.coords)
        elif geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                all_coords.extend(line.coords)
    if not all_coords:
        return None, None
    # Buscar el punto con menor latitud (coordenada[1])
    min_point = min(all_coords, key=lambda p: p[1])
    return min_point[0], min_point[1]  # (longitud, latitud)

# Agregar coordenadas mínimas
POIStreetConcordance[['min_long', 'min_lat']] = POIStreetConcordance['LINK_ID'].apply(
    lambda lid: pd.Series(get_min_lat_coords(lid))
)

# Mostrar algunos resultados
print(POIStreetConcordance[['POI_NAME', 'FAC_DESC_EN', 'FAC_DESC_ES', 'min_long', 'min_lat']].head())

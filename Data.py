import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# Cargar el archivo GeoJSON
streetNav = gpd.read_file("C:/Users/jsnaj/Desktop/HereHackaton/STREETS_NAV/SREETS_NAV_4815079.geojson")
streetNaming = gpd.read_file("C:/Users/jsnaj/Desktop/HereHackaton/STREETS_NAMING_ADDRESSING/SREETS_NAMING_ADDRESSING_4815079.geojson")
POI = pd.read_csv("C:/Users/jsnaj/Desktop/HereHackaton/POIs/POI_4815079.csv")

# Ver nombres de columnas (atributos)
# print(streetNav.columns)

# # Ver tipos de datos por columna
# print(streetNav.dtypes)

multiDigiStreetNav = streetNav[streetNav['MULTIDIGIT'] == 'Y']
multiDigiStreetNav = multiDigiStreetNav[streetNav['ROUNDABOUT'] == 'N']
# Ver resumen general
# multiDigiStreetNav.plot()
# plt.show()
# print(multiDigiStreetNav.info())

print(multiDigiStreetNav[['link_id']])


# Filtrar streetNaming para que solo conserve los link_id del filtro anterior
filteredNaming = streetNaming[streetNaming['link_id'].isin(multiDigiStreetNav['link_id'])]

# Verificar resultado
# Eliminar filas sin geometría válida
filteredNaming = filteredNaming[filteredNaming.geometry.notnull()]
print(filteredNaming[['ST_NAME']])
# filteredNaming.plot()
# plt.show()

linkName = {row['link_id']: row['ST_NAME'] for _, row in filteredNaming.iterrows()}

POIStreetConcordance = POI[POI['LINK_ID'].isin(linkName)]

print("right:")
print(POIStreetConcordance)

print(POIStreetConcordance['FAC_TYPE'].unique())

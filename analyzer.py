import geopandas as gpd
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import matplotlib.pyplot as plt

def query_nearest(source_gdf, target_gdf):
    source_coords = np.array([[pt.x, pt.y] for pt in source_gdf["centroid"]])
    target_coords = np.array([[pt.x, pt.y] for pt in target_gdf["centroid"]])
    
    if len(target_coords) == 0:
        n = len(source_coords)
        return (
            np.full(n, np.nan),
            np.full(n, -1),
            np.full(n, 'L', dtype='<U1'),
            np.full(n, None)
        )
    
    tree = BallTree(target_coords, metric='euclidean')
    dist, idx = tree.query(source_coords, k=1)
    idx_flat = idx.flatten()
    
    direction = np.where(target_coords[idx_flat, 0] > source_coords[:, 0], 'R', 'L')
    link_ids = target_gdf.iloc[idx_flat]["link_id"].values
    
    return dist.flatten(), idx_flat, direction, link_ids
# Cargar el archivo GeoJSON
streetNav = gpd.read_file("C:/Users/jsnaj/Desktop/HereHackaton/STREETS_NAV/SREETS_NAV_4815075.geojson")
streetNaming = gpd.read_file("C:/Users/jsnaj/Desktop/HereHackaton/STREETS_NAMING_ADDRESSING/SREETS_NAMING_ADDRESSING_4815075.geojson")
POI = pd.read_csv("C:/Users/jsnaj/Desktop/HereHackaton/POIs/POI_4815075.csv")

multiDigiStreetNav = streetNav[streetNav['MULTIDIGIT'] == 'Y']
multiDigiStreetNav = multiDigiStreetNav[streetNav['ROUNDABOUT'] == 'N']

# print(multiDigiStreetNav[['link_id']])

filteredNaming = streetNaming[streetNaming['link_id'].isin(multiDigiStreetNav['link_id'])]
filteredNaming = filteredNaming[filteredNaming.geometry.notnull()]
# print(filteredNaming[['ST_NAME']])

linkName = {row['link_id']: row['ST_NAME'] for _, row in filteredNaming.iterrows()}

POIStreetConcordance = POI[POI['LINK_ID'].isin(linkName)]

# print("right:")
# print(POIStreetConcordance)

if multiDigiStreetNav.crs.to_epsg() != 32614:
    print("Reproyectando a EPSG:32614...")
    multiDigiStreetNav = multiDigiStreetNav.to_crs(epsg=32614)

multiDigiStreetNav["centroid"] = multiDigiStreetNav.geometry.centroid

fwd = multiDigiStreetNav[multiDigiStreetNav["DIR_TRAVEL"] == "F"].copy()
rev = multiDigiStreetNav[multiDigiStreetNav["DIR_TRAVEL"] == "T"].copy()

dist_fwd, _ , direction_fwd, link_fwd= query_nearest(fwd, rev)
dist_rev, _ , direction_rev, link_rev= query_nearest(rev, fwd)

df_fwd = pd.DataFrame({
    "link_id": fwd["link_id"].values,
    "dir_travel": "F",
    "separacion_m": dist_fwd,
    "direction_opposite": direction_fwd,
    "link_id_opposite": link_fwd
})

df_rev = pd.DataFrame({
    "link_id": rev["link_id"].values,
    "dir_travel": "T",
    "separacion_m": dist_rev,
    "direction_opposite": direction_rev,
    "link_id_opposite": link_rev
})

df_all = pd.concat([df_fwd, df_rev], ignore_index=True)

print(df_all["link_id"].duplicated().any())


print(df_fwd)

df_bad = df_all[(df_all["separacion_m"] >= 3) & (df_all["separacion_m"] < 80)]

grouped = df_bad.groupby("separacion_m")["direction_opposite"].apply(list)
print(grouped)

facility_map = {
    9587: ('N', 'N'),
    4581: ('N', 'N'),
    7996: ('N', 'N'),
    9718: ('N', 'N'),
    3578: ('Y', 'N'),
    5512: ('N', 'N'),
    7538: ('N', 'N'),
    8699: ('Y', 'N'),
    5511: ('N', 'N'),
    6000: ('N', 'N'),
    9532: ('N', 'N'),
    9051: ('Y', 'N'),
    9059: ('N', 'N'),
    9050: ('Y', 'Y'),
    9058: ('N', 'N'),
    9057: ('N', 'N'),
    9995: ('N', 'N'),
    9999: ('Y', 'Y'),
    7933: ('N', 'N'),
    4170: ('Y', 'N'),
    5000: ('N', 'N'),
    9517: ('Y', 'Y'),
    9056: ('Y', 'Y'),
    9714: ('N', 'N'),
    7985: ('N', 'N'),
    9591: ('Y', 'N'),
    7832: ('N', 'N'),
    9121: ('N', 'N'),
    7994: ('N', 'N'),
    9537: ('N', 'N'),
    9996: ('N', 'N'),
    4100: ('Y', 'N'),
    9987: ('N', 'N'),
    9535: ('Y', 'N'),
    7990: ('N', 'N'),
    9994: ('N', 'N'),
    9211: ('N', 'N'),
    9722: ('N', 'N'),
    9545: ('N', 'N'),
    9723: ('N', 'N'),
    9993: ('N', 'N'),
    9598: ('Y', 'N'),
    4482: ('N', 'N'),
    9527: ('N', 'N'),
    7992: ('N', 'N'),
    9573: ('N', 'N'),
    9525: ('N', 'N'),
    5400: ('N', 'N'),
    9998: ('N', 'N'),
    8200: ('N', 'N'),
    9592: ('N', 'N'),
    5999: ('Y', 'N'),
    9986: ('N', 'N'),
    9560: ('N', 'N'),
    8060: ('N', 'N'),
    7011: ('N', 'N'),
    7998: ('N', 'N'),
    9991: ('N', 'N'),
    8231: ('N', 'N'),
    9724: ('N', 'N'),
    9594: ('Y', 'N'),
    4493: ('N', 'N'),
    9583: ('N', 'N'),
    9725: ('Y', 'N'),
    9715: ('N', 'N'),
    5571: ('N', 'N'),
    8410: ('N', 'N'),
    9730: ('Y', 'Y'),
    4444: ('Y', 'N'),
    9709: ('N', 'N'),
    5813: ('Y', 'Y'),
    9988: ('N', 'N'),
    7013: ('N', 'N'),
    9053: ('Y', 'N'),
    7522: ('N', 'N'),
    7947: ('Y', 'N'),
    7521: ('Y', 'N'),
    7520: ('N', 'N'),
    7929: ('Y', 'N'),
    5540: ('Y', 'N'),
    9565: ('Y', 'N'),
    9992: ('N', 'N'),
    9221: ('N', 'N'),
    9530: ('N', 'N'),
    9589: ('Y', 'N'),
    4580: ('N', 'N'),
    9054: ('Y', 'N'),
    7510: ('N', 'N'),
    9595: ('N', 'N'),
    9590: ('N', 'N'),
    7897: ('Y', 'N'),
    5800: ('N', 'N'),
    9055: ('Y', 'N'),
    8211: ('N', 'N'),
    6512: ('N', 'N'),
    7014: ('Y', 'Y'),
    7012: ('N', 'N'),
    9567: ('N', 'N'),
    9568: ('N', 'N'),
    7997: ('N', 'N'),
    7940: ('N', 'N'),
    9989: ('Y', 'N'),
    9597: ('N', 'N'),
    9717: ('Y', 'Y'),
    7999: ('Y', 'N'),
    7389: ('Y', 'N'),
    9052: ('N', 'N'),
    4013: ('Y', 'Y'),
    9596: ('N', 'N'),
    9593: ('Y', 'N'),
    9719: ('N', 'N'),
    9720: ('N', 'N'),
    9522: ('N', 'N'),
    9710: ('N', 'N'),
    2084: ('N', 'N'),
}


POIIdentifiers = []

for _,x in POIStreetConcordance.iterrows():
    ObjectType = int(x["FAC_TYPE"])
    if facility_map[ObjectType] == ('Y','Y'):
        continue
    RoadDividerSize = df_all[df_all["link_id"] == x["LINK_ID"]]["separacion_m"].values[0]
    if(facility_map[ObjectType][0] == 'Y'):
        continue
    if(RoadDividerSize <= 10):
        POIIdentifiers.append(x["POI_ID"])

print(POIIdentifiers)

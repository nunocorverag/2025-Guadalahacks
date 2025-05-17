import os
import glob
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from sklearn.neighbors import BallTree
import numpy as np

# Configura tus rutas
NAV_DIR = r"C:\Users\52331\Desktop\ArchivosGuadalahack\STREETS_NAV"
NAME_ADDR_DIR = r"C:\Users\52331\Desktop\ArchivosGuadalahack\STREETS_NAMING_ADDRESSING"
OUTPUT_CSV = r"C:\Users\52331\Desktop\ArchivosGuadalahack\tramos_fuera_rango_con_nombre.csv"

def cargar_geojson_de_carpeta(carpeta):
    archivos = glob.glob(os.path.join(carpeta, "*.geojson"))
    if not archivos:
        print(f"⚠️ No se encontraron archivos en {carpeta}")
        return None
    gdfs = []
    for archivo in archivos:
        print(f"📥 Leyendo: {os.path.basename(archivo)}")
        gdf = gpd.read_file(archivo)
        gdfs.append(gdf)
    return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs) if gdfs else None

# Cargar datasets
gdf_nav = cargar_geojson_de_carpeta(NAV_DIR)
gdf_name = cargar_geojson_de_carpeta(NAME_ADDR_DIR)

# Validación
if gdf_nav is None or gdf_nav.empty:
    raise ValueError("❌ No se cargaron archivos válidos desde STREETS_NAV.")
if gdf_name is None or gdf_name.empty:
    raise ValueError("❌ No se cargaron archivos válidos desde STREETS_NAMING_ADDRESSING.")

# Filtrar MULTIDIGIT con condiciones
gdf_md = gdf_nav[
    (gdf_nav["MULTIDIGIT"] == "Y") &
    (gdf_nav["RAMP"] != "Y") &
    (gdf_nav["DIR_TRAVEL"] != "B") &
    (gdf_nav["MANOEUVRE"] != "Y")
].copy()

print(f"\n🔎 Tramos MULTIDIGIT = 'Y' filtrados: {len(gdf_md)}")

# Reproyectar a UTM zona 14N si es necesario
if gdf_md.crs.to_epsg() != 32614:
    print("🌐 Reproyectando a EPSG:32614...")
    gdf_md = gdf_md.to_crs(epsg=32614)

# Calcular centroides
gdf_md["centroid"] = gdf_md.geometry.centroid

# Separar por dirección
fwd = gdf_md[gdf_md["DIR_TRAVEL"] == "F"].copy()
rev = gdf_md[gdf_md["DIR_TRAVEL"] == "T"].copy()

def query_nearest(source_gdf, target_gdf):
    source_coords = np.array([[pt.x, pt.y] for pt in source_gdf["centroid"]])
    target_coords = np.array([[pt.x, pt.y] for pt in target_gdf["centroid"]])
    if len(target_coords) == 0:
        return np.full(len(source_coords), np.nan), np.full(len(source_coords), -1)
    tree = BallTree(target_coords, metric='euclidean')
    dist, idx = tree.query(source_coords, k=1)
    return dist.flatten(), idx.flatten()

# Calcular distancia mínima a carril opuesto
dist_fwd, _ = query_nearest(fwd, rev)
dist_rev, _ = query_nearest(rev, fwd)

# Combinar en DataFrames
df_fwd = pd.DataFrame({
    "link_id": fwd["link_id"].values,
    "dir_travel": "F",
    "separacion_m": dist_fwd
})
df_rev = pd.DataFrame({
    "link_id": rev["link_id"].values,
    "dir_travel": "T",
    "separacion_m": dist_rev
})

df_all = pd.concat([df_fwd, df_rev], ignore_index=True)

# Agregar nombre de calle
if "link_id" in gdf_name.columns and "ST_NAME" in gdf_name.columns:
    df_all = df_all.merge(gdf_name[["link_id", "ST_NAME"]], on="link_id", how="left")
else:
    print("⚠️ El dataset de Naming Addressing no contiene columnas esperadas.")

# Filtrar fuera de rango
df_bad = df_all[
    (df_all["separacion_m"] <= 3) | (df_all["separacion_m"] > 80)
].drop_duplicates(subset=["link_id", "dir_travel"])

# Ordenar resultados
df_bad.sort_values(by="separacion_m", ascending=True, inplace=True)
df_bad.reset_index(drop=True, inplace=True)

# Mostrar resultados
print(f"\n⚠️ Segmentos con MULTIDIGIT mal atribuido: {len(df_bad)}")
print(df_bad[["link_id", "dir_travel", "separacion_m", "ST_NAME"]].head(10))

# Guardar resultados
df_bad.to_csv(OUTPUT_CSV, index=False)
print(f"\n✅ Resultados guardados en: {OUTPUT_CSV}")

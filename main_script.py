import geopandas as gpd
import pandas as pd
import requests
import math
import os
from dotenv import load_dotenv
from pathlib import Path
import time
from shapely.geometry import LineString
from fac_type_lookup import fac_type_lookup

load_dotenv()  # Cargar variables del .env

# Función para determinar el nivel de zoom según el tamaño
def get_zoom_level(size):
    """
    Determina el nivel de zoom según el tamaño del establecimiento
    """
    if size == "big":
        return 16
    elif size == "medium":
        return 17
    elif size == "small":
        return 18
    else:  # any u otros casos
        return 17

# Funciones para conversión de coordenadas
def lat_lon_to_tile(lat, lon, zoom):
    """
    Convierte latitud y longitud a índices de tesela (x, y) para un nivel de zoom determinado.
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    
    n = 2.0 ** zoom
    
    x = int((lon_rad - (-math.pi)) / (2 * math.pi) * n)
    y = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2 * n)
    
    return (x, y)

def tile_coords_to_lat_lon(x, y, zoom):
    """
    Convierte los índices de tesela (x, y) a coordenadas de latitud y longitud.
    """
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1-2 * y/n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def get_satellite_tile(lat, lon, zoom, tile_format, api_key, output_path):
    """
    Obtiene una tesela de imagen satelital y la guarda en un archivo.
    """
    x, y = lat_lon_to_tile(lat, lon, zoom)
    
    # URL para la API de mapas
    url = f'https://maps.hereapi.com/v3/base/mc/{zoom}/{x}/{y}/{tile_format}?style=satellite.day&apiKey={api_key}'
    
    # Hacer la solicitud
    response = requests.get(url)
    
    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        # Guardar la tesela en un archivo
        with open(output_path, 'wb') as file:
            file.write(response.content)
        print(f'Tesela guardada exitosamente en {output_path}')
        # Esperar un breve momento para no sobrecargar la API
        time.sleep(0.5)
        return True
    else:
        print(f'Error al obtener la tesela. Código de estado: {response.status_code}')
        return False

def get_coords_by_percentage(link_id, perc_from_ref, streets_nav):
    """
    Obtiene coordenadas a lo largo de una calle basado en un porcentaje desde el punto de referencia.
    Porcentaje es relativo al nodo de menor latitud.
    """
    # Obtener la geometría del link
    link_geom = streets_nav[streets_nav['link_id'] == link_id].geometry
    
    if link_geom.empty:
        return None, None
    
    # Extraer todas las coordenadas
    all_coords = []
    for geom in link_geom:
        if geom.geom_type == 'LineString':
            all_coords.extend(list(geom.coords))
        elif geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                all_coords.extend(list(line.coords))
    
    if not all_coords:
        return None, None
    
    # Convertir a LineString para poder calcular la distancia a lo largo de la línea
    line = LineString(all_coords)
    
    # Encontrar el punto con menor latitud (más al sur)
    min_lat_point = min(all_coords, key=lambda p: p[1])
    min_lat_idx = all_coords.index(min_lat_point)
    
    # Calcular la longitud total de la línea
    total_length = line.length
    
    # Convertir el porcentaje a una distancia
    target_distance = total_length * (perc_from_ref / 100.0)
    
    # Crear una nueva LineString a partir del punto mínimo
    if min_lat_idx == 0:
        # Si el punto mínimo es el primero, usamos la línea original
        segment = line
    else:
        # Si no, creamos una nueva línea desde el punto mínimo hasta el final
        segment = LineString(all_coords[min_lat_idx:] + all_coords[:min_lat_idx])
    
    # Obtener el punto a la distancia deseada
    if target_distance > segment.length:
        # Si la distancia es mayor que la longitud del segmento, usar el último punto
        target_point = segment.coords[-1]
    else:
        target_point = segment.interpolate(target_distance).coords[0]
    
    return target_point[1], target_point[0]  # Retornar como (lat, lon)

def get_link_coordinates(link_id, streets_nav):
    """
    Obtiene todas las coordenadas del link y retorna el inicio, fin y puntos intermedios importantes
    """
    # Obtener la geometría del link
    link_geom = streets_nav[streets_nav['link_id'] == link_id].geometry
    
    if link_geom.empty:
        return None
    
    # Extraer todas las coordenadas
    all_coords = []
    for geom in link_geom:
        if geom.geom_type == 'LineString':
            all_coords.extend(list(geom.coords))
        elif geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                all_coords.extend(list(line.coords))
    
    if not all_coords:
        return None
    
    # Encontrar punto con menor latitud (más al sur)
    min_lat_point = min(all_coords, key=lambda p: p[1])
    min_lat_idx = all_coords.index(min_lat_point)
    
    # Reordenar coordenadas para que comiencen desde el punto de referencia (menor latitud)
    ordered_coords = all_coords[min_lat_idx:] + all_coords[:min_lat_idx]
    
    # Convertir a formato (lat, lon) para mostrar
    formatted_coords = [(p[1], p[0]) for p in ordered_coords]
    
    # Obtener puntos clave (inicio, 25%, 50%, 75%, fin)
    result = {
        "inicio": formatted_coords[0],
        "fin": formatted_coords[-1],
        "todos": formatted_coords
    }
    
    # Calcular puntos intermedios
    line = LineString(ordered_coords)
    total_length = line.length
    
    percentages = [25, 50, 75]
    for perc in percentages:
        target_distance = total_length * (perc / 100.0)
        if target_distance <= line.length:
            point = line.interpolate(target_distance).coords[0]
            result[f"{perc}%"] = (point[1], point[0])
    
    return result

def process_poi(poi_row, streets_nav, api_key, output_folder, selected_perc=None):
    """
    Procesa un POI para generar una imagen satelital.
    """
    poi_id = poi_row['POI_ID']
    poi_name = poi_row['POI_NAME']
    fac_type = str(poi_row['FAC_TYPE'])
    link_id = poi_row['LINK_ID']
    
    # Usar el porcentaje seleccionado o el valor por defecto
    default_perc = poi_row['PERCFRREF'] if 'PERCFRREF' in poi_row and not pd.isna(poi_row['PERCFRREF']) else 50
    perc_from_ref = selected_perc if selected_perc is not None else default_perc
    
    # Obtener el tamaño del establecimiento
    size = fac_type_lookup.get(fac_type, {}).get("size", "any")
    
    # Determinar el nivel de zoom basado en el tamaño
    zoom_level = get_zoom_level(size)
    
    # Obtener coordenadas basadas en el porcentaje desde la referencia
    lat, lon = get_coords_by_percentage(link_id, perc_from_ref, streets_nav)
    
    if lat is None or lon is None:
        print(f"No se pudieron determinar coordenadas para el POI {poi_id}")
        return None
    
    # Crear carpeta para este POI
    poi_folder = os.path.join(output_folder, f"POI_{poi_id}_{poi_name}")
    os.makedirs(poi_folder, exist_ok=True)
    
    # Generar solo una imagen (no 5 como antes)
    output_path = os.path.join(poi_folder, f"satellite.png")
    success = get_satellite_tile(
        lat, 
        lon, 
        zoom_level, 
        "png", 
        api_key, 
        output_path
    )
    
    if success:
        print(f"Imagen generada para POI {poi_id}")
    
    # Guardar información del POI
    info_path = os.path.join(poi_folder, "poi_info.txt")
    with open(info_path, 'w') as f:
        f.write(f"POI ID: {poi_id}\n")
        f.write(f"Nombre: {poi_name}\n")
        f.write(f"Tipo: {fac_type_lookup.get(fac_type, {}).get('desc_es', 'Desconocido')}\n")
        f.write(f"Tamaño: {size}\n")
        f.write(f"Nivel de zoom: {zoom_level}\n")
        f.write(f"Coordenadas: {lat}, {lon}\n")
        f.write(f"Link ID: {link_id}\n")
        f.write(f"Porcentaje desde referencia: {perc_from_ref}\n")
    
    return {
        "poi_id": poi_id,
        "name": poi_name,
        "type": fac_type_lookup.get(fac_type, {}).get('desc_es', 'Desconocido'),
        "lat": lat,
        "lon": lon,
        "zoom": zoom_level
    }

def show_poi_selection_menu(filtered_pois, page_size=10):
    """
    Muestra un menú paginado para seleccionar un POI
    """
    total_pois = len(filtered_pois)
    total_pages = (total_pois + page_size - 1) // page_size
    current_page = 0
    
    while True:
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, total_pois)
        
        print(f"\nMostrando POIs {start_idx+1}-{end_idx} de {total_pois} (Página {current_page+1}/{total_pages}):")
        
        # Mostrar POIs de la página actual
        for i, (idx, poi) in enumerate(filtered_pois.iloc[start_idx:end_idx].iterrows(), start=1):
            global_idx = start_idx + i
            print(f"{global_idx}. {poi['POI_ID']} - {poi['POI_NAME']} ({poi['FAC_DESC_ES']})")
        
        # Opciones de navegación
        print("\nOpciones:")
        if current_page > 0:
            print("a - Página anterior")
        if current_page < total_pages - 1:
            print("s - Página siguiente")
        print("0 - Volver al menú principal")
        print("Número - Seleccionar POI")
        
        choice = input("\nElija una opción: ").strip().lower()
        
        if choice == 'a' and current_page > 0:
            current_page -= 1
        elif choice == 's' and current_page < total_pages - 1:
            current_page += 1
        elif choice == '0':
            return None
        else:
            try:
                poi_idx = int(choice)
                if 1 <= poi_idx <= total_pois:
                    return filtered_pois.iloc[poi_idx - 1]
                else:
                    print("Número inválido. Inténtalo de nuevo.")
            except ValueError:
                print("Opción no reconocida. Inténtalo de nuevo.")

def main():
    # Configuración
    API_KEY = os.getenv("API_KEY")
    if not API_KEY:
        API_KEY = input("Por favor, introduce tu API key de HERE Maps: ")
    
    output_folder = "satellite_images"
    os.makedirs(output_folder, exist_ok=True)
    
    # Cargar archivos
    print("Cargando archivos...")
    try:
        streetNav = gpd.read_file("data/STREETS_NAV/SREETS_NAV_4815075.geojson")
        streetNaming = gpd.read_file("data/STREETS_NAMING_ADDRESSING/SREETS_NAMING_ADDRESSING_4815075.geojson")
        POI = pd.read_csv("data/POIs/POI_4815075.csv")
    except Exception as e:
        print(f"Error al cargar los archivos: {e}")
        return
    
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
        lambda x: fac_type_lookup.get(x, {}).get("size", "any")
    )
    POIStreetConcordance['FAC_BETWEEN'] = POIStreetConcordance['FAC_TYPE'].astype(str).map(
        lambda x: fac_type_lookup.get(x, {}).get("between", "N")
    )
    
    while True:  # Bucle principal para volver al menú de tipos de POI
        # Obtener los tipos únicos de POI
        unique_fac_types = POIStreetConcordance['FAC_TYPE'].astype(str).unique()
        
        # Mostrar los tipos disponibles con sus descripciones
        print("\nTipos de POI disponibles:")
        for i, fac_type in enumerate(unique_fac_types):
            desc_es = fac_type_lookup.get(fac_type, {}).get("desc_es", "Desconocido")
            size = fac_type_lookup.get(fac_type, {}).get("size", "any")
            print(f"{i+1}. [{fac_type}] {desc_es} (Tamaño: {size})")
        
        print("0. Salir del programa")
        
        # Pedir al usuario que seleccione un tipo de POI
        try:
            selected_idx = int(input("\nSelecciona un tipo de POI (número) o 0 para salir: ")) - 1
            if selected_idx == -1:  # Si seleccionó 0
                print("Saliendo del programa...")
                break
                
            if selected_idx < -1 or selected_idx >= len(unique_fac_types):
                print("Número inválido. Inténtalo de nuevo.")
                continue
        except ValueError:
            print("Por favor, introduce un número válido.")
            continue
        
        selected_fac_type = unique_fac_types[selected_idx]
        desc_es = fac_type_lookup.get(selected_fac_type, {}).get("desc_es", "Desconocido")
        print(f"\nHas seleccionado: [{selected_fac_type}] {desc_es}")
        
        # Filtrar POIs del tipo seleccionado
        filtered_pois = POIStreetConcordance[POIStreetConcordance['FAC_TYPE'].astype(str) == selected_fac_type]
        
        # Verificar si hay POIs disponibles
        if len(filtered_pois) == 0:
            print(f"No hay POIs disponibles del tipo {selected_fac_type}.")
            continue
        
        print(f"\nHay {len(filtered_pois)} POIs disponibles del tipo seleccionado.")
        
        # Bucle para procesar múltiples POIs del mismo tipo
        while True:
            # Mostrar POIs disponibles y seleccionar uno
            selected_poi = show_poi_selection_menu(filtered_pois)
            
            if selected_poi is None:
                print("Volviendo al menú principal...")
                break
            
            print(f"\nHas seleccionado: {selected_poi['POI_NAME']} (ID: {selected_poi['POI_ID']})")
            
            # Obtener información del link y coordenadas
            link_id = selected_poi['LINK_ID']
            link_coords = get_link_coordinates(link_id, streetNav)
            
            if link_coords:
                print("\nCoordenadas disponibles para este POI:")
                print(f"Inicio del segmento: {link_coords['inicio'][0]:.6f}, {link_coords['inicio'][1]:.6f}")
                if "25%" in link_coords:
                    print(f"25% del segmento: {link_coords['25%'][0]:.6f}, {link_coords['25%'][1]:.6f}")
                if "50%" in link_coords:
                    print(f"50% del segmento: {link_coords['50%'][0]:.6f}, {link_coords['50%'][1]:.6f}")
                if "75%" in link_coords:
                    print(f"75% del segmento: {link_coords['75%'][0]:.6f}, {link_coords['75%'][1]:.6f}")
                print(f"Fin del segmento: {link_coords['fin'][0]:.6f}, {link_coords['fin'][1]:.6f}")
            
            # Mostrar porcentaje por defecto
            default_perc = selected_poi['PERCFRREF'] if 'PERCFRREF' in selected_poi and not pd.isna(selected_poi['PERCFRREF']) else 50
            print(f"\nPorcentaje desde referencia recomendado (por defecto): {default_perc}%")
            
            # Solicitar un rango de porcentaje
            print("\nOpciones para seleccionar el porcentaje:")
            print("1. Usar valor por defecto")
            print("2. Ingresar un valor específico")
            print("3. Ver un rango de valores")
            
            perc_option = input("\nSelecciona una opción (1-3): ")
            
            selected_perc = None
            
            if perc_option == "1":
                selected_perc = default_perc
                print(f"Usando el valor por defecto: {default_perc}%")
            elif perc_option == "2":
                try:
                    selected_perc = float(input("Ingresa un porcentaje (0-100): "))
                    if 0 <= selected_perc <= 100:
                        print(f"Has seleccionado: {selected_perc}%")
                    else:
                        print("Valor fuera de rango. Usando el valor por defecto.")
                        selected_perc = default_perc
                except ValueError:
                    print("Valor no válido. Usando el valor por defecto.")
                    selected_perc = default_perc
            elif perc_option == "3":
                # Mostrar un rango de valores
                print("\nRango de valores (0-100%):")
                step = 10  # Incrementos de 10%
                for perc in range(0, 101, step):
                    lat, lon = get_coords_by_percentage(link_id, perc, streetNav)
                    if lat is not None and lon is not None:
                        print(f"{perc}% -> Coordenadas: {lat:.6f}, {lon:.6f}")
                
                try:
                    selected_perc = float(input("\nIngresa un porcentaje (0-100): "))
                    if 0 <= selected_perc <= 100:
                        print(f"Has seleccionado: {selected_perc}%")
                    else:
                        print("Valor fuera de rango. Usando el valor por defecto.")
                        selected_perc = default_perc
                except ValueError:
                    print("Valor no válido. Usando el valor por defecto.")
                    selected_perc = default_perc
            else:
                print(f"Opción no válida. Usando el valor por defecto: {default_perc}%")
                selected_perc = default_perc
            
            # Procesar el POI seleccionado
            print(f"\nProcesando POI {selected_poi['POI_ID']} - {selected_poi['POI_NAME']}...")
            result = process_poi(selected_poi, streetNav, API_KEY, output_folder, selected_perc)
            
            if result:
                print(f"\nPOI procesado correctamente:")
                print(f"ID: {result['poi_id']}")
                print(f"Nombre: {result['name']}")
                print(f"Tipo: {result['type']}")
                print(f"Coordenadas: {result['lat']}, {result['lon']}")
                print(f"Nivel de zoom: {result['zoom']}")
                print(f"\nImagen guardada en: {output_folder}/POI_{result['poi_id']}_{result['name']}/satellite.png")
            else:
                print("Error al procesar el POI seleccionado.")
            
            # Preguntar si desea procesar otro POI
            choice = input("\n¿Deseas procesar otro POI del mismo tipo? (s/n): ").lower()
            if choice != 's':
                break

if __name__ == "__main__":
    main()
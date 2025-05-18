import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import glob
import random
from ultralytics import YOLO
from fac_type_lookup import fac_type_lookup

# Create the reverse lookup
fac_name_to_id = {v["desc_en"]: k for k, v in fac_type_lookup.items()}

def find_model_path(base_dir="model"):
    """
    Busca el archivo best.pt dentro de una carpeta local.
    """
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file == "best.pt":  # <- solo compara el nombre del archivo
                full_path = os.path.join(root, file)
                print(f"Modelo encontrado en: {full_path}")
                return full_path
    print("No se encontró el modelo en el directorio local.")
    return None

def find_test_images(test_dir="test"):
    """Encuentra imágenes en el directorio de prueba"""
    if not os.path.exists(test_dir):
        print(f"El directorio de prueba {test_dir} no existe.")
    
    # Buscar imágenes en el directorio
    image_files = []
    if os.path.exists(test_dir):
        image_files = glob.glob(os.path.join(test_dir, "*.jpg")) + \
                     glob.glob(os.path.join(test_dir, "*.jpeg")) + \
                     glob.glob(os.path.join(test_dir, "*.png"))
    
    if not image_files:
        print("No se encontraron imágenes para clasificar.")
        return []
    
    print(f"Se encontraron {len(image_files)} imágenes para clasificar.")
    return image_files

def detect_and_classify_poi(image_path, model, confidence_threshold=0.01):  # Lowered threshold for better detection
    """
    Detecta y clasifica un punto de interés en una imagen usando un modelo YOLOv8 entrenado.
    
    Args:
        image_path: Ruta a la imagen a clasificar
        model: Modelo YOLOv8 cargado
        confidence_threshold: Umbral mínimo de confianza para aceptar detecciones
        
    Returns:
        Tupla con (fac_type_id, fac_type_name, imagen_con_detecciones)
    """
    try:
        # Verificar que la imagen existe
        if not os.path.exists(image_path):
            print(f"Imagen no encontrada en: {image_path}")
            return None, None, None
        
        # Ejecutar la detección
        results = model.predict(image_path, conf=confidence_threshold, verbose=False)
        
        # Cargar la imagen original para visualización
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Si no hay detecciones, retornar None
        if len(results[0].boxes) == 0:
            print(f"No se detectaron objetos en {os.path.basename(image_path)}.")
            return None, None, img
        
        # Obtener el resultado
        result = results[0]  
        
        # Extraer las cajas y confianzas
        boxes = result.boxes
        confidences = boxes.conf.cpu().numpy()
        
        # Verificar si hay detecciones con suficiente confianza
        if len(confidences) == 0 or max(confidences) < confidence_threshold:
            print(f"No se encontraron detecciones con confianza mayor a {confidence_threshold}")
            return None, None, img
        
        # Obtener la detección con mejor confianza
        best_idx = np.argmax(confidences)
        cls_id = int(boxes.cls[best_idx].item())
        class_name = result.names[cls_id]
        confidence = confidences[best_idx]
        
        # Dibujar el rectángulo y la etiqueta
        box = boxes[best_idx].xyxy.cpu().numpy()[0]
        x1, y1, x2, y2 = map(int, box)
        
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, f"{class_name} {confidence:.2f}", (x1, y1-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # Mapear el nombre de la clase a un ID de tipo de instalación
        fac_type_id = None
        for id_key, name in fac_type_lookup.items():
            if name.lower() == class_name.lower() or name.replace('_', ' ').lower() == class_name.lower():
                fac_type_id = id_key
                break
        
        # Intentar una coincidencia parcial si la exacta falla
        if fac_type_id is None:
            for id_key, name in fac_type_lookup.items():
                if class_name.lower() in name.lower() or name.lower().replace('_', ' ') in class_name.lower():
                    fac_type_id = id_key
                    break
        
        print(f"Detección en {os.path.basename(image_path)}: {class_name} (Confianza: {confidence:.2f})")
        if fac_type_id:
            print(f"   ID FAC_TYPE: {fac_type_id}, Nombre: {fac_type_lookup.get(fac_type_id)}")
        else:
            print(f"   No se pudo mapear la clase {class_name} a un ID FAC_TYPE")
        
        return fac_type_id, class_name, img
    
    except Exception as e:
        print(f"Error en la detección: {e}")
        return None, None, None

def visualize_multiple_detections(results_list, cols=2):
    """Visualiza múltiples imágenes con sus detecciones en una cuadrícula"""
    n = len(results_list)
    if n == 0:
        print("No hay resultados para visualizar.")
        return
    
    rows = (n + cols - 1) // cols  # Calcular número de filas necesarias
    
    plt.figure(figsize=(15, 5*rows))
    
    for i, (fac_type_id, class_name, img) in enumerate(results_list):
        plt.subplot(rows, cols, i+1)
        plt.imshow(img)
        
        if fac_type_id and class_name:
            title = f"{class_name}\nID: {fac_type_id}"
            if fac_type_id in fac_type_lookup:
                title += f"\n{fac_type_lookup[fac_type_id]}"
        else:
            title = "Sin detecciones"
            
        plt.title(title)
        plt.axis('off')
    
    plt.tight_layout()
    plt.show()

def main():
    # Encontrar el modelo
    model_path = find_model_path()
    if not model_path:
        return
    
    # Cargar el modelo
    try:
        model = YOLO(model_path)
        print("Modelo cargado correctamente")
    except Exception as e:
        print(f"Error al cargar el modelo: {e}")
    
    # Encontrar imágenes de prueba
    test_images = find_test_images()
    if not test_images:
        return
    
    # Seleccionar un subconjunto de imágenes
    num_images = min(5, len(test_images))  # Limitar a 5 imágenes
    selected_images = random.sample(test_images, num_images) if len(test_images) > num_images else test_images
    
    print(f"\n🔍 Clasificando {len(selected_images)} imágenes...")
    
    # Procesar cada imagen
    results = []
    for image_path in selected_images:
        print(f"\n📸 Procesando: {os.path.basename(image_path)}")
        fac_type_id, class_name, img_with_detections = detect_and_classify_poi(image_path, model)
        if img_with_detections is not None:  # Asegurarnos de que la imagen se procesó correctamente
            results.append((fac_type_id, class_name, img_with_detections))
    
    # Visualizar resultados
    visualize_multiple_detections(results)
    
    print("\nClasificación de imágenes completada.")

if __name__ == "__main__":
    main()
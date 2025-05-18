# POI Validation and Correction Tool using HERE Data

This project was developed for HERE as part of Guadalahacks 2025 using a provided database of streets and Points of Interest (POIs). Its main objective is to validate the positional accuracy of POIs located near multi-digitized roads and correct or remove them if necessary.

---

## 🧠 Project Overview

The program performs the following steps:

1. **POI Validation**
   - Checks if a POI located near multiple roads is correctly placed.
   - Validates based on characteristics like:
     - Distance between roads.
     - Whether the POI logically fits between the roads.

2. **Satellite Verification via HERE API**
   - If a POI fails the initial validation:
     - A satellite image is fetched via the HERE API for that location.
     - The image is analyzed using a trained YOLO model to detect any relevant object presence.

3. **Correction or Removal**
   - If the POI is detected on the opposite side of the road, its position is updated in the database.
   - If the POI is not detected in either place, it is marked for deletion.

---

## 🛠️ Technologies & Libraries

The project is implemented in **Python** and uses the following libraries:

### 🔍 Data Analysis
- `geopandas`
- `pandas`
- `numpy`
- `sklearn.neighbors.BallTree`

### 🖼️ Image Handling & Object Detection
- `os`
- `cv2` (OpenCV)
- `matplotlib.pyplot`
- `PIL.Image`
- `glob`
- `random`
- `ultralytics.YOLO`

### 🌐 API and Utility
- `requests`
- `dotenv.load_dotenv`
- `pathlib.Path`
- `time`
- `math`
- `shapely.geometry.LineString`

---

## 🧪 How to Use

1. **Setup Environment**
   - Make sure all required libraries are installed:
     ```bash
     pip install -r requirements.txt
     ```
   - Configure your `.env` file with your HERE API key and other necessary credentials.

2. **Adjust File Paths**
   - Each script contains comments marking where you need to update the paths to match your local setup and database location.

3. **Run the Pipeline**
   - Start by executing the validation scripts.
   - If needed, proceed to the image analysis and correction steps using the YOLO-based model.
---

## ✅ Output

- A list of POIs that passed validation successfully.
- A log or table of POIs that were:
  - Corrected to the opposite side of the road.
  - Deleted due to not being found in either expected location.
- A modified version of the original POI database reflecting all valid corrections.

---

## 📌 Notes

- Pay attention to road digitization—POIs near multi-digitized roads require extra scrutiny.
- Image detection relies on the performance of the YOLO model; for best results, the model should be well-trained on satellite imagery similar to that used by HERE.
- File paths must be updated manually in the scripts; look for comments in each file that indicate where these changes are needed.

---

## 🤝 Acknowledgements

This project was developed as part of an initiative with **HERE Technologies** for **Guadalahacks 2025**. We thank them for providing access to high-quality mapping data and API services that made this work possible.

Special thanks to everyone involved in this project:

- @BlitzExp
- @Edgarong17
- @nunocorverag
- @DiegoRomCor
---

import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import pandas as pd
import os
import sys

# --- Handle path for .exe (PyInstaller-compatible) ---
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

model_path = os.path.join(BASE_DIR, "model.pth")
csv_path = os.path.join(BASE_DIR, "data.csv")

# --- Load Model ---
model_data = torch.load(model_path, map_location=torch.device("cpu"))
class_names = model_data['class_names']

model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
model.fc = nn.Linear(model.fc.in_features, len(class_names))
model.load_state_dict(model_data['model_state_dict'])
model.eval()

# --- Load Metadata ---
df = pd.read_csv(csv_path)

# --- Image Preprocessing ---
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

# --- Confidence Threshold ---
CONFIDENCE_THRESHOLD = 0.6  # Adjust as needed

def predict_image(image_path):
    img = Image.open(image_path).convert("RGB")
    img_tensor = transform(img).unsqueeze(0)  # Add batch dim

    with torch.no_grad():
        outputs = model(img_tensor)
        probs = torch.nn.functional.softmax(outputs, dim=1)
        confidence, pred = torch.max(probs, 1)
        confidence = confidence.item()
        predicted_class = class_names[pred.item()]

    if confidence < CONFIDENCE_THRESHOLD:
        return "No Match Found", "N/A", "N/A", "N/A", confidence

    # --- Get metadata from CSV ---
    row = df[df['category'] == predicted_class]
    if not row.empty:
        nomenclature = row.iloc[0]['nomenclature']
        cat_no = row.iloc[0]['cat_no']
        part_no = row.iloc[0]['part_no']
    else:
        nomenclature, cat_no, part_no = "N/A", "N/A", "N/A"

    return predicted_class, nomenclature, cat_no, part_no, confidence

def batch_predict(folder_path):
    predictions = []
    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith((".jpg", ".jpeg", ".png")):
            img_path = os.path.join(folder_path, file_name)
            try:
                pred, nomenclature, cat_no, part_no, confidence = predict_image(img_path)
                predictions.append({
                    "image": img_path,
                    "class": pred,
                    "nomenclature": nomenclature,
                    "cat_no": cat_no,
                    "part_no": part_no,
                    "confidence": confidence
                })
            except Exception as e:
                predictions.append({
                    "image": img_path,
                    "class": "Error",
                    "nomenclature": str(e),
                    "cat_no": "-",
                    "part_no": "-",
                    "confidence": 0.0
                })
    return predictions

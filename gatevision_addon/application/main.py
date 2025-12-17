import cv2
import pytesseract
import json
import time
import paho.mqtt.client as mqtt
import os
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [OPTIMISATION J4125 V1.2.2] ---")

with open("/data/options.json", "r") as f:
    options = json.load(f)

CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])
# ... (Tes autres variables MQTT identiques) ...

def start_detection():
    cap = cv2.VideoCapture(CAMERA_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        # --- ÉCONOMIE RADICALE ---
        # On ne scanne qu'une fois toutes les 4 secondes
        time.sleep(4)

        # REDUCTION DE LA ZONE (Crop)
        # Au lieu de tout analyser, on coupe le haut et le bas
        # On ne garde que la bande du milieu (40% à 70% de la hauteur)
        h, w = frame.shape[:2]
        roi = frame[int(h*0.4):int(h*0.8), 0:w] 
        
        # Redimensionnement très léger
        small = cv2.resize(roi, (640, 240))
        
        # Prétraitement
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        _, processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # OCR avec whitelist caractères pour gagner en vitesse
        config = '--psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(processed, config=config)
        
        raw_plate = "".join(e for e in text if e.isalnum()).upper()

        if len(raw_plate) >= 4:
            for auth_plate in WHITELIST:
                clean_auth = auth_plate.replace(" ", "").upper()
                if clean_auth in raw_plate:
                    log(f"🎯 MATCH : {clean_auth}")
                    # trigger_action(clean_auth)
                    time.sleep(20) # Repos total après détection
                    break

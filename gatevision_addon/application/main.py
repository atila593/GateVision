import cv2
import easyocr
import json
import time
import paho.mqtt.client as mqtt
import os
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [MODE SURVIE GATEVISION V1.1.3] ---")

# Chargement IA
try:
    log("📦 Préparation de l'IA...")
    reader = easyocr.Reader(['fr', 'en'], gpu=False)
    log("✅ IA Prête.")
except Exception as e:
    log(f"❌ Erreur IA : {e}")
    sys.exit(1)

# Config HA
OPTIONS_PATH = "/data/options.json"
with open(OPTIONS_PATH, "r") as f:
    options = json.load(f)

CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])

def start_detection():
    # On définit l'option AVANT d'ouvrir le flux
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
    cap = cv2.VideoCapture(CAMERA_URL, cv2.CAP_FFMPEG)
    
    # On réduit le buffer pour ne pas avoir de retard sur le direct
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
    
    log("🚀 Analyse en cours (Mode Ultra-Léger)...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            log("⚠️ Erreur de flux, tentative de reconnexion...")
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL, cv2.CAP_FFMPEG)
            continue

        # --- OPTIMISATION RADICALE ---
        # 1. On ne traite qu'une image toutes les 2 secondes environ
        time.sleep(2) 
        
        # 2. On réduit l'image à une petite taille (400px de large)
        # C'est suffisant pour lire une plaque mais 10x plus rapide
        height, width = frame.shape[:2]
        new_width = 400
        new_height = int((new_width / width) * height)
        small_frame = cv2.resize(frame, (new_width, new_height))

        # 3. Analyse OCR
        results = reader.readtext(small_frame)
        
        for (bbox, text, prob) in results:
            plate = text.replace(" ", "").replace("-", "").upper()
            if len(plate) >= 5:
                log(f"🔍 Détecté : {plate} ({int(prob*100)}%)")
                if plate in WHITELIST and prob > 0.40:
                    log(f"✅ MATCH : {plate}")
                    # Envoi MQTT ici... (même code que précédemment)

if __name__ == "__main__":
    start_detection()

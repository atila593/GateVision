import cv2
import easyocr
import json
import time
import paho.mqtt.client as mqtt
import os
import sys

# DESACTIVATION DES OPTIMISATIONS QUI FONT CRASHER TON CPU
os.environ["OPENCV_FOR_THREADS_NUM"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

def log(message):
    print(f"{message}", flush=True)

log("--- [MODE SURVIE ULTIME V1.1.4] ---")

# Chargement IA
try:
    log("📦 Préparation de l'IA (CPU unique)...")
    reader = easyocr.Reader(['fr', 'en'], gpu=False)
    log("✅ IA Prête.")
except Exception as e:
    log(f"❌ Erreur IA : {e}")
    sys.exit(1)

# Config HA
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except:
    options = {}

CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])

def start_detection():
    log(f"📸 Connexion à : {CAMERA_URL}")
    # On utilise la méthode la plus simple possible pour OpenCV
    cap = cv2.VideoCapture(CAMERA_URL)
    
    if not cap.isOpened():
        log("❌ Impossible d'ouvrir le flux vidéo. Vérifiez l'URL ou l'IP.")
        return

    log("🚀 ANALYSE ACTIVE. Présentez une plaque...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            log("⚠️ Flux perdu, reconnexion...")
            time.sleep(10)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        # PAUSE POUR LE CPU
        time.sleep(2)

        # REDUCTION TAILLE IMAGE
        small_frame = cv2.resize(frame, (640, 360))

        # IA
        try:
            results = reader.readtext(small_frame)
            for (bbox, text, prob) in results:
                plate = text.replace(" ", "").replace("-", "").upper()
                if len(plate) >= 5:
                    log(f"🔍 Vu : {plate} ({int(prob*100)}%)")
                    # (Code MQTT ici...)
        except Exception as e:
            log(f"⚠️ Erreur pendant l'analyse d'une image : {e}")

if __name__ == "__main__":
    start_detection()

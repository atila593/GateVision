import cv2
import pytesseract
import json
import time
import paho.mqtt.client as mqtt
import os
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [MODE SOLO SANS FRIGATE V1.2.4] ---")

# On utilise TCP pour éviter les artefacts visuels qui trompent l'IA
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

with open("/data/options.json", "r") as f:
    options = json.load(f)

CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])

def start_detection():
    log(f"📸 Connexion directe caméra : {CAMERA_URL}")
    cap = cv2.VideoCapture(CAMERA_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        log("❌ Impossible de se connecter. La caméra est peut-être encore occupée.")
        return

    log("🚀 GateVision est en ligne et SEUL maître du flux.")

    while True:
        ret, frame = cap.read()
        if not ret:
            log("⚠️ Flux interrompu. Reconnexion...")
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        # On analyse toutes les 2 secondes (on peut se le permettre sans Frigate)
        time.sleep(2)

        # Optimisation
        h, w = frame.shape[:2]
        roi = frame[int(h*0.2):int(h*0.8), 0:w] # On garde une large bande centrale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # OCR
        config = '--psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(thresh, config=config)
        
        raw_plate = "".join(e for e in text if e.isalnum()).upper()

        if len(raw_plate) >= 4:
            for auth_plate in WHITELIST:
                if auth_plate.upper() in raw_plate:
                    log(f"🎯 MATCH TROUVÉ : {auth_plate}")
                    # trigger_action(auth_plate)
                    time.sleep(10)
                    break
            else:
                if len(raw_plate) < 15:
                    log(f"🔍 Lu (ignoré) : {raw_plate}")

if __name__ == "__main__":
    start_detection()

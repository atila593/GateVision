import cv2
import pytesseract
import json
import time
import paho.mqtt.client as mqtt
import os
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [OPTIMISATION FINALE J4125 V1.2.2] ---")

# Options pour stabiliser le flux RTSP sur Celeron
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp|threads;1"

with open("/data/options.json", "r") as f:
    options = json.load(f)

CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])

def start_detection():
    # On force FFMPEG comme moteur de lecture
    cap = cv2.VideoCapture(CAMERA_URL, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        log("❌ Impossible de se connecter à la caméra.")
        return

    log("🚀 GateVision est en ligne. Mode économie d'énergie actif.")

    while True:
        # On vide le buffer pour ne pas lire d'anciennes images corrompues
        for _ in range(5):
            cap.grab()
            
        ret, frame = cap.read()
        if not ret:
            log("⚠️ Erreur de décodage ou flux perdu. Reconnexion...")
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL, cv2.CAP_FFMPEG)
            continue

        # PAUSE CPU (Crucial pour ton J4125)
        time.sleep(4)

        # RECADRAGE (CROP) : On ne regarde que le milieu de l'image
        # Cela réduit la zone de calcul de 60%
        h, w = frame.shape[:2]
        roi = frame[int(h*0.3):int(h*0.8), 0:w] 

        # PRÉ-TRAITEMENT
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Améliore la visibilité des lettres
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # LECTURE TESSERACT
        config = '--psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(thresh, config=config)
        
        raw_plate = "".join(e for e in text if e.isalnum()).upper()

        if len(raw_plate) >= 4:
            for auth_plate in WHITELIST:
                clean_auth = auth_plate.replace(" ", "").upper()
                if clean_auth in raw_plate:
                    log(f"🎯 MATCH : {clean_auth}")
                    # trigger_action(clean_auth)
                    time.sleep(20)
                    break
            else:
                if len(raw_plate) < 12:
                    log(f"🔍 Lu (ignoré) : {raw_plate}")

if __name__ == "__main__":
    start_detection()

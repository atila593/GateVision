import cv2
import easyocr
import json
import time
import paho.mqtt.client as mqtt
import requests
from requests.auth import HTTPDigestAuth
import numpy as np
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [GATEVISION V2.6 - HTTP DIGEST MODE] ---")

# 1. Chargement des options
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except Exception as e:
    log(f"❌ Erreur options : {e}")
    sys.exit(1)

# --- CONFIGURATION NETTOYÉE ---
USER = options.get("camera_user", "admin")
PASS = options.get("camera_password", "")
# On ne garde que l'IP pure
IP = options.get("camera_ip", "192.168.1.28").replace("http://", "").replace("rtsp://", "").split('@')[-1].split(':')[0]
PORT = options.get("camera_port", 80)
CHANNEL = options.get("snapshot_channel", "101")

# L'URL standard Hikvision pour les images
URL = f"http://{IP}:{PORT}/ISAPI/Streaming/channels/{CHANNEL}/picture"

log(f"📸 Mode Digest activé sur : {URL}")

# MQTT
WHITELIST = options.get("authorized_plates", [])
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_PORT = options.get("mqtt_port", 1883)
MQTT_USER = options.get("mqtt_user", "")
MQTT_PASS = options.get("mqtt_password", "")
MQTT_TOPIC_CONTROL = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")
MQTT_TOPIC_SENSOR = "gatevision/last_plate"

# Initialisation EasyOCR
log("🧠 Chargement EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False, verbose=False)
log("✅ EasyOCR prêt")

def get_snapshot_digest():
    """Récupère l'image en utilisant l'authentification Digest"""
    try:
        response = requests.get(
            URL, 
            auth=HTTPDigestAuth(USER, PASS), 
            timeout=10
        )
        if response.status_code == 200:
            # Conversion du contenu binaire en image OpenCV
            img_array = np.frombuffer(response.content, np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return frame
        else:
            if response.status_code == 401:
                log("⚠️ Erreur 401 : Authentification Digest échouée. Vérifiez utilisateur/pass.")
            else:
                log(f"⚠️ Erreur HTTP {response.status_code}")
            return None
    except Exception as e:
        log(f"❌ Erreur de connexion : {e}")
        return None

def start_monitoring():
    log("🚀 Surveillance active (Snapshot HTTP Digest)...")
    last_detection_time = 0
    
    while True:
        frame = get_snapshot_digest()
        
        if frame is not None:
            # OCR
            results = reader.readtext(frame)
            for (bbox, text, confidence) in results:
                if confidence > 0.4:
                    cleaned = "".join(c for c in text if c.isalnum()).upper()
                    if len(cleaned) >= 5:
                        log(f"🔍 Plaque : {cleaned} ({confidence:.2f})")
                        
                        is_auth = any(auth.replace(" ", "").upper() in cleaned for auth in WHITELIST)
                        if is_auth and (time.time() - last_detection_time) > 20:
                            log(f"✅ ACCÈS AUTORISÉ : {cleaned}")
                            # --- INSERTION APPEL MQTT ICI ---
                            last_detection_time = time.time()
        
        time.sleep(2) # On prend une photo toutes les 2 secondes

if __name__ == "__main__":
    start_monitoring()

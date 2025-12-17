import cv2
import easyocr
import json
import time
import paho.mqtt.client as mqtt
import requests
import os
import sys

# Forcer l'affichage immédiat dans les logs HA
def log(message):
    print(f"{message}", flush=True)

log("--- [DÉMARRAGE GATEVISION V1.1.0] ---")

# Chemin standard Home Assistant
OPTIONS_PATH = "/data/options.json"

def load_ha_options():
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH, "r") as f:
            try:
                return json.load(f)
            except Exception as e:
                log(f"❌ Erreur lecture options : {e}")
                return {}
    log("⚠️ Fichier options introuvable, utilisation défauts.")
    return {}

options = load_ha_options()

# Config
CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])
METHOD = options.get("output_method", "MQTT")
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_TOPIC = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")

log(f"📸 Caméra cible : {CAMERA_URL}")
log(f"🚗 Liste blanche : {WHITELIST}")

# Initialisation de l'IA avec gestion d'erreur
try:
    log("📦 Chargement des modèles d'IA (EasyOCR)... Cela peut prendre 1 minute.")
    # On force gpu=False car les CPU des box HA ne supportent pas CUDA
    reader = easyocr.Reader(['fr', 'en'], gpu=False)
    log("✅ Modèles IA chargés avec succès !")
except Exception as e:
    log(f"❌ CRASH lors du chargement de l'IA : {e}")
    sys.exit(1)

def trigger_action(plate):
    log(f"✅ ACCÈS AUTORISÉ : {plate}")
    if METHOD == "MQTT":
        try:
            client = mqtt.Client()
            user = options.get("mqtt_user")
            password = options.get("mqtt_password")
            if user and password:
                client.username_pw_set(user, password)
            client.connect(MQTT_BROKER, options.get("mqtt_port", 1883), 60)
            client.publish(MQTT_TOPIC, MQTT_PAYLOAD)
            client.disconnect()
            log(f"📡 Signal MQTT envoyé sur {MQTT_TOPIC}")
        except Exception as e:
            log(f"❌ Erreur MQTT : {e}")

def start_detection():
    if not CAMERA_URL:
        log("❌ Erreur : URL caméra vide !")
        return

    log("🚀 GateVision est en ligne. Lancement de l'analyse vidéo...")
    cap = cv2.VideoCapture(CAMERA_URL)
    last_trigger = 0
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            log("⚠️ Flux vidéo perdu. Tentative de reconnexion...")
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        frame_count += 1
        # Analyse 1 image sur 10 pour économiser 90% du CPU
        if frame_count % 60 != 0:
            continue

        # Analyse OCR
        results = reader.readtext(frame)
        
        for (bbox, text, prob) in results:
            plate = text.replace(" ", "").replace("-", "").upper()
            if plate in WHITELIST and prob > 0.45:
                current_time = time.time()
                if current_time - last_trigger > 30:
                    trigger_action(plate)
                    last_trigger = current_time
            elif len(plate) >= 5:
                # Log discret pour le débug
                log(f"🔍 Plaque vue : {plate} ({int(prob*100)}%)")

if __name__ == "__main__":
    try:
        start_detection()
    except Exception as e:
        log(f"❌ Erreur fatale : {e}")
        sys.exit(1)

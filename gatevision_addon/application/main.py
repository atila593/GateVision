import cv2
import pytesseract
import json
import time
import paho.mqtt.client as mqtt
import os
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [DÉMARRAGE MODE TESSERACT V1.2.0] ---")

# Chargement des options Home Assistant
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except Exception as e:
    log(f"❌ Erreur options : {e}")
    sys.exit(1)

CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_TOPIC = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")

def trigger_action(plate):
    log(f"✅ ACCÈS AUTORISÉ : {plate}")
    try:
        client = mqtt.Client()
        user = options.get("mqtt_user")
        password = options.get("mqtt_password")
        if user and password:
            client.username_pw_set(user, password)
        client.connect(MQTT_BROKER, options.get("mqtt_port", 1883), 60)
        client.publish(MQTT_TOPIC, MQTT_PAYLOAD)
        client.disconnect()
        log(f"📡 Signal MQTT envoyé vers {MQTT_TOPIC}")
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def start_detection():
    log(f"📸 Connexion caméra : {CAMERA_URL}")
    cap = cv2.VideoCapture(CAMERA_URL)
    
    if not cap.isOpened():
        log("❌ Impossible d'ouvrir le flux. Vérifiez l'URL RTSP.")
        return

    log("🚀 GateVision est en ligne (Moteur Tesseract)")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        # On analyse une image toutes les 2 secondes (économie CPU)
        time.sleep(2)

        # Prétraitement léger pour Tesseract
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Lecture de la plaque (psm 7 = une seule ligne de texte)
        text = pytesseract.image_to_string(gray, config='--psm 7')
        
        # Nettoyage du texte pour ne garder que lettres et chiffres
        plate = "".join(e for e in text if e.isalnum()).upper()

        if len(plate) >= 5:
            log(f"🔍 Plaque vue : {plate}")
            if any(auth_plate in plate for auth_plate in WHITELIST):
                trigger_action(plate)
                time.sleep(10) # Pause après détection

if __name__ == "__main__":
    start_detection()

import cv2
import easyocr
import json
import time
import paho.mqtt.client as mqtt
import requests
import os

# Chemin standard où Home Assistant stocke la configuration de l'addon
OPTIONS_PATH = "/data/options.json"

def load_ha_options():
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH, "r") as f:
            return json.load(f)
    else:
        print("⚠️ Fichier d'options introuvable, utilisation de valeurs par défaut.")
        return {}

options = load_ha_options()

# Variables de configuration extraites de l'interface HA
CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])
METHOD = options.get("output_method", "MQTT")
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_TOPIC = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")
WEBHOOK_URL = options.get("webhook_url", "")

# Initialisation de l'IA (OCR)
print("📦 Chargement des modèles d'IA (EasyOCR)...")
reader = easyocr.Reader(['fr', 'en'], gpu=False)

def trigger_action(plate):
    print(f"✅ ACCÈS AUTORISÉ : {plate}")
    
    if METHOD == "MQTT":
        try:
            client = mqtt.Client()
            # On tente de se connecter au broker interne de HA par défaut
            client.connect(MQTT_BROKER)
            client.publish(MQTT_TOPIC, MQTT_PAYLOAD)
            client.disconnect()
            print(f"📡 Signal MQTT envoyé sur {MQTT_TOPIC}")
        except Exception as e:
            print(f"❌ Erreur MQTT : {e}")
            
    elif METHOD == "WEBHOOK" and WEBHOOK_URL:
        try:
            requests.get(WEBHOOK_URL, timeout=5)
            print("🌐 Signal Webhook envoyé")
        except Exception as e:
            print(f"❌ Erreur Webhook : {e}")

def start_detection():
    if not CAMERA_URL:
        print("❌ Erreur : URL de la caméra non configurée dans l'addon.")
        return

    cap = cv2.VideoCapture(CAMERA_URL)
    last_trigger = 0
    
    print(f"🚀 GateVision est en ligne. Analyse de : {CAMERA_URL}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Flux vidéo perdu. Tentative de reconnexion...")
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        # Analyse OCR
        results = reader.readtext(frame)
        
        for (bbox, text, prob) in results:
            # Nettoyage
            plate = text.replace(" ", "").replace("-", "").upper()
            
            # On vérifie si la plaque est dans la liste configurée dans HA
            if plate in WHITELIST and prob > 0.50:
                current_time = time.time()
                if current_time - last_trigger > 30:
                    trigger_action(plate)
                    last_trigger = current_time
            elif len(plate) > 4:
                print(f"🔍 Plaque ignorée : {plate} (Fiabilité: {int(prob*100)}%)")

    cap.release()

if __name__ == "__main__":
    start_detection()

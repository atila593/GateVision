import cv2
import pytesseract
import json
import time
import paho.mqtt.client as mqtt
import os
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [GATEVISION V1.2.6 - FULL HASS & SOLO MODE] ---")

# 1. Chargement des options Home Assistant
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except Exception as e:
    log(f"❌ Erreur options : {e}")
    sys.exit(1)

# Variables de configuration
CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_PORT = options.get("mqtt_port", 1883)
MQTT_USER = options.get("mqtt_user", "")
MQTT_PASS = options.get("mqtt_password", "")
MQTT_TOPIC_CONTROL = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")

# Topic pour le capteur Lovelace
MQTT_TOPIC_SENSOR = "gatevision/last_plate"

# Optimisation OpenCV pour flux RTSP sur Celeron
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

def send_update(plate, authorized=False):
    """ Envoie les infos à Home Assistant via MQTT """
    try:
        client = mqtt.Client()
        if MQTT_USER and MQTT_PASS:
            client.username_pw_set(MQTT_USER, MQTT_PASS)
        
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Données pour le panneau Lovelace
        data = {
            "plate": plate,
            "status": "Autorisé" if authorized else "Inconnu",
            "time": time.strftime("%H:%M:%S")
        }
        client.publish(MQTT_TOPIC_SENSOR, json.dumps(data), retain=True)
        
        # Si autorisé, on envoie aussi l'ordre d'ouverture
        if authorized:
            log(f"🎯 MATCH : {plate}. Ouverture demandée.")
            client.publish(MQTT_TOPIC_CONTROL, MQTT_PAYLOAD)
        
        client.disconnect()
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def start_detection():
    log(f"📸 Connexion caméra : {CAMERA_URL}")
    cap = cv2.VideoCapture(CAMERA_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        log("❌ Impossible de joindre la caméra.")
        return

    log("🚀 Analyse active. Prêt pour détection.")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        # Analyse toutes les 2 secondes pour préserver le CPU
        time.sleep(2)

        # --- PRÉ-TRAITEMENT ---
        h, w = frame.shape[:2]
        # On crop une bande centrale (15% à 85% de la hauteur)
        roi = frame[int(h*0.15):int(h*0.85), 0:w]
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Adaptive threshold pour gérer les phares et reflets
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )

        # --- OCR ---
        # PSM 3 (Auto) + Whitelist pour vitesse
        config = '--psm 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(processed, config=config)
        
        # Nettoyage texte
        raw_text = "".join(e for e in text if e.isalnum()).upper()

        if len(raw_text) >= 4:
            # On vérifie si c'est dans la whitelist
            found = False
            for auth_plate in WHITELIST:
                clean_auth = auth_plate.replace(" ", "").replace("-", "").upper()
                
                if clean_auth in raw_text:
                    send_update(clean_auth, authorized=True)
                    found = True
                    time.sleep(15) # Pause après ouverture
                    break
            
            # Si non autorisé, on met quand même à jour Lovelace
            if not found and "SANRY" not in raw_text:
                if len(raw_text) < 12: # On ignore les phrases trop longues
                    log(f"🔍 Plaque inconnue : {raw_text}")
                    send_update(raw_text, authorized=False)

if __name__ == "__main__":
    try:
        start_detection()
    except Exception as e:
        log(f"❌ Erreur fatale : {e}")
        sys.exit(1)

import cv2
import pytesseract
import json
import time
import paho.mqtt.client as mqtt
import os
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [GATEVISION V1.2.5 - MODE DÉTECTION LARGE] ---")

# Chargement des options
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
    log(f"🎯 MATCH TROUVÉ : {plate}. Envoi du signal MQTT...")
    try:
        client = mqtt.Client()
        user = options.get("mqtt_user")
        password = options.get("mqtt_password")
        if user and password:
            client.username_pw_set(user, password)
        client.connect(MQTT_BROKER, options.get("mqtt_port", 1883), 60)
        client.publish(MQTT_TOPIC, MQTT_PAYLOAD)
        client.disconnect()
        log("📡 Signal envoyé avec succès !")
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def start_detection():
    log(f"📸 Connexion caméra : {CAMERA_URL}")
    cap = cv2.VideoCapture(CAMERA_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    log("🚀 Analyse en cours... Présentez votre plaque.")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        # Analyse toutes les 2 secondes
        time.sleep(2)

        # 1. ZONE DE LECTURE : On prend presque toute la hauteur (10% à 90%)
        h, w = frame.shape[:2]
        roi = frame[int(h*0.1):int(h*0.9), 0:w]

        # 2. PRÉ-TRAITEMENT AMÉLIORÉ (Adaptive Threshold)
        # Idéal pour les changements de lumière et les plaques réfléchissantes
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )

        # 3. LECTURE TESSERACT (Mode PSM 3 : Analyse complète de l'image)
        config = '--psm 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(processed, config=config)
        
        # Nettoyage
        raw_text = "".join(e for e in text if e.isalnum()).upper()

        if len(raw_text) >= 4:
            found = False
            for auth_plate in WHITELIST:
                clean_auth = auth_plate.replace(" ", "").replace("-", "").upper()
                
                # On vérifie si ta plaque est présente dans le texte lu
                if clean_auth in raw_text:
                    trigger_action(clean_auth)
                    found = True
                    time.sleep(15) # Pause après succès
                    break
            
            if not found:
                # On ignore les textes récurrents comme SANRY4 pour ne pas polluer les logs
                if "SANRY" not in raw_text and len(raw_text) < 15:
                    log(f"🔍 Texte vu : {raw_text}")

if __name__ == "__main__":
    start_detection()

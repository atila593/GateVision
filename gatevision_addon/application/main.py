import cv2
import easyocr
import time
import paho.mqtt.client as mqtt
import numpy as np
import json
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [GATEVISION V3.0 - UNIVERSAL ADDON] ---")

# 1. Chargement des options depuis HA
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except Exception as e:
    log(f"❌ Erreur de lecture des options : {e}")
    sys.exit(1)

# Variables de configuration
RTSP_URL = options.get("rtsp_url")
WHITELIST = options.get("authorized_plates", [])
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_PORT = options.get("mqtt_port", 1883)
MQTT_USER = options.get("mqtt_user", "")
MQTT_PASS = options.get("mqtt_password", "")

# Nouvelle variable pour l'entité
TARGET_TOPIC = options.get("mqtt_topic", "gate/control")
PAYLOAD = options.get("mqtt_payload", "ON")
SENSITIVITY = options.get("motion_sensitivity", 5000)

log(f"📋 Plaques autorisées : {', '.join(WHITELIST)}")
log(f"🎯 Entité cible : {TARGET_TOPIC}")

# Initialisation EasyOCR
log("🧠 Chargement EasyOCR (CPU)...")
reader = easyocr.Reader(['en'], gpu=False)
log("✅ Système prêt.")

def send_open_command(plate):
    """Envoie la commande MQTT à l'entité choisie"""
    try:
        client = mqtt.Client()
        if MQTT_USER and MQTT_PASS:
            client.username_pw_set(MQTT_USER, MQTT_PASS)
        
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        log(f"🔓 ACCÈS VALIDÉ pour {plate} -> Commande envoyée à {TARGET_TOPIC}")
        client.publish(TARGET_TOPIC, PAYLOAD)
        
        # On publie aussi l'info pour un capteur de log
        client.publish("gatevision/last_event", json.dumps({"plate": plate, "action": "OPEN"}), retain=True)
        client.disconnect()
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def start_monitoring():
    cap = cv2.VideoCapture(RTSP_URL)
    avg = None
    last_detection_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            log("⚠️ Flux perdu. Tentative de reconnexion...")
            cap = cv2.VideoCapture(RTSP_URL)
            time.sleep(5)
            continue

        # DÉTECTION DE MOUVEMENT (Léger)
        small_frame = cv2.resize(frame, (500, 300))
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if avg is None:
            avg = gray.copy().astype("float")
            continue

        cv2.accumulateWeighted(gray, avg, 0.5)
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
        thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Si mouvement détecté (ex: une voiture entre dans le cadre)
        if np.sum(thresh) > SENSITIVITY:
            now = time.time()
            if now - last_detection_time > 10: # Évite de scanner 100 fois la même voiture
                log("🚗 Mouvement détecté ! Analyse OCR...")
                
                results = reader.readtext(frame)
                for (bbox, text, confidence) in results:
                    if confidence > 0.4:
                        cleaned = "".join(c for c in text if c.isalnum()).upper()
                        log(f"🔍 Plaque lue : {cleaned} ({int(confidence*100)}%)")
                        
                        # Vérification Whitelist
                        if any(auth.replace(" ","") in cleaned for auth in WHITELIST):
                            send_open_command(cleaned)
                            last_detection_time = now
                            break # On arrête l'analyse pour cette image

        # Vider le buffer RTSP pour rester en temps réel
        for _ in range(15): cap.grab()
        time.sleep(0.1)

if __name__ == "__main__":
    start_monitoring()

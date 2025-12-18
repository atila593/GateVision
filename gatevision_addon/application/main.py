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

log("--- [GATEVISION V2.6 - FINAL OPERATIONAL] ---")

# 1. Chargement des options
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except Exception as e:
    log(f"❌ Erreur options : {e}")
    sys.exit(1)

# Variables de configuration (chargées depuis votre YAML)
USER = options.get("camera_user", "admin")
PASS = options.get("camera_password", "")
IP = options.get("camera_ip", "192.168.1.28")
PORT = options.get("camera_port", 80)
CHANNEL = options.get("snapshot_channel", "101")
INTERVAL = options.get("snapshot_interval", 2)

WHITELIST = options.get("authorized_plates", [])
MQTT_BROKER = options.get("mqtt_broker", "192.168.1.142")
MQTT_PORT = options.get("mqtt_port", 1883)
MQTT_USER = options.get("mqtt_user", "")
MQTT_PASS = options.get("mqtt_password", "")
MQTT_TOPIC = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")

# URL Snapshot Hikvision
URL = f"http://{IP}:{PORT}/Streaming/channels/{CHANNEL}/picture"

log(f"📸 Connexion caméra : {IP}:{PORT} (Canal {CHANNEL})")
log(f"📡 MQTT Broker : {MQTT_BROKER}")
log(f"📋 Whitelist : {', '.join(WHITELIST)}")

# Initialisation EasyOCR
log("🧠 Chargement EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False, verbose=False)
log("✅ EasyOCR prêt")

def send_mqtt_command(plate):
    """Envoie l'ordre d'ouverture via MQTT"""
    try:
        client = mqtt.Client()
        if MQTT_USER and MQTT_PASS:
            client.username_pw_set(MQTT_USER, MQTT_PASS)
        
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        log(f"🔓 Envoi commande d'ouverture ({MQTT_TOPIC} -> {MQTT_PAYLOAD})")
        client.publish(MQTT_TOPIC, MQTT_PAYLOAD)
        
        # Optionnel : Publication de la plaque détectée pour affichage dans HA
        sensor_data = {"plate": plate, "time": time.strftime("%H:%M:%S"), "status": "✅ Autorisé"}
        client.publish("gatevision/last_plate", json.dumps(sensor_data), retain=True)
        
        client.disconnect()
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def get_snapshot():
    """Capture d'image en Digest Auth"""
    try:
        response = requests.get(
            URL, 
            auth=HTTPDigestAuth(USER, PASS), 
            timeout=10
        )
        if response.status_code == 200:
            img_array = np.frombuffer(response.content, np.uint8)
            return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        else:
            log(f"⚠️ Erreur Caméra: HTTP {response.status_code}")
            return None
    except Exception as e:
        log(f"❌ Erreur réseau : {e}")
        return None

def start_monitoring():
    log("🚀 Surveillance active...")
    last_detection_time = 0
    cooldown = 20 # 20 secondes entre deux ouvertures

    while True:
        frame = get_snapshot()
        
        if frame is not None:
            # OCR sur l'image
            results = reader.readtext(frame)
            
            for (bbox, text, confidence) in results:
                if confidence > 0.35: # Seuil de confiance
                    # Nettoyage du texte (uniquement lettres et chiffres)
                    cleaned = "".join(c for c in text if c.isalnum()).upper()
                    
                    if len(cleaned) >= 5:
                        log(f"🔍 Plaque lue : {cleaned} ({int(confidence*100)}%)")
                        
                        # Vérification dans la whitelist
                        # On vérifie si une des plaques autorisées est contenue dans le texte lu (ou l'inverse)
                        match = False
                        for auth in WHITELIST:
                            auth_clean = auth.replace(" ", "").upper()
                            if auth_clean in cleaned or cleaned in auth_clean:
                                match = True
                                authorized_plate = auth
                                break
                        
                        if match:
                            current_time = time.time()
                            if (current_time - last_detection_time) > cooldown:
                                log(f"✅ ACCÈS VALIDÉ pour {authorized_plate}")
                                send_mqtt_command(authorized_plate)
                                last_detection_time = current_time
                                time.sleep(5) # Pause après détection réussie
        
        time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        start_monitoring()
    except KeyboardInterrupt:
        log("🛑 Arrêt du script")

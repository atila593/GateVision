import cv2
import easyocr
import json
import time
import paho.mqtt.client as mqtt
import numpy as np
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [GATEVISION V2.3 - RTSP MODE] ---")

# 1. Chargement des options
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except Exception as e:
    log(f"❌ Erreur options : {e}")
    sys.exit(1)

# --- CONFIGURATION RTSP ---
# On construit l'URL exacte qui fonctionne chez vous
CAMERA_USER = options.get("camera_user", "admin")
CAMERA_PASS = options.get("camera_password", "Olivier59")
CAMERA_IP = options.get("camera_ip", "192.168.1.28")

# L'URL que vous avez confirmée
RTSP_URL = f"rtsp://{CAMERA_USER}:{CAMERA_PASS}@{CAMERA_IP}/h264:80/ISAPI/Streaming/Channels/101/picture"

# Options MQTT
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

def get_snapshot_rtsp():
    """Capture une image depuis le flux RTSP via OpenCV"""
    cap = cv2.VideoCapture(RTSP_URL)
    if not cap.isOpened():
        return None
    
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        return frame
    return None

def is_plate_authorized(detected_text):
    clean_detected = "".join(c for c in detected_text if c.isalnum()).upper()
    for auth_plate in WHITELIST:
        clean_auth = "".join(c for c in auth_plate if c.isalnum()).upper()
        if clean_auth in clean_detected or clean_detected in clean_auth:
            if len(clean_detected) >= 4:
                return True, auth_plate
    return False, None

def send_update(plate, authorized=False):
    try:
        client = mqtt.Client()
        if MQTT_USER and MQTT_PASS:
            client.username_pw_set(MQTT_USER, MQTT_PASS)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        data = {
            "plate": plate, 
            "status": "✅ Autorisé" if authorized else "❌ Inconnu", 
            "time": time.strftime("%H:%M:%S")
        }
        client.publish(MQTT_TOPIC_SENSOR, json.dumps(data), retain=True)
        
        if authorized:
            log(f"🔓 OUVERTURE : {plate}")
            client.publish(MQTT_TOPIC_CONTROL, MQTT_PAYLOAD)
        client.disconnect()
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def start_monitoring():
    log(f"📸 Connexion au flux : {RTSP_URL}")
    log("🚀 Surveillance active...")
    
    last_detection_time = 0
    cooldown_period = 15

    while True:
        frame = get_snapshot_rtsp()
        
        if frame is not None:
            # Prétraitement rapide
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # OCR sur l'image complète (ou zone centrale)
            results = reader.readtext(gray, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
            
            for (bbox, text, confidence) in results:
                if confidence > 0.4:
                    cleaned = text.strip().upper()
                    if len(cleaned) >= 5:
                        log(f"🔍 Détecté: {cleaned} ({confidence:.2f})")
                        authorized, matched = is_plate_authorized(cleaned)
                        
                        current_time = time.time()
                        if authorized and (current_time - last_detection_time) > cooldown_period:
                            send_update(matched, True)
                            last_detection_time = current_time
                            time.sleep(5) # Petite pause après succès
                        elif not authorized:
                            send_update(cleaned, False)
        
        time.sleep(2) # Intervalle entre deux captures

if __name__ == "__main__":
    start_monitoring()

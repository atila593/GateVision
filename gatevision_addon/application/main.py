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

log("--- [GATEVISION V2.2 - FIXED AUTH] ---")

# 1. Chargement des options
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except Exception as e:
    log(f"❌ Erreur options : {e}")
    sys.exit(1)

# --- CONFIGURATION & NETTOYAGE ---
# On récupère l'IP et on enlève http:// ou rtsp:// si l'utilisateur l'a mis
RAW_IP = options.get("camera_ip", "192.168.1.28")
CAMERA_IP = RAW_IP.replace("http://", "").replace("rtsp://", "").split('/')[0]

CAMERA_PORT = options.get("camera_port", 80)
CAMERA_USER = options.get("camera_user", "admin")
CAMERA_PASS = options.get("camera_password", "")
SNAPSHOT_CHANNEL = options.get("snapshot_channel", "102")
SNAPSHOT_INTERVAL = options.get("snapshot_interval", 2)

WHITELIST = options.get("authorized_plates", [])
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_PORT = options.get("mqtt_port", 1883)
MQTT_USER = options.get("mqtt_user", "")
MQTT_PASS = options.get("mqtt_password", "")
MQTT_TOPIC_CONTROL = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")
MQTT_TOPIC_SENSOR = "gatevision/last_plate"

# Construction des URLs snapshot (Uniquement HTTP pour les images)
SNAPSHOT_URLS = [
    f"http://{CAMERA_IP}:{CAMERA_PORT}/ISAPI/Streaming/channels/{SNAPSHOT_CHANNEL}/picture",
    f"http://{CAMERA_IP}:{CAMERA_PORT}/Streaming/channels/{SNAPSHOT_CHANNEL}/picture",
    f"http://{CAMERA_IP}:{CAMERA_PORT}/ISAPI/Streaming/Channels/{SNAPSHOT_CHANNEL}/picture",
    f"http://{CAMERA_IP}:{CAMERA_PORT}/Streaming/Channels/{SNAPSHOT_CHANNEL}/picture",
    f"http://{CAMERA_IP}:{CAMERA_PORT}/cgi-bin/snapshot.cgi",
]

WORKING_URL = None

# Initialisation EasyOCR
log("🧠 Chargement EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False, verbose=False)
log("✅ EasyOCR prêt")

# Variables globales
prev_frame_gray = None
last_detection_time = 0
cooldown_period = 15

def find_working_url():
    """Teste toutes les URLs possibles et trouve celle qui fonctionne"""
    global WORKING_URL
    
    log(f"🔍 Recherche de l'URL sur {CAMERA_IP} (Port {CAMERA_PORT})...")
    
    for url in SNAPSHOT_URLS:
        try:
            log(f"   Test: {url}")
            # Utilisation de DigestAuth car Hikvision l'exige par défaut
            response = requests.get(
                url,
                auth=HTTPDigestAuth(CAMERA_USER, CAMERA_PASS),
                timeout=5
            )
            
            if response.status_code == 200 and len(response.content) > 1000:
                img_array = np.frombuffer(response.content, np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    WORKING_URL = url
                    log(f"✅ URL fonctionnelle trouvée: {url}")
                    return True
            else:
                log(f"   ❌ Code HTTP: {response.status_code}")
        except Exception as e:
            log(f"   ❌ Erreur de connexion: {str(e)[:50]}")
            continue
    
    log("❌ Aucune URL snapshot n'a fonctionné")
    log("CONSEIL: Vérifiez que 'Hikvision-CGI' est activé dans la caméra.")
    return False

def get_snapshot():
    """Récupère un snapshot depuis la caméra"""
    try:
        response = requests.get(
            WORKING_URL,
            auth=HTTPDigestAuth(CAMERA_USER, CAMERA_PASS),
            timeout=5
        )
        if response.status_code == 200:
            img_array = np.frombuffer(response.content, np.uint8)
            return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return None
    except:
        return None

def detect_motion(frame):
    global prev_frame_gray
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    
    if prev_frame_gray is None:
        prev_frame_gray = gray
        return False
    
    frame_delta = cv2.absdiff(prev_frame_gray, gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    motion_pixels = np.sum(thresh == 255)
    prev_frame_gray = gray
    
    if motion_pixels > 2000:
        log(f"🚗 Mouvement ({motion_pixels} px)")
        return True
    return False

def preprocess_for_plate(frame):
    h, w = frame.shape[:2]
    # Zone d'intérêt (centre de l'image)
    roi = frame[int(h*0.2):int(h*0.8), int(w*0.1):int(w*0.9)]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    return clahe.apply(gray)

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
        
        data = {"plate": plate, "status": "✅ Autorisé" if authorized else "❌ Inconnu", "time": time.strftime("%H:%M:%S")}
        client.publish(MQTT_TOPIC_SENSOR, json.dumps(data), retain=True)
        
        if authorized:
            log(f"🔓 OUVERTURE : {plate}")
            client.publish(MQTT_TOPIC_CONTROL, MQTT_PAYLOAD)
        client.disconnect()
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def start_monitoring():
    if not find_working_url():
        time.sleep(60)
        return

    log(f"🚀 Surveillance active sur: {WORKING_URL}")
    while True:
        frame = get_snapshot()
        if frame is not None and detect_motion(frame):
            processed = preprocess_for_plate(frame)
            results = reader.readtext(processed, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
            
            for (bbox, text, confidence) in results:
                if confidence > 0.4:
                    cleaned = text.strip().upper()
                    log(f"🔍 Plaque détectée: {cleaned} ({confidence:.2f})")
                    authorized, matched = is_plate_authorized(cleaned)
                    
                    if authorized:
                        send_update(matched, True)
                        time.sleep(cooldown_period)
                        break
                    else:
                        send_update(cleaned, False)
        
        time.sleep(SNAPSHOT_INTERVAL)

if __name__ == "__main__":
    start_monitoring()

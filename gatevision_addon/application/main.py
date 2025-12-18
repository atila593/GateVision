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

log("--- [GATEVISION V2.2 - DIGEST AUTH] ---")

# 1. Chargement des options
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except Exception as e:
    log(f"❌ Erreur options : {e}")
    sys.exit(1)

# Variables de configuration
CAMERA_IP = options.get("camera_ip", "192.168.1.28")
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

# Nettoyage de l'IP au cas où l'utilisateur a mis http:// ou rtsp:// dans les options
clean_ip = CAMERA_IP.replace("http://", "").replace("rtsp://", "").split('/')[0]

# Construction des URLs correctes (Uniquement en HTTP pour les snapshots)
SNAPSHOT_URLS = [
    f"http://{clean_ip}:{CAMERA_PORT}/ISAPI/Streaming/channels/{SNAPSHOT_CHANNEL}/picture",
    f"http://{clean_ip}:{CAMERA_PORT}/Streaming/channels/{SNAPSHOT_CHANNEL}/picture",
    f"http://{clean_ip}:{CAMERA_PORT}/ISAPI/Streaming/Channels/{SNAPSHOT_CHANNEL}/picture",
    f"http://{clean_ip}:{CAMERA_PORT}/Streaming/Channels/{SNAPSHOT_CHANNEL}/picture",
    f"http://{clean_ip}:{CAMERA_PORT}/cgi-bin/snapshot.cgi",
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
    
    log("🔍 Recherche de l'URL snapshot fonctionnelle...")
    
    for url in SNAPSHOT_URLS:
        try:
            log(f"   Test: {url}")
            response = requests.get(
                url,
                auth=HTTPDigestAuth(CAMERA_USER, CAMERA_PASS),
                timeout=5
            )
            
            if response.status_code == 200 and len(response.content) > 1000:
                # Vérifier que c'est bien une image
                img_array = np.frombuffer(response.content, np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    WORKING_URL = url
                    log(f"✅ URL fonctionnelle trouvée: {url}")
                    return True
        except Exception as e:
            log(f"   ❌ Échec: {str(e)[:50]}")
            continue
    
    log("❌ Aucune URL snapshot n'a fonctionné")
    log("")
    log("🔧 SOLUTIONS:")
    log("1. Connectez-vous à votre caméra: http://192.168.1.28")
    log("2. Allez dans: Configuration > Network > Advanced Settings")
    log("3. Changez 'Web Authentication' vers 'digest/basic'")
    log("4. Dans Integration Protocol, activez 'Enable Hikvision-CGI'")
    log("5. Redémarrez la caméra")
    return False

def get_snapshot():
    """Récupère un snapshot depuis la caméra avec authentification digest"""
    try:
        response = requests.get(
            WORKING_URL,
            auth=HTTPDigestAuth(CAMERA_USER, CAMERA_PASS),
            timeout=5
        )
        
        if response.status_code == 200:
            img_array = np.frombuffer(response.content, np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return frame
        else:
            log(f"⚠️ HTTP {response.status_code}")
            return None
    except Exception as e:
        log(f"❌ Erreur snapshot : {e}")
        return None

def detect_motion(frame):
    """Détecte si quelque chose a bougé"""
    global prev_frame_gray
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    
    if prev_frame_gray is None:
        prev_frame_gray = gray
        return False
    
    frame_delta = cv2.absdiff(prev_frame_gray, gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    
    motion_pixels = np.sum(thresh == 255)
    prev_frame_gray = gray
    
    if motion_pixels > 2000:
        log(f"🚗 Mouvement détecté ({motion_pixels} px)")
        return True
    
    return False

def preprocess_for_plate(frame):
    """Améliore l'image pour OCR"""
    h, w = frame.shape[:2]
    roi = frame[int(h*0.2):int(h*0.8), int(w*0.1):int(w*0.9)]
    
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    return enhanced

def clean_plate_text(text):
    """Nettoie le texte OCR"""
    cleaned = "".join(c for c in text if c.isalnum() or c == '-').upper()
    return cleaned.strip()

def is_plate_authorized(detected_text):
    """Vérifie si une plaque est autorisée"""
    detected_clean = detected_text.replace(" ", "").replace("-", "").upper()
    
    for auth_plate in WHITELIST:
        auth_clean = auth_plate.replace(" ", "").replace("-", "").upper()
        
        if auth_clean in detected_clean or detected_clean in auth_clean:
            len_min = min(len(auth_clean), len(detected_clean))
            len_max = max(len(auth_clean), len(detected_clean))
            
            if len_min / len_max > 0.7:
                return True, auth_plate
    
    return False, None

def send_update(plate, authorized=False):
    """Envoie l'info à Home Assistant"""
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
            log(f"✅ OUVERTURE pour {plate}")
            client.publish(MQTT_TOPIC_CONTROL, MQTT_PAYLOAD)
        
        client.disconnect()
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def analyze_frame(frame):
    """Analyse une image"""
    global last_detection_time
    
    processed = preprocess_for_plate(frame)
    
    try:
        results = reader.readtext(processed, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
        
        for (bbox, text, confidence) in results:
            if confidence < 0.4:
                continue
            
            cleaned = clean_plate_text(text)
            
            if len(cleaned) < 5 or len(cleaned) > 12:
                continue
            
            log(f"🔍 Détecté: '{cleaned}' ({confidence:.2f})")
            
            authorized, matched = is_plate_authorized(cleaned)
            current_time = time.time()
            
            if authorized and (current_time - last_detection_time) > cooldown_period:
                send_update(matched, authorized=True)
                last_detection_time = current_time
                return True
            elif not authorized:
                send_update(cleaned, authorized=False)
        
    except Exception as e:
        log(f"❌ Erreur OCR : {e}")
    
    return False

def start_monitoring():
    """Boucle principale"""
    if not find_working_url():
        log("")
        log("⏸️  En pause - Impossible de se connecter à la caméra")
        log("   Vérifiez la configuration et redémarrez l'addon")
        time.sleep(3600)  # Attendre 1h
        return
    
    log(f"📸 URL: {WORKING_URL}")
    log(f"⏱️  Intervalle: {SNAPSHOT_INTERVAL}s")
    log(f"📋 Plaques autorisées: {', '.join(WHITELIST)}")
    log("🚀 Surveillance active...")
    
    consecutive_errors = 0
    
    while True:
        frame = get_snapshot()
        
        if frame is None:
            consecutive_errors += 1
            if consecutive_errors >= 10:
                log(f"❌ Trop d'erreurs. Vérifiez la caméra.")
                consecutive_errors = 0
            time.sleep(SNAPSHOT_INTERVAL)
            continue
        
        consecutive_errors = 0
        
        if detect_motion(frame):
            opened = analyze_frame(frame)
            
            if opened:
                log("⏸️  Pause 15s après ouverture")
                time.sleep(15)
        
        time.sleep(SNAPSHOT_INTERVAL)

if __name__ == "__main__":
    try:
        start_monitoring()
    except KeyboardInterrupt:
        log("🛑 Arrêt")
    except Exception as e:
        log(f"❌ Erreur fatale : {e}")
        sys.exit(1)

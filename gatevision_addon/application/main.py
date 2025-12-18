import cv2
import easyocr
import json
import time
import paho.mqtt.client as mqtt
import requests
import numpy as np
import sys
from io import BytesIO

def log(message):
    print(f"{message}", flush=True)

log("--- [GATEVISION V2.1 - MODE SNAPSHOT] ---")

# 1. Chargement des options
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except Exception as e:
    log(f"❌ Erreur options : {e}")
    sys.exit(1)

# Variables de configuration
SNAPSHOT_URL = options.get("snapshot_url", "")
SNAPSHOT_INTERVAL = options.get("snapshot_interval", 2)  # Secondes entre chaque snapshot
WHITELIST = options.get("authorized_plates", [])
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_PORT = options.get("mqtt_port", 1883)
MQTT_USER = options.get("mqtt_user", "")
MQTT_PASS = options.get("mqtt_password", "")
MQTT_TOPIC_CONTROL = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")
MQTT_TOPIC_SENSOR = "gatevision/last_plate"

# Auth pour la caméra si nécessaire
CAM_USER = options.get("camera_user", "")
CAM_PASS = options.get("camera_password", "")

# Initialisation EasyOCR
log("🧠 Chargement EasyOCR (peut prendre 30s au premier lancement)...")
reader = easyocr.Reader(['en'], gpu=False, verbose=False)
log("✅ EasyOCR prêt")

# Variables globales
prev_frame_gray = None
last_detection_time = 0
cooldown_period = 15  # Secondes avant de réautoriser la même plaque

def get_snapshot():
    """Récupère un snapshot depuis la caméra"""
    try:
        if CAM_USER and CAM_PASS:
            response = requests.get(
                SNAPSHOT_URL, 
                auth=(CAM_USER, CAM_PASS),
                timeout=5
            )
        else:
            response = requests.get(SNAPSHOT_URL, timeout=5)
        
        if response.status_code == 200:
            # Conversion bytes → numpy array → image OpenCV
            img_array = np.frombuffer(response.content, np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return frame
        else:
            log(f"⚠️ HTTP {response.status_code} lors de la récupération du snapshot")
            return None
    except Exception as e:
        log(f"❌ Erreur snapshot : {e}")
        return None

def detect_motion(frame):
    """Détecte si quelque chose a bougé depuis la dernière image"""
    global prev_frame_gray
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    
    if prev_frame_gray is None:
        prev_frame_gray = gray
        return False
    
    # Différence entre les deux images
    frame_delta = cv2.absdiff(prev_frame_gray, gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    
    motion_pixels = np.sum(thresh == 255)
    prev_frame_gray = gray
    
    # Seuil : au moins 2000 pixels ont bougé
    if motion_pixels > 2000:
        log(f"🚗 Mouvement : {motion_pixels} pixels")
        return True
    
    return False

def preprocess_for_plate(frame):
    """Améliore l'image pour la lecture de plaque"""
    # Zone d'intérêt (optionnel, pour focus sur une zone)
    h, w = frame.shape[:2]
    roi = frame[int(h*0.2):int(h*0.8), int(w*0.1):int(w*0.9)]
    
    # Conversion en gris
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Égalisation d'histogramme pour gérer la luminosité
    gray = cv2.equalizeHist(gray)
    
    # Augmentation du contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    return enhanced

def clean_plate_text(text):
    """Nettoie le texte OCR"""
    cleaned = "".join(c for c in text if c.isalnum() or c == '-').upper()
    return cleaned.strip()

def is_plate_authorized(detected_text):
    """Vérifie si une plaque est dans la whitelist"""
    detected_clean = detected_text.replace(" ", "").replace("-", "").upper()
    
    for auth_plate in WHITELIST:
        auth_clean = auth_plate.replace(" ", "").replace("-", "").upper()
        
        # Correspondance exacte ou partielle
        if auth_clean in detected_clean or detected_clean in auth_clean:
            # Calcul de similarité
            len_min = min(len(auth_clean), len(detected_clean))
            len_max = max(len(auth_clean), len(detected_clean))
            
            if len_min / len_max > 0.7:  # 70% de similarité minimum
                return True, auth_plate
    
    return False, None

def send_update(plate, authorized=False):
    """Envoie l'info à Home Assistant via MQTT"""
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
    """Analyse une image pour y trouver une plaque"""
    global last_detection_time
    
    # Pré-traitement
    processed = preprocess_for_plate(frame)
    
    try:
        # OCR avec EasyOCR
        results = reader.readtext(processed, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
        
        for (bbox, text, confidence) in results:
            # Ignorer les détections peu fiables
            if confidence < 0.4:
                continue
            
            cleaned = clean_plate_text(text)
            
            # Filtrer les textes trop courts/longs
            if len(cleaned) < 5 or len(cleaned) > 12:
                continue
            
            log(f"🔍 Détecté: '{cleaned}' (confiance: {confidence:.2f})")
            
            # Vérifier si autorisé
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
    """Boucle principale : snapshot + analyse"""
    log(f"📸 URL Snapshot : {SNAPSHOT_URL}")
    log(f"⏱️  Interval : {SNAPSHOT_INTERVAL}s")
    log("🚀 Surveillance active...")
    
    consecutive_errors = 0
    max_errors = 5
    
    while True:
        # Récupération du snapshot
        frame = get_snapshot()
        
        if frame is None:
            consecutive_errors += 1
            if consecutive_errors >= max_errors:
                log(f"❌ Trop d'erreurs consécutives ({max_errors}). Vérifiez l'URL.")
            time.sleep(SNAPSHOT_INTERVAL)
            continue
        
        consecutive_errors = 0  # Reset compteur d'erreurs
        
        # Détection de mouvement
        if detect_motion(frame):
            # Analyse de la plaque
            opened = analyze_frame(frame)
            
            if opened:
                log("⏸️  Pause de 15s après ouverture...")
                time.sleep(15)
        
        # Attendre avant le prochain snapshot
        time.sleep(SNAPSHOT_INTERVAL)

if __name__ == "__main__":
    try:
        start_monitoring()
    except KeyboardInterrupt:
        log("🛑 Arrêt demandé")
    except Exception as e:
        log(f"❌ Erreur fatale : {e}")
        sys.exit(1)

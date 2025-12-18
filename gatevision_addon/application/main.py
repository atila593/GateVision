import cv2
import easyocr
import json
import time
import paho.mqtt.client as mqtt
import os
import sys
import numpy as np

def log(message):
    print(f"{message}", flush=True)

log("--- [GATEVISION V2.0 - DETECTION OPTIMISEE] ---")

# 1. Chargement des options
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
MQTT_TOPIC_SENSOR = "gatevision/last_plate"

# Initialisation EasyOCR (GPU si disponible)
log("🧠 Chargement du moteur EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False)  # Mettre True si GPU disponible
log("✅ EasyOCR prêt")

# Optimisation RTSP
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

# Variables pour détection de mouvement
prev_frame = None
motion_threshold = 1500  # Nombre de pixels qui ont bougé

def detect_motion(frame):
    """Détecte si quelque chose bouge dans l'image"""
    global prev_frame
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    
    if prev_frame is None:
        prev_frame = gray
        return False
    
    frame_delta = cv2.absdiff(prev_frame, gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    
    motion_pixels = np.sum(thresh == 255)
    prev_frame = gray
    
    return motion_pixels > motion_threshold

def preprocess_for_plate(frame):
    """Pré-traitement optimisé pour plaques d'immatriculation"""
    # Conversion en niveaux de gris
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Égalisation d'histogramme pour gérer la luminosité
    gray = cv2.equalizeHist(gray)
    
    # Débruitage léger
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    
    # Augmentation du contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    return enhanced

def clean_plate_text(text):
    """Nettoie le texte détecté"""
    # Garde seulement alphanumériques et tirets
    cleaned = "".join(c for c in text if c.isalnum() or c == '-').upper()
    # Supprime les espaces multiples
    cleaned = " ".join(cleaned.split())
    return cleaned

def send_update(plate, authorized=False):
    """Envoie les infos à Home Assistant via MQTT"""
    try:
        client = mqtt.Client()
        if MQTT_USER and MQTT_PASS:
            client.username_pw_set(MQTT_USER, MQTT_PASS)
        
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        data = {
            "plate": plate,
            "status": "Autorisé" if authorized else "Inconnu",
            "time": time.strftime("%H:%M:%S")
        }
        client.publish(MQTT_TOPIC_SENSOR, json.dumps(data), retain=True)
        
        if authorized:
            log(f"✅ AUTORISATION : {plate} → Ouverture")
            client.publish(MQTT_TOPIC_CONTROL, MQTT_PAYLOAD)
        
        client.disconnect()
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def is_plate_authorized(detected_text):
    """Vérifie si le texte contient une plaque autorisée"""
    detected_clean = detected_text.replace(" ", "").replace("-", "").upper()
    
    for auth_plate in WHITELIST:
        auth_clean = auth_plate.replace(" ", "").replace("-", "").upper()
        
        # Correspondance exacte ou partielle (au moins 85% des caractères)
        if auth_clean in detected_clean or detected_clean in auth_clean:
            similarity = len(auth_clean) / len(detected_clean) if detected_clean else 0
            if similarity > 0.7:  # Au moins 70% de similarité
                return True, auth_plate
    
    return False, None

def start_detection():
    log(f"📸 Connexion caméra : {CAMERA_URL}")
    cap = cv2.VideoCapture(CAMERA_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 15)  # Limiter à 15 FPS
    
    if not cap.isOpened():
        log("❌ Impossible de se connecter à la caméra")
        return

    log("🚀 Système actif - En attente de mouvement...")
    
    frame_count = 0
    last_detection_time = 0
    cooldown_period = 10  # Secondes entre deux détections de la même plaque
    
    while True:
        ret, frame = cap.read()
        if not ret:
            log("⚠️ Perte de connexion - Reconnexion...")
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue
        
        frame_count += 1
        
        # Analyse du mouvement toutes les 3 frames (5 fps)
        if frame_count % 3 != 0:
            continue
        
        # Détection de mouvement
        if not detect_motion(frame):
            continue
        
        log("🚗 Mouvement détecté - Analyse en cours...")
        
        # Zone d'intérêt plus large (toute la hauteur, centre horizontal)
        h, w = frame.shape[:2]
        roi = frame[0:h, int(w*0.1):int(w*0.9)]  # 80% de la largeur
        
        # Pré-traitement
        processed = preprocess_for_plate(roi)
        
        # OCR avec EasyOCR
        try:
            results = reader.readtext(processed)
            
            for (bbox, text, confidence) in results:
                if confidence < 0.3:  # Ignorer les détections peu fiables
                    continue
                
                cleaned_text = clean_plate_text(text)
                
                # Filtrer les textes trop courts ou trop longs
                if len(cleaned_text) < 4 or len(cleaned_text) > 12:
                    continue
                
                log(f"🔍 Texte détecté : {cleaned_text} (confiance: {confidence:.2f})")
                
                # Vérifier si autorisé
                authorized, matched_plate = is_plate_authorized(cleaned_text)
                
                current_time = time.time()
                if authorized and (current_time - last_detection_time) > cooldown_period:
                    send_update(matched_plate, authorized=True)
                    last_detection_time = current_time
                    time.sleep(15)  # Pause après ouverture
                    break
                elif not authorized:
                    send_update(cleaned_text, authorized=False)
        
        except Exception as e:
            log(f"❌ Erreur OCR : {e}")
        
        # Petite pause pour éviter la surcharge CPU
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        start_detection()
    except Exception as e:
        log(f"❌ Erreur fatale : {e}")
        sys.exit(1)

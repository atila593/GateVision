import cv2
import pytesseract
import json
import time
import paho.mqtt.client as mqtt
import os
import sys

def log(message):
    print(f"{message}", flush=True)

log("--- [DÉMARRAGE GATEVISION V1.2.1 - TESSERACT] ---")

# Chargement des options Home Assistant
try:
    if os.path.exists("/data/options.json"):
        with open("/data/options.json", "r") as f:
            options = json.load(f)
    else:
        log("⚠️ Fichier options.json introuvable.")
        options = {}
except Exception as e:
    log(f"❌ Erreur lecture options : {e}")
    sys.exit(1)

# Variables de configuration
CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_TOPIC = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")
MQTT_USER = options.get("mqtt_user", "")
MQTT_PASS = options.get("mqtt_password", "")
MQTT_PORT = options.get("mqtt_port", 1883)

def trigger_action(plate):
    log(f"🎯 MATCH TROUVÉ : {plate}")
    try:
        client = mqtt.Client()
        if MQTT_USER and MQTT_PASS:
            client.username_pw_set(MQTT_USER, MQTT_PASS)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.publish(MQTT_TOPIC, MQTT_PAYLOAD)
        client.disconnect()
        log(f"📡 Signal MQTT envoyé vers {MQTT_TOPIC}")
    except Exception as e:
        log(f"❌ Erreur MQTT : {e}")

def start_detection():
    if not CAMERA_URL:
        log("❌ URL Caméra vide dans la config !")
        return

    log(f"📸 Connexion caméra : {CAMERA_URL}")
    cap = cv2.VideoCapture(CAMERA_URL)
    
    # Réglage du buffer pour éviter le décalage temporel
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    log("🚀 GateVision est en ligne. Analyse en cours...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            log("⚠️ Flux perdu, tentative de reconnexion dans 5s...")
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        # On attend 2 secondes entre chaque analyse pour ne pas saturer le CPU
        time.sleep(2)

        # --- PRÉ-TRAITEMENT DE L'IMAGE ---
        # 1. Conversion en niveaux de gris
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 2. Augmentation du contraste (Seuillage d'Otsu)
        # Cela rend le fond blanc et les lettres très noires
        _, processed_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3. Lecture par Tesseract
        # psm 11 : recherche de texte partout dans l'image
        text = pytesseract.image_to_string(processed_img, config='--psm 11')
        
        # Nettoyage : on ne garde que les lettres et chiffres
        raw_plate = "".join(e for e in text if e.isalnum()).upper()

        if len(raw_plate) >= 4:
            # On vérifie si une plaque autorisée est présente dans le texte lu
            found = False
            for auth_plate in WHITELIST:
                # Nettoyage de la plaque de la whitelist (au cas où il y ait des espaces)
                clean_auth = auth_plate.replace(" ", "").replace("-", "").upper()
                
                if clean_auth in raw_plate:
                    trigger_action(clean_auth)
                    found = True
                    time.sleep(15) # Pause de 15s après ouverture
                    break
            
            if not found:
                # On log seulement si le texte n'est pas trop long (pour éviter les logs pollués)
                if len(raw_plate) < 15:
                    log(f"🔍 Texte détecté (ignoré) : {raw_plate}")

if __name__ == "__main__":
    try:
        start_detection()
    except Exception as e:
        log(f"❌ Erreur fatale : {e}")
        sys.exit(1)

import cv2
import easyocr
import json
import time
import paho.mqtt.client as mqtt
import requests
import os

# Chemin standard où Home Assistant stocke la configuration de l'addon
OPTIONS_PATH = "/data/options.json"

def load_ha_options():
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH, "r") as f:
            try:
                return json.load(f)
            except Exception as e:
                print(f"❌ Erreur lors de la lecture des options : {e}")
                return {}
    else:
        print("⚠️ Fichier d'options introuvable, utilisation de valeurs par défaut.")
        return {}

# Chargement initial des options
options = load_ha_options()

# Variables de configuration
CAMERA_URL = options.get("camera_url", "")
WHITELIST = options.get("authorized_plates", [])
METHOD = options.get("output_method", "MQTT")
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_TOPIC = options.get("mqtt_topic", "gate/control")
MQTT_PAYLOAD = options.get("mqtt_payload", "ON")
WEBHOOK_URL = options.get("webhook_url", "")

# Initialisation de l'IA (OCR)
print("📦 Chargement des modèles d'IA (EasyOCR)...")
# On utilise le CPU car la plupart des box HA n'ont pas de GPU dédié
reader = easyocr.Reader(['fr', 'en'], gpu=False)

def trigger_action(plate):
    print(f"✅ ACCÈS AUTORISÉ : {plate}")
    
    if METHOD == "MQTT":
        try:
            client = mqtt.Client()
            
            # Récupération dynamique des identifiants depuis les options
            user = options.get("mqtt_user")
            password = options.get("mqtt_password")
            port = options.get("mqtt_port", 1883)
            
            # Si un utilisateur est configuré, on s'authentifie
            if user and password:
                client.username_pw_set(user, password)
                print(f"🔑 Authentification MQTT avec l'utilisateur : {user}")
            
            client.connect(MQTT_BROKER, port, 60)
            client.publish(MQTT_TOPIC, MQTT_PAYLOAD)
            client.disconnect()
            print(f"📡 Signal MQTT envoyé sur le topic '{MQTT_TOPIC}'")
        except Exception as e:
            print(f"❌ Erreur de connexion MQTT : {e}")
            
    elif METHOD == "WEBHOOK" and WEBHOOK_URL:
        try:
            requests.get(WEBHOOK_URL, timeout=5)
            print(f"🌐 Signal Webhook envoyé vers {WEBHOOK_URL}")
        except Exception as e:
            print(f"❌ Erreur Webhook : {e}")

def start_detection():
    if not CAMERA_URL:
        print("❌ Erreur : URL de la caméra non configurée. Vérifiez l'onglet Configuration.")
        return

    print(f"🚀 GateVision est en ligne.")
    print(f"📸 Analyse du flux : {CAMERA_URL}")
    print(f"🚗 Plaques autorisées : {WHITELIST}")

    cap = cv2.VideoCapture(CAMERA_URL)
    last_trigger = 0
    
    frame_count = 0  # Ajoute un compteur
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(5)
            cap = cv2.VideoCapture(CAMERA_URL)
            continue

        frame_count += 1
        # On n'analyse qu'une image sur 10 (environ 1 analyse par seconde)
        if frame_count % 10 != 0:
            continue

        results = reader.readtext(frame)
        
        for (bbox, text, prob) in results:
            # Nettoyage de la plaque (enlève espaces, tirets et met en majuscules)
            plate = text.replace(" ", "").replace("-", "").upper()
            
            # Vérification de la correspondance avec la liste blanche (whitelist)
            if plate in WHITELIST and prob > 0.50:
                current_time = time.time()
                # Sécurité pour ne pas déclencher en boucle (30 secondes de délai)
                if current_time - last_trigger > 30:
                    trigger_action(plate)
                    last_trigger = current_time
            
            # On affiche les plaques détectées mais non autorisées dans les logs pour debug
            elif len(plate) >= 5:
                print(f"🔍 Plaque détectée mais non autorisée : {plate} (Fiabilité: {int(prob*100)}%)")

    cap.release()

if __name__ == "__main__":
    start_detection()

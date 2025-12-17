import cv2
import easyocr
import yaml
import time
import paho.mqtt.client as mqtt
import requests

# Chargement de la configuration universelle
def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

config = load_config()

# Initialisation de l'IA de lecture (OCR)
# Supporte les plaques européennes et standard
reader = easyocr.Reader(['fr', 'en'], gpu=False)

def trigger_action(plate):
    print(f"✅ ACCÈS AUTORISÉ : {plate}")
    
    # Méthode 1 : MQTT (Universel pour Home Assistant, Shelly, etc.)
    if config['output_method'] == "MQTT":
        try:
            client = mqtt.Client()
            client.connect(config['mqtt_broker'])
            client.publish(config['mqtt_topic'], config['mqtt_payload'])
            client.disconnect()
            print("📡 Signal envoyé via MQTT")
        except Exception as e:
            print(f"❌ Erreur MQTT : {e}")
            
    # Méthode 2 : Webhook (Pour Tuya via IFTTT ou API locale)
    elif config['output_method'] == "WEBHOOK":
        try:
            requests.get(config['webhook_url'], timeout=5)
            print("🌐 Signal envoyé via Webhook")
        except Exception as e:
            print(f"❌ Erreur Webhook : {e}")

def start_detection():
    cap = cv2.VideoCapture(config['camera_url'])
    last_trigger = 0
    
    print("🚀 GateVision est en ligne. Analyse du flux vidéo...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            time.sleep(5)
            continue

        # Analyse OCR sur l'image
        results = reader.readtext(frame)
        
        for (bbox, text, prob) in results:
            # Nettoyage du texte (enlève espaces et tirets)
            plate = text.replace(" ", "").replace("-", "").upper()
            
            if plate in config['authorized_plates'] and prob > 0.50:
                current_time = time.time()
                # Anti-rebond : attend 30s entre deux ouvertures
                if current_time - last_trigger > 30:
                    trigger_action(plate)
                    last_trigger = current_time

    cap.release()

if __name__ == "__main__":
    start_detection()

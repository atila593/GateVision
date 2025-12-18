import cv2
import easyocr
import time
import paho.mqtt.client as mqtt
import numpy as np
import json

# --- CONFIGURATION ---
try:
    with open("/data/options.json", "r") as f:
        options = json.load(f)
except:
    options = {}

RTSP_URL = options.get("rtsp_url", "rtsp://admin:password@192.168.1.28:554/Streaming/Channels/102")
WHITELIST = options.get("authorized_plates", [])
MQTT_BROKER = options.get("mqtt_broker", "core-mosquitto")
MQTT_TOPIC = options.get("mqtt_topic", "gate/control")

print("🧠 Chargement EasyOCR...")
reader = easyocr.Reader(['en'], gpu=False)
print("✅ Système prêt. En attente de mouvement...")

def start_monitoring():
    cap = cv2.VideoCapture(RTSP_URL)
    avg = None
    last_ocr_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            cap = cv2.VideoCapture(RTSP_URL)
            time.sleep(5)
            continue

        # 1. PRÉ-TRAITEMENT LÉGER POUR LA DÉTECTION DE MOUVEMENT
        # On réduit l'image pour que le calcul soit instantané
        small_frame = cv2.resize(frame, (500, 300))
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if avg is None:
            avg = gray.copy().astype("float")
            continue

        # On calcule la différence entre l'image actuelle et la moyenne
        cv2.accumulateWeighted(gray, avg, 0.5)
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
        thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]
        
        # 2. SI MOUVEMENT DÉTECTÉ
        if np.sum(thresh) > 5000: # Seuil de mouvement (à ajuster selon la sensibilité voulue)
            current_time = time.time()
            
            # On ne lance l'OCR que si le dernier scan date de plus de 2 secondes
            if current_time - last_ocr_time > 2:
                print("🚗 Mouvement détecté ! Analyse de la plaque...")
                
                # On lance l'OCR sur l'image haute résolution (frame originale)
                results = reader.readtext(frame)
                
                for (bbox, text, confidence) in results:
                    if confidence > 0.4:
                        cleaned = "".join(c for c in text if c.isalnum()).upper()
                        print(f"🔍 Plaque lue : {cleaned} ({int(confidence*100)}%)")
                        
                        if any(auth in cleaned for auth in WHITELIST):
                            print(f"✅ ACCÈS VALIDÉ : {cleaned}")
                            # --- ENVOI MQTT ---
                            try:
                                client = mqtt.Client()
                                client.connect(MQTT_BROKER)
                                client.publish(MQTT_TOPIC, "ON")
                                client.disconnect()
                            except: pass
                            
                last_ocr_time = current_time

        # Vider le buffer pour ne pas avoir de retard (lag)
        for _ in range(10): cap.grab()
        time.sleep(0.1)

if __name__ == "__main__":
    start_monitoring()

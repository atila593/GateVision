import appdaemon.plugins.hass.hassapi as hass
import subprocess
import sys
import os

# 1. Fonction de réparation automatique pour installer les dépendances
def install_fix():
    print("Vérification et installation des dépendances (cela peut prendre 5-10 min)...")
    packages = [
        "paho-mqtt",
        "opencv-python-headless",
        "easyocr --no-deps",
        "torch --index-url https://download.pytorch.org/whl/cpu"
    ]
    for pkg in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", pkg])
        except Exception as e:
            print(f"Erreur lors de l'installation de {pkg}: {e}")

# Tentative d'importation, sinon on lance l'installation
try:
    import easyocr
    import cv2
    import numpy as np
except ImportError:
    install_fix()
    import easyocr
    import cv2
    import numpy as np

class GateVision(hass.Hass):

    def initialize(self):
        self.log("GateVision OCR démarré.")
        # Liste des plaques VIP (modifiez-les ici)
        self.plaques_vip = ["AA123BB", "CC456DD", "GATE123"]
        
        # On écoute les changements sur l'entité de votre caméra ou un déclencheur
        # Remplacez 'binary_sensor.portail_mouvement' par votre capteur
        self.listen_state(self.analyser_plaque, "binary_sensor.portail_mouvement", new="on")
        
        # Initialisation du lecteur OCR (en mode CPU)
        self.reader = easyocr.Reader(['fr', 'en'], gpu=False, model_storage_directory='/opt/easyocr')

    def analyser_plaque(self, entity, attribute, old, new, kwargs):
        self.log("Mouvement détecté, capture de l'image...")
        
        # 2. Capture de l'image depuis Home Assistant
        # Remplacez 'camera.votre_camera' par votre entité caméra
        image_path = "/tmp/snapshot.jpg"
        self.call_service("camera/snapshot", entity_id="camera.votre_camera", filename=image_path)
        
        # Attendre un court instant pour que le fichier soit écrit
        import time
        time.sleep(1)

        if os.path.exists(image_path):
            results = self.reader.readtext(image_path)
            self.log(f"Résultats OCR : {results}")

            for (bbox, text, prob) in results:
                plaque = text.replace(" ", "").upper()
                self.log(f"Plaque détectée : {plaque} (Certitude: {prob})")

                if plaque in self.plaques_vip:
                    self.log(f"ACCÈS ACCORDÉ pour la plaque : {plaque}")
                    # 3. Action : Ouvrir le portail
                    self.turn_on("switch.portail")
                    self.notify(f"Portail ouvert pour {plaque}", title="GateVision")
                    break
        else:
            self.log("Erreur : Impossible de trouver la capture image.")

FROM python:3.9-slim

# 1. Installation des dépendances système indispensables pour l'IA et OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Définition du dossier de travail
WORKDIR /app

# 3. Installation des bibliothèques Python (on le fait avant de copier le code pour gagner du temps)
RUN pip install --no-cache-dir \
    opencv-python-headless \
    easyocr \
    paho-mqtt \
    requests

# 4. Copie de tout le contenu du dossier gatevision_addon vers /app
# Cela va créer /app/application/main.py à l'intérieur de l'addon
COPY . .

# 5. Lancement du script avec le chemin EXACT
# Le "-u" permet de voir les logs en temps réel dans Home Assistant
CMD [ "python3", "-u", "application/main.py" ]

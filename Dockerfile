FROM python:3.9-slim

# Installation des dépendances pour le traitement d'image
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installation des bibliothèques nécessaires
RUN pip install --no-cache-dir \
    opencv-python-headless \
    easyocr \
    pyyaml \
    paho-mqtt \
    requests

COPY . .

# Lancement du script dans le dossier 'application'
CMD [ "python", "app/main.py" ]

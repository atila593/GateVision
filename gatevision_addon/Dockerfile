FROM python:3.9-slim

# Installation des dépendances système mises à jour
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installation des bibliothèques Python
RUN pip install --no-cache-dir \
    opencv-python-headless \
    easyocr \
    pyyaml \
    paho-mqtt \
    requests

COPY . .

# Lancement du script
CMD [ "python3", "-u", "main.py" ]

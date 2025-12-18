ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18
FROM ${BUILD_FROM}

# Installation des dépendances système pour OpenCV et la compilation
RUN apk add --no-cache \
    ffmpeg \
    libjpeg-turbo \
    libpng \
    tiff \
    openblas \
    libstdc++ \
    g++ \
    make \
    python3-dev

# Installation des bibliothèques Python
RUN pip3 install --no-cache-dir \
    opencv-python-headless \
    easyocr \
    paho-mqtt \
    numpy

# Copie du script vers l'addon
COPY application/gatevision.py /gatevision.py

# Commande de lancement (remplace le run.sh)
CMD [ "python3", "/gatevision.py" ]

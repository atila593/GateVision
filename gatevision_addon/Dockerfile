ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Installation des dépendances système et de Python + Pip
RUN apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    libjpeg-turbo \
    libpng \
    tiff \
    openblas \
    libstdc++ \
    g++ \
    make \
    python3-dev

# 2. Installation des bibliothèques Python
# On utilise "python3 -m pip" pour être sûr de pointer vers le bon binaire
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install --no-cache-dir \
    opencv-python-headless \
    easyocr \
    paho-mqtt \
    numpy

# 3. Copie du script (depuis le dossier application)
COPY application/gatevision.py /gatevision.py

# 4. Commande de lancement
CMD [ "python3", "/gatevision.py" ]

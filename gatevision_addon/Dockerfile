ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Installation des dépendances système
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
    python3-dev \
    zlib-dev \
    jpeg-dev

# 2. Installation des bibliothèques Python
# On ajoute --break-system-packages pour autoriser l'installation dans l'image
RUN python3 -m pip install --no-cache-dir --break-system-packages --upgrade pip && \
    python3 -m pip install --no-cache-dir --break-system-packages \
    opencv-python-headless \
    easyocr \
    paho-mqtt \
    numpy

# 3. Copie du script
COPY application/gatevision.py /gatevision.py

# 4. Commande de lancement
CMD [ "python3", "/gatevision.py" ]

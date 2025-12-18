# On part d'une image qui a déjà Python et les outils de build configurés
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

# 1. Installation des dépendances système nécessaires à OpenCV/EasyOCR
RUN apk add --no-cache \
    ffmpeg \
    libjpeg-turbo \
    libpng \
    openblas \
    libstdc++ \
    glib

# 2. Script d'installation forcé
# On installe tout en une fois pour éviter les conflits de cache
RUN pip install --no-cache-dir --break-system-packages \
    numpy==1.26.4 \
    opencv-python-headless==4.10.0.84 \
    paho-mqtt

# 3. Installation de Torch & EasyOCR
# On utilise le flag --no-cache-dir pour éviter de saturer la mémoire de HA
RUN pip install --no-cache-dir --break-system-packages \
    torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --break-system-packages \
    easyocr

# 4. Préparation des dossiers pour les modèles de langue
RUN mkdir -p /config/easyocr && chmod 777 /config/easyocr
ENV EASYOCR_CACHE_DIR=/config/easyocr

# 5. Lancement
COPY application/gatevision.py /gatevision.py
CMD ["python3", "/gatevision.py"]

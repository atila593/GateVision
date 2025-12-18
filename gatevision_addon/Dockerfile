# Utilisation de l'image Python optimisée pour HA sur amd64
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12
FROM ${BUILD_FROM}

# 1. Installation des dépendances système pour OpenCV et le décodage vidéo
RUN apk add --no-cache \
    ffmpeg \
    libjpeg-turbo \
    libpng \
    tiff \
    openblas \
    libstdc++ \
    g++ \
    make \
    zlib-dev \
    jpeg-dev \
    musl-dev \
    linux-headers

# 2. Installation des outils de build et correction du bug setuptools
# Note: Pip est déjà présent dans cette image de base
RUN pip install --no-cache-dir --break-system-packages setuptools==70.0.0 wheel

# 3. Installation d'OpenCV (version headless pour économiser de la place)
RUN pip install --no-cache-dir --break-system-packages opencv-python-headless

# 4. Installation de EasyOCR et ses dépendances
RUN pip install --no-cache-dir --break-system-packages easyocr paho-mqtt numpy

# 5. Copie du script depuis ton dossier application
COPY application/gatevision.py /gatevision.py

# 6. Commande de lancement
CMD [ "python3", "/gatevision.py" ]

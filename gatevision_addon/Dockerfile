ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

# 1. Installation des dépendances système critiques
RUN apk add --no-cache \
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
    jpeg-dev \
    musl-dev \
    linux-headers

# 2. Mise à jour des outils de build (Correction du bug bdist_wheel)
# On installe setuptools et wheel AVANT le reste
RUN python3 -m pip install --no-cache-dir --break-system-packages --upgrade pip setuptools==70.0.0 wheel

# 3. Installation des bibliothèques lourdes
# On sépare pour mieux voir où ça bloque si besoin
RUN python3 -m pip install --no-cache-dir --break-system-packages opencv-python-headless
RUN python3 -m pip install --no-cache-dir --break-system-packages easyocr
RUN python3 -m pip install --no-cache-dir --break-system-packages paho-mqtt numpy

# 4. Copie du script
COPY application/gatevision.py /gatevision.py

# 5. Lancement
CMD [ "python3", "/gatevision.py" ]

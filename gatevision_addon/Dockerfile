ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Installation des paquets via APK (Alpine)
# On inclut py3-pip explicitement
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
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

# 2. Installation de Pip et des outils de build
# On utilise 'python3 -m pip' pour contourner le problème du "not found"
RUN python3 -m pip install --upgrade pip --break-system-packages
RUN python3 -m pip install --no-cache-dir --break-system-packages setuptools==70.0.0 wheel

# 3. Installation d'OpenCV et EasyOCR
# Cette étape est longue, c'est normal
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    opencv-python-headless \
    easyocr \
    paho-mqtt \
    numpy

# 4. Copie du script
COPY application/gatevision.py /gatevision.py

# 5. Lancement
CMD [ "python3", "/gatevision.py" ]

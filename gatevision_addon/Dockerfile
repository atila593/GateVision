ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Installation des paquets PRÉ-COMPILÉS via Alpine (APK)
# On installe OpenCV et Numpy ici pour éviter que Pip ne tente de les compiler
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-numpy \
    py3-opencv \
    ffmpeg \
    libjpeg-turbo \
    libpng \
    tiff \
    openblas \
    libstdc++

# 2. Mise à jour de Pip
RUN python3 -m pip install --upgrade pip --break-system-packages

# 3. Installation de EasyOCR et MQTT
# Comme OpenCV et Numpy sont déjà là via APK, Pip va les détecter et passer à la suite
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    easyocr \
    paho-mqtt

# 4. Finalisation
COPY application/gatevision.py /gatevision.py
CMD [ "python3", "/gatevision.py" ]

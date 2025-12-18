ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Dépendances système minimales
RUN apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    libjpeg-turbo \
    libpng \
    tiff \
    openblas \
    libstdc++ \
    zlib \
    jpeg

# 2. On installe les bibliothèques une par une
# On force des versions stables pour éviter les conflits de build récents
RUN python3 -m pip install --upgrade pip --break-system-packages

# On installe numpy en premier (souvent requis par les autres)
RUN python3 -m pip install --no-cache-dir --break-system-packages numpy

# 3. INSTALLATION D'OPENCV (La partie critique)
# On utilise la version pré-compilée si possible ou on force une version compatible
RUN python3 -m pip install --no-cache-dir --break-system-packages opencv-python-headless==4.10.0.84

# 4. INSTALLATION DE EASYOCR
RUN python3 -m pip install --no-cache-dir --break-system-packages easyocr paho-mqtt

# 5. Finalisation
COPY application/gatevision.py /gatevision.py
CMD [ "python3", "/gatevision.py" ]

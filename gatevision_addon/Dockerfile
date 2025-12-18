ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Installation de TOUT le nécessaire via APK (pré-compilé)
# On inclut py3-opencv et py3-numpy ici pour éviter que Pip n'essaie de les compiler
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-numpy \
    py3-opencv \
    py3-pillow \
    py3-scipy \
    ffmpeg \
    libstdc++ \
    openblas

# 2. On s'assure que Pip est à jour
RUN python3 -m pip install --upgrade pip --break-system-packages

# 3. Installation de Torch (CPU) et Paho-MQTT
# On ne réinstalle PAS numpy ou opencv ici
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    paho-mqtt \
    torch --index-url https://download.pytorch.org/whl/cpu

# 4. Installation de EasyOCR avec --no-deps 
# On utilise --no-deps pour éviter que EasyOCR ne tente de remplacer 
# nos versions APK d'OpenCV/Numpy par des versions Pip qui casseraient tout.
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    easyocr --no-deps \
    python-bidi \
    pyclipper \
    shapely \
    ninja

# 5. Configuration et Lancement
ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_HOME=/opt/torch
ENV EASYOCR_CACHE_DIR=/opt/easyocr
RUN mkdir -p /opt/torch /opt/easyocr && chmod 777 /opt/torch /opt/easyocr

COPY application/gatevision.py /gatevision.py
CMD ["python3", "/gatevision.py"]

# Utilisation du tag 'latest' qui contient Python 3.12 (standard actuel sur HA)
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Installation des paquets système PRÉ-COMPILÉS (Très important pour OpenCV)
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

# 2. Configuration des variables d'environnement
ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_HOME=/opt/torch
ENV EASYOCR_CACHE_DIR=/opt/easyocr

# 3. Installation de PyTorch et EasyOCR
# On installe 'torch' et 'torchvision' séparément car ils sont très lourds
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    torch --index-url https://download.pytorch.org/whl/cpu \
    torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Installation de EasyOCR sans réinstaller Numpy/OpenCV
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    easyocr \
    paho-mqtt

# 5. Finalisation
COPY application/gatevision.py /gatevision.py
CMD ["python3", "/gatevision.py"]

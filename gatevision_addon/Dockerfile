# Utilisation de la base Debian pour éviter le bug Alpine/OpenCV
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Installation des dépendances via APT (Debian)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Configuration environnement
ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_HOME=/opt/torch
ENV EASYOCR_CACHE_DIR=/opt/easyocr

# 3. Installation des paquets Python
# On utilise --break-system-packages car c'est requis dans les conteneurs HA
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    numpy \
    opencv-python-headless \
    paho-mqtt

# 4. Installation de Torch (CPU uniquement pour la légèreté)
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 5. Installation de EasyOCR
RUN python3 -m pip install --no-cache-dir --break-system-packages easyocr

# 6. Copie et lancement
COPY application/gatevision.py /gatevision.py
CMD ["python3", "/gatevision.py"]

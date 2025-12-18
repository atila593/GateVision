ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# -----------------------------
# 1. Dépendances système
# -----------------------------
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

# -----------------------------
# 2. Forcer CPU / chemins cache
# -----------------------------
ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_HOME=/opt/torch
ENV EASYOCR_MODULE_PATH=/opt/easyocr
ENV EASYOCR_CACHE_DIR=/opt/easyocr

# -----------------------------
# 3. Installer TORCH (obligatoire AVANT EasyOCR)
# ⚠️ Wheels Home Assistant musllinux
# -----------------------------
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    torch \
    torchvision

# -----------------------------
# 4. Installer EasyOCR SANS dépendances
# -----------------------------
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    easyocr --no-deps \
    paho-mqtt

# -----------------------------
# 5. Pré-téléchargement modèles OCR (CPU)
# -----------------------------
RUN python3 - << 'EOF'
import easyocr
easyocr.Reader(['en'], gpu=False)
EOF

# -----------------------------
# 6. Application
# -----------------------------
COPY application/gatevision.py /gatevision.py
CMD ["python3", "/gatevision.py"]


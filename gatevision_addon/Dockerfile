ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# -----------------------------
# 1. Installer Python 3.11 explicitement
# -----------------------------
RUN apk add --no-cache \
    python3=3.11.* \
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
# 2. Variables CPU only
# -----------------------------
ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_HOME=/opt/torch
ENV EASYOCR_MODULE_PATH=/opt/easyocr
ENV EASYOCR_CACHE_DIR=/opt/easyocr

# -----------------------------
# 3. Torch (wheels Home Assistant)
# -----------------------------
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    torch \
    torchvision

# -----------------------------
# 4. EasyOCR sans deps
# -----------------------------
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    easyocr --no-deps \
    paho-mqtt

# -----------------------------
# 5. Préchargement modèles OCR
# -----------------------------
RUN python3 - << 'EOF'
import easyocr
easyocr.Reader(['fr'], gpu=False)
EOF

# -----------------------------
# 6. App
# -----------------------------
COPY application/gatevision.py /gatevision.py
CMD ["python3", "/gatevision.py"]



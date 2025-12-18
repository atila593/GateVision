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
# 2. Variables OCR / CPU
# -----------------------------
ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_HOME=/opt/torch
ENV EASYOCR_MODULE_PATH=/opt/easyocr
ENV EASYOCR_CACHE_DIR=/opt/easyocr

# -----------------------------
# 3. Dépendances Python
# ⚠️ pip NON upgradé (bug Alpine)
# -----------------------------
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    easyocr \
    paho-mqtt

# -----------------------------
# 4. Pré-téléchargement modèles EasyOCR (CPU)
# ⚠️ Adapter les langues si besoin
# -----------------------------
RUN python3 - << 'EOF'
import easyocr
easyocr.Reader(
    ['en'],        # 👉 mets ['fr'] ou ['en','fr'] si besoin
    gpu=False
)
EOF

# -----------------------------
# 5. Application
# -----------------------------
COPY application/gatevision.py /gatevision.py

CMD ["python3", "/gatevision.py"]


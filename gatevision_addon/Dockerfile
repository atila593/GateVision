ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Installation des outils de build et dépendances système
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    g++ \
    make \
    musl-dev \
    linux-headers \
    ffmpeg \
    openblas-dev \
    libjpeg-turbo-dev \
    libpng-dev

# 2. Nettoyage préventif du bug de version Alpine
# On force pip à ignorer les versions déclarées par Alpine qui sont mal formatées
RUN rm -rf /usr/lib/python3.12/site-packages/opencv* \
    && rm -rf /usr/lib/python3.12/site-packages/numpy*

# 3. Installation des paquets Python (CPU Only)
# On installe tout via Pip pour avoir des versions cohérentes entre elles
RUN python3 -m pip install --upgrade pip --break-system-packages \
    && python3 -m pip install --no-cache-dir --break-system-packages \
    numpy==1.26.4 \
    opencv-python-headless==4.10.0.84 \
    paho-mqtt

# 4. Installation de Torch et EasyOCR
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && python3 -m pip install --no-cache-dir --break-system-packages \
    easyocr

# 5. Finalisation
COPY application/gatevision.py /gatevision.py

# On crée les répertoires pour éviter des erreurs de permission au lancement
RUN mkdir -p /opt/torch /opt/easyocr && chmod 777 /opt/torch /opt/easyocr

ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_HOME=/opt/torch
ENV EASYOCR_CACHE_DIR=/opt/easyocr

CMD ["python3", "/gatevision.py"]

ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Installation de Python et des dépendances système via APT (Debian)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    gcc \
    g++ \
    make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Correction des outils de build
# On utilise "python3 -m pip" car c'est la méthode la plus sûre
RUN python3 -m pip install --upgrade pip --break-system-packages
RUN python3 -m pip install --no-cache-dir --break-system-packages setuptools==70.0.0 wheel

# 3. Installation des bibliothèques Python
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    opencv-python-headless \
    easyocr \
    paho-mqtt \
    numpy

# 4. Copie du script
COPY application/gatevision.py /gatevision.py

# 5. Lancement
CMD [ "python3", "/gatevision.py" ]

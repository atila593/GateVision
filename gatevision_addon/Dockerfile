FROM python:3.9-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installation des bibliothèques Python
RUN pip install --no-cache-dir \
    opencv-python-headless==4.8.0.76 \
    Pillow==9.5.0 \
    easyocr==1.7.0 \
    paho-mqtt==1.6.1 \
    requests==2.31.0 \
    numpy==1.24.3

COPY . .

CMD [ "python3", "-u", "application/main.py" ]

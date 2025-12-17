FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    opencv-python-headless \
    easyocr \
    pyyaml \
    paho-mqtt \
    requests

COPY . .

# Chemin vers le script main.py
CMD [ "python", "app/main.py" ]

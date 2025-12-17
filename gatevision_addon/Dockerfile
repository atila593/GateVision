FROM python:3.9-slim

# Installation de Tesseract et des dépendances
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 tesseract-ocr tesseract-ocr-fra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    opencv-python-headless \
    pytesseract \
    paho-mqtt \
    requests

COPY . .

CMD [ "python3", "-u", "application/main.py" ]

FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    opencv-python-headless \
    easyocr \
    paho-mqtt \
    requests

# --- CETTE LIGNE EST LA CLÉ ---
# On télécharge les modèles d'IA pendant la construction de l'image
RUN python3 -c "import easyocr; reader = easyocr.Reader(['fr', 'en'], gpu=False)"

COPY . .

CMD [ "python3", "-u", "application/main.py" ]

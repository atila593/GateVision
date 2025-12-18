FROM ghcr.io/home-assistant/amd64-base:python3.11

RUN apk add --no-cache \
    py3-pip \
    py3-numpy \
    py3-opencv \
    ffmpeg \
    libjpeg-turbo \
    libpng \
    tiff \
    openblas \
    libstdc++

ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_HOME=/opt/torch
ENV EASYOCR_CACHE_DIR=/opt/easyocr

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    torch \
    torchvision

RUN python3 -m pip install --no-cache-dir --break-system-packages \
    easyocr --no-deps \
    paho-mqtt

COPY application/gatevision.py /gatevision.py
CMD ["python3", "/gatevision.py"]


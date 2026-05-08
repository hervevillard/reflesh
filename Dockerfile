# ArtSegment — GPU-accelerated desktop app for artist image segmentation
# Base: PyTorch + CUDA 12.6 (SAM3 minimum). Update tag as new images are released.
# SAM3 requires torch>=2.7 and CUDA>=12.6.
FROM pytorch/pytorch:2.7.0-cuda12.6-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    QT_X11_NO_MITSHM=1 \
    DISPLAY=:0 \
    # Suppress HuggingFace symlinks warning (irrelevant inside containers)
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

# System libraries required by PyQt6 / xcb platform plugin
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1 \
    libglib2.0-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libx11-xcb1 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (layer cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install SAM3 from GitHub
RUN pip install --no-cache-dir git+https://github.com/facebookresearch/sam3.git

# Copy application source
COPY . .

# SAM3 weights are downloaded from HuggingFace at runtime (first Analyze click).
# Mount ~/.cache/huggingface via docker-compose to persist across container runs.
# Authentication: set HF_TOKEN env var or run `huggingface-cli login` inside container.

CMD ["python", "main.py"]

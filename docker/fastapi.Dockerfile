FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    pkg-config \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install latest Rust
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt ./

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy your app
COPY backendcode/ ./backendcode/

# Default command (change as needed)
CMD sh -c "uvicorn backendcode.API:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000}"

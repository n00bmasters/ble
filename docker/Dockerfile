# Use official Python slim image
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr (good for logs)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install build deps for some pip packages (if needed)
# NOTE: keep the list minimal. Add 'build-essential' only if you compile C extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app user (non-root) and working dir
RUN useradd --create-home appuser
WORKDIR /home/appuser/app
COPY --chown=appuser:appuser . /home/appuser/app

USER appuser

# Install python dependencies. Put requirements COPY before copying app code for caching.
# (If you want to benefit from cache, COPY requirements first)
# If you copied everything earlier, it's still fine; see "cache-optimized" variant below.
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]


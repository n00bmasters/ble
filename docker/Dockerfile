FROM python:3.11-slim

RUN useradd -m appuser

WORKDIR /opt

RUN apt-get update && apt-get install -y git \
 && git clone https://github.com/n00bmasters/ble \
 && cd ble \
 && git checkout -b backend\
 && git pull origin backend\
 && chown -R appuser:appuser /opt/ble \
 && rm -rf /var/lib/apt/lists/*

USER appuser
WORKDIR /opt/ble

# continue with pip installs etc
#COPY --chown=appuser:appuser requirements.txt /opt/ble/
RUN pip install --upgrade pip wheel
RUN pip install --no-cache-dir -r src/requirements.txt

CMD ["python", "src/app.py"]


FROM python:3.11-slim

# Arbeitsverzeichnis erstellen
WORKDIR /app

# System-Dependencies installieren
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Python-Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode kopieren
COPY ntrip_client.py .

# Verzeichnisse für Logs und Config erstellen
RUN mkdir -p /app/logs /app/config

# Script ausführbar machen
RUN chmod +x ntrip_client.py

# Hauptprogramm starten
CMD ["python3", "-u", "ntrip_client.py"]

# Quick Start Guide

## Schnellstart für mosaic-H NTRIP Client

### 1. Vorbereitung

```bash
# In das Projektverzeichnis wechseln
cd /pfad/zu/mosaikHntripoveruartp2p

# .env Datei erstellen
cp .env.example .env
```

### 2. Konfiguration anpassen

Bearbeite die `.env` Datei mit deinen NTRIP-Zugangsdaten:

```bash
nano .env
```

Mindestens diese Werte anpassen:
- `NTRIP_CASTER` - Hostname deines NTRIP-Casters
- `NTRIP_USERNAME` - Dein Benutzername
- `NTRIP_PASSWORD` - Dein Passwort
- `NTRIP_MOUNTPOINT` - Der Mountpoint für deine Region
- `UART_DEVICE` - Dein USB-TTL Device (meist `/dev/ttyUSB0`)

### 3. Erstkonfiguration des mosaic-H (einmalig)

Setze in der `.env`:
```env
OPERATION_MODE=config
```

Starte den Container:
```bash
docker-compose up
```

Der Container konfiguriert das mosaic-H und beendet sich automatisch.

### 4. Normalbetrieb starten

Setze in der `.env`:
```env
OPERATION_MODE=stream
```

Starte den Container dauerhaft:
```bash
docker-compose up -d
```

### 5. Status überwachen

```bash
# Logs anzeigen
docker-compose logs -f

# Container Status
docker-compose ps
```

### 6. Stoppen

```bash
docker-compose down
```

## Häufige Befehle

```bash
# Container neu bauen nach Änderungen
docker-compose build

# Container neu starten
docker-compose restart

# Container stoppen
docker-compose stop

# Container starten
docker-compose start

# Alle Logs löschen und neu starten
rm -rf logs/*
docker-compose restart
```

## Fehlerbehebung Express

**Container startet nicht:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

**Keine UART-Verbindung:**
```bash
ls -l /dev/ttyUSB*
sudo usermod -a -G dialout $USER
# Neu einloggen!
```

**Keine NTRIP-Verbindung:**
```bash
ping your-ntrip-caster.com
# Zugangsdaten in .env prüfen
```

Mehr Details im [README.md](README.md)

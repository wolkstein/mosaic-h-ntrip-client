# mosaic-H NTRIP Docker Client

Docker-Container-Lösung zur Verbindung eines **mosaic-H GNSS-Moduls** über UART mit einem **NTRIP-Caster** für RTK-Korrekturdaten.

## 🎯 Funktionen

1. **Konfigurationsmodus**: Konfiguriert das mosaic-H Modul über UART-Befehle für NTRIP
2. **Stream-Modus**: Empfängt kontinuierlich RTCM-Korrekturdaten vom NTRIP-Caster und leitet sie über UART an das mosaic-H weiter

## 📋 Systemvoraussetzungen

- **Companion Computer** mit Docker und Docker Compose installiert
- **mosaic-H GNSS-Modul** verbunden über USB-TTL-Adapter (z.B. `/dev/ttyUSB0`)
- **Internet-Verbindung** über Ethernet
- **NTRIP-Caster Zugangsdaten** (Host, Port, Username, Password, Mountpoint)

## 🏗️ Architektur

```
Internet (NTRIP Caster)
         ↓
    Ethernet Port
         ↓
  Companion Computer
    (Docker Container)
         ↓
   USB-TTL Adapter
         ↓
   mosaic-H GNSS Modul
```

## 🚀 Installation & Konfiguration

### 1. Repository klonen oder Dateien kopieren

```bash
cd ~
mkdir mosaic-ntrip
cd mosaic-ntrip
# Kopiere alle Projektdateien hierher
```

### 2. Umgebungsvariablen konfigurieren

Kopiere die Beispiel-Datei und passe sie an:

```bash
cp .env.example .env
nano .env
```

Trage deine NTRIP-Zugangsdaten ein:

```env
# NTRIP Caster Verbindungsparameter
NTRIP_CASTER=ntrip.example.com
NTRIP_PORT=2101
NTRIP_USERNAME=your_username
NTRIP_PASSWORD=your_password
NTRIP_MOUNTPOINT=MOUNT1

# UART Konfiguration
UART_DEVICE=/dev/ttyUSB0
UART_BAUDRATE=115200

# Betriebsmodus
OPERATION_MODE=stream
```

### 3. UART-Device ermitteln

Finde heraus, welches Device dein USB-TTL-Adapter verwendet:

```bash
# Empfohlen: Persistente Device-ID verwenden
ls -la /dev/serial/by-id/

# Beispiel Output:
# usb-Third_Element_Aviation_GmbH_3EA_USB_Mavlink_Emulator_0015871702-if00

# Alternative: Standard Device-Namen (können sich ändern)
ls /dev/ttyUSB*
ls /dev/ttyACM*

# Detaillierte Info
dmesg | grep tty
udevadm info /dev/ttyUSB0
```

**Empfehlung:** Verwende `/dev/serial/by-id/...` statt `/dev/ttyUSB0`, da sich die Nummer nach einem Neustart oder beim Umstecken ändern kann!

Typische Pfade:
- By-ID (empfohlen): `/dev/serial/by-id/usb-FTDI_...`
- Standard: `/dev/ttyUSB0`, `/dev/ttyACM0`

### 4. Container bauen und starten

```bash
# Container bauen
docker-compose build

# Container im Vordergrund starten (für Tests)
docker-compose up

# Container im Hintergrund starten (Produktivbetrieb)
docker-compose up -d
```

## 🔧 Betriebsmodi

### Stream-Modus (Standard)

Leitet kontinuierlich RTCM-Korrekturdaten vom NTRIP-Caster an das mosaic-H Modul weiter.

```env
OPERATION_MODE=stream
```

**Verwendung:**
- Normaler Betrieb für RTK-Positionierung
- Container läuft dauerhaft
- Automatische Reconnect-Funktion bei Verbindungsabbruch

### Konfigurations-Modus

Konfiguriert das mosaic-H Modul einmalig und beendet sich dann.

```env
OPERATION_MODE=config
```

**Verwendung:**
- Erstmalige Einrichtung des mosaic-H
- Änderung der NTRIP-Einstellungen im Modul
- Container beendet sich nach erfolgreicher Konfiguration

**Zusätzliche Parameter für Config-Modus:**

```env
MOSAIC_NTRIP_MODE=Client          # Client oder Server
MOSAIC_NTRIP_CONNECTION=NTR1       # NTR1, NTR2, NTR3
MOSAIC_NTRIP_VERSION=v2            # v1, v2, auto
MOSAIC_SEND_GGA=auto               # off, sec1, sec5, sec10, sec60, auto
```

## 📊 Logs überwachen

```bash
# Live-Logs anzeigen
docker-compose logs -f

# Letzte 100 Zeilen
docker-compose logs --tail=100

# Log-Datei direkt anschauen
tail -f logs/ntrip_client.log
```

## 🛠️ Troubleshooting

### UART-Device nicht gefunden

```bash
# Berechtigungen prüfen
ls -l /dev/ttyUSB0

# Benutzer zur dialout-Gruppe hinzufügen (falls nötig)
sudo usermod -a -G dialout $USER

# System neu starten oder neu einloggen
```

### Keine Verbindung zum NTRIP-Caster

- Überprüfe Internet-Verbindung: `ping ntrip.example.com`
- Überprüfe Zugangsdaten in `.env`
- Überprüfe Firewall-Einstellungen
- Teste manuell mit einem NTRIP-Client (z.B. RTKLIB)

### mosaic-H reagiert nicht

```bash
# Teste UART-Kommunikation manuell
screen /dev/ttyUSB0 115200

# Oder mit minicom
minicom -D /dev/ttyUSB0 -b 115200

# Im Terminal Kommandos senden:
# getNTRIPSettings,NTR1
```

### Container startet nicht

```bash
# Container-Status prüfen
docker-compose ps

# Detaillierte Fehler anzeigen
docker-compose logs

# Container neu bauen
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## 📝 Wichtige mosaic-H Kommandos

### NTRIP Client konfigurieren

```
setNTRIPSettings,NTR1,Client,ntrip.example.com,2101,USER,PASSWD,MOUNT1
```

### NTRIP Einstellungen abfragen

```
getNTRIPSettings,NTR1
```

### NTRIP Verbindung schließen

```
setNTRIPSettings,NTR1,off
```

### Status abfragen

```
# NTRIP Client Status
getNTRIPClientStatus

# Allgemeiner Receiver Status
getReceiverStatus
```

## 🔄 Automatischer Start beim Booten

```bash
# Docker-Compose als systemd Service einrichten
sudo nano /etc/systemd/system/mosaic-ntrip.service
```

Inhalt:

```ini
[Unit]
Description=mosaic-H NTRIP Client
Requires=docker.service
After=docker.service

[Service]
Type=simple
WorkingDirectory=/home/pi/mosaic-ntrip
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Service aktivieren:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mosaic-ntrip.service
sudo systemctl start mosaic-ntrip.service

# Status prüfen
sudo systemctl status mosaic-ntrip.service
```

## 📂 Projektstruktur

```
mosaic-ntrip/
├── docker-compose.yml      # Docker Compose Konfiguration
├── Dockerfile              # Container-Image Definition
├── ntrip_client.py        # Hauptprogramm (Python)
├── requirements.txt       # Python-Abhängigkeiten
├── .env.example          # Beispiel-Umgebungsvariablen
├── .env                  # Ihre Konfiguration (nicht versioniert)
├── config/               # Zusätzliche Konfigurationsdateien
├── logs/                 # Log-Dateien
│   └── ntrip_client.log
└── README.md             # Diese Datei
```

## 🔐 Sicherheitshinweise

- Die `.env`-Datei enthält sensitive Zugangsdaten
- Füge `.env` zur `.gitignore` hinzu
- Verwende starke Passwörter für NTRIP-Zugang
- Beschränke Netzwerkzugriff auf notwendige Ports

## 📖 Weiterführende Informationen

- [mosaic-H Reference Guide](mosaic-H-Firmware-v4.14.10-Reference-Guide.txt)
- [NTRIP Protocol Specification](https://www.igs.org/rts/ntrip/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🤝 Support

Bei Problemen oder Fragen:

1. Überprüfe die Logs: `docker-compose logs -f`
2. Teste UART-Verbindung manuell
3. Überprüfe NTRIP-Caster Erreichbarkeit
4. Konsultiere das mosaic-H Reference Guide

## 📄 Lizenz

Dieses Projekt ist für den internen Gebrauch bestimmt.

---

**Hinweis:** Dieses System wurde für den Betrieb auf einem Companion Computer entwickelt, der über einen USB-TTL-Adapter mit einem mosaic-H GNSS-Modul verbunden ist.

# Development Notes - mosaic-H NTRIP Docker Client

## Session vom 17. November 2025

### 🎯 Projektziel
Docker-Container-System für mosaic-H GNSS-Modul zur Verbindung mit NTRIP-Caster über UART (USB-TTL-Adapter).

---

## 📋 Was wurde erstellt

### 1. Hauptkomponenten
- **docker-compose.yml** - Container-Orchestrierung mit allen Parametern
- **Dockerfile** - Python 3.11-slim mit pyserial
- **ntrip_client.py** - Hauptanwendung mit zwei Modi:
  - **Config-Modus**: Konfiguriert mosaic-H über UART-Befehle
  - **Stream-Modus**: Leitet RTCM-Daten vom NTRIP-Caster an mosaic-H weiter
- **requirements.txt** - Python-Dependencies (pyserial==3.5)
- **.env** - Aktuelle Konfiguration (mit Device-ID)
- **.env.example** - Konfigurationsvorlage

### 2. Dokumentation
- **README.md** - Ausführliche Anleitung mit Troubleshooting
- **QUICKSTART.md** - Schnellstartanleitung
- **.gitignore** - Git-Konfiguration

### 3. Verzeichnisstruktur
```
mosaikHntripoveruartp2p/
├── docker-compose.yml
├── Dockerfile
├── ntrip_client.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
├── QUICKSTART.md
├── config/
├── logs/
└── docs/
    ├── mosaic-H-Firmware-v4.14.10-Reference-Guide.txt
    └── mosaic-H-Firmware-v4.14.10-Reference-Guide.pdf (zu verschieben)
```

---

## 🔧 Technische Entscheidungen

### Architektur-Ansatz
**Entschieden für: Python NTRIP Client auf Companion Computer**

```
Internet (NTRIP Caster)
    ↓
Companion Computer (Python Docker Container)
    ↓ RTCM-Daten via UART
mosaic-H GNSS Modul (empfängt & verarbeitet)
```

**Verworfener Ansatz:** Point-to-Point Protocol (P2PP)
- Wäre komplexer (PPP-Daemon, IP-Routing)
- Keine Latenz-Vorteile (gleiche UART-Baudrate)
- Mehr Fehlerquellen
- Schwierigeres Debugging

**Begründung:**
- RTCM-Updates kommen nur alle 1-5 Sekunden
- 50-100ms Latenz ist vernachlässigbar
- Direktes RTCM-Forwarding ist sogar schneller als P2PP
- Einfachere Implementierung und Wartung

### UART Device-Pfad
**Entschieden für: `/dev/serial/by-id/`**

Aktuelles Device:
```
/dev/serial/by-id/usb-Third_Element_Aviation_GmbH_3EA_USB_Mavlink_Emulator_0015871702-if00
```

**Vorteile:**
- Persistente Zuordnung (überlebt Neustarts)
- Unabhängig vom USB-Port
- Kein Durcheinander bei mehreren USB-Geräten

### Authentifizierung
**Optional implementiert:**
- mosaic-H hat standardmäßig "anonymous" Zugriff aktiviert
- Login-Funktion wurde als optionales Feature eingebaut
- Parameter: `MOSAIC_USERNAME` und `MOSAIC_PASSWORD`
- Wird nur verwendet, wenn gesetzt (sonst anonymous access)

---

## ⚙️ mosaic-H Konfiguration

### Was im mosaic-H gemacht wurde:
1. ✅ **NTRIP Client deaktiviert** (NTR1 auf "off")
   - Via Web-Interface: Communication > NTRIP Settings > Mode: off
   - Verhindert Konflikt mit externem Python NTRIP Client

2. ✅ **COM-Port Einstellungen** (Standard belassen)
   - 115200 Baud, 8N1, kein Flow Control
   - Auto-Input-Mode (erkennt RTCM automatisch)

3. ⏳ **Noch zu tun:**
   - Konfiguration speichern mit `saveConfig`

### Wichtige mosaic-H Befehle:
```bash
# NTRIP Client deaktivieren
setNTRIPSettings,NTR1,off

# COM-Port prüfen
getCOMSettings,COM1

# Data Input/Output prüfen (sollte Auto sein)
getDataInOut,COM1

# Konfiguration speichern
saveConfig

# Status abfragen
getReceiverStatus
```

---

## 🔌 Hardware-Setup

```
CompanionComputer
    |
    ├─ Ethernet Port → Modem/Router → Internet (NTRIP Caster)
    |
    └─ USB Port → USB-TTL Adapter (by-id: usb-Third_Element_Aviation_GmbH...)
                      |
                      └─ UART → mosaic-H GNSS Modul
```

---

## 📝 Konfigurationsparameter

### NTRIP-Parameter (.env)
```env
NTRIP_CASTER=ntrip.example.com        # NTRIP Caster Hostname
NTRIP_PORT=2101                        # Standard NTRIP Port
NTRIP_USERNAME=your_username           # Caster Username
NTRIP_PASSWORD=your_password           # Caster Password
NTRIP_MOUNTPOINT=MOUNT1                # Mountpoint für Region
```

### UART-Parameter
```env
UART_DEVICE=/dev/serial/by-id/usb-Third_Element_Aviation_GmbH_3EA_USB_Mavlink_Emulator_0015871702-if00
UART_BAUDRATE=115200
```

### Betriebsmodus
```env
OPERATION_MODE=stream                  # "config" oder "stream"
```

**Config-Modus:** 
- Konfiguriert mosaic-H einmalig
- Container beendet sich nach Konfiguration

**Stream-Modus:**
- Kontinuierliche RTCM-Weiterleitung
- Automatische Reconnect-Funktion
- Läuft dauerhaft

### Optionale mosaic-H Authentifizierung
```env
MOSAIC_USERNAME=                       # Leer = anonymous access
MOSAIC_PASSWORD=
```

---

## 🐛 Wichtige Erkenntnisse aus dem Handbuch

### 1. Anonymous Access
- mosaic-H erlaubt standardmäßig "anonymous" Zugriff über COM/UART
- Kein Login erforderlich für Kommandozeilen-Befehle
- Login nur relevant für Web-Interface, FTP, SSH
- Kann mit `setDefaultAccessLevel` geändert werden

### 2. RTCM Auto-Erkennung
- mosaic-H erkennt RTCM-Daten automatisch auf COM-Port
- Input-Mode "Auto" ist Standard
- Keine spezielle Konfiguration nötig für RTCM-Empfang

### 3. Point-to-Point Protocol
- **NICHT** erforderlich für RTCM-Weiterleitung
- Nur für TCP/IP über Serial-Verbindung
- Würde Internet-Zugriff über UART ermöglichen
- Für unseren Use-Case unnötig komplex

---

## 🚀 Nächste Schritte für morgen

### 1. NTRIP-Zugangsdaten eintragen
```bash
nano .env
```
- Echte NTRIP Caster URL
- Username/Password
- Mountpoint für Region

### 2. Container bauen und testen
```bash
cd /pfad/zu/mosaikHntripoveruartp2p
docker-compose build
docker-compose up
```

### 3. Logs überwachen
Erwartete Log-Ausgaben:
```
Verbinde zu NTRIP Caster...
Erfolgreich mit NTRIP Caster verbunden
RTCM Daten empfangen und weitergeleitet: X bytes
```

### 4. mosaic-H Status prüfen
Im Web-Interface:
- Status > Position sollte wechseln zu:
  - **RTK Float** (erste Korrekturen ankommen)
  - **RTK Fixed** (volle Genauigkeit, cm-Level)

### 5. Optional: GitHub Repository erstellen
```bash
git init
git add .
git commit -m "Initial commit: mosaic-H NTRIP Docker Client"
gh repo create mosaic-h-ntrip-client --private --source=. --remote=origin
git push -u origin main
```

---

## 📚 Referenzen

### Wichtige Handbuch-Kapitel
- **Section 1.10** - Configure the Receiver in NTRIP Client Mode
- **Section 1.24** - Manage Users (Authentication)
- **Section 1.1.3.3** - Point-to-Point Link (wurde verworfen)
- **Section 3.2.14** - NTRIP Settings Commands

### Wichtige Kommandos
```bash
# NTRIP
setNTRIPSettings,<connection>,<mode>,<caster>,<port>,<user>,<pwd>,<mount>
getNTRIPSettings,<connection>

# User Management
login,<username>,<password>
getUserAccessLevel

# COM Port
getCOMSettings,<port>
getDataInOut,<connection>

# Config
saveConfig
```

---

## 🔍 Troubleshooting-Checkliste

### Container startet nicht
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Keine UART-Verbindung
```bash
ls -la /dev/serial/by-id/
sudo usermod -a -G dialout $USER
# Neu einloggen!
```

### Keine NTRIP-Verbindung
```bash
ping ntrip.example.com
# Zugangsdaten in .env prüfen
# Firewall-Einstellungen prüfen
```

### mosaic-H empfängt keine Daten
- NTRIP Client im mosaic-H deaktiviert? (`setNTRIPSettings,NTR1,off`)
- COM-Port auf 115200 Baud?
- UART-Device-Pfad korrekt in `.env`?
- Container-Logs prüfen: `docker-compose logs -f`

---

## 💡 Offene Fragen / ToDo

- [ ] NTRIP-Caster Zugangsdaten beschaffen
- [ ] Ersten Test durchführen
- [ ] RTK Fixed Status erreichen
- [ ] GitHub Repository erstellen (optional)
- [ ] Systemd Service für Autostart einrichten (optional)

---

## 📊 Performance-Erwartungen

### Latenz
- NTRIP Caster → Companion: 50-150ms
- Python Processing: 1-10ms
- UART Transfer: 1-5ms
- **Gesamt: ~55-165ms** (vernachlässigbar bei 1-5s RTCM-Updates)

### Positionsgenauigkeit
- **Standalone:** 1-5m
- **RTK Float:** 10-50cm
- **RTK Fixed:** 1-3cm (horizontal), 2-5cm (vertikal)

### Datenrate
- RTCM-Daten: ~500-2000 Bytes/Sekunde
- UART @ 115200 Baud: ~11.5 KB/s (ausreichend!)

---

## 🎯 Erfolgs-Kriterien

1. ✅ Container startet ohne Fehler
2. ✅ Verbindung zum NTRIP Caster hergestellt
3. ✅ RTCM-Daten werden empfangen (Log zeigt Bytes)
4. ✅ mosaic-H wechselt zu RTK Float/Fixed
5. ✅ Positionsgenauigkeit <10cm erreicht
6. ✅ System läuft stabil über mehrere Stunden

---

**Status:** Entwicklung abgeschlossen, bereit für ersten Test
**Letztes Update:** 17. November 2025

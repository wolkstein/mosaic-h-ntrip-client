#!/usr/bin/env python3
"""
NTRIP Client für mosaic-H GNSS Modul
Holt RTCM Korrekturdaten von einem NTRIP Caster und leitet sie über UART an das mosaic-H weiter
"""

import os
import sys
import time
import serial
import socket
import base64
import logging
from datetime import datetime

# Logging konfigurieren
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/ntrip_client.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NTRIPClient:
    """NTRIP Client zum Empfangen von RTCM-Korrekturdaten"""
    
    def __init__(self, caster, port, username, password, mountpoint):
        self.caster = caster
        self.port = int(port)
        self.username = username
        self.password = password
        self.mountpoint = mountpoint
        self.socket = None
        
    def connect(self):
        """Verbindung zum NTRIP Caster herstellen"""
        try:
            logger.info(f"Verbinde zu NTRIP Caster {self.caster}:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.caster, self.port))
            
            # NTRIP Request senden
            auth_string = f"{self.username}:{self.password}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            request = (
                f"GET /{self.mountpoint} HTTP/1.0\r\n"
                f"User-Agent: NTRIP mosaic-H-Client/1.0\r\n"
                f"Authorization: Basic {auth_b64}\r\n"
                f"Accept: */*\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            )
            
            self.socket.send(request.encode('ascii'))
            
            # Response lesen
            response = self.socket.recv(1024).decode('ascii', errors='ignore')
            logger.info(f"NTRIP Response: {response.split()[0:2]}")
            
            if "200 OK" in response or "ICY 200 OK" in response:
                logger.info("Erfolgreich mit NTRIP Caster verbunden")
                return True
            else:
                logger.error(f"NTRIP Verbindung fehlgeschlagen: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Verbinden zum NTRIP Caster: {e}")
            return False
    
    def send_gga(self, gga_sentence):
        """GGA Position zum NTRIP Caster senden (für VRS)"""
        try:
            if self.socket and gga_sentence:
                self.socket.send(gga_sentence.encode('ascii'))
                return True
            return False
        except Exception as e:
            logger.error(f"Fehler beim Senden von GGA: {e}")
            return False
    
    def receive_data(self, timeout=5):
        """RTCM Daten vom NTRIP Caster empfangen"""
        try:
            self.socket.settimeout(timeout)
            data = self.socket.recv(4096)
            return data
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"Fehler beim Empfangen von Daten: {e}")
            return None
    
    def close(self):
        """Verbindung schließen"""
        if self.socket:
            try:
                self.socket.close()
                logger.info("NTRIP Verbindung geschlossen")
            except:
                pass


class MosaicUARTInterface:
    """UART Interface zum mosaic-H Modul"""
    
    def __init__(self, device, baudrate=115200):
        self.device = device
        self.baudrate = baudrate
        self.serial = None
        
    def connect(self):
        """Verbindung zum UART Device herstellen"""
        try:
            logger.info(f"Öffne UART Device {self.device} mit {self.baudrate} Baud...")
            self.serial = serial.Serial(
                port=self.device,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            time.sleep(0.5)  # Kurze Pause für Initialisierung
            logger.info("UART Verbindung hergestellt")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Öffnen von {self.device}: {e}")
            return False
    
    def read_nmea(self, timeout=1.0, debug=False):
        """NMEA GGA Nachricht vom mosaic-H lesen"""
        try:
            if not self.serial or not self.serial.is_open:
                return None
            
            start_time = time.time()
            buffer = ""
            
            while time.time() - start_time < timeout:
                if self.serial.in_waiting:
                    chunk = self.serial.read(self.serial.in_waiting).decode('ascii', errors='ignore')
                    buffer += chunk
                    
                    if debug and chunk:
                        logger.debug(f"UART empfangen: {repr(chunk[:100])}")
                    
                    # Suche nach GGA Nachricht
                    lines = buffer.split('\n')
                    for line in lines:
                        if '$GPGGA' in line or '$GNGGA' in line:
                            # Validiere Checksum wenn vorhanden
                            if '*' in line:
                                line = line.strip()
                                if not line.endswith('\r\n'):
                                    line += '\r\n'
                                return line
                time.sleep(0.01)
            
            if debug and buffer:
                logger.debug(f"Buffer enthielt keine GGA: {repr(buffer[:200])}")
            
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim Lesen von NMEA: {e}")
            return None
    
    def send_data(self, data):
        """Daten über UART senden"""
        try:
            if self.serial and self.serial.is_open:
                self.serial.write(data)
                return True
            return False
        except Exception as e:
            logger.error(f"Fehler beim Senden über UART: {e}")
            return False
    
    def send_command(self, command):
        """Kommando an mosaic-H senden"""
        try:
            # Puffer leeren vor dem Senden
            if self.serial.in_waiting:
                self.serial.reset_input_buffer()
            
            cmd = command.strip() + "\r\n"
            logger.info(f"Sende Kommando: {command}")
            self.serial.write(cmd.encode('ascii'))
            self.serial.flush()
            time.sleep(0.3)
            
            # Response lesen
            response = ""
            start_time = time.time()
            while time.time() - start_time < 3:
                if self.serial.in_waiting:
                    chunk = self.serial.read(self.serial.in_waiting).decode('ascii', errors='ignore')
                    response += chunk
                    if '\n' in chunk:
                        time.sleep(0.1)  # Kurz warten für komplette Antwort
                        if self.serial.in_waiting == 0:
                            break
                time.sleep(0.1)
            
            if response:
                logger.info(f"Response: {response.strip()}")
            else:
                logger.warning("Keine Response vom mosaic-H erhalten")
            return response
            
        except Exception as e:
            logger.error(f"Fehler beim Senden des Kommandos: {e}")
            return ""
    
    def login(self, username, password):
        """Login am mosaic-H durchführen (optional)"""
        if not username or not password:
            logger.info("Kein Username/Password angegeben - verwende anonymous access")
            return True
        
        try:
            logger.info(f"Versuche Login als Benutzer: {username}")
            cmd = f"login,{username},{password}"
            response = self.send_command(cmd)
            
            # Prüfe ob Login erfolgreich war
            if "login successful" in response.lower() or "$R" in response:
                logger.info("Login erfolgreich")
                return True
            else:
                logger.warning(f"Login möglicherweise fehlgeschlagen: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Login: {e}")
            return False
    
    def close(self):
        """UART Verbindung schließen"""
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                logger.info("UART Verbindung geschlossen")
            except:
                pass


def configure_mosaic_ntrip(uart, config):
    """Konfiguriert das mosaic-H Modul für NTRIP"""
    logger.info("=== Starte mosaic-H NTRIP Konfiguration ===")
    
    # Kommunikationstest mit mosaic-H
    logger.info("Teste Kommunikation mit mosaic-H...")
    response = uart.send_command("getCOMSettings,COM2")
    # mosaic-H antwortet mit $R: oder $R; oder $R?
    if not response or not response.strip():
        logger.error("Keine Antwort vom mosaic-H erhalten!")
        logger.error("Prüfe UART-Verbindung und Baudrate (sollte 115200 sein)")
        return False
    elif "$R?" in response and "Invalid" in response:
        logger.error(f"mosaic-H meldet ungültigen Befehl: {response.strip()}")
        return False
    else:
        logger.info("✓ Kommunikation mit mosaic-H erfolgreich")
    
    # Optional: Login durchführen
    if 'mosaic_username' in config and 'mosaic_password' in config:
        uart.login(config['mosaic_username'], config['mosaic_password'])
    
    # NMEA GGA Ausgabe auf COM2 aktivieren (für VRS NTRIP)
    # COM2 = UART2 Port (wo der Companion Computer angeschlossen ist)
    logger.info("Aktiviere NMEA Ausgabe auf COM2...")
    uart.send_command("setDataInOut,COM2,,+NMEA")
    time.sleep(0.5)
    
    logger.info("Konfiguriere NMEA GGA Stream auf COM2...")
    uart.send_command("setNMEAOutput,Stream1,COM2,GGA,sec1")
    time.sleep(0.5)
    
    connection = config['connection']
    mode = config['mode']
    caster = config['caster']
    port = config['port']
    username = config['username']
    password = config['password']
    mountpoint = config['mountpoint']
    version = config['version']
    send_gga = config['send_gga']
    
    # NTRIP Connection konfigurieren
    if mode == "Client":
        cmd = f"setNTRIPSettings,{connection},{mode},{caster},{port},{username},{password},{mountpoint}"
        uart.send_command(cmd)
        time.sleep(0.5)
        
        # Version und GGA Einstellungen
        if version != "auto":
            logger.info(f"Setze NTRIP Version auf {version}")
        
        if send_gga != "auto":
            logger.info(f"Setze GGA Intervall auf {send_gga}")
        
        # Status abfragen
        uart.send_command(f"getNTRIPSettings,{connection}")
        
    elif mode == "Server":
        cmd = f"setNTRIPSettings,{connection},{mode},{caster},{port},{username},{password},{mountpoint}"
        uart.send_command(cmd)
    
    # Konfiguration dauerhaft speichern
    logger.info("Speichere Konfiguration...")
    uart.send_command("exeWriteSettings")
    time.sleep(1)
    
    logger.info("=== mosaic-H NTRIP Konfiguration abgeschlossen ===")
    return True


def stream_mode(ntrip_client, uart):
    """Stream-Modus: Leitet NTRIP Daten kontinuierlich an mosaic-H weiter"""
    logger.info("=== Starte Stream-Modus ===")
    
    bytes_received = 0
    last_log_time = time.time()
    last_gga_time = 0  # Sofort beim Start senden
    gga_interval = 5  # GGA alle 5 Sekunden senden
    gga_sent = False
    
    try:
        while True:
            current_time = time.time()
            
            # GGA Position zum Caster senden (für VRS)
            if current_time - last_gga_time >= gga_interval:
                gga = uart.read_nmea(timeout=1.0, debug=(not gga_sent))
                if gga:
                    if ntrip_client.send_gga(gga):
                        if not gga_sent:
                            logger.info(f"Erste GGA Position gesendet: {gga.strip()}")
                            gga_sent = True
                        last_gga_time = current_time
                else:
                    if not gga_sent:
                        logger.warning("Keine GGA Position vom mosaic-H empfangen - mosaic-H gibt evtl. keine NMEA Daten aus")
                    last_gga_time = current_time  # Verhindere zu häufiges Logging
            
            # Daten vom NTRIP Caster empfangen
            data = ntrip_client.receive_data(timeout=1)
            
            if data:
                # Daten über UART an mosaic-H senden
                if uart.send_data(data):
                    bytes_received += len(data)
                    
                    # Log alle 10 Sekunden
                    if current_time - last_log_time >= 10:
                        logger.info(f"RTCM Daten empfangen und weitergeleitet: {bytes_received} bytes")
                        last_log_time = current_time
            elif gga_sent and current_time - last_log_time >= 30:
                # Nur warnen wenn GGA gesendet wurde und länger keine Daten kommen
                logger.warning("Keine RTCM Daten vom NTRIP Caster empfangen - Reconnect...")
                return False  # Reconnect erforderlich
                
    except KeyboardInterrupt:
        logger.info("Stream-Modus durch Benutzer beendet")
        return True
    except Exception as e:
        logger.error(f"Fehler im Stream-Modus: {e}")
        return False


def main():
    """Hauptprogramm"""
    
    # Umgebungsvariablen lesen
    operation_mode = os.getenv('OPERATION_MODE', 'stream')
    
    # NTRIP Parameter
    ntrip_caster = os.getenv('NTRIP_CASTER')
    ntrip_port = os.getenv('NTRIP_PORT', '2101')
    ntrip_username = os.getenv('NTRIP_USERNAME')
    ntrip_password = os.getenv('NTRIP_PASSWORD')
    ntrip_mountpoint = os.getenv('NTRIP_MOUNTPOINT')
    
    # UART Parameter
    uart_device = os.getenv('UART_DEVICE', '/dev/ttyUSB0')
    uart_baudrate = int(os.getenv('UART_BAUDRATE', '115200'))
    
    # mosaic-H Konfiguration
    mosaic_ntrip_mode = os.getenv('MOSAIC_NTRIP_MODE', 'Client')
    mosaic_ntrip_connection = os.getenv('MOSAIC_NTRIP_CONNECTION', 'NTR1')
    mosaic_ntrip_version = os.getenv('MOSAIC_NTRIP_VERSION', 'v2')
    mosaic_send_gga = os.getenv('MOSAIC_SEND_GGA', 'auto')
    
    # mosaic-H Authentifizierung (optional)
    mosaic_username = os.getenv('MOSAIC_USERNAME', '')
    mosaic_password = os.getenv('MOSAIC_PASSWORD', '')
    
    # Validierung
    if not all([ntrip_caster, ntrip_username, ntrip_password, ntrip_mountpoint]):
        logger.error("NTRIP Parameter nicht vollständig konfiguriert!")
        logger.error("Bitte NTRIP_CASTER, NTRIP_USERNAME, NTRIP_PASSWORD und NTRIP_MOUNTPOINT setzen")
        sys.exit(1)
    
    logger.info("=== mosaic-H NTRIP Client gestartet ===")
    logger.info(f"Betriebsmodus: {operation_mode}")
    logger.info(f"NTRIP Caster: {ntrip_caster}:{ntrip_port}")
    logger.info(f"Mount Point: {ntrip_mountpoint}")
    logger.info(f"UART Device: {uart_device}")
    logger.info(f"UART Baudrate: {uart_baudrate} Baud")
    
    # UART Interface initialisieren
    uart = MosaicUARTInterface(uart_device, uart_baudrate)
    if not uart.connect():
        logger.error("UART Verbindung fehlgeschlagen!")
        sys.exit(1)
    
    # Config-Modus: Konfiguriere mosaic-H und beende
    if operation_mode == "config":
        config = {
            'connection': mosaic_ntrip_connection,
            'mode': mosaic_ntrip_mode,
            'caster': ntrip_caster,
            'port': ntrip_port,
            'username': ntrip_username,
            'password': ntrip_password,
            'mountpoint': ntrip_mountpoint,
            'version': mosaic_ntrip_version,
            'send_gga': mosaic_send_gga,
            'mosaic_username': mosaic_username,
            'mosaic_password': mosaic_password
        }
        success = configure_mosaic_ntrip(uart, config)
        uart.close()
        if not success:
            logger.error("Konfiguration fehlgeschlagen!")
            sys.exit(1)
        logger.info("Konfiguration abgeschlossen. Container wird beendet.")
        sys.exit(0)
    
    # Stream-Modus: Kontinuierliche Weiterleitung von NTRIP Daten
    elif operation_mode == "stream":
        reconnect_delay = 5
        
        while True:
            # NTRIP Client initialisieren
            ntrip_client = NTRIPClient(
                ntrip_caster,
                ntrip_port,
                ntrip_username,
                ntrip_password,
                ntrip_mountpoint
            )
            
            # Verbindung zum NTRIP Caster herstellen
            if ntrip_client.connect():
                # Stream-Modus starten
                result = stream_mode(ntrip_client, uart)
                
                if result:  # Benutzer-Interrupt
                    break
            
            # Cleanup
            ntrip_client.close()
            
            # Reconnect nach Verzögerung
            logger.info(f"Reconnect in {reconnect_delay} Sekunden...")
            time.sleep(reconnect_delay)
    
    else:
        logger.error(f"Unbekannter Betriebsmodus: {operation_mode}")
        logger.error("Erlaubte Modi: 'config', 'stream'")
        sys.exit(1)
    
    # Cleanup
    uart.close()
    logger.info("=== mosaic-H NTRIP Client beendet ===")


if __name__ == "__main__":
    main()

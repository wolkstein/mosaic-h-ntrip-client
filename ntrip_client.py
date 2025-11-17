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
logging.basicConfig(
    level=logging.INFO,
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
            cmd = command.strip() + "\r\n"
            logger.info(f"Sende Kommando: {command}")
            self.serial.write(cmd.encode('ascii'))
            time.sleep(0.2)
            
            # Response lesen
            response = ""
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.serial.in_waiting:
                    response += self.serial.read(self.serial.in_waiting).decode('ascii', errors='ignore')
                time.sleep(0.1)
            
            if response:
                logger.info(f"Response: {response.strip()}")
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
    
    # Optional: Login durchführen
    if 'mosaic_username' in config and 'mosaic_password' in config:
        uart.login(config['mosaic_username'], config['mosaic_password'])
    
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
    
    logger.info("=== mosaic-H NTRIP Konfiguration abgeschlossen ===")


def stream_mode(ntrip_client, uart):
    """Stream-Modus: Leitet NTRIP Daten kontinuierlich an mosaic-H weiter"""
    logger.info("=== Starte Stream-Modus ===")
    
    bytes_received = 0
    last_log_time = time.time()
    
    try:
        while True:
            # Daten vom NTRIP Caster empfangen
            data = ntrip_client.receive_data(timeout=30)
            
            if data:
                # Daten über UART an mosaic-H senden
                if uart.send_data(data):
                    bytes_received += len(data)
                    
                    # Log alle 10 Sekunden
                    current_time = time.time()
                    if current_time - last_log_time >= 10:
                        logger.info(f"RTCM Daten empfangen und weitergeleitet: {bytes_received} bytes")
                        last_log_time = current_time
            else:
                logger.warning("Keine Daten vom NTRIP Caster empfangen - Reconnect...")
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
        configure_mosaic_ntrip(uart, config)
        uart.close()
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

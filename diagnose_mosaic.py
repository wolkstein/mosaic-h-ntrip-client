#!/usr/bin/env python3
"""
mosaic-H Diagnose Script

Liest wichtige Konfigurationsparameter vom mosaic-H aus, um RTK Performance zu analysieren.
Verwendung: python diagnose_mosaic.py
"""

import serial
import time
import sys

# UART Konfiguration - ANPASSEN falls nötig!
UART_DEVICE = "/dev/ttyACM0"  # oder COM Port unter Windows
UART_BAUDRATE = 115200
UART_TIMEOUT = 2  # Sekunden


class MosaicDiagnose:
    """Diagnose-Klasse für mosaic-H GNSS Modul"""
    
    def __init__(self, port, baudrate=115200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
    
    def connect(self):
        """Verbindung zum mosaic-H herstellen"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            print(f"✓ Verbunden mit {self.port} @ {self.baudrate} baud")
            time.sleep(0.5)  # Zeit für Initialisierung
            return True
        except serial.SerialException as e:
            print(f"✗ Fehler beim Öffnen von {self.port}: {e}")
            print("\nHinweis: Docker Container stoppen mit: docker-compose down")
            return False
    
    def disconnect(self):
        """Verbindung trennen"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("\n✓ Verbindung getrennt")
    
    def send_command(self, command):
        """Befehl an mosaic-H senden und Antwort empfangen"""
        if not self.ser or not self.ser.is_open:
            return None
        
        try:
            # Buffer leeren
            self.ser.reset_input_buffer()
            
            # Befehl senden
            cmd = f"{command}\r\n"
            self.ser.write(cmd.encode('ascii'))
            
            # Antwort lesen (mehrere Zeilen möglich)
            response_lines = []
            start_time = time.time()
            
            while time.time() - start_time < self.timeout:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('ascii', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        # Wenn wir eine vollständige Antwort haben (endet oft mit leerem Prompt)
                        if line.startswith("COM") and ">" in line:
                            break
                else:
                    time.sleep(0.1)
            
            return '\n'.join(response_lines)
        
        except Exception as e:
            print(f"Fehler bei Befehl '{command}': {e}")
            return None
    
    def print_section(self, title):
        """Formatierte Sektion ausgeben"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}")
    
    def print_command(self, command, description):
        """Befehl ausführen und Antwort ausgeben"""
        print(f"\n→ {description}")
        print(f"  Befehl: {command}")
        response = self.send_command(command)
        if response:
            # Antwort formatiert ausgeben
            for line in response.split('\n'):
                if line and not line.startswith("COM"):  # Prompt-Zeilen überspringen
                    print(f"  {line}")
        else:
            print("  ✗ Keine Antwort erhalten")
        time.sleep(0.3)  # Kurze Pause zwischen Befehlen
    
    def run_diagnostics(self):
        """Vollständige Diagnose durchführen"""
        
        self.print_section("SYSTEM INFO")
        self.print_command("getReceiverInfo", "Receiver Model & Firmware")
        self.print_command("getHardwareVersion", "Hardware Version")
        
        self.print_section("COM PORT EINSTELLUNGEN")
        self.print_command("getCOMSettings,COM1", "COM1 (Flight Controller)")
        self.print_command("getCOMSettings,COM2", "COM2 (Companion Computer)")
        self.print_command("getDataInOut,COM1", "COM1 Data In/Out")
        self.print_command("getDataInOut,COM2", "COM2 Data In/Out")
        
        self.print_section("SBF OUTPUT KONFIGURATION")
        self.print_command("getSBFOutput,Stream1", "SBF Stream 1 (normalerweise COM1)")
        self.print_command("getSBFOutput,Stream2", "SBF Stream 2")
        
        self.print_section("NMEA OUTPUT KONFIGURATION")
        self.print_command("getNMEAOutput,Stream1", "NMEA Stream 1 (für VRS)")
        
        self.print_section("GNSS KONSTELLATIONEN")
        self.print_command("getSignalTracking", "Aktive Signale & Konstellationen")
        self.print_command("getElevationMask", "Elevation Mask (Mindesthöhe Satelliten)")
        
        self.print_section("RTK / DIFFERENTIAL CORRECTION")
        self.print_command("getDiffCorrSettings", "Differential Correction Settings")
        self.print_command("getDiffCorrUsage", "Verwendung von Diff. Corrections")
        self.print_command("getPVTMode", "PVT Mode (Stand-Alone, DGNSS, RTK, etc.)")
        self.print_command("getReceiverDynamics", "Receiver Dynamics (Static/Kinematic)")
        
        self.print_section("RTK AMBIGUITY RESOLUTION")
        self.print_command("getAmbiguityMode", "Ambiguity Resolution Mode")
        
        self.print_section("ATTITUDE & HEADING (Dual-Antenna)")
        self.print_command("getAttitudeStatus", "Attitude/Heading Status")
        self.print_command("getAttitudeCoverage", "Attitude Antenna Coverage")
        
        self.print_section("NTRIP EINSTELLUNGEN")
        self.print_command("getNTRIPSettings,NTR1", "NTRIP Connection 1")
        
        self.print_section("AKTUELLER STATUS")
        self.print_command("getPVTMode", "Aktueller PVT Mode")
        self.print_command("getTrackingStatus", "Tracking Status (Satelliten)")
        
        print(f"\n{'='*70}")
        print("  DIAGNOSE ABGESCHLOSSEN")
        print(f"{'='*70}\n")


def main():
    """Hauptprogramm"""
    print("\n" + "="*70)
    print("  mosaic-H GNSS Diagnose Tool")
    print("="*70)
    
    # UART Device aus Umgebungsvariable oder Default
    import os
    uart_device = os.getenv('UART_DEVICE', UART_DEVICE)
    
    print(f"\nVerbinde mit: {uart_device}")
    print(f"Baudrate: {UART_BAUDRATE}")
    print("\nHinweis: Docker Container muss gestoppt sein!")
    print("         → docker-compose down\n")
    
    diag = MosaicDiagnose(uart_device, UART_BAUDRATE, UART_TIMEOUT)
    
    if not diag.connect():
        sys.exit(1)
    
    try:
        diag.run_diagnostics()
    except KeyboardInterrupt:
        print("\n\n✗ Diagnose abgebrochen (Ctrl+C)")
    except Exception as e:
        print(f"\n\n✗ Fehler während Diagnose: {e}")
    finally:
        diag.disconnect()


if __name__ == "__main__":
    main()

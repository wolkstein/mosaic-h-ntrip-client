#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mosaic-H RTK Optimization Script

Optimiert die mosaic-H Einstellungen für bessere RTK Performance.
Verwendung: python3 optimize_rtk.py
"""

import serial
import time
import sys
import os

# UART Konfiguration
UART_DEVICE = os.getenv('UART_DEVICE', "/dev/ttyACM0")
UART_BAUDRATE = 115200
UART_TIMEOUT = 2


class MosaicOptimizer:
    """Optimierungs-Klasse für mosaic-H RTK Settings"""
    
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
            time.sleep(0.5)
            
            # COM2 in Command-Modus zwingen
            print("Setze COM2 in Command-Modus...")
            self.ser.write(b"SSSSSSSSSS\r\n")
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            
            return True
        except serial.SerialException as e:
            print(f"✗ Fehler: {e}")
            return False
    
    def disconnect(self):
        """Verbindung trennen"""
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def send_command(self, command):
        """Befehl senden und Antwort lesen"""
        if not self.ser or not self.ser.is_open:
            return None
        
        try:
            self.ser.reset_input_buffer()
            cmd = f"{command}\r\n"
            self.ser.write(cmd.encode('ascii'))
            
            response_lines = []
            start_time = time.time()
            
            while time.time() - start_time < self.timeout:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('ascii', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        if line.startswith("COM") and ">" in line:
                            break
                else:
                    time.sleep(0.1)
            
            return '\n'.join(response_lines)
        except Exception as e:
            print(f"Fehler bei '{command}': {e}")
            return None
    
    def restore_nmea_mode(self):
        """COM2 zurück in NMEA-Modus"""
        self.ser.reset_input_buffer()
        self.ser.write(b"setDataInOut,COM2,,+NMEA\r\n")
        time.sleep(0.5)
        self.ser.write(b"setNMEAOutput,Stream1,COM2,GGA,sec1\r\n")
        time.sleep(0.5)
    
    def optimize(self):
        """RTK-Optimierungen durchführen"""
        print("\n" + "="*70)
        print("  mosaic-H RTK OPTIMIERUNG")
        print("="*70)
        
        # Aktuelle Einstellungen lesen
        print("\n→ Lese aktuelle Einstellungen...")
        response = self.send_command("getElevationMask")
        print(response)
        
        current_pvt_mask = None
        if response:
            for line in response.split('\n'):
                if "ElevationMask, PVT," in line:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        current_pvt_mask = parts[2].strip()
        
        print(f"\n→ Aktuelle PVT Elevation Mask: {current_pvt_mask}°")
        
        # Optimierung 1: Elevation Mask auf 5° setzen
        print("\n" + "="*70)
        print("  OPTIMIERUNG 1: Elevation Mask")
        print("="*70)
        print("\nBeschreibung:")
        print("  Reduziert die minimale Satellitenhöhe für PVT-Berechnung")
        print("  von 10° auf 5°. Dies erhöht die Anzahl nutzbarer Satelliten")
        print("  und verbessert die RTK-Performance, besonders in städtischen")
        print("  Gebieten oder bei eingeschränkter Himmelssicht.")
        print(f"\n  Aktuell: {current_pvt_mask}°")
        print("  Neu:     5°")
        
        response = input("\nElevation Mask auf 5° setzen? (j/n): ")
        
        if response.lower() in ['j', 'y', 'yes', 'ja']:
            print("\nSetze Elevation Mask auf 5°...")
            result = self.send_command("setElevationMask,PVT,5")
            print(result)
            
            # Verifizieren
            time.sleep(0.5)
            verify = self.send_command("getElevationMask")
            print("\nVerifizierung:")
            print(verify)
            
            # Speichern
            print("\nSpeichere Einstellungen dauerhaft...")
            save_result = self.send_command("exeWriteSettings")
            print(save_result)
            
            print("\n✓ Elevation Mask auf 5° gesetzt und gespeichert!")
        else:
            print("\n→ Übersprungen")
        
        # Weitere mögliche Optimierungen
        print("\n" + "="*70)
        print("  WEITERE OPTIMIERUNGSMÖGLICHKEITEN")
        print("="*70)
        
        print("\n→ RTK Einstellungen prüfen...")
        pvt_mode = self.send_command("getPVTMode")
        print(pvt_mode)
        
        print("\n→ DiffCorr Timeout prüfen...")
        diffcorr = self.send_command("getDiffCorrUsage")
        print(diffcorr)
        
        print("\n" + "="*70)
        print("  OPTIMIERUNG ABGESCHLOSSEN")
        print("="*70)
        print("\nEmpfehlungen:")
        print("  1. Docker Container neu starten: docker-compose up -d")
        print("  2. RTK-Fix-Zeit beobachten (sollte schneller sein)")
        print("  3. Satellitenanzahl in QGC/PX4 prüfen (sollte höher sein)")
        print("\nWeitere Performance-Faktoren:")
        print("  - Antennenposition: Freie Himmelssicht wichtig")
        print("  - NTRIP-Verbindung: Stabile Internetverbindung")
        print("  - RTCM-Alter: Sollte < 2 Sekunden sein")
        print("  - Baseline-Distanz: VRS funktioniert bis ~70km")
        
        # COM2 zurück in NMEA-Modus
        print("\n" + "="*70)
        print("  COM2 wird zurück in NMEA-Modus gesetzt...")
        print("="*70)
        self.restore_nmea_mode()
        print("✓ COM2 ist wieder im NMEA-Modus")


def main():
    """Hauptprogramm"""
    print("\n" + "="*70)
    print("  mosaic-H RTK Optimization Tool")
    print("="*70)
    print(f"\nVerbinde mit: {UART_DEVICE}")
    print(f"Baudrate: {UART_BAUDRATE}")
    print("\nHinweis: Docker Container muss gestoppt sein!")
    print("         → docker-compose down\n")
    
    optimizer = MosaicOptimizer(UART_DEVICE, UART_BAUDRATE, UART_TIMEOUT)
    
    if not optimizer.connect():
        sys.exit(1)
    
    try:
        optimizer.optimize()
    except KeyboardInterrupt:
        print("\n\n✗ Abgebrochen (Ctrl+C)")
    except Exception as e:
        print(f"\n\n✗ Fehler: {e}")
    finally:
        optimizer.disconnect()
        print("\n✓ Verbindung getrennt\n")


if __name__ == "__main__":
    main()

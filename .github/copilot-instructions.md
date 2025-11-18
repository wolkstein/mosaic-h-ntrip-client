# mosaic-H NTRIP Docker Client - AI Agent Guide

## Project Overview
Python-based Docker client for Holibro mosaic-H GNSS module that provides VRS-based RTK corrections via NTRIP. Implements bidirectional communication: sends GGA position to VRS caster, receives RTCM corrections. Written in German but code comments/docs mix German/English.

**Status: ✅ Productively deployed and tested (Nov 18, 2025)**

## Architecture & Key Design Decisions

### System Flow (VRS RTK)
```
Internet (VRS NTRIP Caster)
    ↑ GGA Position (every 5s)
    ↓ RTCM corrections (~9KB/10s)
Docker Container (Python NTRIP client)
    ↑ reads NMEA GGA from COM2
    ↓ sends RTCM to COM2 (115200 baud)
mosaic-H GNSS Module (Rover)
    ↑ outputs GGA via COM2
    ↓ processes RTCM for RTK
```

**Critical: VRS requires bidirectional communication**
- GGA position must be sent to caster (interval: 5 seconds is sufficient for rover)
- Caster responds with location-specific RTCM corrections
- NMEA output must be enabled on COM2: `setNMEAOutput,Stream1,COM2,GGA,sec1`
- Direct RTCM forwarding (no P2PP needed - simpler, equally fast)

### Two Operating Modes
1. **config**: One-time configuration of mosaic-H module via UART commands, then exits
   - Enables NMEA output on COM2
   - Configures GGA stream (1 Hz)
   - Saves settings with `exeWriteSettings`
2. **stream**: Continuous bidirectional data relay with auto-reconnect (production mode)
   - Reads GGA from mosaic-H (every 5s)
   - Sends GGA to NTRIP caster
   - Forwards RTCM corrections to mosaic-H

Mode is controlled by `OPERATION_MODE` env var in `.env` file.

## File Structure & Responsibilities

- `ntrip_client.py`: Single-file application with classes and functions:
  - `NTRIPClient`: HTTP-based NTRIP protocol, handles caster connection/auth, sends GGA to caster
  - `MosaicUARTInterface`: Serial communication, sends commands, reads NMEA, forwards RTCM data
  - `configure_mosaic_ntrip()`: Config mode - sets up NMEA output and saves settings
  - `stream_mode()`: Data relay - reads GGA, sends to caster, forwards RTCM to module
- `docker-compose.yml`: Container orchestration, mounts `/dev/serial/by-id/*` as `/dev/ttyACM0`
- `.env`: Configuration (not in repo, use `.env.example` as template)
- `logs/ntrip_client.log`: Application logs (dual output: file + stdout)

## Critical Patterns

### UART Device Path & Hardware
**Always use `/dev/serial/by-id/` paths in `.env`, mapped to `/dev/ttyACM0` in container**
- By-ID paths are persistent across reboots/USB reconnections
- Example: `/dev/serial/by-id/usb-Third_Element_Aviation_GmbH_3EA_USB_Mavlink_Emulator_0015871742-if00`
- Find with: `ls /dev/serial/by-id/`
- Docker maps this to `/dev/ttyACM0` inside container (not ttyUSB0!)
- mosaic-H has COM1 (Flight Controller) and COM2 (Companion Computer) - we use COM2

### mosaic-H Communication
- Default: Anonymous access (no login required)
- Commands: ASCII strings terminated with `\r\n`
- Responses: `$R:` or `$R;` prefix (not consistent!)
- Key commands:
  - `getCOMSettings,COM2` - test communication
  - `setDataInOut,COM2,,+NMEA` - enable NMEA output
  - `setNMEAOutput,Stream1,COM2,GGA,sec1` - configure GGA stream
  - `setNTRIPSettings,<conn>,<mode>,<caster>,<port>,<user>,<pass>,<mount>` - NTRIP config
  - `exeWriteSettings` - save config permanently (not `saveConfig`!)

### NTRIP Protocol
- HTTP/1.0 GET request with Basic Auth header
- User-Agent: `NTRIP mosaic-H-Client/1.0`
- Success: `200 OK` or `ICY 200 OK` response
- Binary RTCM data stream follows HTTP headers
- 4KB read chunks with 30s timeout

## Development Workflows

### Local Testing
```bash
# Build and run in config mode (one-time setup)
docker-compose build
docker-compose up

# Switch to stream mode (edit .env: OPERATION_MODE=stream)
docker-compose up -d

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Debugging
- Logs go to both stdout and `/app/logs/ntrip_client.log`
- Check UART permissions if connection fails (container needs `privileged: true`)
- Verify NTRIP caster credentials and mountpoint availability
- mosaic-H commands return responses within 2 seconds (timeout hardcoded)

## Configuration Management

All config via environment variables in `.env` (see `.env.example`):
- **Required**: `NTRIP_CASTER`, `NTRIP_USERNAME`, `NTRIP_PASSWORD`, `NTRIP_MOUNTPOINT`, `UART_DEVICE`
- **Optional**: `MOSAIC_USERNAME`/`MOSAIC_PASSWORD` (only if module has non-default access level)
- Validation: Application exits immediately if required vars missing

## Integration Points

### External Dependencies
- NTRIP Caster: Real-time GNSS correction service (external, credentials required)
- mosaic-H Module: Septentrio GNSS receiver (v4.14.10 firmware)
- USB-TTL Adapter: Physical serial bridge to module

### Data Flow
- Inbound: RTCM binary data from NTRIP (via TCP socket)
- Outbound: Raw RTCM bytes to UART (no parsing/modification)
- No data transformation or protocol conversion occurs

## Important Constraints

- Python 3.11-slim base image
- Single dependency: `pyserial==3.5`
- Network mode: `host` (container shares host network stack)
- Requires privileged container for device access
- No tests currently implemented
- Designed for ARM-based companion computers (though arch-agnostic)

## Reference Documentation

- `docs/mosaic-H-Firmware-v4.14.10-Reference-Guide.txt`: Full mosaic-H command reference
- `DEVELOPMENT_NOTES.md`: Design decisions, architecture rationale, session logs
- `QUICKSTART.md`: Essential commands for operators
- README.md: Complete setup guide with troubleshooting

## Common Modifications

When editing `ntrip_client.py`:
- Reconnect logic is in `main()` loop (5s delay hardcoded)
- Logging interval: 10s in `stream_mode()` function
- UART timeout: 1s (serial.Serial constructor)
- NTRIP socket timeout: 10s for connect, 30s for data receive
- All hardcoded timeouts are in seconds (use `time.sleep()` or socket timeouts)

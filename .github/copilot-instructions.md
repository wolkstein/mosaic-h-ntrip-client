# mosaic-H NTRIP Docker Client - AI Agent Guide

## Project Overview
Python-based Docker client that bridges a mosaic-H GNSS module (via UART) to an NTRIP caster for RTK correction data. Written in German but code comments/docs mix German/English.

## Architecture & Key Design Decisions

### System Flow
```
Internet (NTRIP Caster)
    ↓ RTCM corrections
Docker Container (Python NTRIP client)
    ↓ UART (115200 baud)
mosaic-H GNSS Module
```

**Critical: Direct RTCM forwarding approach was chosen over Point-to-Point Protocol (P2PP)**
- P2PP would add unnecessary complexity (PPP daemon, IP routing)
- RTCM updates only arrive every 1-5 seconds, so 50-100ms latency is negligible
- Direct forwarding is simpler to debug and maintain
- See `DEVELOPMENT_NOTES.md` for full rationale

### Two Operating Modes
1. **config**: One-time configuration of mosaic-H module via UART commands, then exits
2. **stream**: Continuous RTCM data relay with auto-reconnect (production mode)

Mode is controlled by `OPERATION_MODE` env var in `.env` file.

## File Structure & Responsibilities

- `ntrip_client.py`: Single-file application with three classes:
  - `NTRIPClient`: HTTP-based NTRIP protocol, handles caster connection/authentication
  - `MosaicUARTInterface`: Serial communication, sends commands and raw RTCM data
  - Functions: `configure_mosaic_ntrip()` for config mode, `stream_mode()` for data relay
- `docker-compose.yml`: Container orchestration, passes through UART device with `privileged: true`
- `.env`: Configuration (not in repo, use `.env.example` as template)
- `logs/ntrip_client.log.txt`: Application logs (dual output: file + stdout)

## Critical Patterns

### UART Device Path
**Always use `/dev/serial/by-id/` paths, never `/dev/ttyUSB0`**
- By-ID paths are persistent across reboots/USB reconnections
- Example: `/dev/serial/by-id/usb-Third_Element_Aviation_GmbH_3EA_USB_Mavlink_Emulator_0015871702-if00`
- Find with: `ls /dev/serial/by-id/`
- This is documented in both README.md and `.env.example`

### mosaic-H Communication
- Default: Anonymous access (no login required)
- Commands: ASCII strings terminated with `\r\n`
- Optional login via `login,username,password` command (rarely needed)
- Auto-detects RTCM data format on UART (no special config needed)
- Key command: `setNTRIPSettings,<connection>,<mode>,<caster>,<port>,<user>,<pass>,<mount>`

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

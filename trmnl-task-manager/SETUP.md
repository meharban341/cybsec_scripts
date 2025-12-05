# TRMNL Task Manager Widget

Display Windows Server 2019 Task Manager metrics on your TRMNL e-ink display.

## Features

**Basic (psutil):**
- Real-time CPU usage with progress bar
- Memory usage and availability
- Disk usage per partition
- Network I/O statistics (total bytes)
- Top processes by CPU/Memory
- System uptime and hostname

**Enhanced (with HWiNFO64):**
- Real-time network throughput (download/upload speed in KB/s or MB/s)
- CPU and GPU temperatures
- GPU usage, memory, and clock speed
- Fan speeds
- Per-adapter network stats

## Quick Start (Polling Method - Recommended)

### Step 1: Set up the server on Windows Server 2019

1. **Install Python** (if not already installed):
   - Download from https://python.org/downloads/
   - Check "Add Python to PATH" during installation

2. **Install dependencies**:
   ```powershell
   pip install psutil
   ```

3. **Copy files to your server**:
   - `server.py` - The metrics API server

4. **Run the server**:
   ```powershell
   python server.py
   ```

   The server will start on port 8080. You should see:
   ```
   Server running on http://0.0.0.0:8080
   ```

5. **Test it works**:
   - Open browser: `http://localhost:8080/metrics`
   - You should see JSON with all your system metrics

### Step 2: Configure your firewall

Allow inbound connections on port 8080:

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "TRMNL Metrics" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

### Step 3: Create the TRMNL Private Plugin

1. Go to [TRMNL Dashboard](https://usetrmnl.com/dashboard)
2. Click **Plugins** → **Private Plugin** → **Add New**
3. Configure:
   - **Name**: Task Manager
   - **Strategy**: Polling
   - **Polling URL**: `http://YOUR_SERVER_IP:8080/metrics`
   - **Polling interval**: 5 minutes (or your preference)

4. Click **Markup** tab and paste the contents of `trmnl_markup.html`

5. **Save** and add to your playlist!

## Alternative: Webhook Push Method

If you can't open ports on your server, use the webhook push method instead:

1. Create a Private Plugin with **Webhook** strategy
2. Copy your webhook URL (looks like `https://usetrmnl.com/api/custom_plugins/abc123`)
3. Edit `webhook_push.py` and set your webhook URL
4. Schedule the script to run periodically:

   **Using Task Scheduler:**
   ```
   Program: python
   Arguments: C:\path\to\webhook_push.py
   Trigger: Every 5 minutes
   ```

## Running as a Windows Service

To keep the server running 24/7:

### Option 1: NSSM (Recommended)

1. Download NSSM from https://nssm.cc/download
2. Install as service:
   ```powershell
   nssm install TRMNLMetrics "C:\Python\python.exe" "C:\path\to\server.py"
   nssm start TRMNLMetrics
   ```

### Option 2: Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: "At startup"
4. Action: Start a program
   - Program: `pythonw.exe` (silent, no console window)
   - Arguments: `C:\path\to\server.py`
5. Check "Run whether user is logged on or not"

## HWiNFO64 Integration (Optional but Recommended)

HWiNFO64 provides much more detailed hardware monitoring than Windows APIs, including **real-time network throughput** (the actual download/upload speeds you see in Task Manager's Performance tab).

### Why HWiNFO64?

| Metric | Without HWiNFO | With HWiNFO |
|--------|---------------|-------------|
| Network | Total bytes (cumulative) | Live speed (KB/s, MB/s) |
| CPU Temp | Not available | Yes |
| GPU Stats | Not available | Usage, temp, memory, clock |
| Fan Speeds | Not available | Yes |

### Setup Instructions

1. **Download HWiNFO64** (free for personal use):
   - https://www.hwinfo.com/download/
   - Use version **6.42 or earlier** for Remote Sensor Monitor compatibility
   - Or use HWiNFO Pro (any version) for unlimited shared memory

2. **Download Remote Sensor Monitor**:
   - https://www.hwinfo.com/forum/threads/introducing-remote-sensor-monitor-a-restful-web-server.1025/
   - Extract to a folder (e.g., `C:\Tools\RemoteSensorMonitor\`)

3. **Configure HWiNFO64**:
   - Start HWiNFO64 in **Sensors-only** mode
   - Go to **Settings** (gear icon)
   - Check **Shared Memory Support** under General/UI
   - Click OK and restart HWiNFO

4. **Start Remote Sensor Monitor**:
   ```powershell
   cd C:\Tools\RemoteSensorMonitor
   .\RemoteSensorMonitor.exe --hwinfo=1
   ```

   You should see: `Web server started on port 55555`

5. **Test it**:
   - Open browser: `http://localhost:55555`
   - You should see JSON with all HWiNFO sensor data

6. **Run both at startup** (optional):
   Create a batch file `start-monitoring.bat`:
   ```batch
   @echo off
   start "" "C:\Program Files\HWiNFO64\HWiNFO64.exe" -sensors
   timeout /t 5
   start "" "C:\Tools\RemoteSensorMonitor\RemoteSensorMonitor.exe" --hwinfo=1
   ```
   Add this to Task Scheduler to run at startup.

### Firewall Rule for Remote Sensor Monitor

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Remote Sensor Monitor" -Direction Inbound -Protocol TCP -LocalPort 55555 -Action Allow
```

### Configuration

In `server.py`, HWiNFO integration is enabled by default:

```python
# HWiNFO64 Remote Sensor Monitor Integration
HWINFO_ENABLED = True          # Set to False to disable
HWINFO_HOST = "127.0.0.1"      # Usually localhost
HWINFO_PORT = 55555            # Default RSM port
```

If HWiNFO/RSM isn't running, the server gracefully falls back to basic psutil metrics.

### HWiNFO License Note

- **Free version**: Shared memory works for 12 hours, then requires restart
- **Pro version** ($25): Unlimited shared memory support

For a server that runs 24/7, HWiNFO Pro is recommended, or set up a scheduled task to restart HWiNFO every 12 hours.

## Customizing the Display

Edit `trmnl_markup.html` to customize what's shown. TRMNL uses [Liquid templating](https://shopify.github.io/liquid/).

### Available Variables

**Basic metrics (always available):**
```
{{ timestamp }}                    - Last update time
{{ system.hostname }}              - Server hostname
{{ system.os }}                    - Operating system
{{ system.uptime }}                - System uptime

{{ cpu.usage_percent }}            - CPU usage %
{{ cpu.usage_bar }}                - Visual bar (████░░░░░░)
{{ cpu.cores_logical }}            - Number of logical cores
{{ cpu.frequency_mhz }}            - Current CPU frequency

{{ memory.usage_percent }}         - Memory usage %
{{ memory.usage_bar }}             - Visual bar
{{ memory.used }}                  - Used memory (e.g., "8.5GB")
{{ memory.total }}                 - Total memory

{{ disk.partitions }}              - Array of disk partitions
{{ disk.partitions[0].mountpoint }}
{{ disk.partitions[0].percent }}
{{ disk.partitions[0].used }}
{{ disk.partitions[0].total }}

{{ network.bytes_sent }}           - Total bytes sent
{{ network.bytes_recv }}           - Total bytes received
{{ network.active_connections }}   - Number of active connections

{{ processes.by_cpu }}             - Top processes by CPU
{{ processes.by_cpu[0].name }}
{{ processes.by_cpu[0].cpu }}
{{ processes.by_cpu[0].memory }}
```

**HWiNFO64 metrics (when available):**
```
{{ hwinfo.available }}             - true/false

# Network (real-time throughput)
{{ hwinfo.network.download_rate }} - e.g., "1.5 MB/s"
{{ hwinfo.network.upload_rate }}   - e.g., "256 KB/s"
{{ hwinfo.network.total_download }} - Total downloaded
{{ hwinfo.network.total_upload }}  - Total uploaded

# Temperatures
{{ hwinfo.temps.cpu_temp }}        - e.g., "45°C"
{{ hwinfo.temps.gpu_temp }}        - e.g., "52°C"
{{ hwinfo.temps.system_temp }}     - Motherboard temp

# GPU
{{ hwinfo.gpu.usage_percent }}     - GPU load %
{{ hwinfo.gpu.usage_bar }}         - Visual bar
{{ hwinfo.gpu.memory_used }}       - e.g., "2048 MB"
{{ hwinfo.gpu.clock_mhz }}         - GPU clock speed
{{ hwinfo.gpu.power_watts }}       - Power consumption

# Fans
{{ hwinfo.fans }}                  - Array of fan speeds
{{ hwinfo.fans[0].name }}
{{ hwinfo.fans[0].rpm }}
```

## Troubleshooting

### TRMNL shows old data or nothing
- Check the server is running: `http://YOUR_IP:8080/health`
- Verify firewall allows port 8080
- Check TRMNL can reach your server (must be on same network or publicly accessible)

### "Connection refused" errors
- Server might not be running
- Wrong IP address configured
- Firewall blocking the connection

### High CPU usage
- The `psutil.cpu_percent(interval=1)` call blocks for 1 second
- This is normal and ensures accurate readings

### HWiNFO64 not detected
- Ensure HWiNFO is running in **Sensors-only** mode
- Check **Shared Memory Support** is enabled in HWiNFO settings
- Verify Remote Sensor Monitor is running: `http://localhost:55555`
- Check you're using HWiNFO v6.42 or earlier (or Pro version)
- The free version's shared memory expires after 12 hours - restart HWiNFO

### HWiNFO network speed shows 0 or N/A
- Network monitoring may need to be enabled in HWiNFO
- Go to HWiNFO Settings → Sensor / Other → Network monitoring
- Some adapters may not report throughput

## Network Requirements

Your TRMNL device needs to reach your Windows Server:

| Setup | Requirements |
|-------|-------------|
| Same LAN | Server's local IP (e.g., 192.168.1.100:8080) |
| Remote | Port forwarding or VPN or use webhook method |
| Cloud Server | Public IP with firewall rule |

## Security Considerations

- The metrics endpoint has no authentication by default
- Only expose on trusted networks
- Consider adding basic auth or running behind a reverse proxy with auth
- The webhook method avoids exposing any ports

## Files

| File | Description |
|------|-------------|
| `server.py` | HTTP server that exposes metrics (polling method) |
| `webhook_push.py` | Script to push metrics to TRMNL (webhook method) |
| `trmnl_markup.html` | TRMNL display template |
| `requirements.txt` | Python dependencies |

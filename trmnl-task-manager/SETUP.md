# TRMNL Task Manager Widget

Display Windows Server 2019 Task Manager metrics on your TRMNL e-ink display.

![Preview](preview-concept.png)

## Features

- Real-time CPU usage with progress bar
- Memory usage and availability
- Disk usage per partition
- Network I/O statistics
- Top processes by CPU/Memory
- System uptime and hostname

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

## Customizing the Display

Edit `trmnl_markup.html` to customize what's shown. TRMNL uses [Liquid templating](https://shopify.github.io/liquid/).

### Available Variables

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

{{ processes.by_cpu }}             - Top processes by CPU
{{ processes.by_cpu[0].name }}
{{ processes.by_cpu[0].cpu }}
{{ processes.by_cpu[0].memory }}
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

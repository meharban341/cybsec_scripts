"""
TRMNL Task Manager Widget - Windows Server Metrics API
Collects system performance metrics and exposes them for TRMNL polling.

Supports optional HWiNFO64 integration via Remote Sensor Monitor for
detailed hardware metrics (temps, voltages, network throughput, etc.)

Run this on your Windows Server 2019 machine.
"""

import json
import psutil
import platform
import socket
import urllib.request
import urllib.error
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional

# Configuration
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 8080       # Change if needed

# HWiNFO64 Remote Sensor Monitor Integration (optional)
# Download from: https://www.hwinfo.com/forum/threads/introducing-remote-sensor-monitor-a-restful-web-server.1025/
HWINFO_ENABLED = True                    # Set to False to disable HWiNFO integration
HWINFO_HOST = "127.0.0.1"                # Remote Sensor Monitor host
HWINFO_PORT = 55555                      # Remote Sensor Monitor port (default: 55555)
HWINFO_TIMEOUT = 2                       # Timeout in seconds


def get_size(bytes_val: float, suffix: str = "B") -> str:
    """Convert bytes to human readable format."""
    for unit in ["", "K", "M", "G", "T"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f}{unit}{suffix}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f}P{suffix}"


def get_cpu_metrics() -> dict[str, Any]:
    """Get CPU performance metrics."""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_freq = psutil.cpu_freq()
    cpu_count = psutil.cpu_count()
    cpu_count_logical = psutil.cpu_count(logical=True)

    # Per-core usage
    per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)

    return {
        "usage_percent": cpu_percent,
        "frequency_mhz": round(cpu_freq.current, 0) if cpu_freq else "N/A",
        "frequency_max_mhz": round(cpu_freq.max, 0) if cpu_freq else "N/A",
        "cores_physical": cpu_count,
        "cores_logical": cpu_count_logical,
        "per_core_usage": per_cpu[:8],  # Limit to 8 cores for display
        "usage_bar": "█" * int(cpu_percent / 10) + "░" * (10 - int(cpu_percent / 10))
    }


def get_memory_metrics() -> dict[str, Any]:
    """Get memory performance metrics."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "total": get_size(mem.total),
        "available": get_size(mem.available),
        "used": get_size(mem.used),
        "usage_percent": mem.percent,
        "swap_total": get_size(swap.total),
        "swap_used": get_size(swap.used),
        "swap_percent": swap.percent,
        "usage_bar": "█" * int(mem.percent / 10) + "░" * (10 - int(mem.percent / 10))
    }


def get_disk_metrics() -> dict[str, Any]:
    """Get disk performance metrics."""
    partitions = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            partitions.append({
                "device": partition.device[:10],  # Truncate for display
                "mountpoint": partition.mountpoint,
                "total": get_size(usage.total),
                "used": get_size(usage.used),
                "free": get_size(usage.free),
                "percent": usage.percent,
                "usage_bar": "█" * int(usage.percent / 10) + "░" * (10 - int(usage.percent / 10))
            })
        except PermissionError:
            continue

    # Disk I/O
    disk_io = psutil.disk_io_counters()

    return {
        "partitions": partitions[:4],  # Limit to 4 partitions for display
        "io_read": get_size(disk_io.read_bytes) if disk_io else "N/A",
        "io_write": get_size(disk_io.write_bytes) if disk_io else "N/A"
    }


def get_network_metrics() -> dict[str, Any]:
    """Get network performance metrics."""
    net_io = psutil.net_io_counters()

    # Get active connections count
    connections = len(psutil.net_connections())

    return {
        "bytes_sent": get_size(net_io.bytes_sent),
        "bytes_recv": get_size(net_io.bytes_recv),
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv,
        "active_connections": connections
    }


# =============================================================================
# HWiNFO64 Integration via Remote Sensor Monitor
# =============================================================================

def fetch_hwinfo_data() -> Optional[list[dict]]:
    """Fetch sensor data from HWiNFO64 via Remote Sensor Monitor."""
    if not HWINFO_ENABLED:
        return None

    try:
        url = f"http://{HWINFO_HOST}:{HWINFO_PORT}"
        request = urllib.request.Request(url, headers={'User-Agent': 'TRMNL-TaskManager/1.0'})
        with urllib.request.urlopen(request, timeout=HWINFO_TIMEOUT) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        # HWiNFO not available, fail silently
        return None


def find_hwinfo_sensor(data: list[dict], sensor_class: str = None,
                        sensor_name: str = None, partial_match: bool = True) -> Optional[dict]:
    """Find a specific sensor in HWiNFO data."""
    if not data:
        return None

    for sensor in data:
        class_match = True
        name_match = True

        if sensor_class:
            if partial_match:
                class_match = sensor_class.lower() in sensor.get('SensorClass', '').lower()
            else:
                class_match = sensor.get('SensorClass', '').lower() == sensor_class.lower()

        if sensor_name:
            if partial_match:
                name_match = sensor_name.lower() in sensor.get('SensorName', '').lower()
            else:
                name_match = sensor.get('SensorName', '').lower() == sensor_name.lower()

        if class_match and name_match:
            return sensor

    return None


def find_hwinfo_sensors(data: list[dict], sensor_class: str = None,
                         sensor_name: str = None, partial_match: bool = True) -> list[dict]:
    """Find all matching sensors in HWiNFO data."""
    if not data:
        return []

    results = []
    for sensor in data:
        class_match = True
        name_match = True

        if sensor_class:
            if partial_match:
                class_match = sensor_class.lower() in sensor.get('SensorClass', '').lower()
            else:
                class_match = sensor.get('SensorClass', '').lower() == sensor_class.lower()

        if sensor_name:
            if partial_match:
                name_match = sensor_name.lower() in sensor.get('SensorName', '').lower()
            else:
                name_match = sensor.get('SensorName', '').lower() == sensor_name.lower()

        if class_match and name_match:
            results.append(sensor)

    return results


def get_hwinfo_network_metrics(hwinfo_data: list[dict]) -> dict[str, Any]:
    """Extract network metrics from HWiNFO64 data."""
    if not hwinfo_data:
        return {}

    network = {
        "available": True,
        "adapters": []
    }

    # Find network-related sensors
    # Common HWiNFO network sensor names:
    # - "Current DL rate" / "Current UL rate" (download/upload speed)
    # - "DL Bandwidth Usage" / "UL Bandwidth Usage"
    # - "Total DL" / "Total UL" (total transferred)

    dl_rate = find_hwinfo_sensor(hwinfo_data, sensor_name="Current DL rate")
    ul_rate = find_hwinfo_sensor(hwinfo_data, sensor_name="Current UL rate")
    dl_total = find_hwinfo_sensor(hwinfo_data, sensor_name="Total DL")
    ul_total = find_hwinfo_sensor(hwinfo_data, sensor_name="Total UL")

    # Also look for per-adapter stats
    dl_rates = find_hwinfo_sensors(hwinfo_data, sensor_name="DL rate")
    ul_rates = find_hwinfo_sensors(hwinfo_data, sensor_name="UL rate")

    if dl_rate:
        network["download_rate"] = f"{dl_rate.get('SensorValue', '0')} {dl_rate.get('SensorUnit', 'KB/s')}"
        network["download_rate_value"] = float(dl_rate.get('SensorValue', 0))

    if ul_rate:
        network["upload_rate"] = f"{ul_rate.get('SensorValue', '0')} {ul_rate.get('SensorUnit', 'KB/s')}"
        network["upload_rate_value"] = float(ul_rate.get('SensorValue', 0))

    if dl_total:
        network["total_download"] = f"{dl_total.get('SensorValue', '0')} {dl_total.get('SensorUnit', 'MB')}"

    if ul_total:
        network["total_upload"] = f"{ul_total.get('SensorValue', '0')} {ul_total.get('SensorUnit', 'MB')}"

    # Build per-adapter info if available
    for dl in dl_rates:
        adapter_name = dl.get('SensorClass', 'Unknown')
        # Find matching upload rate
        ul = None
        for u in ul_rates:
            if u.get('SensorClass') == adapter_name:
                ul = u
                break

        network["adapters"].append({
            "name": adapter_name[:25],
            "download": f"{dl.get('SensorValue', '0')} {dl.get('SensorUnit', 'KB/s')}",
            "upload": f"{ul.get('SensorValue', '0')} {ul.get('SensorUnit', 'KB/s')}" if ul else "N/A"
        })

    return network


def get_hwinfo_temps(hwinfo_data: list[dict]) -> dict[str, Any]:
    """Extract temperature readings from HWiNFO64 data."""
    if not hwinfo_data:
        return {}

    temps = {}

    # CPU Temperature
    cpu_temp = find_hwinfo_sensor(hwinfo_data, sensor_name="CPU Package")
    if not cpu_temp:
        cpu_temp = find_hwinfo_sensor(hwinfo_data, sensor_name="CPU (Tctl/Tdie)")
    if not cpu_temp:
        cpu_temp = find_hwinfo_sensor(hwinfo_data, sensor_name="Core Temperatures")

    if cpu_temp and cpu_temp.get('SensorUnit') == '°C':
        temps["cpu_temp"] = f"{cpu_temp.get('SensorValue', 'N/A')}°C"
        temps["cpu_temp_value"] = float(cpu_temp.get('SensorValue', 0))

    # GPU Temperature
    gpu_temp = find_hwinfo_sensor(hwinfo_data, sensor_name="GPU Temperature")
    if gpu_temp and gpu_temp.get('SensorUnit') == '°C':
        temps["gpu_temp"] = f"{gpu_temp.get('SensorValue', 'N/A')}°C"
        temps["gpu_temp_value"] = float(gpu_temp.get('SensorValue', 0))

    # Motherboard/System temp
    sys_temp = find_hwinfo_sensor(hwinfo_data, sensor_name="System")
    if not sys_temp:
        sys_temp = find_hwinfo_sensor(hwinfo_data, sensor_name="Motherboard")

    if sys_temp and sys_temp.get('SensorUnit') == '°C':
        temps["system_temp"] = f"{sys_temp.get('SensorValue', 'N/A')}°C"

    # SSD/HDD temps
    drive_temps = find_hwinfo_sensors(hwinfo_data, sensor_name="Drive Temperature")
    if drive_temps:
        temps["drive_temps"] = []
        for dt in drive_temps[:4]:  # Limit to 4 drives
            temps["drive_temps"].append({
                "name": dt.get('SensorClass', 'Drive')[:15],
                "temp": f"{dt.get('SensorValue', 'N/A')}°C"
            })

    return temps


def get_hwinfo_gpu_metrics(hwinfo_data: list[dict]) -> dict[str, Any]:
    """Extract GPU metrics from HWiNFO64 data."""
    if not hwinfo_data:
        return {}

    gpu = {}

    # GPU Usage/Load
    gpu_load = find_hwinfo_sensor(hwinfo_data, sensor_name="GPU Core Load")
    if not gpu_load:
        gpu_load = find_hwinfo_sensor(hwinfo_data, sensor_name="GPU Utilization")

    if gpu_load:
        gpu["usage_percent"] = float(gpu_load.get('SensorValue', 0))
        gpu["usage_bar"] = "█" * int(gpu["usage_percent"] / 10) + "░" * (10 - int(gpu["usage_percent"] / 10))

    # GPU Memory
    gpu_mem = find_hwinfo_sensor(hwinfo_data, sensor_name="GPU Memory Usage")
    if not gpu_mem:
        gpu_mem = find_hwinfo_sensor(hwinfo_data, sensor_name="GPU Memory Allocated")

    if gpu_mem:
        gpu["memory_used"] = f"{gpu_mem.get('SensorValue', '0')} {gpu_mem.get('SensorUnit', 'MB')}"

    # GPU Clock
    gpu_clock = find_hwinfo_sensor(hwinfo_data, sensor_name="GPU Clock")
    if gpu_clock:
        gpu["clock_mhz"] = f"{gpu_clock.get('SensorValue', '0')} MHz"

    # GPU Power
    gpu_power = find_hwinfo_sensor(hwinfo_data, sensor_name="GPU Power")
    if gpu_power:
        gpu["power_watts"] = f"{gpu_power.get('SensorValue', '0')} W"

    return gpu


def get_hwinfo_fan_speeds(hwinfo_data: list[dict]) -> list[dict]:
    """Extract fan speed readings from HWiNFO64 data."""
    if not hwinfo_data:
        return []

    fans = []
    fan_sensors = find_hwinfo_sensors(hwinfo_data, sensor_name="Fan")

    for fan in fan_sensors[:6]:  # Limit to 6 fans
        if fan.get('SensorUnit') == 'RPM':
            fans.append({
                "name": fan.get('SensorName', 'Fan')[:15],
                "rpm": f"{fan.get('SensorValue', '0')} RPM"
            })

    return fans


def get_all_hwinfo_metrics() -> dict[str, Any]:
    """Collect all HWiNFO64 metrics."""
    hwinfo_data = fetch_hwinfo_data()

    if not hwinfo_data:
        return {"available": False}

    return {
        "available": True,
        "network": get_hwinfo_network_metrics(hwinfo_data),
        "temps": get_hwinfo_temps(hwinfo_data),
        "gpu": get_hwinfo_gpu_metrics(hwinfo_data),
        "fans": get_hwinfo_fan_speeds(hwinfo_data)
    }


def get_top_processes(limit: int = 5) -> list[dict[str, Any]]:
    """Get top processes by CPU and memory usage."""
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            processes.append({
                "pid": pinfo['pid'],
                "name": pinfo['name'][:20] if pinfo['name'] else "Unknown",
                "cpu": round(pinfo['cpu_percent'] or 0, 1),
                "memory": round(pinfo['memory_percent'] or 0, 1)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by CPU usage
    top_cpu = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:limit]
    # Sort by memory usage
    top_mem = sorted(processes, key=lambda x: x['memory'], reverse=True)[:limit]

    return {
        "by_cpu": top_cpu,
        "by_memory": top_mem
    }


def get_system_info() -> dict[str, Any]:
    """Get general system information."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time

    # Format uptime
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m"

    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version()[:30],
        "architecture": platform.machine(),
        "uptime": uptime_str,
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M")
    }


def collect_all_metrics() -> dict[str, Any]:
    """Collect all system metrics for TRMNL."""
    metrics = {
        "merge_variables": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": get_system_info(),
            "cpu": get_cpu_metrics(),
            "memory": get_memory_metrics(),
            "disk": get_disk_metrics(),
            "network": get_network_metrics(),
            "processes": get_top_processes(5),
            "hwinfo": get_all_hwinfo_metrics()
        }
    }

    # If HWiNFO network data is available, enhance the network section
    hwinfo = metrics["merge_variables"]["hwinfo"]
    if hwinfo.get("available") and hwinfo.get("network", {}).get("download_rate"):
        metrics["merge_variables"]["network"]["hwinfo_download"] = hwinfo["network"].get("download_rate", "N/A")
        metrics["merge_variables"]["network"]["hwinfo_upload"] = hwinfo["network"].get("upload_rate", "N/A")

    return metrics


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics endpoint."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/" or self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            metrics = collect_all_metrics()
            self.wfile.write(json.dumps(metrics, indent=2).encode())

        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Custom logging."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    """Start the metrics server."""
    # Check HWiNFO availability
    hwinfo_status = "Disabled"
    if HWINFO_ENABLED:
        hwinfo_data = fetch_hwinfo_data()
        if hwinfo_data:
            hwinfo_status = f"Connected ({len(hwinfo_data)} sensors)"
        else:
            hwinfo_status = f"Not detected (port {HWINFO_PORT})"

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          TRMNL Task Manager Widget - Metrics Server          ║
╠══════════════════════════════════════════════════════════════╣
║  Endpoints:                                                  ║
║    GET /metrics  - Returns all system metrics (JSON)         ║
║    GET /health   - Health check                              ║
╠══════════════════════════════════════════════════════════════╣
║  HWiNFO64: {hwinfo_status:<49}║
╠══════════════════════════════════════════════════════════════╣
║  For TRMNL Polling URL use:                                  ║
║    http://<your-server-ip>:{PORT}/metrics                    ║
╚══════════════════════════════════════════════════════════════╝
    """)

    server = HTTPServer((HOST, PORT), MetricsHandler)
    print(f"Server running on http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    main()

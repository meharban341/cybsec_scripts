"""
TRMNL Task Manager Widget - Windows Server Metrics API
Collects system performance metrics and exposes them for TRMNL polling.

Run this on your Windows Server 2019 machine.
"""

import json
import psutil
import platform
import socket
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

# Configuration
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 8080       # Change if needed


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
    return {
        "merge_variables": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": get_system_info(),
            "cpu": get_cpu_metrics(),
            "memory": get_memory_metrics(),
            "disk": get_disk_metrics(),
            "network": get_network_metrics(),
            "processes": get_top_processes(5)
        }
    }


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
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          TRMNL Task Manager Widget - Metrics Server          ║
╠══════════════════════════════════════════════════════════════╣
║  Endpoints:                                                  ║
║    GET /metrics  - Returns all system metrics (JSON)         ║
║    GET /health   - Health check                              ║
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

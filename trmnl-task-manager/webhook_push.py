"""
TRMNL Task Manager Widget - Webhook Push Script
Pushes system metrics to TRMNL webhook endpoint.

Use this if you prefer to push data rather than having TRMNL poll.
Schedule this script to run periodically (e.g., every 5 minutes via Task Scheduler).
"""

import json
import urllib.request
import urllib.error
import psutil
import platform
import socket
from datetime import datetime
from typing import Any

# ============================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================
TRMNL_WEBHOOK_URL = "https://usetrmnl.com/api/custom_plugins/YOUR_PLUGIN_UUID"
# ============================================


def get_size(bytes_val: float, suffix: str = "B") -> str:
    """Convert bytes to human readable format."""
    for unit in ["", "K", "M", "G", "T"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f}{unit}{suffix}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f}P{suffix}"


def collect_metrics() -> dict[str, Any]:
    """Collect all system metrics."""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_freq = psutil.cpu_freq()

    # Memory
    mem = psutil.virtual_memory()

    # Disk
    disk_info = []
    for partition in psutil.disk_partitions()[:2]:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({
                "mountpoint": partition.mountpoint,
                "percent": usage.percent,
                "used": get_size(usage.used),
                "total": get_size(usage.total)
            })
        except PermissionError:
            continue

    # Network
    net_io = psutil.net_io_counters()

    # Top processes
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            processes.append({
                "name": (pinfo['name'] or "Unknown")[:20],
                "cpu": round(pinfo['cpu_percent'] or 0, 1),
                "memory": round(pinfo['memory_percent'] or 0, 1)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    top_procs = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:4]

    # System info
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    days = uptime.days
    hours = uptime.seconds // 3600

    return {
        "merge_variables": {
            "timestamp": datetime.now().strftime("%H:%M"),
            "system": {
                "hostname": socket.gethostname(),
                "os": platform.system(),
                "uptime": f"{days}d {hours}h"
            },
            "cpu": {
                "usage_percent": cpu_percent,
                "frequency_mhz": round(cpu_freq.current, 0) if cpu_freq else 0,
                "cores_logical": psutil.cpu_count(logical=True),
                "usage_bar": "█" * int(cpu_percent / 10) + "░" * (10 - int(cpu_percent / 10))
            },
            "memory": {
                "usage_percent": mem.percent,
                "used": get_size(mem.used),
                "total": get_size(mem.total),
                "usage_bar": "█" * int(mem.percent / 10) + "░" * (10 - int(mem.percent / 10))
            },
            "disk": {
                "partitions": disk_info
            },
            "network": {
                "bytes_sent": get_size(net_io.bytes_sent),
                "bytes_recv": get_size(net_io.bytes_recv)
            },
            "processes": {
                "by_cpu": top_procs
            }
        }
    }


def push_to_trmnl(data: dict) -> bool:
    """Push metrics to TRMNL webhook."""
    if "YOUR_PLUGIN_UUID" in TRMNL_WEBHOOK_URL:
        print("ERROR: Please update TRMNL_WEBHOOK_URL with your plugin UUID!")
        print("Find it in: TRMNL Dashboard > Your Plugin > Settings > Webhook URL")
        return False

    try:
        json_data = json.dumps(data).encode('utf-8')

        request = urllib.request.Request(
            TRMNL_WEBHOOK_URL,
            data=json_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'TRMNL-TaskManager/1.0'
            },
            method='POST'
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status == 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Metrics pushed successfully!")
                return True
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Push failed: {response.status}")
                return False

    except urllib.error.URLError as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Network error: {e}")
        return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
        return False


def main():
    """Collect and push metrics."""
    print("Collecting system metrics...")
    metrics = collect_metrics()

    print("Pushing to TRMNL...")
    success = push_to_trmnl(metrics)

    if success:
        print("Done!")
    else:
        print("Failed to push metrics. Check your webhook URL and network connection.")


if __name__ == "__main__":
    main()

"""
Module: system_heartbeat
=======================

This module provides a simple heartbeat mechanism for a diagnostic agent
running on a Raspberry Pi. The heartbeat periodically collects basic
system metrics such as uptime, CPU temperature, disk usage, and network
interface details. Collected data are stored in JSON format at a
configured path (`/agent_memory/connectivity.json` by default). The
module exposes a `start_heartbeat` function which spawns a daemon
thread to perform this work in the background.

Design considerations:

* **Efficiency**: The collector sleeps between cycles and avoids
  expensive operations. It uses Python's standard library where
  possible, falling back on `psutil` if available for more detailed
  metrics.
* **Resilience**: All data gathering operations are wrapped in
  `try/except` blocks. When a metric cannot be retrieved, a
  placeholder value such as ``"unavailable"`` is returned instead of
  raising an exception.
* **Extensibility**: New metrics can be added by defining helper
  functions similar to the existing ones and including them in the
  heartbeat data structure.

Example usage::

    from system_heartbeat import start_heartbeat
    # Start heartbeat thread with a 60‑second interval
    thread = start_heartbeat(interval=60)
    # Continue running your main application code...

Note that the thread is marked as a daemon; it will not prevent
program exit if the main thread finishes.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Union

try:
    # psutil provides convenient access to system metrics but may not be
    # installed on all systems. Import errors are handled gracefully.
    import psutil  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    psutil = None  # type: ignore


def _get_system_uptime() -> Union[float, str]:
    """
    Retrieve the system uptime in seconds.

    Tries to read ``/proc/uptime`` first (available on Linux systems
    including the Raspberry Pi). If that fails, attempts to fall back
    to ``psutil.boot_time()``. On failure, returns ``"unavailable"``.

    :returns: Uptime in seconds as a float, or ``"unavailable"`` if it
              cannot be determined.
    """
    try:
        # /proc/uptime returns two numbers: uptime and idle time.
        with open("/proc/uptime", "r", encoding="utf-8") as f:
            uptime_seconds_str = f.readline().split()[0]
            return float(uptime_seconds_str)
    except Exception:
        # Fallback: if psutil is available, derive uptime from boot time
        if psutil is not None:
            try:
                return float(time.time() - psutil.boot_time())
            except Exception:
                pass
        return "unavailable"


def _get_cpu_temperature() -> Union[float, str]:
    """
    Obtain the current CPU temperature in degrees Celsius.

    On a Raspberry Pi, the temperature is exposed via
    ``/sys/class/thermal/thermal_zone0/temp``. If that fails, the
    function attempts to use `psutil.sensors_temperatures`. If both
    methods fail, returns ``"unavailable"``.

    :returns: Temperature in Celsius as a float, or ``"unavailable"`` if
              not obtainable.
    """
    # Try the standard Raspberry Pi thermal zone
    thermal_path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(thermal_path, "r", encoding="utf-8") as f:
            milli_celsius = int(f.readline().strip())
            return milli_celsius / 1000.0
    except Exception:
        # Fallback to psutil if available
        if psutil is not None:
            try:
                temps: Dict[str, List[psutil._common.sdiskpart]] = psutil.sensors_temperatures()  # type: ignore
                # Iterate through all temperature sensors and pick the first with a reading
                for entries in temps.values():
                    for entry in entries:
                        current = getattr(entry, "current", None)
                        if current is not None:
                            return float(current)
            except Exception:
                pass
        return "unavailable"


def _get_disk_usage() -> Union[Dict[str, Union[int, float]], str]:
    """
    Collect disk usage statistics for the root filesystem.

    Uses `psutil.disk_usage` if available; otherwise falls back to
    ``os.statvfs``. The returned dictionary contains raw byte counts
    along with a usage percentage.

    :returns: A dictionary with keys ``total``, ``used``, ``free`` and
              ``percent`` describing the disk usage, or ``"unavailable"``
              if metrics cannot be gathered.
    """
    try:
        if psutil is not None:
            usage = psutil.disk_usage("/")  # type: ignore
            return {
                "total": int(usage.total),
                "used": int(usage.used),
                "free": int(usage.free),
                "percent": float(usage.percent),
            }
        # Fallback using os.statvfs
        stat = os.statvfs("/")
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_bsize
        used = total - free
        percent = (used / total * 100.0) if total else 0.0
        return {
            "total": int(total),
            "used": int(used),
            "free": int(free),
            "percent": float(percent),
        }
    except Exception:
        return "unavailable"


def _get_network_interfaces() -> Union[Dict[str, Dict[str, Union[List[str], bool]]], str]:
    """
    Gather information about network interfaces.

    Returns a mapping keyed by interface name. Each value contains a
    list of IPv4 addresses and a boolean indicating whether the
    interface is operational (``True`` for up, ``False`` for down).
    Attempts to use psutil when available, falling back to invoking
    the ``ip -j address`` command.

    :returns: A dictionary mapping interface names to dictionaries with
              keys ``ip_addresses`` and ``is_up``, or ``"unavailable"``
              if metrics cannot be gathered.
    """
    interfaces: Dict[str, Dict[str, Union[List[str], bool]]] = {}
    # First attempt to use psutil if it provides detailed interface information
    if psutil is not None:
        try:
            addrs = psutil.net_if_addrs()  # type: ignore
            stats = psutil.net_if_stats()  # type: ignore
            for name, addr_list in addrs.items():
                ip_addresses: List[str] = []
                # Filter for IPv4 addresses
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        ip_addresses.append(addr.address)
                iface_stat = stats.get(name)
                is_up = bool(iface_stat.isup) if iface_stat is not None else False
                interfaces[name] = {
                    "ip_addresses": ip_addresses,
                    "is_up": is_up,
                }
        except Exception:
            # In case psutil failed, fall back to parsing ip command output
            interfaces = {}

    # If no interfaces found via psutil or psutil isn't available, use ip command
    if not interfaces:
        try:
            # Use 'ip' to fetch JSON formatted interface data. The '-j' flag
            # tells iproute2 to output JSON, which simplifies parsing.
            ip_output = subprocess.check_output(
                ["ip", "-j", "address"],
                stderr=subprocess.DEVNULL,
                encoding="utf-8",
            )
            parsed: List[Dict[str, Union[str, List]]]
            parsed = json.loads(ip_output)
            for iface in parsed:
                name = str(iface.get("ifname", ""))
                addr_info = iface.get("addr_info", [])
                ip_addresses: List[str] = []
                if isinstance(addr_info, list):
                    for addr in addr_info:
                        if addr.get("family") == "inet":
                            ip_local = addr.get("local")
                            if ip_local:
                                ip_addresses.append(str(ip_local))
                # Some kernels report "UP" or "DOWN" in operstate
                operstate = str(iface.get("operstate", "")).upper()
                interfaces[name] = {
                    "ip_addresses": ip_addresses,
                    "is_up": operstate == "UP",
                }
        except Exception:
            # If everything fails, return unavailable
            return "unavailable"
    return interfaces


def _collect_heartbeat() -> Dict[str, Union[float, str, Dict]]:
    """
    Collect all heartbeat metrics into a single dictionary.

    The structure of the returned dictionary is as follows::

        {
            "uptime_seconds": <float or "unavailable">,
            "cpu_temperature_celsius": <float or "unavailable">,
            "disk_usage": <dict or "unavailable">,
            "network_interfaces": <dict or "unavailable">,
            "last_updated": <ISO 8601 timestamp string>
        }

    :returns: A dictionary containing metrics and a timestamp.
    """
    return {
        "uptime_seconds": _get_system_uptime(),
        "cpu_temperature_celsius": _get_cpu_temperature(),
        "disk_usage": _get_disk_usage(),
        "network_interfaces": _get_network_interfaces(),
        # Use UTC ISO8601 format with a trailing 'Z' to denote Zulu time
        "last_updated": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def _write_heartbeat_to_file(
    data: Dict[str, Union[float, str, Dict]],
    filepath: str = "/agent_memory/connectivity.json",
) -> bool:
    """
    Serialize the provided heartbeat data to JSON and write it to a file.

    :param data: The heartbeat dictionary returned from
                 ``_collect_heartbeat``.
    :param filepath: Destination path for the JSON output. If the
                     directory does not exist, it will be created. The
                     default path is ``/agent_memory/connectivity.json``.
    :returns: ``True`` if the file was written successfully, ``False``
              otherwise.
    """
    try:
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        # In case of any write error, return False
        return False


def _heartbeat_loop(interval: int) -> None:
    """
    Internal loop that continuously collects and writes heartbeat data.

    :param interval: Number of seconds to wait between each
                     heartbeat collection. A minimum of 1 second is
                     enforced to avoid busy looping.
    """
    # Ensure the interval is at least 1 second
    sleep_interval = max(1, int(interval))
    while True:
        data = _collect_heartbeat()
        _write_heartbeat_to_file(data)
        # Sleep outside the collection to allow other threads to run
        time.sleep(sleep_interval)


def start_heartbeat(interval: int = 60) -> threading.Thread:
    """
    Start the heartbeat thread.

    Spawns a daemon thread which repeatedly invokes the internal
    heartbeat loop at the given interval. The thread will run until
    the parent process exits. Use this function from the main
    application to begin collecting heartbeat metrics.

    :param interval: Number of seconds between heartbeats. Defaults to
                     60 seconds. Values less than 1 second are
                     coerced to 1 second.
    :returns: The ``threading.Thread`` instance representing the
              heartbeat thread. The thread is started before
              returning.
    """
    # Instantiate the thread as a daemon so it won't block program exit
    thread = threading.Thread(
        target=_heartbeat_loop,
        args=(interval,),
        name="system_heartbeat",
        daemon=True,
    )
    thread.start()
    return thread


__all__ = [
    "start_heartbeat",
    # Expose helper functions for testing or advanced usage
    "_collect_heartbeat",
    "_write_heartbeat_to_file",
    "_get_system_uptime",
    "_get_cpu_temperature",
    "_get_disk_usage",
    "_get_network_interfaces",
]
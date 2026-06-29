#!/usr/bin/env python3
"""
ADB Tool for Android TV.
Wraps ADB commands into a clean, JSON-friendly CLI utility for easy programmatic use.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional


class ADBTool:
    def __init__(self, serial: Optional[str] = None):
        self.serial = serial or os.environ.get("ADB_SERIAL")
        # Locate ADB
        self.adb_path = "adb"
        # Check if adb is in a specific known location from the environment check
        known_adb = "/home/macd/android-sdk/platform-tools/adb"
        if os.path.exists(known_adb):
            self.adb_path = known_adb

    def _run_cmd(self, args: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Helper to run adb commands with correct serial targeting."""
        cmd = [self.adb_path]
        if self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                text=True,
                check=False
            )
            return result
        except FileNotFoundError:
            print(json.dumps({"error": f"ADB executable not found at '{self.adb_path}'"}), file=sys.stderr)
            sys.exit(1)

    def _get_devices(self) -> List[Dict[str, str]]:
        """Returns list of connected devices."""
        try:
            result = subprocess.run(
                [self.adb_path, "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
        except FileNotFoundError:
            return []

        devices = []
        for line in result.stdout.splitlines():
            if line.startswith("List of devices") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                devices.append({
                    "serial": parts[0],
                    "status": parts[1]
                })
        return devices

    def _auto_select_device(self):
        """If serial is not set, auto-select if exactly one device is connected."""
        if self.serial:
            return
        devices = self._get_devices()
        connected = [d for d in devices if d["status"] == "device"]
        if len(connected) == 1:
            self.serial = connected[0]["serial"]

    def _get_local_subnet(self) -> str:
        """Try to auto-detect the active local subnet range."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            parts = local_ip.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        except Exception:
            pass
        return "192.168.1.0/24"

    def _get_status_notes(self, status: str) -> str:
        """Friendly advice on device connection statuses."""
        if status == "device":
            return "Connected successfully. ADB debugging is enabled and authorized."
        elif status == "unauthorized":
            return "ADB debugging is enabled but UNAUTHORIZED. PLEASE CHECK YOUR TV SCREEN and select 'Always allow from this computer' / 'OK' to authorize."
        elif status == "offline":
            return "Device is offline. Try toggling ADB Debugging off and on in Developer Options on the TV."
        elif status == "disabled":
            return "Google Cast device detected, but ADB debugging is disabled or unsupported. Follow setup instructions to enable ADB."
        return "Unknown status. Ensure network ADB debugging is active."

    def _get_instructions(self) -> List[str]:
        """Instructions for enabling Wireless ADB debugging on Android TV."""
        return [
            "To enable Wireless ADB Debugging on your Android TV:",
            "  1. Go to Settings > Device Preferences (or System) > About.",
            "  2. Scroll down to 'Build' or 'OS Build' and click it 7 times until the toast 'You are now a developer!' appears.",
            "  3. Go back one screen and open the newly revealed 'Developer Options' menu.",
            "  4. Turn ON 'USB Debugging'.",
            "  5. Turn ON 'Network Debugging' or 'Wireless ADB Debugging' (if available). Note: Many TVs automatically expose network debugging on port 5555 as soon as USB Debugging is ON and they are connected to WiFi.",
            "  6. Find your TV's IP address under Settings > Network & Internet.",
            "  7. Run: adb_tool.py connect <TV_IP>"
        ]

    def _get_eureka_info(self, ip: str) -> Dict[str, Any]:
        """Query standard local Google Cast eureka_info endpoint for friendly name and model details."""
        url = f"http://{ip}:8008/setup/eureka_info"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=0.6) as response:
                data = json.loads(response.read().decode('utf-8'))
                return {
                    "friendly_name": data.get("name"),
                    "model_name": data.get("model_name"),
                    "manufacturer": data.get("manufacturer")
                }
        except Exception:
            pass
        return {}

    def scan_lan(self, subnet: Optional[str] = None, deep: bool = False) -> Dict[str, Any]:
        """Scan local subnet for port 5555 (ADB) and optionally port 8008 (Google Cast) to probe devices."""
        if not subnet:
            subnet = self._get_local_subnet()

        match = re.match(r"^(\d+\.\d+\.\d+)\.\d+/24$", subnet)
        if not match:
            return {"success": False, "error": f"Invalid subnet format. Expected CIDR (e.g. 192.168.1.0/24), got: {subnet}"}
        
        prefix = f"{match.group(1)}."

        import socket
        from concurrent.futures import ThreadPoolExecutor

        # Active devices discovery structure
        discovered_ports = {} # IP -> set of open ports

        def check_ip(ip: str):
            # Check ADB port
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                res = s.connect_ex((ip, 5555))
                if res == 0:
                    discovered_ports.setdefault(ip, set()).add(5555)
                s.close()
            except Exception:
                pass

            # If deep scan, check standard Google Cast port as well
            if deep:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    res = s.connect_ex((ip, 8008))
                    if res == 0:
                        discovered_ports.setdefault(ip, set()).add(8008)
                    s.close()
                except Exception:
                    pass

        ips = [f"{prefix}{i}" for i in range(1, 255)]
        with ThreadPoolExecutor(max_workers=50) as executor:
            executor.map(check_ip, ips)

        devices_found = []
        for ip in sorted(discovered_ports.keys()):
            ports = discovered_ports[ip]
            has_adb = 5555 in ports
            has_cast = 8008 in ports

            status = "disabled"
            if has_adb:
                target = f"{ip}:5555"
                # Refresh ADB session
                subprocess.run([self.adb_path, "disconnect", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run([self.adb_path, "connect", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                dev_res = subprocess.run([self.adb_path, "devices"], stdout=subprocess.PIPE, text=True)
                status = "unauthorized"
                for line in dev_res.stdout.splitlines():
                    if line.startswith(target):
                        status = line.split()[1]
                        break

            # Try to fetch Google Cast Eureka details if available
            friendly_name = None
            cast_model = None
            cast_man = None
            if has_cast:
                cast_details = self._get_eureka_info(ip)
                friendly_name = cast_details.get("friendly_name")
                cast_model = cast_details.get("model_name")
                cast_man = cast_details.get("manufacturer")

            device_info = {
                "ip": ip,
                "status": status,
                "notes": self._get_status_notes(status),
                "ports_open": sorted(list(ports))
            }
            if friendly_name:
                device_info["friendly_name"] = friendly_name

            # Query ADB properties if authorized
            if status == "device":
                try:
                    orig_serial = self.serial
                    self.serial = f"{ip}:5555"
                    
                    brand = self._run_cmd(["shell", "getprop", "ro.product.brand"]).stdout.strip()
                    model = self._run_cmd(["shell", "getprop", "ro.product.model"]).stdout.strip()
                    
                    app_info = self.get_current_app()
                    focused_app = app_info.get("focused_app") if app_info.get("success") else None
                    
                    device_info.update({
                        "brand": brand or cast_man or "unknown",
                        "model": model or cast_model or "unknown",
                        "focused_app": focused_app
                    })
                    
                    self.serial = orig_serial
                except Exception:
                    pass
            else:
                # Add basic brand/model if retrieved via cast interface
                if cast_man:
                    device_info["brand"] = cast_man
                if cast_model:
                    device_info["model"] = cast_model

            devices_found.append(device_info)

        instructions = []
        if not devices_found or any(d["status"] in ("unauthorized", "disabled") for d in devices_found):
            instructions = self._get_instructions()

        return {
            "success": True,
            "subnet_scanned": subnet,
            "deep_scan_active": deep,
            "devices_found": devices_found,
            "instructions": instructions
        }

    def connect(self, target: str) -> Dict[str, Any]:
        """Connect to an Android TV via IP/Port."""
        if ":" not in target:
            target = f"{target}:5555"
        
        result = subprocess.run(
            [self.adb_path, "connect", target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        success = "connected to" in result.stdout.lower() or "already connected" in result.stdout.lower()
        status = "unknown"
        if success:
            self.serial = target
            # Query dev status
            dev_res = subprocess.run([self.adb_path, "devices"], stdout=subprocess.PIPE, text=True)
            for line in dev_res.stdout.splitlines():
                if line.startswith(target):
                    status = line.split()[1]
                    break
            
        return {
            "action": "connect",
            "target": target,
            "success": success,
            "status": status,
            "notes": self._get_status_notes(status) if success else "Failed to connect. Is debugging enabled?",
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.stderr else None
        }

    def disconnect(self, target: Optional[str] = None) -> Dict[str, Any]:
        """Disconnect Android TV."""
        args = ["disconnect"]
        if target:
            if ":" not in target and target != "all":
                target = f"{target}:5555"
            args.append(target)
            
        result = subprocess.run(
            [self.adb_path] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return {
            "action": "disconnect",
            "target": target or "all",
            "success": result.returncode == 0,
            "output": result.stdout.strip()
        }

    def list_devices(self) -> Dict[str, Any]:
        """List all connected devices."""
        return {
            "devices": self._get_devices(),
            "current_serial": self.serial
        }

    def get_power_status(self) -> Dict[str, Any]:
        """Get the TV's power/screen state."""
        self._auto_select_device()
        result = self._run_cmd(["shell", "dumpsys", "power"])
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}

        wakefulness = "unknown"
        display_power = "unknown"
        
        for line in result.stdout.splitlines():
            if "mWakefulness=" in line:
                match = re.search(r"mWakefulness=(\w+)", line)
                if match:
                    wakefulness = match.group(1)
            elif "Display Power: state=" in line:
                match = re.search(r"state=(\w+)", line)
                if match:
                    display_power = match.group(1)

        is_on = None
        if display_power != "unknown":
            is_on = display_power.upper() == "ON"
        elif wakefulness != "unknown":
            is_on = wakefulness.upper() == "AWAKE"

        return {
            "success": True,
            "wakefulness": wakefulness,
            "display_power": display_power,
            "is_on": is_on
        }

    def set_power(self, state: str) -> Dict[str, Any]:
        """Turn power on/off or toggle."""
        self._auto_select_device()
        current = self.get_power_status()
        if not current.get("success"):
            return current

        target_state = state.lower()
        is_on = current.get("is_on")

        if target_state == "on" and is_on is True:
            return {"success": True, "action": "power_on", "changed": False, "status": "already on"}
        elif target_state == "off" and is_on is False:
            return {"success": True, "action": "power_off", "changed": False, "status": "already off"}

        if target_state == "on":
            result = self._run_cmd(["shell", "input", "keyevent", "224"])
        elif target_state == "off":
            result = self._run_cmd(["shell", "input", "keyevent", "223"])
        else:  # toggle
            result = self._run_cmd(["shell", "input", "keyevent", "26"])

        time.sleep(0.5)
        new_status = self.get_power_status()
        return {
            "success": result.returncode == 0,
            "action": f"power_{target_state}",
            "changed": is_on != new_status.get("is_on"),
            "new_state": new_status
        }

    def get_current_app(self) -> Dict[str, Any]:
        """Retrieve current foreground app and activity."""
        self._auto_select_device()
        result = self._run_cmd(["shell", "dumpsys", "window", "displays"])
        
        if result.returncode != 0 or "mCurrentFocus" not in result.stdout:
            result = self._run_cmd(["shell", "dumpsys", "window"])
            
        output = result.stdout
        focused_app = None
        
        match = re.search(r"mCurrentFocus=Window\{[a-f0-9]+ \S+ ([^/]+)/([^}]+)\}", output)
        if not match:
            match = re.search(r"mFocusedApp=ActivityRecord\{[a-f0-9]+ \S+ ([^/]+)/([^ ]+)", output)
        
        if not match:
            resumed_result = self._run_cmd(["shell", "dumpsys", "activity", "activities"])
            match = re.search(r"mResumedActivity: \S+ \S+ ([^/]+)/([^ ]+)", resumed_result.stdout)

        if match:
            package = match.group(1)
            activity = match.group(2).rstrip("}")
            focused_app = f"{package}/{activity}"
        else:
            package = "unknown"
            activity = "unknown"

        return {
            "success": result.returncode == 0,
            "focused_app": focused_app,
            "package": package,
            "activity": activity
        }

    def keyevent(self, key: str) -> Dict[str, Any]:
        """Send a keyevent to the device."""
        self._auto_select_device()
        
        key_map = {
            "up": "19", "dpad_up": "19",
            "down": "20", "dpad_down": "20",
            "left": "21", "dpad_left": "21",
            "right": "22", "dpad_right": "22",
            "enter": "23", "dpad_center": "23", "select": "23",
            "back": "4",
            "home": "3",
            "menu": "82",
            "play": "126",
            "pause": "127",
            "play_pause": "85", "playpause": "85",
            "stop": "86",
            "next": "87",
            "prev": "88", "previous": "88",
            "volume_up": "24", "vol_up": "24",
            "volume_down": "25", "vol_down": "25",
            "volume_mute": "164", "mute": "164",
            "power": "26",
            "sleep": "223",
            "wakeup": "224",
            "guide": "172",
            "settings": "176",
            "channel_up": "166", "ch_up": "166",
            "channel_down": "167", "ch_down": "167"
        }
        
        target_key = key.lower().strip()
        code = key_map.get(target_key, target_key)
        
        result = self._run_cmd(["shell", "input", "keyevent", code])
        return {
            "success": result.returncode == 0,
            "key": key,
            "keycode_used": code,
            "error": result.stderr.strip() if result.returncode != 0 else None
        }

    def input_text(self, text: str) -> Dict[str, Any]:
        """Send keyboard text input (escapes spaces)."""
        self._auto_select_device()
        escaped_text = text.replace(" ", "%s")
        
        result = self._run_cmd(["shell", "input", "text", escaped_text])
        return {
            "success": result.returncode == 0,
            "text": text,
            "sent_text": escaped_text,
            "error": result.stderr.strip() if result.returncode != 0 else None
        }

    def list_apps(self, third_party_only: bool = False) -> Dict[str, Any]:
        """List installed apps."""
        self._auto_select_device()
        args = ["shell", "pm", "list", "packages"]
        if third_party_only:
            args.append("-3")
            
        result = self._run_cmd(args)
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip()}
            
        packages = []
        for line in result.stdout.splitlines():
            if line.startswith("package:"):
                packages.append(line.replace("package:", "").strip())
                
        return {
            "success": True,
            "count": len(packages),
            "packages": sorted(packages)
        }

    def app_action(self, action: str, package: str) -> Dict[str, Any]:
        """Perform action on app: start, stop, clear, uninstall."""
        self._auto_select_device()
        action = action.lower()
        
        if action == "start":
            result = self._run_cmd(["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"])
            success = "using main activity" in result.stdout.lower() or result.returncode == 0
        elif action == "stop":
            result = self._run_cmd(["shell", "am", "force-stop", package])
            success = result.returncode == 0
        elif action == "clear":
            result = self._run_cmd(["shell", "pm", "clear", package])
            success = result.returncode == 0
        elif action == "uninstall":
            result = self._run_cmd(["uninstall", package])
            success = "success" in result.stdout.lower() or result.returncode == 0
        else:
            return {"success": False, "error": f"Unknown app action: {action}"}
            
        return {
            "success": success,
            "action": action,
            "package": package,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else None
        }

    def launch_uri(self, uri: str, package: Optional[str] = None) -> Dict[str, Any]:
        """Launch deep link URI, optionally with specific package target."""
        self._auto_select_device()
        args = ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", uri]
        if package:
            args.extend([package])
            
        result = self._run_cmd(args)
        success = "error" not in result.stdout.lower() and result.returncode == 0
        return {
            "success": success,
            "uri": uri,
            "package": package,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else None
        }

    def install_apk(self, local_path: str) -> Dict[str, Any]:
        """Install local APK file to TV."""
        self._auto_select_device()
        if not os.path.exists(local_path):
            return {"success": False, "error": f"Local file not found: {local_path}"}
            
        result = self._run_cmd(["install", "-r", local_path])
        success = "success" in result.stdout.lower() or result.returncode == 0
        return {
            "success": success,
            "apk_path": local_path,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else None
        }

    def capture_screenshot(self, output_path: str) -> Dict[str, Any]:
        """Capture screenshot from Android TV, pull to local machine, and clean up."""
        self._auto_select_device()
        remote_path = "/sdcard/screen.png"
        
        cap_res = self._run_cmd(["shell", "screencap", "-p", remote_path])
        if cap_res.returncode != 0:
            return {"success": False, "error": f"Failed to capture screen: {cap_res.stderr.strip()}"}
            
        pull_res = self._run_cmd(["pull", remote_path, output_path])
        if pull_res.returncode != 0:
            self._run_cmd(["shell", "rm", remote_path])
            return {"success": False, "error": f"Failed to pull screenshot: {pull_res.stderr.strip()}"}
            
        self._run_cmd(["shell", "rm", remote_path])
        
        return {
            "success": True,
            "local_path": os.path.abspath(output_path)
        }

    def get_info(self) -> Dict[str, Any]:
        """Gather detailed device information."""
        self._auto_select_device()
        
        brand = self._run_cmd(["shell", "getprop", "ro.product.brand"]).stdout.strip()
        model = self._run_cmd(["shell", "getprop", "ro.product.model"]).stdout.strip()
        version = self._run_cmd(["shell", "getprop", "ro.build.version.release"]).stdout.strip()
        sdk = self._run_cmd(["shell", "getprop", "ro.build.version.sdk"]).stdout.strip()
        
        size_res = self._run_cmd(["shell", "wm", "size"])
        size = "unknown"
        if size_res.returncode == 0:
            match = re.search(r"Physical size:\s*(\d+x\d+)", size_res.stdout)
            if match:
                size = match.group(1)

        power = self.get_power_status()
        app = self.get_current_app()

        return {
            "success": True,
            "serial": self.serial,
            "brand": brand,
            "model": model,
            "android_version": version,
            "sdk_level": sdk,
            "resolution": size,
            "power_status": power if power.get("success") else "unknown",
            "current_app": app if app.get("success") else "unknown"
        }


def main():
    parser = argparse.ArgumentParser(description="Android TV ADB CLI tool.")
    parser.add_argument("-s", "--serial", help="Target device serial/IP.")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Scan LAN
    p_scan = subparsers.add_parser("scan", help="Scan local network for Android TVs with port 5555 open.")
    p_scan.add_argument("-r", "--range", help="Subnet range CIDR (default: auto-detect e.g. 192.168.1.0/24).")
    p_scan.add_argument("-d", "--deep", action="store_true", help="Perform deep scan checking Cast port 8008 to find devices with ADB disabled.")

    # Connect
    p_conn = subparsers.add_parser("connect", help="Connect to TV via IP.")
    p_conn.add_argument("target", help="IP address or IP:port of the TV.")
    
    # Disconnect
    p_disc = subparsers.add_parser("disconnect", help="Disconnect from TV.")
    p_disc.add_argument("target", nargs="?", help="IP address or IP:port (optional).")
    
    # Devices
    subparsers.add_parser("devices", help="List connected ADB devices.")
    
    # Info
    subparsers.add_parser("info", help="Get comprehensive TV information.")
    
    # Power
    p_pow = subparsers.add_parser("power", help="Get or set screen/power state.")
    p_pow.add_argument("state", nargs="?", choices=["get", "on", "off", "toggle"], default="get")
    
    # Current app
    subparsers.add_parser("current-app", help="Show active foreground app.")
    
    # Key
    p_key = subparsers.add_parser("key", help="Send input keyevent.")
    p_key.add_argument("key_name", help="Key name (e.g., up, down, back, home, enter, play) or integer keycode.")
    
    # Text
    p_text = subparsers.add_parser("text", help="Send keyboard text input.")
    p_text.add_argument("string", help="Text string to input.")
    
    # Apps
    p_apps = subparsers.add_parser("apps", help="List installed apps.")
    p_apps.add_argument("-3", "--third-party", action="store_true", help="List third party apps only.")
    
    # App actions (start, stop, clear, uninstall)
    p_act = subparsers.add_parser("app-action", help="Perform action on a package.")
    p_act.add_argument("action", choices=["start", "stop", "clear", "uninstall"])
    p_act.add_argument("package", help="Package name of the target app.")
    
    # Launch URI
    p_uri = subparsers.add_parser("launch-uri", help="Start activity with a VIEW intent URI.")
    p_uri.add_argument("uri", help="Target deep-link URI (e.g. youtube://watch?v=...).")
    p_uri.add_argument("-p", "--package", help="Target package name.")
    
    # Install APK
    p_inst = subparsers.add_parser("install", help="Install a local APK file.")
    p_inst.add_argument("apk_path", help="Local path to APK file.")
    
    # Screenshot
    p_ss = subparsers.add_parser("screenshot", help="Capture screenshot.")
    p_ss.add_argument("output_path", help="Local path where screen.png should be saved.")

    args = parser.parse_args()
    tool = ADBTool(serial=args.serial)
    
    output = {}
    if args.command == "scan":
        output = tool.scan_lan(subnet=args.range, deep=args.deep)
    elif args.command == "connect":
        output = tool.connect(args.target)
    elif args.command == "disconnect":
        output = tool.disconnect(args.target)
    elif args.command == "devices":
        output = tool.list_devices()
    elif args.command == "info":
        output = tool.get_info()
    elif args.command == "power":
        if args.state == "get":
            output = tool.get_power_status()
        else:
            output = tool.set_power(args.state)
    elif args.command == "current-app":
        output = tool.get_current_app()
    elif args.command == "key":
        output = tool.keyevent(args.key_name)
    elif args.command == "text":
        output = tool.input_text(args.string)
    elif args.command == "apps":
        output = tool.list_apps(third_party_only=args.third_party)
    elif args.command == "app-action":
        output = tool.app_action(args.action, args.package)
    elif args.command == "launch-uri":
        output = tool.launch_uri(args.uri, args.package)
    elif args.command == "install":
        output = tool.install_apk(args.apk_path)
    elif args.command == "screenshot":
        output = tool.capture_screenshot(args.output_path)
        
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

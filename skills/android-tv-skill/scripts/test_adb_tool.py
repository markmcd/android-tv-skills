#!/usr/bin/env python3
"""
Unit tests for ADBTool.
Mocks subprocess to verify correct commands are generated and output is parsed properly.
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess
import os
import sys

# Add scripts directory to path to import adb_tool
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from adb_tool import ADBTool


class TestADBTool(unittest.TestCase):
    def setUp(self):
        self.tool = ADBTool(serial="192.168.1.100:5555")

    @patch("subprocess.run")
    def test_run_cmd_with_serial(self, mock_run):
        """Test that commands include the serial flag when set."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "-s", "192.168.1.100:5555", "shell", "getprop"],
            returncode=0,
            stdout="test_output",
            stderr=""
        )
        
        result = self.tool._run_cmd(["shell", "getprop"])
        self.assertEqual(result.stdout, "test_output")
        mock_run.assert_called_with(
            ["/home/macd/android-sdk/platform-tools/adb", "-s", "192.168.1.100:5555", "shell", "getprop"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

    @patch("subprocess.run")
    def test_connect(self, mock_run):
        """Test the connect command logic."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "connect", "192.168.1.50:5555"],
            returncode=0,
            stdout="connected to 192.168.1.50:5555",
            stderr=""
        )
        
        # Unset serial first to test connection auto-assignment
        self.tool.serial = None
        result = self.tool.connect("192.168.1.50")
        
        self.assertTrue(result["success"])
        self.assertEqual(self.tool.serial, "192.168.1.50:5555")

    @patch("subprocess.run")
    def test_get_power_status_awake(self, mock_run):
        """Test parsing of wakefulness when awake."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "shell", "dumpsys", "power"],
            returncode=0,
            stdout="mWakefulness=Awake\nDisplay Power: state=ON",
            stderr=""
        )
        
        status = self.tool.get_power_status()
        self.assertTrue(status["success"])
        self.assertEqual(status["wakefulness"], "Awake")
        self.assertEqual(status["display_power"], "ON")
        self.assertTrue(status["is_on"])

    @patch("subprocess.run")
    def test_get_power_status_sleep(self, mock_run):
        """Test parsing of wakefulness when asleep."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "shell", "dumpsys", "power"],
            returncode=0,
            stdout="mWakefulness=Asleep\nDisplay Power: state=OFF",
            stderr=""
        )
        
        status = self.tool.get_power_status()
        self.assertTrue(status["success"])
        self.assertEqual(status["wakefulness"], "Asleep")
        self.assertEqual(status["display_power"], "OFF")
        self.assertFalse(status["is_on"])

    @patch("subprocess.run")
    def test_get_current_app(self, mock_run):
        """Test parsing of active application focus."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "shell", "dumpsys", "window", "displays"],
            returncode=0,
            stdout="mCurrentFocus=Window{36f78ea u0 com.google.android.youtube.tv/com.google.android.apps.youtube.tv.activity.MainActivity}",
            stderr=""
        )
        
        app = self.tool.get_current_app()
        self.assertTrue(app["success"])
        self.assertEqual(app["focused_app"], "com.google.android.youtube.tv/com.google.android.apps.youtube.tv.activity.MainActivity")
        self.assertEqual(app["package"], "com.google.android.youtube.tv")
        self.assertEqual(app["activity"], "com.google.android.apps.youtube.tv.activity.MainActivity")

    @patch("subprocess.run")
    def test_keyevent(self, mock_run):
        """Test mapping and sending of key events."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "shell", "input", "keyevent", "19"],
            returncode=0,
            stdout="",
            stderr=""
        )
        
        res = self.tool.keyevent("up")
        self.assertTrue(res["success"])
        self.assertEqual(res["keycode_used"], "19")

    @patch("subprocess.run")
    def test_input_text(self, mock_run):
        """Test text formatting with spaces."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["adb", "shell", "input", "text", "hello%sworld"],
            returncode=0,
            stdout="",
            stderr=""
        )
        
        res = self.tool.input_text("hello world")
        self.assertTrue(res["success"])
        self.assertEqual(res["sent_text"], "hello%sworld")

    @patch("socket.socket")
    @patch("subprocess.run")
    def test_scan_lan_unauthorized(self, mock_run, mock_socket):
        """Test scanning LAN subnet with a mock open port that is unauthorized."""
        # Mock socket to return 0 (success connection) for exactly one IP
        mock_sock_inst = MagicMock()
        mock_socket.return_value = mock_sock_inst
        mock_sock_inst.connect_ex.side_effect = lambda addr: 0 if addr[0] == "192.168.1.100" and addr[1] == 5555 else 1

        # Mock subprocess.run to return devices list where 192.168.1.100 is unauthorized
        def mock_run_side_effect(args, **kwargs):
            if "devices" in args:
                return subprocess.CompletedProcess(
                    args=args, returncode=0,
                    stdout="List of devices attached\n192.168.1.100:5555\tunauthorized\n",
                    stderr=""
                )
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
            
        mock_run.side_effect = mock_run_side_effect

        result = self.tool.scan_lan(subnet="192.168.1.0/24")
        self.assertTrue(result["success"])
        self.assertEqual(result["subnet_scanned"], "192.168.1.0/24")
        self.assertEqual(len(result["devices_found"]), 1)
        self.assertEqual(result["devices_found"][0]["ip"], "192.168.1.100")
        self.assertEqual(result["devices_found"][0]["status"], "unauthorized")
        self.assertTrue(len(result["instructions"]) > 0)

    @patch("socket.socket")
    @patch("subprocess.run")
    @patch("urllib.request.urlopen")
    def test_scan_lan_deep_cast_only(self, mock_urlopen, mock_run, mock_socket):
        """Test deep scanning where a Cast-only device is detected on port 8008."""
        # Mock socket: 192.168.1.58 has 8008 open, but 5555 closed
        mock_sock_inst = MagicMock()
        mock_socket.return_value = mock_sock_inst
        mock_sock_inst.connect_ex.side_effect = lambda addr: 0 if addr[0] == "192.168.1.58" and addr[1] == 8008 else 1

        # Mock urllib.request.urlopen to return mock Chromecast Eureka JSON
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"name": "Bedroom TV", "model_name": "Chromecast Ultra", "manufacturer": "Google"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Mock subprocess.run
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        result = self.tool.scan_lan(subnet="192.168.1.0/24", deep=True)
        self.assertTrue(result["success"])
        self.assertTrue(result["deep_scan_active"])
        self.assertEqual(len(result["devices_found"]), 1)
        
        device = result["devices_found"][0]
        self.assertEqual(device["ip"], "192.168.1.58")
        self.assertEqual(device["status"], "disabled")  # ADB is closed
        self.assertEqual(device["friendly_name"], "Bedroom TV")
        self.assertEqual(device["brand"], "Google")
        self.assertEqual(device["model"], "Chromecast Ultra")
        self.assertEqual(device["ports_open"], [8008])


if __name__ == "__main__":
    unittest.main()

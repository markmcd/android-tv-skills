---
name: android-tv-skill
description: Automates and controls Android TV devices over ADB (Android Debug Bridge). Use when the agent needs to scan the LAN for TVs, control playback, navigate menus, launch apps/content/deep links, capture screenshots, or manage installed applications on an Android TV device.
---

# Android TV Skill

This skill enables the agent to discover, interact with, control, and automate Android TV devices via the Android Debug Bridge (ADB). It wraps ADB commands into a clean, unified CLI tool, and provides reference materials for navigation keycodes and streaming application intents.

## Prerequisites & TV Setup

To use this skill, network/wireless ADB debugging must be enabled on your Android TV:

1. **Enable Developer Options**:
   - On the TV, go to **Settings** > **Device Preferences** (or **System**) > **About**.
   - Scroll down to **Build** (or **OS Build**) and click it rapidly **7 times** until a message reads *"You are now a developer!"*.
2. **Enable ADB Debugging**:
   - Go back one level to the main **Settings** screen and select the newly revealed **Developer Options**.
   - Find and turn ON **USB Debugging**.
   - Find and turn ON **Wireless Debugging** (or **Network Debugging**) if available.
   > *Note: On most Android TVs, enabling "USB Debugging" automatically exposes the standard ADB port (5555) over your Wi-Fi network.*
3. **Authorize Your Computer**:
   - The first time you connect to the TV, keep its screen ON.
   - When the connection is attempted, a prompt will appear on the TV: *"Allow USB debugging?"*.
   - Check **"Always allow from this computer"** and select **OK** / **Allow**.

---

## Quick Start & Setup

To find and connect to a TV on your local network:

```bash
# 1. Scan your LAN to auto-detect any TVs with ADB enabled
./scripts/adb_tool.py scan

# 2. Connect to the TV using its detected IP address
./scripts/adb_tool.py connect 192.168.86.150

# 3. Verify connection and get detailed hardware/software properties
./scripts/adb_tool.py info
```

---

## Core Capabilities

The `adb_tool.py` script offers a clean JSON interface to interact with the device.

### 1. Network Scan & Discovery
Scan the local subnet CIDR (defaults to auto-detecting your computer's active IP subnet) to identify any Android TV with port 5555 open, reporting connection status and instructions.

```bash
# Auto-detect subnet and scan all IPs for open ADB ports
./scripts/adb_tool.py scan

# Scan a custom CIDR subnet range with deep Google Cast discovery
./scripts/adb_tool.py scan --deep --range 192.168.1.0/24
```

### 2. Device Connection & Information
Retrieve connected devices, current foreground application, display resolution, and build properties.

```bash
# List all connected ADB devices
./scripts/adb_tool.py devices

# Query brand, model, Android OS version, active app, and power status
./scripts/adb_tool.py info

# Get only the current foreground app package and active activity
./scripts/adb_tool.py current-app
```

### 3. Power and Screen Control
Query the TV display/power state or wake/sleep the device.

```bash
# Query display power status (returns display state, e.g., ON/OFF/Asleep)
./scripts/adb_tool.py power

# Wake up the device (turns screen ON)
./scripts/adb_tool.py power on

# Put the device to sleep (turns screen OFF)
./scripts/adb_tool.py power off

# Toggle the power key
./scripts/adb_tool.py power toggle
```

### 4. Navigation and Keyboard Inputs
Simulate remote control button presses and standard alphanumeric text entry.

```bash
# Send standard D-pad or navigation keys (up, down, left, right, enter, back, home, menu)
./scripts/adb_tool.py key enter
./scripts/adb_tool.py key back
./scripts/adb_tool.py key home

# Input a text string (automatically handles spaces)
./scripts/adb_tool.py text "Gemini CLI"
```

### 5. Application Management
List installed packages, launch apps, force stop them, clear data, or uninstall them.

```bash
# List all installed third-party apps
./scripts/adb_tool.py apps -3

# Force stop an application package
./scripts/adb_tool.py app-action stop com.google.android.youtube.tv

# Clear all cached data/state for an app
./scripts/adb_tool.py app-action clear com.google.android.youtube.tv

# Uninstall an application
./scripts/adb_tool.py app-action uninstall com.google.android.youtube.tv
```

### 6. Media Control
Control playback using standardized media buttons.

```bash
# Send media controls (play, pause, play_pause, stop, next, prev)
./scripts/adb_tool.py key play_pause
./scripts/adb_tool.py key volume_up
./scripts/adb_tool.py key volume_down
./scripts/adb_tool.py key mute
```

### 7. Deep Linking & Automations
Launch target streaming apps directly to specific content using deep link intent URIs.

```bash
# Play a YouTube video directly
./scripts/adb_tool.py launch-uri "vnd.youtube://watch?v=dQw4w9WgXcQ" -p com.google.android.youtube.tv

# Launch general deep link with package specifier
./scripts/adb_tool.py launch-uri "https://www.netflix.com/watch/80018499" -p com.netflix.ninja
```

### 8. Screenshot Verification
Take a screenshot of the current TV screen and download it locally. Extremely useful for verifying the UI state or checking what is currently playing.

```bash
# Take a screenshot and save it to the local directory
./scripts/adb_tool.py screenshot ./tv_screen.png
```

---

## Interrogation Strategies (What's Playing / On-Screen)

When a user asks **"what's playing?"**, **"what's on the screen?"**, or **"what movie is this?"**, execute the following diagnostics sequentially depending on the target application:

### Strategy A: Probe Active Media Sessions (Most reliable for metadata)
Query the OS-level `media_session` stack to retrieve active stream metadata, titles, descriptions, and playback timeline.
```bash
# Run shell command to dump media session status
adb -s <TV_IP>:5555 shell dumpsys media_session
```
* **How to analyze**:
  - Look under the **`Sessions Stack`** for active sessions (e.g. `active=true`).
  - Locate the **`metadata`** line. Apps like **Spotify**, **YouTube**, and **Plex** write explicit metadata here (e.g. `metadata: size=8, description=R U Sleeping`).
  - Locate the **`state`** line. It contains the real-time playback state and elapsed position (e.g., `PlaybackState {state=PLAYING(3), position=678844}`). Convert `position` from milliseconds to minutes to find playback progress.
  - *Note*: **Netflix** and **Disney+** leave `metadata` fields empty (`null`), but still expose the real-time elapsed playback position and speed.

### Strategy B: Extract On-Screen UI Tree Layout (For scraping text overlays)
Scrape the visible layout tree to extract textual labels, titles, or active menu options.
```bash
# Dump the on-screen UI hierarchy to a temporary file
adb -s <TV_IP>:5555 shell uiautomator dump /sdcard/window_dump.xml
# Cat or read the file locally to inspect node texts
adb -s <TV_IP>:5555 shell cat /sdcard/window_dump.xml
```
* **How to analyze**:
  - Inspect the XML layout nodes for `text="..."` or `content-desc="..."` matching title names, duration markers, or channel numbers.
  - **The Canvas Exception**: Premium streaming applications (such as **Netflix**) use custom hardware-accelerated canvas engines (e.g., the *Gibbon* engine) rather than standard Android UI widgets. The entire screen will report as a single blank container node (`com.netflix.ninja:id/gibbon`), making visible text extraction impossible via this method.

### Strategy C: Screenshot Verification
Attempt to visually capture the current framebuffer of the display.
```bash
# Use adb_tool.py to pull the TV screen locally
./scripts/adb_tool.py -s <TV_IP> screenshot ./screen.png
```
* **How to analyze**:
  - Save the file and inspect it visually (or programmatically if vision APIs are available).
  - **The DRM Exception (`FLAG_SECURE`)**: When premium applications are actively playing copyrighted material (using hardware decoders or Widevine DRM), the system applies `FLAG_SECURE`. This blocks the frame capture pipeline, causing the `screencap` command to fail (returning exit code 1) or produce a completely black rectangle over the protected video area.

## Interrogation Strategies (What can <app> do?)

When a user asks what an app can do, or if you need to determine what's possible
in an app, you can reverse engineer the intents and activities through ADB.

### Strategy: Interrogating App Intents & Supported Activities
When asked to control or deep-link into a specific application whose interface, activities, or intent schemes are not immediately obvious or documented, use ADB to reverse-engineer its capabilities.

#### Step 1: Dump active package routing tables
Query Android's Package Manager registry to find registered activities and their declared intent-filters (actions, schemes, and categories):
```bash
adb -s <TV_IP>:5555 shell dumpsys package <package_name>
```
* **How to analyze**:
  - Search the output for the **`Activity Resolver Table`** section.
  - Locate nested blocks containing `Action:`, `Scheme:`, or `Authority:`.
  - For example, if you see:
    ```text
    Schemes:
      sbsondemand:
        Action: "android.intent.action.VIEW"
    ```
    This tells you that you can launch the app directly using `am start -a android.intent.action.VIEW -d "sbsondemand://..."`.

#### Step 2: Extract and parse AndroidManifest.xml (For complete, raw schema)
If package dumps are too cluttered or truncated, pull the compiled APK to your host and read the manifest XML tree:
```bash
# 1. Locate the physical path of the APK on the TV
adb -s <TV_IP>:5555 shell pm path <package_name>
# Output: package:/data/app/~~.../base.apk

# 2. Pull the APK locally
adb -s <TV_IP>:5555 pull /data/app/~~.../base.apk ./temp_app.apk

# 3. Dump the structured manifest tree
aapt dump xmltree temp_app.apk AndroidManifest.xml
```
* **How to analyze**:
  - Scan the manifest for `<activity>` blocks. Any activity with an `<intent-filter>` containing `<action android:name="android.intent.action.VIEW"/>` and a `<data>` block is a candidate for direct deep-linking via `launch-uri`.

---

## Bundled Resources

### `scripts/adb_tool.py`
A highly robust Python utility that wraps command-line ADB processes, implements subnet scanning, and formats standard inputs, parsing errors, and device details into well-structured JSON outputs.
- Supports `-s` or `--serial` flag to target specific connected TVs.

### `references/key_codes.md`
A complete reference of Android TV keycodes (DPAD keys, media, volume, numeric, power, guide, and settings keys), popular streaming app package names, and deep-link intent structures.
- Use this file as a reference when mapping complex remote buttons or custom app-launch behaviors.

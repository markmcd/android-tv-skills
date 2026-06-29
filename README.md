<div align="center">

# Android TV skill

[![License](https://img.shields.io/badge/License-Apache-green.svg)](LICENSE)
![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-green)
[![Skills](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)

<br>

**Discover, control, and automate Android TV and Google Cast devices on your local network through your agent.**

<br>

Control your TV, monitor what's playing and launch specific shows using your
personal agent.

```bash
npx skills add markmcd/android-tv-skills
```

</div>

---

Uses (and requires) [adb](https://developer.android.com/tools/adb) to control
any Android-powered device on your network, including Chromecast and Google TV
devices.

Once installed and enabled, you can get your agent to:

 * Scan for ADB-active devices
 * Deep scan for devices that do not have ADB enabled, including ChromeCast and
   speakers
 * Launch and control apps using your agent: "5 minutes before kickoff, start the Sportsball app and navigate to the AUS v USA game and start playing"
 * Queries and controls OS `MediaSession` data, runs `uiautomator` and if necessary, takes screenshots to determine what's running
 * Or just get your agent to rickroll your roommates: "Rickroll every display on this network"

---

## Device setup

Before you can control a device remotely, it will need to be in debug mode and
allow network/WiFi debugging. The agent can guide you through the process, but
you will need physical access to the TV. Once this has been done, as long as
you "remember this device", you will have control over the TV.

Full details on the process are on the [ADB
docs](https://developer.android.com/tools/adb#Enabling)

## How does it work?

`adb` allows sending Android
[`Intent`](https://developer.android.com/reference/android/content/Intent)
messages to any connected devices, allowing deep links into any installed
apps, with payloads. This skill provides tooling and instructions to your agent
so that your commands are converted to Android messages, so:

```
"rickroll the loungeroom"
```

becomes:

```
$ adb -s 192.168.67.69:5555 shell am start -a android.intent.action.VIEW -d "vnd.youtube://watch?v=dQw4w9WgXcQ" com.google.android.youtube.tv
```

Popular apps are likely known to frontier models already, but the skill
outlines how to reverse engineer these if necessary, and you can ask the agent
to "tell me what I can do with &lt;my app&gt;"

---

## Usage examples

All operations are handled by the unified, JSON-formatted `adb_tool.py` script.

### Network Sweep
```
> what devices are on my network?
> do a deep scan for any others
```

### Query TV Status
```
> what's on my lounge room TV?
> are any of my displays currently on?
> what's on the outside TV?
```

### Media Controls
```
> press mute on the Chromecast
> navigate the current app to turn on subtitles
> skip to the next song playing
```

### Play YouTube Video
```
> play https://www.youtube.com/watch?v=dQw4w9WgXcQ on all TVs.
```

## A note on DRM

Note that some app introspection may be limited due to DRM. Clients like
Widevine typically block screenshots, preventing queries like "What's on the TV"
from working.

This can be compounded with apps like Netflix, that do not publish current media
info (like video name) to the OS [`MediaSession`
](https://developer.android.com/media/media3/session/control-playback).
Additionally, Netflix also uses a custom canvas to render their app UI, which
also blocks tools like `uiautomator` from inspecting the UI hierarchy.

DRM does not block controls, or anything you would be able to do with a remote,
so most features will still work.

## Disclaimer

This is not an official project and not endorsed by Google or Android.

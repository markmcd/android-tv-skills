# Android TV Keycodes, Package Names, and Intents

This document provides a reference of standard keycodes, package names, and intent deep-links for automating Android TV.

## Common Keycodes

| Key Name | Code (Int) | Code (String) | Description |
|---|---|---|---|
| **UP** | 19 | `KEYCODE_DPAD_UP` | D-pad Up |
| **DOWN** | 20 | `KEYCODE_DPAD_DOWN` | D-pad Down |
| **LEFT** | 21 | `KEYCODE_DPAD_LEFT` | D-pad Left |
| **RIGHT** | 22 | `KEYCODE_DPAD_RIGHT` | D-pad Right |
| **ENTER** | 23 | `KEYCODE_DPAD_CENTER` | Select / Center Click |
| **BACK** | 4 | `KEYCODE_BACK` | Go Back |
| **HOME** | 3 | `KEYCODE_HOME` | System Home / Launcher |
| **MENU** | 82 | `KEYCODE_MENU` | Menu Button |
| **POWER** | 26 | `KEYCODE_POWER` | Toggle Power State |
| **SLEEP** | 223 | `KEYCODE_SLEEP` | Sleep (Force Screen Off) |
| **WAKEUP** | 224 | `KEYCODE_WAKEUP` | Wakeup (Force Screen On) |
| **PLAY_PAUSE**| 85 | `KEYCODE_MEDIA_PLAY_PAUSE`| Toggle Play / Pause |
| **PLAY** | 126 | `KEYCODE_MEDIA_PLAY` | Media Play |
| **PAUSE** | 127 | `KEYCODE_MEDIA_PAUSE` | Media Pause |
| **STOP** | 86 | `KEYCODE_MEDIA_STOP` | Media Stop |
| **VOL_UP** | 24 | `KEYCODE_VOLUME_UP` | Volume Up |
| **VOL_DOWN** | 25 | `KEYCODE_VOLUME_DOWN` | Volume Down |
| **MUTE** | 164 | `KEYCODE_VOLUME_MUTE` | Mute Toggle |
| **SETTINGS** | 176 | `KEYCODE_SETTINGS` | System Settings |
| **GUIDE** | 172 | `KEYCODE_GUIDE` | EPG / Guide |

---

## Popular Streaming App Packages

| App Name | Package Name | Common Launcher/Main Activity |
|---|---|---|
| **YouTube** | `com.google.android.youtube.tv` | `com.google.android.apps.youtube.tv.activity.MainActivity` |
| **Netflix** | `com.netflix.ninja` | `com.netflix.ninja.MainActivity` |
| **Prime Video** | `com.amazon.amazonvideo.livingroom` | `com.amazon.ignite.multiscreen.LiveActivity` |
| **Disney+** | `com.disney.disneyplus` | `com.disney.disneyplus.MainActivity` |
| **Hulu** | `com.hulu.livingroom` | `com.hulu.livingroom.activity.MainActivity` |
| **Plex** | `com.plexapp.android` | `com.plexapp.plex.activities.SplashActivity` |
| **Spotify** | `com.spotify.tv.android` | `com.spotify.tv.android.SpotifyTVActivity` |

---

## Intent Deep-Link URIs

You can launch standard streaming services directly to specific content using deep-link intents via `launch-uri`.

### 1. YouTube
- **Watch video**: `vnd.youtube://watch?v=VIDEO_ID` (e.g. `vnd.youtube://watch?v=dQw4w9WgXcQ`)
- **Open channel**: `vnd.youtube://user/CHANNEL_NAME` or `vnd.youtube://channel/CHANNEL_ID`

### 2. Netflix
- **Play video**: `https://www.netflix.com/watch/VIDEO_ID`

### 3. Prime Video
- **Play video**: `https://watch.amazon.com/watch?asin=ASIN`

### 4. General Web/Browser Links
- **Open URL**: `https://google.com` (Opens in default TV browser if installed)

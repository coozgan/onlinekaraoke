# Karaoke room (Songerist-style)

One screen plays YouTube karaoke videos. Guests join from their phones with a room code or QR code to search YouTube, reserve songs, and control the queue.

Needs `yt-dlp` (search) and optionally `qrencode` (QR) and `cloudflared` (online join). All are already installed here.

```
python3 server.py            # guests on the same Wi-Fi
python3 server.py --online   # also prints a public link for guests outside your Wi-Fi
```

Open `/tv` on the big screen and click **Start the screen**. The TV makes its own secret key the first time and keeps it, and the server turns that key into the TV's 6-letter room code. The code stays the same after server restarts, and each TV gets its own room. Phones join with the code or QR shown on the TV.

Phones can search by song or artist (only videos with karaoke, minus one or instrumental in the title, like Songerist) or paste a YouTube link, or tap **Trending** (most viewed karaoke this year, shown on join). Results drop videos whose owners block playback on other sites, and repeat searches come from a 1-hour cache. They can reserve up to 10 songs each, pause or play, skip, move a song to the top, and remove songs. The TV plays the queue in order and skips videos whose owners block embedding.

## Xiaomi / Android TV app

The app is a full-screen WebView that opens the TV link and starts with sound, so no click is needed. Build it with the installed Android SDK (no Gradle):

```
tv-app/build.sh https://karaoke.joshyfruit.com/tv   # makes tv-app/karaoke-tv.apk
```

Install: on the TV, open Settings > Device Preferences > About and click Build 7 times. Then turn on USB debugging in Developer options, and run `adb connect <tv-ip>:5555` and `adb install tv-app/karaoke-tv.apk`. You can also copy the APK to a USB stick and open it with the TV's file manager (allow unknown apps). Rebuild if the server address changes. Clearing the app's data gives the TV a new key and room code. A DHCP reservation on the router keeps the IP fixed. `PUBLIC_URL` sets the join link the TV shows.

Test: `python3 -m unittest test_server`

Limits: rooms are kept in memory, so a restart empties the queue (up to 50 TVs, the longest idle is dropped). Anyone with the code can control the queue. No accounts, chat or scoring.

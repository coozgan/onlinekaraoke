# Karaoke room (Songerist-style)

One screen plays YouTube karaoke videos. Guests join from their phones with a room code or QR code to search YouTube, reserve songs, and control the queue.

Needs `yt-dlp` (search) and optionally `qrencode` (QR) and `cloudflared` (online join). All are already installed here.

```
python3 server.py            # guests on the same Wi-Fi
python3 server.py --online   # also prints a public link for guests outside your Wi-Fi
```

The server prints two links:
- **TV screen**: `http://localhost:8010/tv#<key>`. Open it on the big screen and click **Start the screen**. The key in the link is what lets this screen advance the queue, so don't share it.
- **Phones**: the join link and the 6-letter room code, which are also shown on the TV.

Phones can search by song or artist (only videos with karaoke, minus one or instrumental in the title, like Songerist) or paste a YouTube link, or tap **Trending** (most viewed karaoke this year, shown on join). Results drop videos whose owners block playback on other sites, and repeat searches come from a 1-hour cache. They can reserve up to 3 songs each, pause or play, skip, move a song to the top, and remove songs. The TV plays the queue in order and skips videos whose owners block embedding.

Test: `python3 -m unittest test_server`

Limits: one room per server run, kept in memory (a restart gives a new code and an empty queue). Anyone with the code can control the queue. No accounts, chat or scoring.

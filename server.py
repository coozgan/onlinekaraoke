#!/usr/bin/env python3
"""Karaoke room. One TV screen plays YouTube karaoke; phones join with a code to search, reserve and control.

Run: python3 server.py            (phones on the same Wi-Fi)
     python3 server.py --online   (also opens a public cloudflared link)
"""
import atexit, hashlib, json, os, re, secrets, socket, subprocess, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DIR = os.path.dirname(os.path.abspath(__file__))
TV_KEY = re.compile(r'^[A-Za-z0-9_-]{16,64}$')
ALPHA = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # 32 letters, no 0/O/1/I
MAX_ROOMS = 50
BASE = 'http://127.0.0.1:8010'
VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
LINK = re.compile(r'(?:youtu\.be/|[?&]v=|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})')
KARAOKE = re.compile(r'karaoke|videoke|minus ?one|instrumental|backing track|sing ?along', re.I)
PER_GUEST = 10  # songs each guest can have waiting
# Most viewed karaoke videos uploaded this year (sp = sort by views, this year, videos only).
TRENDING = 'https://www.youtube.com/results?search_query=karaoke&sp=CAMSBAgFEAE'
POOL = ThreadPoolExecutor(16)
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://www.youtube.com; "
       "frame-src https://www.youtube-nocookie.com https://www.youtube.com; img-src 'self' https://i.ytimg.com; "
       "style-src 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'")


def code_for(key):
    """The room code comes from the TV's key, so after a server restart the TV gets the same code back."""
    return ''.join(ALPHA[b % 32] for b in hashlib.sha256(key.encode()).digest()[:6])


class Room:
    # ponytail: rooms live in memory. A server restart keeps the TV's code but empties the queue.
    def __init__(self, key):
        self.key, self.code, self.seen = key, code_for(key), time.time()
        self.lock = threading.Lock()
        self.queue, self.current, self.paused, self.seq = [], None, False, 0

    def join_url(self):
        return f'{BASE}/?code={self.code}'

    def state(self):
        with self.lock:
            return {'code': self.code, 'join': self.join_url(), 'current': self.current,
                    'queue': list(self.queue), 'paused': self.paused}

    def _advance(self):
        self.current = self.queue.pop(0) if self.queue else None
        self.paused = False

    def reserve(self, name, vid, title, channel):
        name = str(name or '').strip()[:30]
        if not name:
            return 'Type your name first.'
        if not VIDEO_ID.match(str(vid or '')):
            return 'That is not a YouTube video.'
        with self.lock:
            if any(q['id'] == vid for q in self.queue) or (self.current and self.current['id'] == vid):
                return 'That song is already in the queue.'
            if sum(q['by'].lower() == name.lower() for q in self.queue) >= PER_GUEST:
                return f'You already have {PER_GUEST} songs waiting. Reserve more after one plays.'
            self.seq += 1
            self.queue.append({'n': self.seq, 'id': vid, 'title': str(title or vid)[:200],
                               'channel': str(channel or '')[:100], 'by': name})
            if not self.current:
                self._advance()

    def control(self, action, item=None):
        with self.lock:
            if action in ('pause', 'play'):
                self.paused = action == 'pause' and bool(self.current)
            elif action == 'skip':
                self._advance()
            elif action in ('remove', 'top'):
                found = next((q for q in self.queue if q['n'] == item), None)
                if not found:
                    return 'That song is no longer in the queue.'
                self.queue.remove(found)
                if action == 'top':
                    self.queue.insert(0, found)
            else:
                return 'Unknown action.'

    def ended(self, item):
        # Only the item that finished advances the queue, so a late or repeated report can't skip a song.
        with self.lock:
            if self.current and self.current['n'] == item:
                self._advance()


ROOMS, ROOMS_LOCK = {}, threading.Lock()  # code -> Room


def tv_room(key):
    """A TV opens (or reopens) its room with the secret key it generated. None if the key is malformed."""
    key = str(key or '')
    if not TV_KEY.match(key):
        return None
    with ROOMS_LOCK:
        room = ROOMS.get(code_for(key))
        if room and not secrets.compare_digest(room.key, key):
            return None  # another TV's key maps to this code (about 1 in a billion)
        if not room:
            if len(ROOMS) >= MAX_ROOMS:  # ponytail: cap memory by dropping the longest-idle TV; add auth if strangers abuse it
                del ROOMS[min(ROOMS.values(), key=lambda r: r.seen).code]
            room = ROOMS[code_for(key)] = Room(key)
        room.seen = time.time()
        return room


def find(code='', key=''):
    """Phones find a room by its code. The TV opens its room by key, so it comes back after a server restart."""
    return tv_room(key) if key else ROOMS.get(str(code).strip().upper())


def yt(target):
    """Ask yt-dlp for a search or a single video. List args, no shell: the query is never interpreted."""
    out = subprocess.run(['yt-dlp', '--flat-playlist', '--playlist-end', '40', '-J', '--no-warnings', '--', target],
                         capture_output=True, text=True, timeout=30)
    if out.returncode:
        raise RuntimeError('YouTube search failed. Check the internet connection.')
    data = json.loads(out.stdout)
    return data.get('entries') or [data]


def embeddable(vid):
    """YouTube's oEmbed answers 401/403 when the owner disabled playback on other sites, 404 when it's gone."""
    try:
        urllib.request.urlopen('https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=' + vid,
                               timeout=4).close()
        return True
    except urllib.error.HTTPError as e:
        return e.code == 429 or e.code >= 500  # rate limited or YouTube down: keep it, the TV still skips failures
    except OSError:
        return True


_cache = {}
def search(q):
    """Empty q gives trending. Results are cached so repeat searches and trending are instant."""
    q = q.strip()[:100]
    hit = _cache.get(q.lower())
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    link = LINK.search(q)
    if link:  # a pasted link plays as-is, like Songerist's "My YouTube"
        items = yt('https://www.youtube.com/watch?v=' + link.group(1))
    else:  # like Songerist: only videos whose title says karaoke / minus one / instrumental
        items = [e for e in yt(f'ytsearch20:{q} karaoke' if q else TRENDING) if KARAOKE.search(e.get('title') or '')]
    items = [e for e in items if VIDEO_ID.match(e.get('id') or '')][:25]
    ok = list(POOL.map(embeddable, [e['id'] for e in items]))
    results = [{'id': e['id'], 'title': e.get('title') or e['id'], 'duration': e.get('duration'),
                'channel': e.get('channel') or e.get('uploader') or ''}
               for e, good in zip(items, ok) if good][:20 if q else 25]
    if len(_cache) > 500:  # ponytail: crude bound, fine for one party; use an LRU if rooms get long-lived
        _cache.clear()
    _cache[q.lower()] = (time.time(), results)
    return results


_qr = {}
def qr_svg(url):
    if url not in _qr:
        try:
            _qr[url] = subprocess.run(['qrencode', '-t', 'SVG', '-m', '1', '-o', '-', url],
                                      capture_output=True, timeout=5, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            return None  # ponytail: no qrencode means no QR; the TV still shows the link and code
    return _qr[url]


class H(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, ctype='application/json'):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')  # YouTube embeds need a referrer
        if ctype.startswith('text/html'):
            self.send_header('Content-Security-Policy', CSP)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        pages = {'/': ('remote.html', 'text/html; charset=utf-8'),
                 '/tv': ('tv.html', 'text/html; charset=utf-8'),
                 '/logo.png': ('logo.png', 'image/png')}
        if url.path in pages:
            name, ctype = pages[url.path]
            with open(os.path.join(DIR, name), 'rb') as f:
                return self.reply(200, f.read(), ctype)
        if url.path == '/qr.svg':
            room = ROOMS.get(q.get('code', '').upper())
            svg = room and qr_svg(room.join_url())
            return self.reply(200, svg, 'image/svg+xml') if svg else self.reply(404, {'error': 'No QR'})
        room = find(q.get('code', ''), q.get('key', ''))
        if url.path in ('/api/state', '/api/search') and not room:
            return self.reply(403, {'error': 'Wrong room code. Check the code on the TV.'})
        if url.path == '/api/state':
            return self.reply(200, room.state())
        if url.path == '/api/search':
            try:
                return self.reply(200, {'results': search(q.get('q', ''))})
            except (RuntimeError, subprocess.SubprocessError, OSError, ValueError) as e:
                return self.reply(502, {'error': str(e) if isinstance(e, RuntimeError) else 'YouTube search failed.'})
        self.reply(404, {'error': 'Not found'})

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length') or 0)
            if not 0 <= size <= 4096:
                raise ValueError
            body = json.loads(self.rfile.read(size) or b'{}')
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self.reply(400, {'error': 'Bad request'})
        path, item = urlparse(self.path).path, body.get('item')
        room = find(body.get('code', ''), body.get('key', ''))
        if not room:
            return self.reply(403, {'error': 'Wrong room code. Check the code on the TV.'})
        item = item if isinstance(item, int) else None
        if path == '/api/reserve':
            err = room.reserve(body.get('name'), body.get('id'), body.get('title'), body.get('channel'))
        elif path == '/api/control':
            err = room.control(body.get('action'), item)
        elif path == '/api/ended':
            if not body.get('key'):
                return self.reply(403, {'error': 'Only the TV screen can report the end of a song.'})
            err = room.ended(item)
        else:
            return self.reply(404, {'error': 'Not found'})
        self.reply(400, {'error': err}) if err else self.reply(200, room.state())


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))  # UDP connect sends nothing; it only picks the outgoing interface
        return s.getsockname()[0]
    except OSError:
        return '127.0.0.1'
    finally:
        s.close()


def tunnel(port):
    global BASE
    proc = subprocess.Popen(['cloudflared', 'tunnel', '--no-autoupdate', '--url', f'http://127.0.0.1:{port}'],
                            stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
    atexit.register(proc.terminate)
    for line in proc.stderr:
        found = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
        if found:
            BASE = found.group(0)
            # Some label-restricted videos only play when the embedding page is https on a real domain.
            print(f'TV screen over HTTPS (plays more videos): {BASE}/tv', flush=True)
            break
    for _ in proc.stderr:  # keep reading so cloudflared never blocks on a full pipe
        pass


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8010'))
    BASE = (os.environ.get('PUBLIC_URL') or f'http://{lan_ip()}:{port}').rstrip('/')
    server = ThreadingHTTPServer(('0.0.0.0', port), H)  # 0.0.0.0 so phones on the Wi-Fi can reach it
    threading.Thread(target=lambda: search(''), daemon=True).start()  # warm trending so phones see it at once
    if '--online' in sys.argv:
        threading.Thread(target=tunnel, args=(port,), daemon=True).start()
    print(f'TV screen (open on the big screen): {BASE}/tv   Phones join with the code it shows.', flush=True)
    server.serve_forever()

# Run: python3 -m unittest test_server   (offline: YouTube search is not called)
import json, threading, unittest, urllib.error, urllib.request
from http.server import ThreadingHTTPServer
import server


class T(unittest.TestCase):
    def test_queue_rules(self):
        r = server.Room()
        self.assertEqual(r.reserve('', 'aaaaaaaaaaa', 't', ''), 'Type your name first.')
        self.assertEqual(r.reserve('Ann', 'bad id', 't', ''), 'That is not a YouTube video.')
        self.assertIsNone(r.reserve('Ann', 'aaaaaaaaaaa', 'A', ''))
        self.assertEqual(r.current['id'], 'aaaaaaaaaaa')  # first song starts at once
        self.assertIn('already', r.reserve('Bob', 'aaaaaaaaaaa', 'A', ''))
        for i in 'bcd':
            self.assertIsNone(r.reserve('Ann', i * 11, i, ''))
        self.assertIn('3 songs', r.reserve('ann', 'eeeeeeeeeee', 'e', ''))  # limit ignores case
        self.assertIsNone(r.control('top', r.queue[2]['n']))
        self.assertEqual(r.queue[0]['id'], 'ddddddddddd')
        r.ended(999)  # stale report from the TV does nothing
        self.assertEqual(r.current['id'], 'aaaaaaaaaaa')
        r.ended(r.current['n'])
        self.assertEqual(r.current['id'], 'ddddddddddd')
        self.assertIsNone(r.control('pause'))
        self.assertTrue(r.state()['paused'])
        r.control('skip')
        self.assertFalse(r.state()['paused'])

    def test_http_access(self):
        httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.H)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.shutdown)
        base, room = f'http://127.0.0.1:{httpd.server_port}', server.ROOM

        def post(path, body):
            req = urllib.request.Request(base + path, json.dumps(body).encode(), {'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req) as res:
                    return res.status, json.load(res)
            except urllib.error.HTTPError as e:
                return e.code, json.load(e)

        self.assertEqual(post('/api/reserve', {'code': 'WRONG1', 'name': 'x', 'id': 'aaaaaaaaaaa'})[0], 403)
        self.assertEqual(post('/api/reserve', {'code': 'ñ✓', 'name': 'x', 'id': 'aaaaaaaaaaa'})[0], 403)
        self.assertEqual(post('/api/reserve', {'code': room.code.lower(), 'name': 'Zed', 'id': 'zzzzzzzzzzz'})[0], 200)
        self.assertEqual(post('/api/ended', {'code': room.code, 'item': 1})[0], 403)  # guests can't end songs
        with urllib.request.urlopen(base + '/tv') as res:
            self.assertIn("connect-src 'self'", res.headers['Content-Security-Policy'])
        status, _ = post('/api/control', {'key': room.tv_key, 'action': 'nope'})
        self.assertEqual(status, 400)

    def test_search_filters_and_caches(self):
        calls = []
        fake = [{'id': 'okokokokok1', 'title': 'Song A Karaoke'}, {'id': 'blockedvid1', 'title': 'Song B Karaoke'},
                {'id': 'okokokokok2', 'title': 'Song C Official Video'}]
        orig = server.yt, server.embeddable
        server.yt = lambda t: calls.append(t) or fake
        server.embeddable = lambda vid: vid != 'blockedvid1'
        try:
            server._cache.clear()
            self.assertEqual([r['id'] for r in server.search('song')], ['okokokokok1'])  # blocked + non-karaoke dropped
            server.search('SONG ')
            self.assertEqual(len(calls), 1)  # second search served from cache
            server.search('')
            self.assertEqual(calls[-1], server.TRENDING)
        finally:
            server.yt, server.embeddable = orig
            server._cache.clear()


if __name__ == '__main__':
    unittest.main()

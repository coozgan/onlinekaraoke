# Songerist clone (local)

A static, offline copy of the Songerist interface, based on the logged-in site as seen in your browser.

Run: `python3 -m http.server 8000`, then open http://localhost:8000. Test: `node test.js`.

Works: home (For you / Songs / Posts tabs), song cards, karaoke player with word-by-word highlighting, chords view, likes, comments, posts, studio drafts, search (Ctrl/Cmd+K or /), dark/light theme, mobile menu. Everything is saved in localStorage.

Not included: audio, real lyrics (the player uses original placeholder text), live rooms, accounts, messages, payments. These need a backend. A CSP blocks all network calls.

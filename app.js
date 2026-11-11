// Songerist local clone. No network: everything lives in localStorage.
// ponytail: catalog is the song list seen on the live home feed (titles only). Lyrics are an original
// placeholder, not the real songs. Add real content only from songs you own or have licensed.
const SONGS = [
  ['Barkada Forever', 'karaoke', 54], ['Pag May Tama Ka', 'karaoke', 10], ['Kung Tayo Sa Ibang Mundo', 'karaoke', 12],
  ['Pinagtagpo Ngunit Hindi Tinadhana', 'karaoke', 12], ['Mas Mahal Na Kita Ngayon (Rock)', 'chords', 1],
  ['Tahimik Na Apoy', 'chords', 1], ['Kapit Lang Hanggang Bukas', 'chords', 1], ['Hindi Patas', 'chords', 1],
  ['Ikaw Lang Sinta', 'chords', 1], ['Kahit Malayo Ka', 'chords', 1], ['Muli', 'chords', 1],
  ["Sa'yo Ko Nakita (Rock)", 'karaoke', 20], ['Hindi Ako Ang Pinili Mo', 'karaoke', 30],
].map(([title, kind, plays], id) => ({ id, title, artist: 'Gallops OPM', kind, plays }));

const DEMO = [ // [chord, line]; original placeholder text
  ['C', 'This is a demo line for the local player'], ['G', 'Each word lights up as the beat goes by'],
  ['Am', 'Swap in a song you own to sing along'], ['F', 'And share the stage with friends tonight'],
];

const search = (q, songs = SONGS) => {
  q = q.trim().toLowerCase();
  return q ? songs.filter(s => (s.title + ' ' + s.artist).toLowerCase().includes(q)) : [];
};
// Which word of DEMO is lit at time t (seconds), at `wps` words per second. Returns [line, word] or null.
const wordAt = (t, wps = 2, lines = DEMO) => {
  let n = Math.floor(t * wps);
  for (let i = 0; i < lines.length; i++) {
    const w = lines[i][1].split(' ').length;
    if (n < w) return [i, n];
    n -= w;
  }
  return null;
};
if (typeof module !== 'undefined') module.exports = { SONGS, DEMO, search, wordAt };

if (typeof document !== 'undefined') {
  const $ = s => document.querySelector(s);
  const db = {
    get: (k, d) => { try { return JSON.parse(localStorage.getItem('sg.' + k)) ?? d; } catch { return d; } },
    set: (k, v) => localStorage.setItem('sg.' + k, JSON.stringify(v)),
  };
  // Build DOM from [tag, attrs, ...children]; strings become text nodes, so user input is never parsed as HTML.
  const h = (tag, attrs = {}, ...kids) => {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) k.startsWith('on') ? el.addEventListener(k.slice(2), v) : el.setAttribute(k, v);
    el.append(...kids.flat().filter(k => k != null));
    return el;
  };
  const hue = s => [...s.title].reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
  const cover = s => h('span', { class: 'cover', style: `background:linear-gradient(135deg,hsl(${hue(s)} 70% 50%),hsl(${hue(s) + 60} 70% 40%))`, 'aria-hidden': 'true' }, '♪');

  const likes = () => db.get('likes', {});
  const likeBtn = key => {
    const n = (likes()[key] ? 1 : 0);
    return h('button', { 'aria-pressed': String(!!n), onclick: e => {
      const l = likes(); l[key] ? delete l[key] : (l[key] = 1); db.set('likes', l); e.currentTarget.replaceWith(likeBtn(key));
    } }, `👍 ${n}`);
  };
  const comments = key => {
    const list = h('ul');
    const draw = () => list.replaceChildren(...(db.get('c.' + key, [])).map(c => h('li', {}, c)));
    draw();
    const inp = h('input', { maxlength: '500', placeholder: 'Write a comment…', 'aria-label': 'Comment' });
    return h('details', {}, h('summary', {}, `💬 ${db.get('c.' + key, []).length}`), list,
      h('form', { onsubmit: e => { e.preventDefault(); const v = inp.value.trim(); if (!v) return;
        db.set('c.' + key, [...db.get('c.' + key, []), v]); inp.value = ''; draw(); } }, inp, ' ', h('button', {}, 'Send')));
  };
  const songTile = s => h('div', { class: 'box' },
    h('div', { class: 'mut' }, '🎵 ', h('b', {}, s.artist), ' published a song'),
    h('button', { class: 'tile', onclick: () => openCard(s) }, cover(s),
      h('span', {}, h('b', {}, s.title), h('br'), h('small', { class: 'mut' }, `${s.artist} · chords${s.kind === 'karaoke' ? ' + karaoke' : ''} · ${s.plays + db.get('plays.' + s.id, 0)} plays`))),
    h('div', { class: 'row' }, likeBtn('s' + s.id), comments('s' + s.id)));

  function openCard(s) {
    $('#cardTitle').textContent = s.title;
    $('#cardSub').textContent = s.artist;
    $('#cardActions').replaceChildren(
      h('a', { class: 'primary', href: `#/sing/${s.id}`, onclick: () => $('#card').close() }, h('button', { class: 'primary' }, '▶ Sing karaoke')),
      h('a', { href: `#/chords/${s.id}`, onclick: () => $('#card').close() }, h('button', {}, '♫ Lyrics and chords')));
    $('#card').showModal();
  }

  const composer = () => {
    const ta = h('textarea', { maxlength: '3000', placeholder: "What's on your mind?", 'aria-label': "What's on your mind?" });
    const who = h('select', { 'aria-label': 'Who can see this' }, h('option', { value: 'all' }, '🌐 Everyone'), h('option', { value: 'me' }, '🔒 Only me'));
    return h('form', { class: 'box', onsubmit: e => { e.preventDefault(); const t = ta.value.trim(); if (!t) return;
      db.set('posts', [{ id: Date.now(), t, who: who.value }, ...db.get('posts', [])]); route(); } },
      ta, h('div', { class: 'row' }, who, h('span', { class: 'spacer' }), h('button', { class: 'primary' }, 'Post')));
  };
  const postTile = p => h('div', { class: 'box' }, h('div', { class: 'mut' }, `You · ${new Date(p.id).toLocaleString()} · ${p.who === 'me' ? '🔒' : '🌐'}`),
    h('p', { style: 'white-space:pre-wrap' }, p.t),
    h('div', { class: 'row' }, likeBtn('p' + p.id), comments('p' + p.id),
      h('button', { onclick: () => { db.set('posts', db.get('posts', []).filter(x => x.id !== p.id)); route(); } }, 'Delete')));

  const pages = {
    '': (tab = new URLSearchParams(location.hash.split('?')[1]).get('tab') || 'foryou') => [
      h('section', { class: 'hero' }, h('p', { class: 'mut' }, 'Hi! 👋'),
        h('h1', {}, 'Play the chords. Sing the song. ', h('span', {}, 'Share the stage.')),
        h('p', { class: 'mut' }, 'Karaoke with lyrics that light up word by word, chords that play along, and rooms with your friends.')),
      h('a', { class: 'ch', href: '#/challenge' }, '🏆', h('span', {}, h('small', { class: 'mut' }, 'Weekly Challenge'), h('br'), h('b', {}, SONGS.at(-1).title)), h('span', { class: 'spacer' }), 'Join'),
      h('div', { class: 'quick', style: 'margin-top:1em' }, [['🎤', 'Karaoke', 'Sing now', 'karaoke'], ['🎸', 'Chords', 'Play along', 'chords'], ['🏠', 'Rooms', 'Sing with friends', 'rooms'], ['✎', 'Studio', 'Make a song', 'studio']]
        .map(([i, b, s, r]) => h('a', { href: '#/' + r }, h('span', { style: 'font-size:26px' }, i), h('b', {}, b), h('small', {}, s)))),
      h('nav', { class: 'tabs', 'aria-label': 'Home' }, [['foryou', 'For you'], ['songs', 'Songs'], ['posts', 'Posts']]
        .map(([k, l]) => h('a', { href: k === 'foryou' ? '#/' : `#/?tab=${k}`, ...(tab === k ? { 'aria-current': 'page' } : {}) }, l))),
      tab !== 'songs' && composer(),
      tab !== 'songs' && db.get('posts', []).map(postTile),
      tab !== 'posts' && SONGS.map(songTile),
    ],
    karaoke: () => [h('h1', {}, 'Online Karaoke'), SONGS.filter(s => s.kind === 'karaoke').map(songTile)],
    chords: id => id == null ? [h('h1', {}, 'Chords Feed'), SONGS.map(songTile)] : chordsPage(SONGS[id]),
    sing: id => singPage(SONGS[id]),
    rooms: () => [h('h1', {}, 'Rooms'), h('p', { class: 'box' }, 'Live rooms need a realtime server, which this local clone does not have. Use Online Karaoke to sing solo.')],
    challenge: () => [h('h1', {}, 'Weekly Challenge'), h('p', { class: 'mut' }, 'Sing this week\'s song and post it.'), songTile(SONGS.at(-1))],
    studio: () => {
      const t = h('input', { maxlength: '80', placeholder: 'Song title', 'aria-label': 'Song title', required: '' });
      return [h('h1', {}, 'Studio'), h('form', { class: 'box', onsubmit: e => { e.preventDefault();
        db.set('posts', [{ id: Date.now(), t: `🎵 New song draft: ${t.value.trim()}`, who: 'me' }, ...db.get('posts', [])]); location.hash = '#/?tab=posts'; } },
        h('label', {}, 'Title ', t), ' ', h('button', { class: 'primary' }, 'Save draft'))];
    },
    about: () => [h('h1', {}, 'About'), h('p', {}, 'A local, offline clone of the Songerist interface. Nothing you do here reaches songerist.com.')],
  };
  const notFound = () => [h('h1', {}, 'Not found'), h('a', { href: '#/' }, 'Go home')];

  const chordsPage = s => s ? [h('h1', {}, s.title), h('p', { class: 'mut' }, s.artist + ' · placeholder lyrics'),
    h('div', { class: 'lyrics' }, DEMO.map(([c, l]) => h('div', { class: 'line' }, h('span', { class: 'chord' }, c), l)))] : notFound();

  let timer;
  function singPage(s) {
    if (!s) return notFound();
    db.set('plays.' + s.id, db.get('plays.' + s.id, 0) + 1);
    const words = DEMO.map(([c, l]) => l.split(' ').map(w => h('span', { class: 'w' }, w + ' ')));
    const box = h('div', { class: 'lyrics', 'aria-live': 'off' }, DEMO.map(([c], i) => h('div', { class: 'line' }, h('span', { class: 'chord' }, c), words[i])));
    let t0, paused = 0;
    const btn = h('button', { class: 'primary', onclick: () => {
      if (timer) { clearInterval(timer); timer = null; paused = (performance.now() - t0) / 1000; btn.textContent = '▶ Resume'; return; }
      t0 = performance.now() - paused * 1000; btn.textContent = '⏸ Pause';
      timer = setInterval(() => {
        const at = wordAt((performance.now() - t0) / 1000);
        words.flat().forEach(w => w.classList.remove('on'));
        if (!at) { clearInterval(timer); timer = null; paused = 0; btn.textContent = '↺ Again'; return; }
        words[at[0]][at[1]].classList.add('on');
      }, 100);
    } }, '▶ Start');
    return [h('h1', {}, '🎤 ' + s.title), h('p', { class: 'mut' }, 'No audio in the local clone: lyrics follow a steady beat.'), btn, box];
  }

  function route() {
    clearInterval(timer); timer = null;
    const [path] = location.hash.replace(/^#\/?/, '').split('?');
    const [name, arg] = path.split('/');
    const page = pages[name];
    $('#view').replaceChildren(...(page ? page(arg) : notFound()).flat().filter(Boolean));
    $('#pageTitle').textContent = $('#view h1')?.textContent || 'Home';
    document.querySelectorAll('.side a').forEach(a => a.toggleAttribute('aria-current', a.getAttribute('href') === '#/' + name));
    $('#side').classList.remove('open'); $('#menu').setAttribute('aria-expanded', 'false');
  }

  // Search dialog: Ctrl/Cmd+K or /, arrow keys to choose, Enter to open.
  let sel = 0;
  const drawResults = () => {
    const r = search($('#q').value);
    sel = Math.min(sel, Math.max(r.length - 1, 0));
    $('#results').replaceChildren(...r.map((s, i) => h('a', { href: `#/chords/${s.id}`, role: 'option', class: i === sel ? 'sel' : '', onclick: () => $('#search').close() }, s.title, h('small', { class: 'mut' }, ' · ' + s.artist))),
      ...(r.length || !$('#q').value.trim() ? [] : [h('p', { class: 'mut' }, 'No results')]));
  };
  const openSearch = () => { $('#q').value = ''; sel = 0; drawResults(); $('#search').showModal(); };
  $('#q').addEventListener('input', () => { sel = 0; drawResults(); });
  $('#q').addEventListener('keydown', e => {
    const n = $('#results').querySelectorAll('a').length;
    if (e.key === 'ArrowDown') { sel = (sel + 1) % (n || 1); drawResults(); e.preventDefault(); }
    if (e.key === 'ArrowUp') { sel = (sel - 1 + n) % (n || 1); drawResults(); e.preventDefault(); }
    if (e.key === 'Enter') $('#results a.sel')?.click();
  });
  document.addEventListener('keydown', e => {
    if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !/INPUT|TEXTAREA/.test(document.activeElement.tagName))) { e.preventDefault(); openSearch(); }
  });
  $('#searchOpen').onclick = openSearch;
  $('#cardX').onclick = () => $('#card').close();

  const setTheme = t => { document.documentElement.dataset.theme = t; $('#theme').setAttribute('aria-checked', String(t === 'dark')); $('#theme').textContent = t === 'dark' ? '☾' : '☀'; db.set('theme', t); };
  setTheme(db.get('theme', 'dark'));
  $('#theme').onclick = () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  $('#menu').onclick = () => $('#menu').setAttribute('aria-expanded', String($('#side').classList.toggle('open')));
  if (db.get('betaHidden')) $('#beta').hidden = true;
  $('#betaX').onclick = () => { $('#beta').hidden = true; db.set('betaHidden', true); };

  addEventListener('hashchange', route);
  route();
}

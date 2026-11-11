// Run: node test.js
const assert = require('assert');
const fs = require('fs');
const { SONGS, search, wordAt } = require('./app.js');

assert.deepStrictEqual(search(''), []);
assert.strictEqual(search('  MULI ').length, 1);
assert.strictEqual(search('gallops').length, SONGS.length);
assert.deepStrictEqual(wordAt(0), [0, 0]);
assert.deepStrictEqual(wordAt(0.99), [0, 1]);
assert.deepStrictEqual(wordAt(4.5), [1, 0]); // line 0 has 9 words at 2 words/s
assert.strictEqual(wordAt(999), null);
// The clone must never talk to the network or use HTML injection.
const src = fs.readFileSync(__dirname + '/app.js', 'utf8');
assert(!/fetch\(|XMLHttpRequest|WebSocket|innerHTML|songerist\.com\//.test(src));
assert(fs.readFileSync(__dirname + '/index.html', 'utf8').includes("connect-src 'none'"));
console.log('ok');

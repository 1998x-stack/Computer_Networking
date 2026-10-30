const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('article export preserves content and serializes each comment exactly once', async () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'markdown.js'), 'utf8');
  let onReady;
  let save;
  let exportedBlob;
  let clicked = false;
  let revoked = false;
  let removed = false;

  const page = {
    outerHTML: '<main class="container"><h1>Heading</h1><pre><code>example</code></pre>'
      + '<table><tr><td>cell</td></tr></table><p>notes'
      + '<div class="comment">one-note</div></p></main>',
    querySelectorAll(selector) {
      if (selector === 'script, .comment-input-container') {
        return [{ remove() { removed = true; } }];
      }
      return [];
    }
  };

  class FakeURL extends URL {
    static createObjectURL(blob) { exportedBlob = blob; return 'blob:mock'; }
    static revokeObjectURL() { revoked = true; }
  }

  const document = {
    documentElement: { lang: 'zh-CN' },
    baseURI: 'https://example.org/network/lesson.html',
    title: 'Network & Notes',
    addEventListener(event, handler) {
      if (event === 'DOMContentLoaded') onReady = handler;
    },
    querySelectorAll() { return []; },
    querySelector(selector) {
      return selector === '.container' ? { cloneNode() { return page; } } : null;
    },
    createElement(tag) {
      if (tag === 'button') {
        return { addEventListener(event, handler) { if (event === 'click') save = handler; } };
      }
      if (tag === 'a') {
        return { click() { clicked = true; } };
      }
      throw new Error('unexpected element: ' + tag);
    },
    body: { appendChild() {} }
  };

  vm.runInNewContext(source, {
    window: {}, document, Blob, URL: FakeURL,
    setTimeout(fn) { fn(); }
  });
  onReady();
  save();

  assert.equal(clicked, true);
  assert.equal(revoked, true);
  assert.equal(removed, true);
  assert.ok(exportedBlob);
  const html = await exportedBlob.text();
  assert.match(html, /<!doctype html>/);
  assert.match(html, /<pre><code>example<\/code><\/pre>/);
  assert.match(html, /<table><tr><td>cell<\/td><\/tr><\/table>/);
  assert.equal((html.match(/class="comment"/g) || []).length, 1);
  assert.match(html, /<title>Network &amp; Notes<\/title>/);
  assert.doesNotMatch(html, /<script/);
});

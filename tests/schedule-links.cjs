const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('Skedz links follow the selected schedule and preserve Prague time', async () => {
  const elements = {};
  for (const id of ['timezone', 'apps-heading', 'apps-copy', 'notice', 'status', 'schedule', 'skedz-link', 'official-program', 'conference-logo', 'streams-heading', 'streams']) {
    elements[id] = { textContent: '', href: '', replaceChildren() {}, append() {} };
  }
  const xml = { textContent: '', set href(value) { this.url = new URL(value, 'https://example.github.io/booklet/').href; }, get href() { return this.url; } };
  elements['xml-link'] = xml;
  const buttons = ['cz', 'en'].map(language => ({ dataset: { language }, setAttribute() {}, addEventListener(name, fn) { this.click = fn; } }));
  const document = { documentElement: {}, getElementById: id => elements[id], querySelectorAll: () => buttons, createElement: () => ({ append() {} }) };
  const streams = JSON.parse(fs.readFileSync('data/streams.json', 'utf8'));
  const context = { document, URL, streams, setInterval() {}, fetch: async () => ({ ok: false }) };
  vm.runInNewContext(fs.readFileSync('build/site/schedule.js', 'utf8'), context);
  for (const [index, language] of ['cz', 'en'].entries()) {
    await buttons[index].click();
    assert.equal(elements['official-program'].href, language === 'cz' ? 'https://www.caj-u-mefista.cz/program/' : 'https://www.caj-u-mefista.cz/program-1/');
    if (language === 'en') assert.equal(elements.timezone.textContent, 'All times are in Prague time (CET, GMT+1).');
    assert.equal(elements['conference-logo'].src, `logo-${language}.jpg`);
    const url = new URL(elements['skedz-link'].href);
    assert.equal(url.origin, 'https://app.skedz.org');
    assert.equal(url.searchParams.get('url'), `https://example.github.io/booklet/schedule-${language}.xml`);
    assert.equal(url.searchParams.get('timezone'), 'Europe/Prague');
  }
});

test('stream selection follows current and next Prague stream windows', () => {
  const streams = JSON.parse(fs.readFileSync('data/streams.json', 'utf8'));
  const document = { querySelectorAll: () => [], documentElement: {}, getElementById: () => ({ setAttribute() {}, replaceChildren() {}, append() {} }), createElement: () => ({ append() {} }) };
  const context = { document, streams, URL, setInterval() {}, fetch: async () => ({ ok: false }) };
  vm.runInNewContext(fs.readFileSync('build/site/schedule.js', 'utf8'), context);
  const select = date => context.highlightStreams(Date.parse(date));
  assert.equal(select('2026-10-30T15:00:00+01:00'), 0);
  assert.equal(select('2026-10-30T16:15:00+01:00'), 0);
  assert.equal(select('2026-10-30T21:30:00+01:00'), 1);
  assert.equal(select('2026-10-31T14:00:00+01:00'), 2);
  assert.equal(select('2026-11-01T18:00:00+01:00'), -1);
});

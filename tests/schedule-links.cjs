const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('Skedz links follow the selected schedule and preserve Prague time', async () => {
  const elements = {};
  for (const id of ['timezone', 'apps-heading', 'apps-copy', 'notice', 'status', 'schedule', 'skedz-link']) {
    elements[id] = { textContent: '', href: '', replaceChildren() {} };
  }
  const xml = { textContent: '', set href(value) { this.url = new URL(value, 'https://example.github.io/booklet/').href; }, get href() { return this.url; } };
  elements['xml-link'] = xml;
  const buttons = ['cz', 'en'].map(language => ({ dataset: { language }, setAttribute() {}, addEventListener(name, fn) { this.click = fn; } }));
  const document = { documentElement: {}, getElementById: id => elements[id], querySelectorAll: () => buttons };
  const context = { document, URL, fetch: async () => ({ ok: false }) };
  vm.runInNewContext(fs.readFileSync('build/site/schedule.js', 'utf8'), context);
  for (const [index, language] of ['cz', 'en'].entries()) {
    await buttons[index].click();
    const url = new URL(elements['skedz-link'].href);
    assert.equal(url.origin, 'https://app.skedz.org');
    assert.equal(url.searchParams.get('url'), `https://example.github.io/booklet/schedule-${language}.xml`);
    assert.equal(url.searchParams.get('timezone'), 'Europe/Prague');
  }
});

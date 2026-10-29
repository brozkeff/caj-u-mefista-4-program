'use strict';
const translations = {
  cz: { streams: 'Online přenosy', live: 'Právě probíhá', next: 'Nejbližší přenos', official: 'Oficiální program na webu konference ↗', officialUrl: 'https://www.caj-u-mefista.cz/program/', logoAlt: 'Čaj u Mefista 4', timezone: 'Časy jsou uvedeny v časovém pásmu Praha (Europe/Prague).', loading: 'Načítám program…', error: 'Program se nepodařilo načíst. Zkuste to prosím později.', details: 'Anotace', apps: 'Program v mobilu', copy: 'Na Androidu můžete načíst XML do Giggity. Na iPhonu otevřete program ve Skedz; v Safari jej můžete přidat na plochu.', notice: 'Výstavy jsou uvedeny bez času. Délky některých položek jsou orientační.', locale: 'cs-CZ' },
  en: { streams: 'Live streams', live: 'Live now', next: 'Next stream', official: 'Official programme on the conference website ↗', officialUrl: 'https://www.caj-u-mefista.cz/program-1/', logoAlt: 'Tea at Mephisto’s 4', timezone: 'All times are in Prague time (CET, GMT+1).', loading: 'Loading the schedule…', error: 'The schedule could not be loaded. Please try again later.', details: 'Abstract', apps: 'Schedule on your phone', copy: 'On Android, you can load the XML in Giggity. On iPhone, open the schedule in Skedz; you can add it to your Home Screen from Safari.', notice: 'Exhibitions are listed without a time. Some event durations are estimates.', locale: 'en-GB' }
};
function highlightStreams(now = Date.now()) {
  const active = streams.findIndex(stream => now >= Date.parse(stream.start) && now < Date.parse(stream.end));
  const next = streams.findIndex(stream => now < Date.parse(stream.start));
  return active >= 0 ? active : next;
}
function showStreams(language) {
  const t = translations[language], target = document.getElementById('streams');
  document.getElementById('streams-heading').textContent = t.streams;
  const selected = highlightStreams(), now = Date.now();
  target.replaceChildren();
  streams.forEach((stream, index) => {
    const link = document.createElement('a');
    link.href = stream.url;
    if (index === selected) link.className = 'active';
    link.textContent = `${stream[language]} · ${stream.start.slice(11, 16)}–${stream.end.slice(11, 16)} ↗`;
    if (index === selected) {
      const label = document.createElement('small');
      label.textContent = now >= Date.parse(stream.start) ? t.live : t.next;
      link.append(label);
    }
    target.append(link);
  });
}
let selectedLanguage = 'cz';
setInterval(() => showStreams(selectedLanguage), 60000);
let current = 0;
async function show(language) {
  const request = ++current, t = translations[language];
  selectedLanguage = language;
  showStreams(language);
  document.documentElement.lang = language === 'cz' ? 'cs' : 'en';
  document.querySelectorAll('[data-language]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.language === language)));
  for (const [id, text] of Object.entries({ timezone: t.timezone, 'apps-heading': t.apps, 'apps-copy': t.copy, notice: t.notice, status: t.loading })) document.getElementById(id).textContent = text;
  const official = document.getElementById('official-program');
  official.href = t.officialUrl; official.textContent = t.official;
  const logo = document.getElementById('conference-logo');
  logo.src = `logo-${language}.jpg`; logo.alt = t.logoAlt;
  const xmlLink = document.getElementById('xml-link');
  xmlLink.href = `schedule-${language}.xml`;
  xmlLink.textContent = `XML · ${language.toUpperCase()} ↓`;
  const skedz = new URL('https://app.skedz.org/');
  skedz.searchParams.set('url', xmlLink.href);
  skedz.searchParams.set('timezone', 'Europe/Prague');
  document.getElementById('skedz-link').href = skedz.href;
  const target = document.getElementById('schedule');
  target.replaceChildren();
  try {
    const response = await fetch(xmlLink.href);
    if (!response.ok) throw new Error('HTTP error');
    const xml = new DOMParser().parseFromString(await response.text(), 'application/xml');
    if (xml.querySelector('parsererror') || !xml.querySelector('schedule')) throw new Error('Invalid XML');
    if (request !== current) return;
    for (const day of xml.querySelectorAll('schedule > day')) {
      const section = document.createElement('section'); section.className = 'day';
      const heading = document.createElement('h2');
      // A UTC date here formats the date label only; event times remain the XML's Prague wall times.
      heading.textContent = new Intl.DateTimeFormat(t.locale, { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' }).format(new Date(`${day.getAttribute('date')}T12:00:00Z`));
      section.append(heading);
      for (const exhibition of day.querySelectorAll('untimed_events > event')) {
        const row = document.createElement('article'); row.className = 'event';
        const time = document.createElement('span'); time.textContent = '—';
        const title = document.createElement('h3'); title.textContent = exhibition.textContent;
        row.append(time, title); section.append(row);
      }
      const events = [...day.querySelectorAll('room > event')].sort((a, b) => a.querySelector('start').textContent.localeCompare(b.querySelector('start').textContent));
      for (const event of events) {
        const row = document.createElement('article'); row.className = 'event';
        const time = document.createElement('time'); time.textContent = event.querySelector('start').textContent;
        const content = document.createElement('div');
        const title = document.createElement('h3'); title.textContent = event.querySelector('title').textContent; content.append(title);
        const people = [...event.querySelectorAll('persons > person')].map(person => person.textContent).join(', ');
        if (people) { const p = document.createElement('p'); p.textContent = people; content.append(p); }
        const abstract = event.querySelector('abstract')?.textContent.trim();
        if (abstract) { const details = document.createElement('details'), summary = document.createElement('summary'), p = document.createElement('p'); summary.textContent = t.details; p.className = 'abstract'; p.textContent = abstract; details.append(summary, p); content.append(details); }
        row.append(time, content); section.append(row);
      }
      target.append(section);
    }
    document.getElementById('status').textContent = '';
  } catch (error) { if (request === current) document.getElementById('status').textContent = t.error; }
}
document.querySelectorAll('[data-language]').forEach(button => button.addEventListener('click', () => show(button.dataset.language)));
show('cz');

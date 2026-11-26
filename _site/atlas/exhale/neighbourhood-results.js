function createNeighbourhoodResults(metadata, valuesFor) {
  const form = document.getElementById('neighbourhood-search');
  const search = document.getElementById('neighbourhood-query');
  const status = document.getElementById('neighbourhood-status');
  const table = document.getElementById('neighbourhood-table');
  const caption = table.caption;
  const rows = table.tBodies[0];
  const vulnerabilityHeading = document.getElementById('neighbourhood-vulnerability');
  const pagination = document.getElementById('neighbourhood-pages');
  const previous = document.getElementById('neighbourhood-previous');
  const next = document.getElementById('neighbourhood-next');

  const pageSize = 12;
  const collator = new Intl.Collator('en-GB', { sensitivity: 'base', numeric: true });
  function normalise(text) {
    return text.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase('en-GB')
      .replace(/['’]/g, '').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  }

  const areas = metadata.code.map((code, index) => ({
    index,
    code,
    name: metadata.name[index],
    country: metadata.country[index],
    region: metadata.region[index],
    searchName: normalise(metadata.name[index]),
    searchCode: normalise(code),
  })).sort((a, b) => collator.compare(a.name, b.name) || collator.compare(a.code, b.code));

  let selection;
  let matches = areas;
  let page = 0;

  function appendText(parent, tag, text, className) {
    const child = document.createElement(tag);
    child.textContent = text;
    if (className) child.className = className;
    parent.append(child);
    return child;
  }

  function render() {
    const first = page * pageSize;
    const last = Math.min(first + pageSize, matches.length);
    let message = 'No neighbourhoods match your search.';
    if (matches.length === 1) message = '1 neighbourhood found.';
    if (matches.length > 1) {
      message = `Showing ${first + 1}–${last} of ${matches.length.toLocaleString('en-GB')} neighbourhoods.`;
    }
    if (status.textContent !== message) status.textContent = message;
    table.hidden = matches.length === 0;
    pagination.hidden = matches.length <= pageSize;
    previous.setAttribute('aria-disabled', String(first === 0));
    next.setAttribute('aria-disabled', String(last === matches.length));
    vulnerabilityHeading.hidden = !selection.vul;
    caption.replaceChildren();
    appendText(caption, 'strong', selection.poll);
    appendText(caption, 'span', selection.indLabel);
    if (selection.vul) appendText(caption, 'span', selection.vulLabel);

    const pageRows = document.createDocumentFragment();
    for (const area of matches.slice(first, last)) {
      const { indicator, vulnerability } = valuesFor(area.index);
      const row = document.createElement('tr');
      const heading = appendText(row, 'th', area.name);
      heading.scope = 'row';
      const location = area.country === 'England' && area.region
        ? `${area.region}, ${area.country}` : area.country;
      appendText(heading, 'span', area.code, 'neighbourhood-code');
      appendText(heading, 'span', location, 'neighbourhood-location');
      appendText(row, 'td', indicator);
      if (selection.vul) appendText(row, 'td', vulnerability);
      pageRows.append(row);
    }
    rows.replaceChildren(pageRows);
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const query = normalise(search.value);
    const words = query.split(' ');
    matches = query ? areas.filter((area) =>
      area.searchCode.includes(query) || words.every((word) => area.searchName.includes(word))
    ) : areas;
    page = 0;
    render();
  });
  document.getElementById('neighbourhood-clear').addEventListener('click', () => {
    search.value = '';
    form.requestSubmit();
    search.focus();
  });

  function turnPage(button, step) {
    if (button.getAttribute('aria-disabled') === 'true') return;
    page += step;
    render();
  }
  previous.addEventListener('click', () => turnPage(previous, -1));
  next.addEventListener('click', () => turnPage(next, 1));

  return function updateResults(nextSelection) {
    selection = nextSelection;
    render();
  };
}

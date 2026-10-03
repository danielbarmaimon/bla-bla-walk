// Both address fields share bounded, cancellable official lookup.
export function addressSearch(input, list, status, mode, select, samples, settings) {
  let timer;
  let controller;
  let version = 0;

  function clear() {
    clearTimeout(timer);
    controller?.abort();
    version += 1;
    list.replaceChildren();
    list.hidden = true;
    input.setAttribute('aria-expanded', 'false');
  }

  function render(places, token) {
    if (token !== version) return;
    list.replaceChildren();
    for (const place of places) {
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('role', 'option');
      button.textContent = place.name;
      button.onclick = () => {
        clear();
        select(place);
        status.textContent = place.id.startsWith('address-') ? 'Address selected · © swisstopo' : 'Sample place selected';
      };
      list.append(button);
    }
    list.hidden = !places.length;
    input.setAttribute('aria-expanded', String(places.length > 0));
  }

  async function search(query, token) {
    controller = new AbortController();
    status.textContent = 'Searching Basel addresses…';
    try {
      const response = await fetch('/api/addresses', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query,
          mode
        }),
        signal: controller.signal,
        cache: 'no-store'
      });
      if (!response.ok) throw new Error('Search unavailable');
      const value = await response.json();
      if (token !== version) return;
      const local = samples.filter(place => place.name.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
      render([...value.places, ...local].slice(0, 10), token);
      status.textContent = value.places.length ? 'Choose an address · © swisstopo' : local.length ? 'Sample matches only; no official address found.' : 'No address found in Basel-Stadt. Add the street number or pin on map.';
    } catch (error) {
      if (error.name === 'AbortError' || token !== version) return;
      render(samples.filter(place => place.name.toLocaleLowerCase().includes(query.toLocaleLowerCase())), token);
      status.textContent = 'Address search unavailable. Try again or pin on map.';
    }
  }

  input.addEventListener('input', () => {
    clear();
    const query = input.value.trim();
    if (query.length < 3) {
      status.textContent = 'Type at least three characters, then choose a result.';
      return;
    }
    const token = version;
    if (mode === 'offline') {
      render(samples.filter(place => place.name.toLocaleLowerCase().includes(query.toLocaleLowerCase())), token);
      status.textContent = 'Offline: address lookup unavailable. Choose a sample place or pin on map.';
      return;
    }
    timer = setTimeout(() => search(query, token), settings.debounce_ms);
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'Escape') clear();
    if (event.key === 'ArrowDown' && !list.hidden) {
      event.preventDefault();
      list.querySelector('button')?.focus();
    }
    if (event.key === 'Enter' && !list.hidden) {
      event.preventDefault();
      list.querySelector('button')?.click();
    }
  });
  list.addEventListener('keydown', event => {
    const buttons = [...list.querySelectorAll('button')];
    const index = buttons.indexOf(document.activeElement);
    if (event.key === 'Escape') {
      clear();
      input.focus();
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      buttons[(index + (event.key === 'ArrowDown' ? 1 : buttons.length - 1)) % buttons.length]?.focus();
    }
  });
  input.disabled = false;
  return clear;
}

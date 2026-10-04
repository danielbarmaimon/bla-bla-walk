import {
  savedLandmarkEvidence,
  searchSavedLandmarks
} from './route-landmarks.js';

// Saved matches reuse local data; the existing official lookup still sends queries.
const landmarkEvidence = fetch('/api/route-amenities?mode=offline', {
    cache: 'no-store'
  })
  .then(response => response.ok ? response.json() : null)
  .then(amenities => savedLandmarkEvidence(amenities))
  .catch(() => savedLandmarkEvidence());

// Both journey fields share bounded, cancellable address and landmark lookup.
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
      if (place.landmark) {
        const detail = document.createElement('small');
        detail.textContent = ' · Saved mapped landmark · OpenStreetMap';
        if (place.locationHint) detail.textContent += ` · ${place.locationHint}`;
        button.append(detail);
      } else if (!place.id.startsWith('address-')) {
        const detail = document.createElement('small');
        detail.textContent = ' · Sample place';
        button.append(detail);
      }
      button.onclick = () => {
        clear();
        select(place);
        status.textContent = place.landmark ? 'Mapped landmark selected · © OpenStreetMap contributors; entrance and access unverified.' : place.id.startsWith('address-') ? 'Address selected · © swisstopo' : 'Sample place selected';
      };
      list.append(button);
    }
    list.hidden = !places.length;
    input.setAttribute('aria-expanded', String(places.length > 0));
  }

  async function localMatches(query, token) {
    const evidence = await landmarkEvidence;
    if (token !== version) return [];
    const landmarks = searchSavedLandmarks(query, evidence, settings.result_limit);
    const local = samples.filter(place => place.name.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
    return [...landmarks, ...local].slice(0, 10);
  }

  async function search(query, token) {
    controller = new AbortController();
    const local = await localMatches(query, token);
    if (token !== version) return;
    render(local, token);
    status.textContent = 'Searching Basel addresses; saved landmark coverage is limited…';
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
      render([...local, ...value.places].slice(0, 10), token);
      status.textContent = local.some(place => place.landmark) ? 'Choose a saved mapped landmark or address. Landmark coverage is limited; access unverified.' : value.places.length ? 'Choose an address · © swisstopo' : local.length ? 'Sample matches only; no official address found.' : 'No address or saved landmark found. Try another name, street number or pin on map.';
    } catch (error) {
      if (error.name === 'AbortError' || token !== version) return;
      render(local, token);
      status.textContent = local.some(place => place.landmark) ? 'Address search unavailable. Saved mapped landmarks available; coverage limited.' : 'Address search unavailable. Try again or pin on map.';
    }
  }

  input.addEventListener('input', async () => {
    clear();
    const query = input.value.trim();
    if (query.length < 3) {
      status.textContent = 'Type at least three characters, then choose a result.';
      return;
    }
    const token = version;
    if (mode === 'offline') {
      const local = await localMatches(query, token);
      if (token !== version) return;
      render(local, token);
      status.textContent = 'Offline: choose a saved mapped landmark, sample place or map pin. Landmark coverage is limited.';
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
  input.placeholder = 'Search a Basel address or landmark';
  list.setAttribute('aria-label', input.id === 'origin-input' ? 'Suggested starting addresses and landmarks' : 'Suggested destination addresses and landmarks');
  return clear;
}

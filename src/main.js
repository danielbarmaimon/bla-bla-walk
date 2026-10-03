import {
  loadSnapshot
} from './api.js';
import {
  createMap
} from './map.js';

const app = document.querySelector('#app');
app.innerHTML = `
  <header>
    <div><p class="eyebrow">Bla Bla Walk</p><h1>Explore Basel</h1></div>
    <div><p id="mode-title">Map foundation</p>
    <nav aria-label="Data mode"><a href="/?mode=online">Online</a> · <a href="/?mode=offline">Offline</a> · <a href="/">Fixtures</a></nav></div>
  </header>
  <main>
    <aside aria-label="Map layers and feature information">
      <section>
        <h2>Layers</h2>
        <p class="notice" id="mode-notice">Loading selected data mode…</p>
        <p id="api-status" role="status">Loading fixture API…</p>
        <button id="reload" type="button">Reload layers</button>
        <label class="layer-control" for="pet-layer-toggle">
          <input id="pet-layer-toggle" type="checkbox">
          <span><strong>Historical PET heat layer</strong><small>Fixed 14:00 summer scenario · Geodaten Kanton Basel-Stadt · CC BY 4.0</small></span>
        </label>
        <p id="pet-status" role="status">PET map is shown in online mode.</p>
        <details class="pet-legend">
          <summary>PET class legend</summary>
          <ul id="pet-legend-list" aria-label="Physiological Equivalent Temperature classes"></ul>
        </details>
        <div id="layers"></div>
      </section>
      <section aria-labelledby="features-title">
        <h2 id="features-title">Inspect a feature</h2>
        <p>Click a marker, or choose a feature below.</p>
        <div id="features"></div>
      </section>
      <section id="details" aria-label="Selected feature" aria-live="polite">
        <p>Select a feature to see its source and timestamps.</p>
      </section>
    </aside>
    <section class="map-panel" aria-label="Basel map">
      <div id="map" tabindex="0" role="region" aria-label="Interactive Basel map. Arrow keys pan; plus and minus zoom."></div>
      <p id="basemap-status" role="status">Loading Basel basemap…</p>
      <p class="map-note">PET colours show the canton’s modelled 14:00 summer scenario, not today’s weather. Route details show estimated distance in each PET class; unknown map cells remain unknown.</p>
    </section>
  </main>`;

const status = document.querySelector('#api-status');
const layerControls = document.querySelector('#layers');
const featureList = document.querySelector('#features');
const details = document.querySelector('#details');
const reload = document.querySelector('#reload');
const petToggle = document.querySelector('#pet-layer-toggle');
const map = createMap(
  document.querySelector('#map'),
  showFeature,
  (message) => {
    document.querySelector('#basemap-status').textContent = message;
  },
  (message) => {
    document.querySelector('#pet-status').textContent = message;
  },
);
const dataMode = new URLSearchParams(location.search).get('mode') || 'fixture';
petToggle.checked = dataMode === 'online';
petToggle.disabled = dataMode !== 'online';
document.querySelector('#pet-status').textContent = dataMode === 'offline'
  ? 'PET map needs internet; saved route classes, when available, are stale.'
  : dataMode === 'online'
    ? 'Loading the historical PET map…'
    : 'Open Online mode to load the historical PET map and route classes.';
map.setPetVisible(petToggle.checked);
petToggle.addEventListener('change', () => map.setPetVisible(petToggle.checked));

/** Render untrusted feature text as text nodes, including timestamps and gaps. */
/** @param {import('./interfaces').MapFeature} feature */
function showFeature(feature) {
  details.replaceChildren();
  const title = document.createElement('h2');
  title.textContent = feature.label;
  details.append(title);
  const source = feature.provenance;
  const rows = [
    ['Data mode', source.fixture ? 'Synthetic fixture' : 'Provider data'],
    ['Availability', feature.availability],
    ['Value', feature.value == null ? 'Unknown / no value' : `${feature.value} ${feature.unit ?? ''}`],
    ['Meaning', feature.explanation],
    ['Drinking water', feature.drinking_water ?? 'Not applicable'],
    ['Route distance', feature.route ? `${Math.round(feature.route.distance_m)} m · ${Math.round(feature.route.duration_s / 60)} min walking estimate` : 'Not applicable'],
    ['Provider', source.provider],
    ['Attribution', source.attribution],
    ['Licence', source.licence],
    ['Observed', formatTime(source.observed_at)],
    ['Retrieved', formatTime(source.retrieved_at)],
  ];
  const list = document.createElement('dl');
  rows.forEach(([label, value]) => {
    const term = document.createElement('dt');
    term.textContent = label;
    const description = document.createElement('dd');
    description.textContent = value;
    list.append(term, description);
  });
  details.append(list);
  if (feature.pet) {
    const petTitle = document.createElement('h3');
    petTitle.textContent = 'Historical PET along this route';
    const petNote = document.createElement('p');
    petNote.textContent = `${feature.pet.scenario}. ${Math.round(feature.pet.known_distance_m)} m classified; ${Math.round(feature.pet.unknown_distance_m)} m unknown, sampled at ${feature.pet.resolution_m} m.`;
    const petBands = document.createElement('ul');
    Object.entries(feature.pet.class_distances_m).forEach(([band, distance]) => {
      const item = document.createElement('li');
      item.textContent = `${band}: ${Math.round(distance)} m`;
      petBands.append(item);
    });
    details.append(petTitle, petNote, petBands);
    const petSource = document.createElement('p');
    petSource.textContent = `${feature.pet.provenance.attribution} · ${feature.pet.provenance.licence} · ${feature.pet.availability} · retrieved ${formatTime(feature.pet.provenance.retrieved_at)}`;
    details.append(petSource);
  }
  if (source.source_url?.startsWith('https://')) {
    const link = document.createElement('a');
    link.href = source.source_url;
    link.textContent = 'Open source metadata';
    details.append(link);
  }
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString('en-GB', {
    timeZone: 'UTC'
  }) + ' UTC' : 'Unknown / not supplied';
}

async function renderPetLegend() {
  const list = document.querySelector('#pet-legend-list');
  try {
    const response = await fetch('/config/pet-classes.json');
    if (!response.ok) throw new Error('Legend unavailable');
    const config = await response.json();
    config.classes.forEach((petClass) => {
      const item = document.createElement('li');
      const swatch = document.createElement('span');
      swatch.className = 'pet-swatch';
      swatch.style.backgroundColor = `rgb(${petClass.rgb.join(',')})`;
      const label = document.createElement('span');
      label.textContent = petClass.label;
      item.append(swatch, label);
      list.append(item);
    });
  } catch {
    list.textContent = 'PET class legend unavailable.';
  }
}

/** @param {import('./interfaces').MapLayer[]} layers */
function renderLayers(layers) {
  layerControls.replaceChildren();
  featureList.replaceChildren();
  layers.forEach((layer) => {
    const control = document.createElement('label');
    control.className = 'layer-control';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = true;
    const text = document.createElement('span');
    const name = document.createElement('strong');
    name.textContent = layer.label;
    const summary = document.createElement('small');
    summary.textContent = `${layer.availability} · ${layer.explanation}`;
    text.append(name, summary);
    control.append(checkbox, text);
    layerControls.append(control);
    const group = document.createElement('div');
    group.className = 'feature-group';
    layer.features.forEach((feature) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = feature.route && feature.pet
        ? `${feature.label} · ${Math.round(feature.route.distance_m)} m · PET ${feature.pet.availability} · ${Math.round(feature.pet.known_distance_m)} m classified · ${Math.round(feature.pet.unknown_distance_m)} m unknown`
        : `${feature.label} · ${feature.availability}`;
      button.addEventListener('click', () => {
        showFeature(feature);
        map.focus(feature);
      });
      group.append(button);
    });
    checkbox.addEventListener('change', () => {
      map.setVisible(layer.id, checkbox.checked);
      group.hidden = !checkbox.checked;
      details.textContent = 'Select a visible sample to inspect its source.';
    });
    featureList.append(group);
  });
}

async function refresh() {
  reload.disabled = true;
  status.textContent = 'Loading fixture API…';
  try {
    const snapshot = await loadSnapshot();
    const messages = {
      fixture: 'Fixture mode: invented locations and values. Not current conditions.',
      offline: 'Offline mode: saved provider data. Observations are historical; no live refresh.',
      online: 'Online mode: provider data with source timestamps. Missing and stale values remain explicit.',
    };
    document.querySelector('#mode-title').textContent = `${snapshot.mode} data mode`;
    document.querySelector('#mode-notice').textContent = messages[snapshot.mode];
    map.replaceLayers(snapshot.layers);
    renderLayers(snapshot.layers);
    details.textContent = 'Select a feature to see its source and timestamps.';
    const label = snapshot.mode === 'fixture' ? 'Fixture API' : snapshot.mode === 'offline' ? 'Saved data API' : 'Provider API';
    status.textContent = `${label} connected · snapshot ${formatTime(snapshot.generated_at)}`;
  } catch {
    map.replaceLayers([]);
    layerControls.replaceChildren();
    featureList.replaceChildren();
    details.textContent = 'No overlay data available. The basemap can still be used.';
    status.textContent = 'Layers missing: API unavailable, saved data missing, or invalid response. Check setup, then reload layers.';
  } finally {
    reload.disabled = false;
  }
}

reload.addEventListener('click', () => void refresh());
void renderPetLegend();
void refresh();

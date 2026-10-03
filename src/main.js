import {
  parseSnapshot
} from './api.js';
import {
  createMap
} from './map.js';
import {
  CATEGORIES,
  PLACES
} from './sample-places.js';
import {
  FOUNTAIN_BUFFER_M,
  SENSOR_BUFFER_M,
  routeGeometry,
  nearbyFeatures
} from './route-planner-data.js';
import {
  WAYFINDING_PLACES,
  COOL_PLACES,
  routeStops
} from './wayfinding-places.js';

const FALLBACK_START = {
  id: 'sbb',
  name: 'Basel SBB · demo start',
  lon: 7.590209,
  lat: 47.548055
};
const MARKTPLATZ = PLACES.find((place) => place.id === 'marktplatz');
const mode = new URLSearchParams(location.search).get('mode') || 'fixture';
const state = {
  snapshot: null,
  origin: FALLBACK_START,
  destination: MARKTPLATZ,
  preference: 'fast',
  selectedRouteId: 'demo-route-a',
  route: null
};
const $ = (selector) => document.querySelector(selector);
const routes = () => state.snapshot?.layers.find((layer) => layer.kind === 'route')?.features ?? [];
const selectedRoute = () => routes().find((route) => route.id === state.selectedRouteId) ?? routes()[0];
const routePairSelected = () => state.origin.id === 'sbb' && state.destination?.id === 'marktplatz';
const sourceFeatures = (kind) => state.snapshot?.layers.find((layer) => layer.kind === kind)?.features ?? [];
const fountainsNearRoute = () => state.route ? nearbyFeatures(state.route, sourceFeatures('fountain'), FOUNTAIN_BUFFER_M) : [];
const sensorsNearRoute = () => state.route ? nearbyFeatures(state.route, sourceFeatures('observation'), SENSOR_BUFFER_M) : [];

function icon(name) {
  const image = document.createElement('img');
  image.src = `/src/icons/${name}.svg`;
  image.alt = '';
  image.width = 20;
  image.height = 20;
  return image;
}
document.querySelectorAll('[data-icon]').forEach((slot) => slot.replaceChildren(icon(slot.dataset.icon)));

function formatTime(value) {
  return value ? `${new Date(value).toLocaleString('en-GB', { timeZone: 'UTC' })} UTC` : 'Unknown / not supplied';
}

function showFeature(feature) {
  const details = $('#details');
  details.replaceChildren();
  const title = document.createElement('h3');
  title.textContent = feature.label;
  details.append(title);
  const source = feature.provenance;
  const rows = [
    ['Data mode', source.fixture ? 'Synthetic fixture' : 'Provider data'],
    ['Availability', feature.availability],
    ['Value', feature.value == null ? 'Unknown / no value' : `${feature.value} ${feature.unit ?? ''}`],
    ['Meaning', feature.explanation],
    ['Drinking water', feature.drinking_water ?? 'Not applicable'],
    ['Walking estimate', feature.route ? `${Math.round(feature.route.distance_m)} m · ${Math.round(feature.route.duration_s / 60)} min` : 'Not applicable'],
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
    const heading = document.createElement('h4');
    heading.textContent = 'Historical PET along this route';
    const summary = document.createElement('p');
    summary.textContent = `${feature.pet.scenario}. ${Math.round(feature.pet.known_distance_m)} m classified; ${Math.round(feature.pet.unknown_distance_m)} m unknown at ${feature.pet.resolution_m} m resolution.`;
    const bands = document.createElement('ul');
    Object.entries(feature.pet.class_distances_m).forEach(([band, distance]) => {
      const item = document.createElement('li');
      item.textContent = `${band}: ${Math.round(distance)} m`;
      bands.append(item);
    });
    details.append(heading, summary, bands);
  }
  if (source.source_url?.startsWith('https://')) {
    const link = document.createElement('a');
    link.href = source.source_url;
    link.textContent = 'Open source metadata';
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    details.append(link);
  }
}

function renderFeatures() {
  const list = $('#features');
  list.replaceChildren();
  state.snapshot?.layers.forEach((layer) => {
    const group = document.createElement('details');
    group.className = 'feature-group';
    const summary = document.createElement('summary');
    summary.textContent = `${layer.label} · ${layer.availability}`;
    group.append(summary);
    layer.features.forEach((feature) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = feature.route ? `${feature.label} · ${Math.round(feature.route.distance_m)} m · PET ${feature.pet?.availability ?? 'unavailable'}` : `${feature.label} · ${feature.availability}`;
      button.addEventListener('click', () => {
        showFeature(feature);
        map.focus(feature);
      });
      group.append(button);
    });
    list.append(group);
  });
}

function renderLayers() {
  const container = $('#layers');
  container.replaceChildren();
  state.snapshot?.layers.forEach((layer) => {
    const label = document.createElement('label');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = true;
    const text = document.createElement('span');
    const name = document.createElement('strong');
    name.textContent = layer.label;
    const note = document.createElement('small');
    note.textContent = `${layer.availability} · ${layer.explanation}`;
    text.append(name, note);
    label.append(checkbox, text);
    container.append(label);
    checkbox.addEventListener('change', () => map.setVisible(layer.id, checkbox.checked));
  });
}

function distanceMetres(a, b) {
  const radians = Math.PI / 180;
  const dLat = (b.lat - a.lat) * radians;
  const dLon = (b.lon - a.lon) * radians;
  const arc = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * radians) * Math.cos(b.lat * radians) * Math.sin(dLon / 2) ** 2;
  return 12742000 * Math.asin(Math.sqrt(arc));
}

function closestPlace(category) {
  return PLACES.filter((place) => place.category === category && place.id !== state.origin.id).sort((a, b) => distanceMetres(state.origin, a) - distanceMetres(state.origin, b))[0];
}

function renderQuickPlaces() {
  const grid = $('#quick-grid');
  grid.replaceChildren();
  CATEGORIES.forEach(([category, iconName]) => {
    const place = closestPlace(category);
    if (!place) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'quick-tile';
    button.append(icon(iconName));
    const title = document.createElement('strong');
    title.textContent = category;
    const label = document.createElement('small');
    label.textContent = place.name;
    button.append(title, label);
    button.addEventListener('click', () => selectDestination(place));
    grid.append(button);
  });
}

function renderSuggestions(query) {
  const list = $('#suggestions');
  list.replaceChildren();
  const matches = PLACES.filter((place) => `${place.name} ${place.category}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())).slice(0, 6);
  if (!query.trim() || !matches.length) {
    list.hidden = true;
    return;
  }
  matches.forEach((place) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('role', 'option');
    button.textContent = place.name;
    button.addEventListener('click', () => selectDestination(place));
    list.append(button);
  });
  list.hidden = false;
}

function setPins() {
  map.setPins(state.origin, state.destination);
}

function selectDestination(place) {
  state.destination = place;
  $('#destination-input').value = place.name;
  $('#suggestions').hidden = true;
  renderJourney();
  setPins();
}

function setOrigin(place, message) {
  state.origin = place;
  $('#origin-input').value = place.name;
  $('#origin-status').textContent = message;
  renderQuickPlaces();
  renderJourney();
  setPins();
}

function selectPreference(preference) {
  state.preference = preference;
  $('#fast-mode').setAttribute('aria-pressed', String(preference === 'fast'));
  $('#shade-mode').setAttribute('aria-pressed', String(preference === 'shade'));
  if (preference === 'fast' && routes().length) state.selectedRouteId = [...routes()].sort((a, b) => a.route.duration_s - b.route.duration_s)[0].id;
  renderJourney();
}

function routeSteps() {
  const route = selectedRoute();
  if (!route || !routePairSelected()) return [];
  const water = fountainsNearRoute().find((point) => point.distance <= 25);
  const steps = [
    ['Start', 'Begin at Basel SBB / Centralbahnplatz.', 'Checked route snapshot start; local access is not verified.'],
    ['Walk', `Follow the highlighted walking option${route.label ? `, ${route.label}` : ''}.`, 'Street directions beyond the named path are not separately audited.'],
  ];
  if (route.id === 'demo-route-a') {
    steps.push(['Wayfinding', 'Barfüsserplatz is a named point on this route.', 'Nearby landmarks and visibility are unverified.']);
    steps.push(['Rest', 'Optional rest near Barfüsserplatz.', 'Example cue; seating and access are unverified.']);
  }
  if (water) steps.push(['Water', `${water.feature.label} is near the route.`, 'Location only; drinking water and operation are unknown.']);
  if (route.id === 'demo-route-a') steps.push(['Pause', 'Optional pause before Marktplatz.', 'Example cue; no verified seating information.']);
  steps.push(['Arrive', 'Finish at Marktplatz.', 'Checked route snapshot destination; local access is not verified.']);
  return steps;
}

function appendStep([type, instruction, note]) {
  const item = document.createElement('li');
  if (['Rest', 'Pause', 'Water'].includes(type)) item.className = 'care-step';
  const heading = document.createElement('strong');
  const icons = {
    Rest: 'armchair',
    Pause: 'pause',
    Water: 'droplets',
    Wayfinding: 'landmark'
  };
  if (icons[type]) heading.append(icon(icons[type]));
  heading.append(document.createTextNode(type));
  const text = document.createElement('p');
  text.textContent = instruction;
  const detail = document.createElement('small');
  detail.textContent = note;
  item.append(heading, text, detail);
  $('#step-list').append(item);
}

function renderRouteOptions() {
  const list = $('#route-options');
  list.replaceChildren();
  if (!routePairSelected()) return;
  routes().forEach((route) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'route-option';
    button.setAttribute('aria-pressed', String(route.id === state.selectedRouteId));
    const title = document.createElement('strong');
    title.textContent = route.label;
    const metrics = document.createElement('span');
    metrics.textContent = `${Math.round(route.route.distance_m)} m · ${Math.round(route.route.duration_s / 60)} min walking estimate`;
    const pet = document.createElement('small');
    pet.textContent = route.pet ? `Historical PET: ${Math.round(route.pet.known_distance_m)} m classified · ${Math.round(route.pet.unknown_distance_m)} m unknown · ${route.pet.availability}` : 'Historical PET route classes unavailable';
    button.append(title, metrics, pet);
    button.addEventListener('click', () => {
      state.selectedRouteId = route.id;
      renderJourney();
      map.focus(route);
    });
    list.append(button);
  });
}

function renderNearby() {
  const details = $('#nearby-details');
  details.hidden = !routePairSelected() || !state.route;
  if (details.hidden) return;
  const fountains = fountainsNearRoute();
  const sensors = sensorsNearRoute();
  $('#nearby-summary').textContent = `Nearby source points · ${fountains.length} fountains, ${sensors.length} sensors`;
  const list = $('#nearby-list');
  list.replaceChildren();
  fountains.forEach(({
    feature,
    distance
  }) => {
    const item = document.createElement('li');
    item.textContent = `Fountain · ${feature.label} · ${Math.round(distance)} m from route · drinking status unknown`;
    list.append(item);
  });
  sensors.forEach(({
    feature,
    distance
  }) => {
    const item = document.createElement('li');
    item.textContent = `Sensor · ${feature.label} · ${Math.round(distance)} m from route · ${feature.value == null ? 'no reading' : `${feature.value.toFixed(1)}°C`} · ${feature.availability} · observed ${formatTime(feature.provenance.observed_at)}`;
    list.append(item);
  });
  const contextPlaces = selectedRoute()?.id === 'demo-route-a' ? [...WAYFINDING_PLACES, ...COOL_PLACES] : [];
  contextPlaces.forEach((place) => {
    const item = document.createElement('li');
    item.textContent = `${place.label} · ${place.note} `;
    const source = document.createElement('a');
    source.href = place.sourceUrl ?? place.operatorUrl;
    source.textContent = 'Source';
    source.target = '_blank';
    source.rel = 'noopener noreferrer';
    item.append(source);
    list.append(item);
  });
}

function renderJourney() {
  const destination = state.destination;
  const route = selectedRoute();
  state.route = routePairSelected() && route ? routeGeometry(route.geometry.coordinates) : null;
  $('#selected-journey').hidden = !destination;
  $('#map-title').textContent = destination?.name ?? 'Explore Basel';
  $('#step-list').replaceChildren();
  $('#journey-mode').textContent = state.preference === 'fast' ? 'Fastest preference' : 'More shade preference';
  $('#journey-title').textContent = destination?.name ?? '';
  $('#journey-summary').textContent = routePairSelected() && route ? `From Basel SBB. ${routes().length} checked walking alternatives are available.` : 'No checked street route is available for this selected pair. Use the Basel SBB → Marktplatz example.';
  $('#preference-note').textContent = state.preference === 'fast' ? 'Fastest selects the shorter checked walking estimate. More shade is not ranked until current shade calculations are available.' : 'Current shade is not calculated yet. Historical PET summaries stay available for each route; compare options manually.';
  $('#steps-summary').textContent = routePairSelected() && route ? `${state.preference === 'fast' ? 'Fastest' : 'More shade'} preference · ${Math.round(route.route.distance_m)} m · access and temporary closures unverified` : 'Checked route and step guidance are unavailable for this selection.';
  routeSteps().forEach(appendStep);
  $('#source-status').textContent = state.snapshot ? `${state.snapshot.mode} data · ${fountainsNearRoute().length} fountains within ${FOUNTAIN_BUFFER_M} m · ${sensorsNearRoute().length} sensors within ${SENSOR_BUFFER_M} m` : 'Map data has not loaded.';
  renderRouteOptions();
  renderNearby();
  const markers = [];
  if (routePairSelected() && state.route) {
    if (selectedRoute().id === 'demo-route-a') {
      routeStops(state.route, fountainsNearRoute()).forEach((stop) => markers.push({
        kind: stop.type,
        label: stop.type.toUpperCase(),
        coordinates: stop.coordinates
      }));
      if ($('#landmark-toggle').checked) WAYFINDING_PLACES.forEach((place) => markers.push({
        kind: 'landmark',
        label: place.label,
        coordinates: place.coordinates
      }));
    }
    if (selectedRoute().id === 'demo-route-a' && $('#cool-place-toggle').checked) COOL_PLACES.forEach((place) => markers.push({
      kind: 'landmark',
      label: 'Cool-place candidate',
      coordinates: place.coordinates
    }));
  }
  map.setContextMarkers(markers);
}

function renderPetLegend() {
  const list = $('#pet-legend-list');
  fetch('/config/pet-classes.json').then((response) => response.json()).then((config) => {
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
  }).catch(() => {
    list.textContent = 'PET class legend unavailable.';
  });
}

const map = createMap($('#map'), showFeature, (message) => {
  $('#basemap-status').textContent = message;
}, (message) => {
  $('#pet-status').textContent = message;
});
$('#pet-layer-toggle').checked = mode === 'online';
$('#pet-layer-toggle').disabled = mode !== 'online';
$('#pet-layer-toggle').addEventListener('change', (event) => map.setPetVisible(event.target.checked));
map.setPetVisible(mode === 'online');

async function refresh() {
  $('#mode-notice').textContent = 'Loading selected data mode…';
  try {
    const response = await fetch(`/api/map?mode=${encodeURIComponent(mode)}`, {
      signal: AbortSignal.timeout(mode === 'online' ? 90_000 : 10_000)
    });
    if (!response.ok) throw new Error('Map API unavailable');
    state.snapshot = parseSnapshot(await response.json());
    const messages = {
      fixture: 'Example mode: invented locations and values, not current conditions.',
      online: 'Online mode: provider data with source timestamps; missing and stale values remain explicit.',
      offline: 'Offline mode: saved provider data only. Observation timestamps retain their original dates.'
    };
    $('#mode-notice').textContent = messages[state.snapshot.mode] ?? 'Selected map data loaded.';
    map.replaceLayers(state.snapshot.layers);
    renderLayers();
    renderFeatures();
    if (routes().length && routePairSelected()) {
      state.selectedRouteId = routes().some((route) => route.id === state.selectedRouteId) ? state.selectedRouteId : routes()[0].id;
      if (state.preference === 'fast') state.selectedRouteId = [...routes()].sort((a, b) => a.route.duration_s - b.route.duration_s)[0].id;
    }
    renderJourney();
  } catch {
    state.snapshot = null;
    state.route = null;
    map.replaceLayers([]);
    renderLayers();
    renderFeatures();
    $('#mode-notice').textContent = 'Map data unavailable. The basemap can still be used.';
    $('#source-status').textContent = 'No map snapshot available.';
    renderJourney();
  }
}

function showMap() {
  document.body.dataset.view = 'map';
  map.updateSize();
  map.focusCoordinates([
    [state.origin.lon, state.origin.lat], ...(state.destination ? [
      [state.destination.lon, state.destination.lat]
    ] : [])
  ]);
}

function showPlan() {
  document.body.dataset.view = 'plan';
  map.setPicking(null);
  $('#map-pick-banner').hidden = true;
}

function pickOnMap(kind) {
  $('#map-pick-banner').textContent = kind === 'origin' ? 'Tap the map to set your starting point.' : 'Tap the map to set your destination.';
  $('#map-pick-banner').hidden = false;
  map.setPicking(kind, (pickedKind, point) => {
    const place = {
      id: `pin-${pickedKind}`,
      name: pickedKind === 'origin' ? 'Pinned starting point' : 'Pinned destination',
      ...point
    };
    if (pickedKind === 'origin') setOrigin(place, 'Map point selected');
    else selectDestination(place);
    $('#map-pick-banner').hidden = true;
    map.focusCoordinates([
      [state.origin.lon, state.origin.lat], ...(state.destination ? [
        [state.destination.lon, state.destination.lat]
      ] : [])
    ]);
  });
  showMap();
}

function useGps() {
  $('#origin-status').textContent = 'Finding your location…';
  if (!navigator.geolocation) {
    $('#origin-status').textContent = 'GPS unavailable. Enter or pin your start.';
    return;
  }
  navigator.geolocation.getCurrentPosition(({
    coords
  }) => {
    const insideBasel = coords.longitude >= 7.54 && coords.longitude <= 7.71 && coords.latitude >= 47.50 && coords.latitude <= 47.61;
    if (!insideBasel) {
      $('#origin-status').textContent = 'Outside Basel preview. Enter or pin your start.';
      return;
    }
    setOrigin({
      id: 'gps',
      name: 'My current location',
      lon: coords.longitude,
      lat: coords.latitude
    }, 'GPS location selected');
  }, () => {
    $('#origin-status').textContent = 'GPS unavailable. Enter or pin your start.';
  }, {
    enableHighAccuracy: false,
    timeout: 6000,
    maximumAge: 60000
  });
}

$('#destination-input').addEventListener('input', (event) => renderSuggestions(event.target.value));
$('#destination-input').addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && $('#suggestions button')) {
    event.preventDefault();
    $('#suggestions button').click();
  }
});
$('#origin-input').addEventListener('change', (event) => {
  const place = PLACES.find((item) => item.name.toLocaleLowerCase() === event.target.value.trim().toLocaleLowerCase());
  if (place) setOrigin(place, 'Starting point selected');
  else {
    $('#origin-status').textContent = 'Choose a sample place or pin your start.';
    event.target.value = state.origin.name;
  }
});
$('#gps-button').addEventListener('click', useGps);
$('#pick-origin').addEventListener('click', () => pickOnMap('origin'));
$('#pick-destination').addEventListener('click', () => pickOnMap('destination'));
$('#fast-mode').addEventListener('click', () => selectPreference('fast'));
$('#shade-mode').addEventListener('click', () => selectPreference('shade'));
$('#show-route').addEventListener('click', showMap);
$('#back-to-plan').addEventListener('click', showPlan);
$('#try-example').addEventListener('click', () => {
  setOrigin(FALLBACK_START, 'Example start selected');
  selectDestination(MARKTPLATZ);
  showMap();
});
$('#landmark-toggle').addEventListener('change', renderJourney);
$('#cool-place-toggle').addEventListener('change', renderJourney);
PLACES.forEach((place) => {
  const option = document.createElement('option');
  option.value = place.name;
  $('#origin-options').append(option);
});
renderQuickPlaces();
setPins();
renderPetLegend();
void refresh();

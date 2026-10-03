import {
  routeAmenities,
  amenityLabel
} from './route-amenities.js';
import {
  addressSearch
} from './address-search.js';
import {
  walkingRouting
} from './walking-routing.js';
import {
  parseSnapshot
} from './api.js';
import {
  renderTripComparison
} from './comparison.js';
import {
  journeyCalculation
} from './journey-calculation.js';
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
  route: null,
  comparisonJob: null,
  chosenRouteId: null,
  walkingLayer: null,
  routingStatus: '',
  amenities: null,
  amenitiesStatus: 'Loading real route-stop data…',
};
const $ = (selector) => document.querySelector(selector);
const routes = () => routePairSelected() ? state.snapshot?.layers.find((layer) => layer.kind === 'route')?.features ?? [] : state.walkingLayer?.features ?? [];
const selectedRoute = () => routes().find((route) => route.id === state.selectedRouteId) ?? routes()[0];
const routePairSelected = () => state.origin.id === 'sbb' && state.destination?.id === 'marktplatz';
const sourceFeatures = (kind) => state.snapshot?.layers.find((layer) => layer.kind === kind)?.features ?? [];
const fountainsNearRoute = () => state.route && state.amenities ? nearbyFeatures(state.route, state.amenities.fountains.features, FOUNTAIN_BUFFER_M) : [];
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
  $('#map-feature-details').replaceChildren(...Array.from(details.childNodes, node => node.cloneNode(true)));
  $('#map-feature-inspector').hidden = false;
  $('#map-feature-inspector').open = true;
}

function renderFeatures() {
  const list = $('#features');
  list.replaceChildren();
  displayLayers().forEach((layer) => {
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
  displayLayers().forEach((layer) => {
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

function setPins() {
  map.setPins(state.origin, state.destination);
}

function selectDestination(place) {
  calculation.clear();
  state.destination = place;
  updateWalkingRoute();
  $('#destination-input').value = place.name;
  $('#suggestions').hidden = true;
  renderJourney();
  setPins();
  map.focusCoordinates([
    [state.origin.lon, state.origin.lat],
    [place.lon, place.lat]
  ]);
}

function setOrigin(place, message) {
  calculation.clear();
  state.origin = place;
  updateWalkingRoute();
  $('#origin-input').value = place.name;
  $('#origin-status').textContent = message;
  renderQuickPlaces();
  renderJourney();
  setPins();
  map.focusCoordinates([
    [place.lon, place.lat], ...state.destination ? [
      [state.destination.lon, state.destination.lat]
    ] : []
  ]);
}

function selectPreference(preference) {
  state.preference = preference;
  $('#fast-mode').setAttribute('aria-pressed', String(preference === 'fast'));
  $('#shade-mode').setAttribute('aria-pressed', String(preference === 'shade'));
  $('#balanced-mode').setAttribute('aria-pressed', String(preference === 'balanced'));
  const winner = activeComparison()?.winner;
  if (winner) state.selectedRouteId = winner;
  renderJourney();
}

function routeSteps() {
  const route = selectedRoute();
  if (!route) return [];
  if (!routePairSelected()) return [
    ['Walking network route', 'Inspect the calculated street route on the map.', 'Turn-by-turn guidance, shade and temporary access remain unverified.']
  ];
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

function activeComparison() {
  if (state.comparisonJob?.status !== 'ready') return null;
  return state.comparisonJob.choices[state.preference === 'fast' ? 'fastest_overall' : state.preference === 'shade' ? 'more_shade' : 'baseline'];
}

function renderRouteOptions() {
  const list = $('#route-options');
  const focused = list.contains(document.activeElement) ? document.activeElement.dataset : null;
  if (!routes().length) {
    list.replaceChildren();
    return;
  }
  renderTripComparison(list, {
    routes: routes(),
    comparison: state.comparisonJob?.status === 'ready' ? state.comparisonJob.choices : null,
    chosenRouteId: state.chosenRouteId,
    selectedRouteId: state.selectedRouteId,
    preference: state.preference === 'fast' ? 'fastest_overall' : state.preference === 'shade' ? 'more_shade' : 'baseline',
    onChoose: (route) => {
      if (!activeComparison()?.manual_choices.includes(route.id)) return;
      state.chosenRouteId = route.id;
      state.selectedRouteId = route.id;
      renderJourney();
      $('#route-options .comparison-primary[aria-pressed="true"]')?.focus();
    },
    onShow: (route) => {
      state.selectedRouteId = route.id;
      renderJourney();
      showMap();
      map.focus(route);
    }
  });
  if (focused?.routeId) list.querySelector(`[data-route-id="${CSS.escape(focused.routeId)}"][data-action="${focused.action}"]`)?.focus();
}

function renderNearby() {
  const details = $('#nearby-details');
  details.hidden = !state.route;
  if (details.hidden) return;
  const fountains = fountainsNearRoute();
  const sensors = sensorsNearRoute();
  const stopCandidates = currentAmenities().filter(item => item.feature.kind === 'rest');
  $('#nearby-summary').textContent = `Route stops · ${fountains.length} fountains, ${stopCandidates.filter(item=>item.feature.rest_type==='bench').length} benches, ${stopCandidates.filter(item=>item.feature.rest_type!=='bench').length} rest candidates`;
  const list = $('#nearby-list');
  list.replaceChildren();
  fountains.forEach(({
    feature,
    distance
  }) => {
    const item = document.createElement('li');
    item.textContent = `Fountain · ${feature.label} · ${Math.round(distance)} m from route · drinking/operation/access unknown · ${feature.explanation}`;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Show fountain';
    button.onclick = () => {
      showFeature(feature);
      map.focus(feature);
    };
    item.append(button);
    list.append(item);
  });
  stopCandidates.forEach(({
    feature,
    distance,
    fraction
  }) => {
    const item = document.createElement('li');
    item.textContent = `${amenityLabel(feature)} · ${Math.round(fraction*state.route.length)} m along route · ${Math.round(distance)} m away · ${feature.explanation}`;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = `Show ${feature.label}`;
    button.onclick = () => {
      showFeature(feature);
      map.focus(feature);
    };
    item.append(button);
    list.append(item);
  });
  const status = document.createElement('li');
  status.textContent = `${state.amenitiesStatus} Distance is geometric proximity, not a verified walking detour.`;
  list.append(status);
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
  state.route = route ? routeGeometry(route.geometry.coordinates) : null;
  $('#selected-journey').hidden = !destination;
  $('#map-title').textContent = destination?.name ?? 'Explore Basel';
  $('#step-list').replaceChildren();
  $('#journey-mode').textContent = state.preference === 'fast' ? 'Fastest overall' : state.preference === 'shade' ? 'More shade' : 'Balanced';
  $('#journey-title').textContent = destination?.name ?? '';
  $('#journey-summary').textContent = routePairSelected() && route ? `From Basel SBB. ${routes().length} checked walking alternatives are available.` : state.routingStatus;
  $('#preference-note').textContent = routePairSelected() ? activeComparison()?.explanation ?? 'Calculate this departure to inspect shade and eligibility. Transit is unavailable. Historical PET stays separate from current shade.' : 'Walking geometry and estimated time are available when routing succeeds. Shade, access and shade-based ranking are unknown for this pair.';
  $('#steps-summary').textContent = route ? `${state.chosenRouteId === route.id ? 'Chosen eligible route' : 'Inspecting route'} · ${Math.round(route.route.distance_m)} m · access and temporary closures unverified` : 'Walking route unavailable for this selection.';
  routeSteps().forEach(appendStep);
  $('#source-status').textContent = `${state.amenitiesStatus} · ${fountainsNearRoute().length} real fountains within ${FOUNTAIN_BUFFER_M} m`;
  renderRouteOptions();
  renderNearby();
  const markers = [];
  if ($('#route-stops-toggle').checked) currentAmenities().slice(0, stopSettings.max_markers).forEach(({
    feature
  }) => markers.push({
    kind: feature.kind === 'fountain' ? 'water' : feature.rest_type,
    label: amenityLabel(feature),
    coordinates: feature.geometry.coordinates,
    sourceFeature: feature
  }));
  if (routePairSelected() && state.route) {
    if (selectedRoute().id === 'demo-route-a') {
      if ($('#landmark-toggle').checked) WAYFINDING_PLACES.forEach((place) => markers.push({
        kind: 'landmark',
        label: place.label,
        coordinates: place.coordinates
      }));
    }
  }
  map.setContextMarkers(markers);
  const evidence = routePairSelected() && state.comparisonJob?.status === 'ready' ? state.comparisonJob.evidence : [];
  map.setShadeSamples(routes(), evidence);
  $('#calculate-journey').disabled = !routePairSelected() || !routes().length || state.comparisonJob?.status === 'running';
  $('#retry-walking-route').hidden = routePairSelected();
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
const stopSettings = await fetch('/config/route-stops.json').then(response => response.json());

function currentAmenities() {
  const indoor = $('#cool-place-toggle').checked ? COOL_PLACES.map(place => ({
    id: place.id,
    label: place.label,
    kind: 'rest',
    rest_type: 'indoor',
    geometry: {
      type: 'Point',
      coordinates: place.coordinates
    },
    availability: 'unknown',
    explanation: place.note,
    provenance: {
      provider: 'Curated canton/operator evidence',
      source_url: place.sourceUrl,
      attribution: 'Operator factual information',
      licence: 'Linked factual summary; website media not redistributed',
      fixture: false
    }
  })) : [];
  return routeAmenities(state.route, state.amenities, stopSettings, indoor);
}
fetch(`/api/route-amenities?mode=${encodeURIComponent(mode)}`).then(response => {
  if (!response.ok) throw new Error('Stop data unavailable');
  return response.json();
}).then(data => {
  state.amenities = data;
  state.amenitiesStatus = `Route candidates: IWB ${data.fountains.availability} · OSM ${data.rest_stops.availability}; source dates in details`;
  renderJourney();
}).catch(() => {
  state.amenitiesStatus = 'Real route-stop data unavailable; no candidates inferred.';
  renderJourney();
});
$('#route-stops-toggle').addEventListener('change', renderJourney);
const calculation = journeyCalculation((job, message) => {
  state.comparisonJob = job;
  if (!activeComparison()?.manual_choices.includes(state.chosenRouteId)) state.chosenRouteId = null;
  $('#comparison-control-status').textContent = `${message}${job?.status === 'running' ? ` ${job.completed_samples} of ${job.total_samples} samples completed.` : ''}`;
  renderJourney();
});
const routingSettings = await fetch('/config/walking-routing.json').then(response => response.json());
const walking = walkingRouting(mode, routingSettings, (layer, message) => {
  state.walkingLayer = layer;
  state.routingStatus = message;
  state.selectedRouteId = layer?.features[0]?.id ?? null;
  syncWalkingLayers();
  renderJourney();
});

function displayLayers() {
  const layers = state.snapshot?.layers ?? [];
  const routeLayer = routePairSelected() ? layers.find(layer => layer.kind === 'route') : state.walkingLayer;
  return [...layers.filter(layer => layer.kind !== 'route'), ...routeLayer ? [routeLayer] : []];
}

function syncWalkingLayers() {
  map.replaceLayers(displayLayers());
  renderLayers();
  renderFeatures();
}

function updateWalkingRoute() {
  state.walkingLayer = null;
  state.chosenRouteId = null;
  walking.clear();
  if (routePairSelected()) {
    syncWalkingLayers();
    return;
  }
  walking.start([state.origin.lon, state.origin.lat], [state.destination.lon, state.destination.lat]);
}
$('#retry-walking-route').addEventListener('click', updateWalkingRoute);

function setDepartureNow() {
  const now = new Date();
  $('#departure-time').value = new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 19);
  calculation.clear();
}
$('#departure-time').step = '1';
setDepartureNow();
$('#departure-time').addEventListener('input', () => {
  $('#departure-time').setCustomValidity('');
  calculation.clear();
});
$('#departure-now').addEventListener('click', setDepartureNow);
$('#calculate-journey').addEventListener('click', () => {
  const input = $('#departure-time');
  const date = new Date(input.value);
  input.setCustomValidity(Number.isFinite(date.getTime()) ? '' : 'Choose a valid departure time.');
  if (input.reportValidity()) void calculation.start(date.toISOString());
});

function updatePreferences() {
  calculation.setPreferences({
    weights: Object.fromEntries(['shade', 'duration', 'water'].map((name) => [name, Number($(`#weight-${name}`).value)])),
    extra_time_limit_minutes: $('#shade-detour-limit').value === '5' ? 5 : null,
  });
}
$('#shade-detour-limit').addEventListener('change', updatePreferences);
['shade', 'duration', 'water'].forEach((name) => $(`#weight-${name}`).addEventListener('change', updatePreferences));
$('#balanced-mode').addEventListener('click', () => selectPreference('balanced'));
$('#shade-samples-toggle').addEventListener('change', (event) => map.setShadeVisible(event.target.checked));
fetch('/api/coverage').then((response) => {
  if (!response.ok) throw new Error('Coverage unavailable');
  return response.json();
}).then((coverage) => map.setCoverage(coverage)).catch(() => {
  $('#layer-note').textContent = 'City boundary unavailable; calculation support remains explicit in route evidence.';
});

$('#pet-layer-toggle').checked = mode === 'online';
$('#pet-layer-toggle').disabled = mode !== 'online';
$('#pet-layer-toggle').addEventListener('change', (event) => map.setPetVisible(event.target.checked));
map.setPetVisible(mode === 'online');

async function refresh() {
  calculation.clear();
  $('#mode-notice').textContent = 'Loading selected data mode…';
  try {
    const response = await fetch(`/api/map?mode=${encodeURIComponent(mode)}`, {
      signal: AbortSignal.timeout(mode === 'online' ? 90_000 : 10_000)
    });
    if (!response.ok) throw new Error('Map API unavailable');
    state.snapshot = parseSnapshot(await response.json());
    if (!routes().length) {
      const routeResponse = await fetch('/api/walking-routes', {
        signal: AbortSignal.timeout(10_000)
      });
      if (!routeResponse.ok) throw new Error('Saved walking routes unavailable');
      state.snapshot = parseSnapshot({
        ...state.snapshot,
        layers: [...state.snapshot.layers, await routeResponse.json()]
      });
    }
    const messages = {
      fixture: 'Example mode: synthetic sensor and fountain layers beside sourced walking geometry. Route stop candidates use saved IWB/OSM data with their own dates. Calculated shade uses local prepared inputs.',
      online: 'Online mode: provider data with source timestamps; missing and stale values remain explicit.',
      offline: 'Offline mode: saved provider data only. Observation timestamps retain their original dates.'
    };
    $('#mode-notice').textContent = messages[state.snapshot.mode] ?? 'Selected map data loaded.';
    syncWalkingLayers();
    renderLayers();
    renderFeatures();
    if (routes().length && routePairSelected()) {
      state.selectedRouteId = routes().some((route) => route.id === state.selectedRouteId) ? state.selectedRouteId : routes()[0].id;

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

const searchSettings = await fetch('/config/address-search.json').then(response => response.json());
addressSearch($('#destination-input'), $('#suggestions'), $('#destination-status'), mode, selectDestination, PLACES, searchSettings);
addressSearch($('#origin-input'), $('#origin-suggestions'), $('#origin-status'), mode, place => setOrigin(place, 'Address selected'), PLACES, searchSettings);
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
renderQuickPlaces();
setPins();
renderPetLegend();
void refresh();

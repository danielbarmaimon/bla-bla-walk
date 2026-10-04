import {
  routeAmenities,
  amenityLabel,
  plannedRestStops
} from './route-amenities.js';
import {
  badgeActive,
  installLayerBadges,
  visibleRouteIds
} from './layer-badges.js';
import {
  scheduledOpen
} from './supermarket-hours.js';
import {
  routeTemperatureView,
  showRouteTemperature
} from './route-temperature-view.js';
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
  routeGeometry,
  nearbyFeatures,
  coordinateAtFraction
} from './route-planner-data.js';
import {
  WAYFINDING_PLACES
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
  origin: null,
  destination: null,
  submitted: false,
  tripVersion: 0,
  busy: false,
  calculationKind: null,
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
let temperatureView = null;
const routes = () => !state.submitted ? [] : routePairSelected() ? state.snapshot?.layers.find((layer) => layer.kind === 'route')?.features ?? [] : state.walkingLayer?.features ?? [];
const selectedRoute = () => routes().find((route) => route.id === state.selectedRouteId) ?? routes()[0];
const routePairSelected = () => state.origin?.id === 'sbb' && state.destination?.id === 'marktplatz';
const fountainsNearRoute = () => state.route && state.amenities ? nearbyFeatures(state.route, state.amenities.fountains.features, FOUNTAIN_BUFFER_M) : [];

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
    ['Mapped opening hours', feature.opening_hours ?? 'Not applicable'],
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
  displayLayers().forEach(layer => {
    const paragraph = document.createElement('p');
    paragraph.textContent = `${layer.label} · ${layer.availability} · ${layer.explanation}`;
    container.append(paragraph);
    if (layer.kind !== 'route') map.setVisible(layer.id, badgeActive(layer.kind === 'observation' ? '#weather-stations-toggle' : '#fountains-layer-toggle'));
  });
}

function distanceMetres(a, b) {
  const radians = Math.PI / 180;
  const dLat = (b.lat - a.lat) * radians;
  const dLon = (b.lon - a.lon) * radians;
  const arc = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * radians) * Math.cos(b.lat * radians) * Math.sin(dLon / 2) ** 2;
  return 12742000 * Math.asin(Math.sqrt(arc));
}

function renderQuickPlaces() {
  const grid = $('#quick-grid');
  grid.replaceChildren();
  if (!state.origin) {
    $('#quick-place-status').textContent = 'Choose a start first';
    return;
  }
  const data = state.amenities;
  const groups = data ? [
    ['Supermarket', 'shopping-basket', data.rest_stops.features.filter(f => f.rest_type === 'indoor')],
    ['Fountain', 'droplets', data.fountains.features],
    ['Park', 'trees', data.rest_stops.features.filter(f => f.rest_type === 'park')],
  ] : [];
  const actual = groups.flatMap(([category, iconName, features]) => {
    const candidates = features.map(f => ({
      id: f.id,
      name: f.label,
      lon: f.geometry.coordinates[0],
      lat: f.geometry.coordinates[1]
    }));
    const place = candidates.sort((a, b) => distanceMetres(state.origin, a) - distanceMetres(state.origin, b))[0];
    return place ? [{
      category,
      iconName,
      place,
      sample: false
    }] : [];
  });
  const choices = actual.length ? actual : CATEGORIES.slice(0, 3).flatMap(([category, iconName]) => {
    const place = PLACES.filter(p => p.category === category && p.id !== state.origin.id)
      .sort((a, b) => distanceMetres(state.origin, a) - distanceMetres(state.origin, b))[0];
    return place ? [{
      category,
      iconName,
      place,
      sample: true
    }] : [];
  });
  $('#quick-place-status').textContent = actual.length ? 'Mapped places · access/hours unverified' : 'Sample places';
  for (const {
      category,
      iconName,
      place,
      sample
    }
    of choices) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'quick-tile';
    const title = document.createElement('strong');
    title.textContent = category;
    const label = document.createElement('small');
    label.textContent = place.name;
    const distance = document.createElement('small');
    distance.textContent = `${sample ? 'Sample · ' : ''}${Math.round(distanceMetres(state.origin, place))} m straight-line`;
    button.append(icon(iconName), title, label, distance);
    button.onclick = () => selectDestination(place);
    grid.append(button);
  }
}

function tripCoordinates() {
  return [state.origin, state.destination].filter(Boolean).map(place => [place.lon, place.lat]);
}

function invalidateTrip(message = 'Choose your start and destination, then calculate.') {
  state.tripVersion += 1;
  state.submitted = false;
  state.busy = false;
  state.calculationKind = null;
  state.walkingLayer = null;
  state.routingStatus = '';
  state.chosenRouteId = null;
  calculation.clear();
  walking.clear();
  syncWalkingLayers();
  $('#trip-status').textContent = message;
  renderJourney();
}

function setPins() {
  map.setPins(state.origin, state.destination);
}

function selectDestination(place) {
  state.destination = place;
  invalidateTrip();
  $('#destination-input').value = place.name;
  $('#suggestions').hidden = true;
  renderJourney();
  setPins();
  map.focusCoordinates(tripCoordinates());
}

function setOrigin(place, message) {
  state.origin = place;
  invalidateTrip();
  $('#origin-input').value = place.name;
  $('#origin-status').textContent = message;
  renderQuickPlaces();
  renderJourney();
  setPins();
  map.focusCoordinates(tripCoordinates());
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

  }
  if (water) steps.push(['Water', `${water.feature.label} is near the route.`, 'Location only; drinking water and operation are unknown.']);
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
  item.append(heading, text);
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
  const fountains = visibleAmenities().filter(item => item.feature.kind === 'fountain');
  const stopCandidates = visibleAmenities().filter(item => item.feature.kind === 'rest');
  const planned = plannedRestStops(state.route, selectedRoute()?.route.duration_s, stopSettings.rest_interval_minutes);
  $('#nearby-summary').textContent = `Route stops · ${fountains.length} fountains, ${stopCandidates.filter(item=>item.feature.rest_type==='bench').length} benches · ${planned.length} planned rests`;
  const list = $('#nearby-list');
  list.replaceChildren();
  fountains.forEach(({
    feature,
    distance
  }) => {
    const item = document.createElement('li');
    item.textContent = `Water · ${Math.round(distance)} m off route`;
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
    item.textContent = `${feature.rest_type === "indoor" ? "Supermarket" : amenityLabel(feature)} · ${Math.round(fraction*state.route.length)} m along route · ${Math.round(distance)} m away`;
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
  $('#route-candidate-notes').textContent = status.textContent;
  $('#route-candidate-notes').textContent += ' ' + currentAmenities().map(item => `${item.feature.label}: ${item.feature.explanation}`).join(' ');

}

function renderJourney() {
  document.body.dataset.trip = state.submitted ? 'results' : 'start';
  $('#temperature-sample').replaceChildren();
  const destination = state.destination;
  const route = selectedRoute();
  state.route = route ? routeGeometry(route.geometry.coordinates) : null;
  $('#selected-journey').hidden = !state.submitted || !route;
  $('#map-title').textContent = destination?.name ?? 'Explore Basel';
  $('#step-list').replaceChildren();
  $('#journey-mode').textContent = state.preference === 'fast' ? 'Fastest overall' : state.preference === 'shade' ? 'More shade' : 'Balanced';
  $('#journey-title').textContent = destination?.name ?? '';
  $('#journey-summary').textContent = routePairSelected() && route ? `From Basel SBB. ${routes().length} checked walking alternatives are available.` : state.routingStatus;
  $('#preference-note').textContent = routePairSelected() ? activeComparison()?.explanation ?? 'Calculate this departure to inspect shade and eligibility. Transit is unavailable. Historical PET stays separate from current shade.' : 'Walking geometry and estimated time are available when routing succeeds. Shade, access and shade-based ranking are unknown for this pair.';
  $('#steps-summary').textContent = route ? `${Math.round(route.route.distance_m)} m · ${Math.round(route.route.duration_s/60)} min walking` : 'Walking route unavailable for this selection.';
  const steps = routeSteps();
  const arrival = steps.at(-1)?.[0] === 'Arrive' ? steps.pop() : null;
  steps.forEach(appendStep);
  plannedRestStops(state.route, route?.route.duration_s, stopSettings.rest_interval_minutes).forEach(stop => appendStep(['Rest', `Planned pause after ${stop.walk_minutes} minutes walking.`, 'On-route planning prompt; seating not guaranteed.']));
  if (arrival) appendStep(arrival);
  $('#source-status').textContent = `${state.amenitiesStatus} · ${fountainsNearRoute().length} real fountains within ${FOUNTAIN_BUFFER_M} m`;
  renderRouteOptions();
  renderNearby();
  const supermarkets = openSupermarkets();
  $('#interior-list-section').hidden = !badgeActive('#cool-place-toggle');
  $('#interior-list').replaceChildren();
  supermarkets.forEach(feature => {
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = feature.label;
    button.onclick = () => {
      map.focus(feature);
      showFeature(feature);
    };
    item.append(button);
    $('#interior-list').append(item);
  });
  if (!supermarkets.length) $('#interior-list').textContent = 'No supermarkets with supported open hours at this departure.';
  const markers = [];
  visibleAmenities().slice(0, stopSettings.max_markers).forEach(({
    feature,
    fraction
  }) => markers.push({
    kind: feature.kind === 'fountain' ? 'water' : feature.rest_type,
    label: amenityLabel(feature),
    coordinates: coordinateAtFraction(state.route, fraction),
    sourceFeature: feature
  }));
  if (badgeActive('#rest-stop-toggle')) plannedRestStops(state.route, selectedRoute()?.route.duration_s, stopSettings.rest_interval_minutes).forEach(stop => markers.push({
    kind: 'rest',
    label: `REST ${stop.walk_minutes}m`,
    coordinates: stop.coordinates,
  }));
  if (badgeActive('#cool-place-toggle')) supermarkets.forEach(feature => markers.push({
    kind: 'indoor',
    label: feature.label,
    coordinates: feature.geometry.coordinates,
    sourceFeature: feature
  }));
  if (routePairSelected() && state.route) {
    if (selectedRoute().id === 'demo-route-a') {
      if (badgeActive('#landmark-toggle')) WAYFINDING_PLACES.forEach((place) => markers.push({
        kind: 'landmark',
        label: place.label,
        coordinates: place.coordinates
      }));
    }
  }
  map.setContextMarkers(markers);
  const evidence = routePairSelected() && state.comparisonJob?.status === 'ready' ? state.comparisonJob.evidence : [];
  map.setShadeSamples(routes(), evidence);
  const visible = visibleRouteIds(routes(), activeComparison()?.winner, badgeActive('#fast-route-toggle'), badgeActive('#recommended-route-toggle'));
  map.setRouteVisibility(visible);
  temperatureView?.render(state.route, visible.includes(route?.id));
  map.setShadeVisible(badgeActive('#shade-samples-toggle'));
  map.setPetVisible(badgeActive('#pet-layer-toggle'));
  renderLayers();
  $('#route-display-info').textContent = `Fast route uses the lowest walking-time estimate. ${activeComparison()?.winner ? 'Recommended uses the supported comparison winner.' : 'Recommended is unavailable until an eligible comparison winner exists.'}`;
  const notes = $('#route-step-notes');
  notes.replaceChildren();
  routeSteps().forEach(([type, instruction, note]) => {
    const p = document.createElement('p');
    p.textContent = `${type}: ${note}`;
    notes.append(p);
  });
  $('#calculate-journey').disabled = state.busy || !state.origin || !state.destination;
  $('#calculate-journey').textContent = state.busy ? 'Finding routes…' : 'Calculate';
  $('#cancel-journey').hidden = !state.busy;
  $('#planner-title').closest('.planner').setAttribute('aria-busy', String(state.busy));
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
  $('#basemap-status').hidden = !message.includes('unavailable');
}, (message) => {
  $('#pet-status').textContent = message;
}, showRouteTemperature);
const stopSettings = await fetch('/config/route-stops.json').then(response => response.json());
temperatureView = await routeTemperatureView(map, mode, renderJourney);

function currentAmenities() {
  const data = state.amenities;
  const candidates = routeAmenities(state.route, data, stopSettings);
  return candidates.filter(item => item.feature.rest_type !== 'indoor');
}

function visibleAmenities() {
  return currentAmenities().filter(({
    feature
  }) => feature.rest_type !== 'indoor' && badgeActive(feature.kind === 'fountain' ? '#water-stop-toggle' : feature.rest_type === 'bench' ? '#bench-stop-toggle' : '#rest-stop-toggle'));
}

function openSupermarkets() {
  const departure = new Date($('#departure-time').value || Date.now());
  return (state.amenities?.rest_stops.features ?? []).filter(feature =>
    feature.rest_type === 'indoor' && scheduledOpen(feature.opening_hours, departure, stopSettings.public_holidays));
}
fetch(`/api/route-amenities?mode=${encodeURIComponent(mode)}`).then(response => {
  if (!response.ok) throw new Error('Stop data unavailable');
  return response.json();
}).then(data => {
  state.amenities = data;
  state.amenitiesStatus = `Route candidates: IWB ${data.fountains.availability} · OSM ${data.rest_stops.availability}; source dates in details`;
  renderQuickPlaces();
  renderJourney();
}).catch(() => {
  state.amenitiesStatus = 'Real route-stop data unavailable; no candidates inferred.';
  renderJourney();
});
installLayerBadges(renderJourney);
const calculation = journeyCalculation((job, message) => {
  state.comparisonJob = job;
  if (!activeComparison()?.manual_choices.includes(state.chosenRouteId)) state.chosenRouteId = null;
  if (state.calculationKind === 'comparison') {
    $('#trip-status').textContent = message;
    if (job && job.status !== 'running') state.busy = false;
    if (!job && !message.startsWith('Choose a departure') && !message.startsWith('Checking local')) state.busy = false;
  }
  $('#comparison-control-status').textContent = `${message}${job?.status === 'running' ? ` ${job.completed_samples} of ${job.total_samples} samples completed.` : ''}`;
  renderJourney();
});
const routingSettings = await fetch('/config/walking-routing.json').then(response => response.json());
const walking = walkingRouting(mode, routingSettings, (layer, message) => {
  state.walkingLayer = layer;
  state.routingStatus = message;
  if (state.calculationKind === 'walking') {
    state.busy = !layer && message.startsWith('Calculating');
    $('#trip-status').textContent = layer ? 'Routes ready. Shade comparison unavailable for this pair.' : message;
  }
  state.selectedRouteId = layer?.features[0]?.id ?? null;
  syncWalkingLayers();
  renderJourney();
});

function displayLayers() {
  const layers = state.snapshot?.layers ?? [];
  const routeLayer = !state.submitted ? null : routePairSelected() ? layers.find(layer => layer.kind === 'route') : state.walkingLayer;
  return [...layers.filter(layer => layer.kind !== 'route'), ...routeLayer ? [routeLayer] : []];
}

function syncWalkingLayers() {
  map.replaceLayers(displayLayers());
  renderLayers();
  renderFeatures();
}

async function findRoutes() {
  if (state.busy) return;
  if (!state.origin || !state.destination) {
    $('#trip-status').textContent = 'Choose both addresses from the suggestions, or pin them on the map.';
    return;
  }
  const date = $('#departure-now').getAttribute('aria-pressed') === 'true' ? new Date() : new Date($('#departure-time').value);
  if ($('#departure-now').getAttribute('aria-pressed') === 'true') $('#departure-time').value = new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 19);
  if (!Number.isFinite(date.getTime())) {
    $('#trip-status').textContent = 'Choose a valid departure time.';
    return;
  }
  invalidateTrip();
  const version = state.tripVersion;
  state.submitted = true;
  state.busy = true;
  if (routePairSelected()) {
    state.calculationKind = 'comparison';
    if (!routes().length) {
      state.busy = false;
      $('#trip-status').textContent = 'Saved example unavailable. Retry after data loads.';
    } else {
      state.selectedRouteId = [...routes()].sort((a, b) => a.route.duration_s - b.route.duration_s)[0].id;
      syncWalkingLayers();
      renderJourney();
      await calculation.start(date.toISOString());
      if (version !== state.tripVersion) return;
      state.busy = state.comparisonJob?.status === 'running';
    }
  } else {
    state.calculationKind = 'walking';
    walking.start([state.origin.lon, state.origin.lat], [state.destination.lon, state.destination.lat]);
  }
  renderJourney();
}

function setDepartureNow() {
  const now = new Date();
  $('#departure-time').value = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 19);
  $('#departure-picker').hidden = true;
  $('#departure-now').setAttribute('aria-pressed', 'true');
  $('#departure-later').setAttribute('aria-pressed', 'false');
  invalidateTrip();
}
$('#departure-time').step = '1';
setDepartureNow();
$('#departure-time').addEventListener('input', () => {
  $('#departure-time').setCustomValidity('');
  invalidateTrip('Departure changed. Calculate again.');
});
$('#departure-now').addEventListener('click', setDepartureNow);
$('#departure-later').addEventListener('click', () => {
  $('#departure-picker').hidden = false;
  $('#departure-now').setAttribute('aria-pressed', 'false');
  $('#departure-later').setAttribute('aria-pressed', 'true');
  invalidateTrip('Departure changed. Calculate again.');
  $('#departure-time').focus();
});
$('#calculate-journey').addEventListener('click', () => void findRoutes());
$('#cancel-journey').addEventListener('click', () => invalidateTrip('Calculation cancelled. You can calculate again.'));

function updatePreferences() {
  calculation.setPreferences({
    weights: Object.fromEntries(['shade', 'duration', 'water'].map((name) => [name, Number($(`#weight-${name}`).value)])),
    extra_time_limit_minutes: $('#shade-detour-limit').value === '5' ? 5 : null,
  });
}
$('#shade-detour-limit').addEventListener('change', updatePreferences);
['shade', 'duration', 'water'].forEach((name) => $(`#weight-${name}`).addEventListener('change', updatePreferences));
$('#balanced-mode').addEventListener('click', () => selectPreference('balanced'));

fetch('/api/coverage').then((response) => {
  if (!response.ok) throw new Error('Coverage unavailable');
  return response.json();
}).then((coverage) => map.setCoverage(coverage)).catch(() => {
  $('#layer-note').textContent = 'City boundary unavailable; calculation support remains explicit in route evidence.';
});


async function refresh() {
  calculation.clear();
  $('#mode-notice').textContent = 'Loading selected data mode…';
  try {
    const response = await fetch(`/api/map?mode=${encodeURIComponent(mode)}`, {
      signal: AbortSignal.timeout(mode === 'online' ? 90_000 : 10_000)
    });
    if (!response.ok) throw new Error('Map API unavailable');
    state.snapshot = parseSnapshot(await response.json());
    if (!state.snapshot.layers.some(layer => layer.kind === 'route')) {
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
      state.selectedRouteId = [...routes()].sort((a, b) => a.route.duration_s - b.route.duration_s)[0].id;

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
  map.focusCoordinates(tripCoordinates());
}

function showPlan() {
  document.body.dataset.view = 'plan';
  map.setPicking(null);
  $('#map-pick-banner').hidden = true;
  requestAnimationFrame(() => map.updateSize());
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
    map.focusCoordinates(tripCoordinates());
    showPlan();
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
for (const kind of ['origin', 'destination']) $(`#${kind}-input`).addEventListener('input', () => {
  state[kind] = null;
  invalidateTrip('Choose a matching address from the suggestions.');
  setPins();
  if (kind === 'origin') renderQuickPlaces();
});
$('#gps-button').addEventListener('click', useGps);
$('#pick-origin').addEventListener('click', () => pickOnMap('origin'));
$('#pick-destination').addEventListener('click', () => pickOnMap('destination'));
$('#fast-mode').addEventListener('click', () => selectPreference('fast'));
$('#shade-mode').addEventListener('click', () => selectPreference('shade'));
$('#show-information').addEventListener('click', () => {
  $('#information-sources').open = true;
});
$('#back-to-plan').addEventListener('click', showPlan);
$('#try-example').addEventListener('click', () => {
  setOrigin(FALLBACK_START, 'Example start selected');
  selectDestination(MARKTPLATZ);
  $('#trip-status').textContent = 'Saved example selected. Calculate to compare.';
});


$('#try-example').disabled = false;
renderQuickPlaces();
setPins();
renderPetLegend();
void refresh();

import { CATEGORIES, PLACES } from './sample-places.js';

const FALLBACK_START = { id: 'sbb', name: 'Basel SBB · sample start', lon: 7.5895, lat: 47.5474 };
const state = { origin: FALLBACK_START, destination: null, mode: 'fast', picking: null, offline: false, basemapError: false };
const $ = (selector) => document.querySelector(selector);

function icon(name) {
  const image = document.createElement('img');
  image.src = `/poc-assets/icons/${name}.svg`;
  image.alt = '';
  image.width = 22;
  image.height = 22;
  return image;
}

document.querySelectorAll('[data-icon]').forEach((slot) => slot.replaceChildren(icon(slot.dataset.icon)));

/** Distance ranks only the small sample catalog, not every Basel destination. */
function distanceMetres(a, b) {
  const radians = Math.PI / 180;
  const deltaLat = (b.lat - a.lat) * radians;
  const deltaLon = (b.lon - a.lon) * radians;
  const arc = Math.sin(deltaLat / 2) ** 2 +
    Math.cos(a.lat * radians) * Math.cos(b.lat * radians) * Math.sin(deltaLon / 2) ** 2;
  return 12742000 * Math.asin(Math.sqrt(arc));
}

function closestPlace(category) {
  return PLACES.filter((place) => place.category === category && place.id !== state.origin.id)
    .sort((a, b) => distanceMetres(state.origin, a) - distanceMetres(state.origin, b))[0];
}

function renderQuickPlaces() {
  const grid = $('#quick-grid');
  grid.replaceChildren();
  CATEGORIES.forEach(([category, iconName]) => {
    const place = closestPlace(category);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'quick-tile';
    button.append(icon(iconName));
    const name = document.createElement('strong');
    name.textContent = category;
    const detail = document.createElement('small');
    detail.textContent = place.name;
    button.append(name, detail);
    button.addEventListener('click', () => selectDestination(place));
    grid.append(button);
  });
}

function renderSuggestions(query) {
  const list = $('#suggestions');
  list.replaceChildren();
  const matches = PLACES.filter((place) => `${place.name} ${place.category}`
    .toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())).slice(0, 5);
  if (!query.trim() || matches.length === 0) {
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

function selectDestination(place) {
  state.destination = place;
  state.picking = null;
  $('#destination-input').value = place.name;
  $('#suggestions').hidden = true;
  renderJourney();
  if (document.body.dataset.view === 'plan') {
    $('#selected-journey').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function setOrigin(place, message) {
  state.origin = place;
  $('#origin-input').value = place.name;
  $('#origin-status').textContent = message;
  state.picking = null;
  renderQuickPlaces();
  renderJourney();
}

function setMode(mode) {
  state.mode = mode;
  $('#fast-mode').setAttribute('aria-pressed', String(mode === 'fast'));
  $('#shade-mode').setAttribute('aria-pressed', String(mode === 'shade'));
  renderJourney();
}

function useGps() {
  $('#origin-status').textContent = 'Finding your location…';
  if (!navigator.geolocation) {
    $('#origin-status').textContent = 'GPS unavailable. Enter or pin your start.';
    return;
  }
  navigator.geolocation.getCurrentPosition(({ coords }) => {
    const insideBasel = coords.longitude >= 7.54 && coords.longitude <= 7.71 &&
      coords.latitude >= 47.50 && coords.latitude <= 47.61;
    if (!insideBasel) {
      $('#origin-status').textContent = 'Outside Basel preview. Enter or pin your start.';
      return;
    }
    setOrigin({ id: 'gps', name: 'My current location', lon: coords.longitude, lat: coords.latitude },
      'GPS location selected');
  }, () => {
    $('#origin-status').textContent = 'GPS unavailable. Enter or pin your start.';
  }, { enableHighAccuracy: false, timeout: 6000, maximumAge: 60000 });
}

function pickOnMap(kind) {
  state.picking = kind;
  $('#map-pick-banner').textContent = kind === 'origin' ?
    'Tap the map to place your starting point.' : 'Tap the map to place your destination.';
  $('#map-pick-banner').hidden = false;
  showMap();
}

function showMap() {
  document.body.dataset.view = 'map';
  window.routePreviewMap?.updateSize();
  if (state.destination) focusJourney();
}

function showPlan() {
  document.body.dataset.view = 'plan';
  state.picking = null;
  $('#map-pick-banner').hidden = true;
  window.routePreviewMap?.updateSize();
}

function sampleSteps() {
  if (!state.destination) return [];
  const exampleTram = state.origin.id === 'sbb' && state.destination.id === 'migros-city';
  if (exampleTram) return [
    ['Walk', 'Go to the Basel SBB tram stop.', 'Example access walk'],
    ['Tram', 'Take a tram toward Marktplatz.', 'Direction and service unverified'],
    ['Exit', 'Get off near Marktplatz.', 'Example tram exit'],
    ['Rest', 'Pause at a nearby bench if available.', 'Bench availability unverified'],
    ['Arrive', `Walk to ${state.destination.name}.`, 'Example final walk'],
  ];
  return [
    ['Start', `Leave from ${state.origin.name}.`, 'Starting point'],
    ['Walk', `Head toward ${state.destination.name}.`, 'Walking corridor not verified'],
    ['Rest', 'Pause at a bench or water stop if available.', 'Stops not verified'],
    ['Arrive', `Reach ${state.destination.name}.`, 'Destination'],
  ];
}

function renderJourney() {
  const destination = state.destination;
  $('#selected-journey').hidden = !destination;
  $('#map-title').textContent = destination ? destination.name : 'Explore Basel';
  $('#step-list').replaceChildren();
  if (destination) {
    $('#journey-mode').textContent = state.mode === 'fast' ? 'Fastest preference' : 'More shade preference';
    $('#journey-title').textContent = destination.name;
    $('#journey-summary').textContent = `From ${state.origin.name}. This sample shows the intended trip flow.`;
    const preference = state.mode === 'fast' ? 'Fastest' : 'More shade';
    $('#steps-summary').textContent = `${preference} preference · ${state.origin.name} to ${destination.name} · illustrative steps`;
    sampleSteps().forEach(([type, instruction, note]) => {
      const item = document.createElement('li');
      const heading = document.createElement('strong');
      heading.textContent = type;
      const text = document.createElement('p');
      text.textContent = instruction;
      const detail = document.createElement('small');
      detail.textContent = note;
      item.append(heading, text, detail);
      $('#step-list').append(item);
    });
  } else {
    $('#steps-summary').textContent = 'Choose a destination to preview directions.';
  }
  updateMapOverlay();
  renderMapRoute();
}

function updateMapOverlay() {
  if (state.basemapError) {
    $('#map-overlay').textContent = state.offline ?
      'Offline tiles missing. Run offline preparation.' : 'Basemap unavailable. Check connection.';
    return;
  }
  const preference = state.mode === 'fast' ? 'Fastest' : 'More shade';
  $('#map-overlay').textContent = state.destination ?
    `${preference} preference · schematic link, not a walking path` :
    'Choose a place to preview a schematic connection.';
}

let mapSource;
function renderMapRoute() {
  if (!mapSource || !window.ol) return;
  mapSource.clear();
  const { Feature } = window.ol;
  const { Point, LineString } = window.ol.geom;
  const project = (place) => window.ol.proj.fromLonLat([place.lon, place.lat]);
  const origin = new Feature(new Point(project(state.origin)));
  origin.set('kind', 'origin');
  mapSource.addFeature(origin);
  if (!state.destination) return;
  const destination = new Feature(new Point(project(state.destination)));
  destination.set('kind', 'destination');
  mapSource.addFeature(destination);
  const line = new Feature(new LineString([project(state.origin), project(state.destination)]));
  line.set('kind', 'route');
  mapSource.addFeature(line);
}

function focusJourney() {
  if (!state.destination || !window.routePreviewMap) return;
  const a = window.ol.proj.fromLonLat([state.origin.lon, state.origin.lat]);
  const b = window.ol.proj.fromLonLat([state.destination.lon, state.destination.lat]);
  const extent = [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
  window.routePreviewMap.getView().fit(extent, { padding: [90, 90, 90, 90], maxZoom: 15, duration: 300 });
}

async function createMap() {
  const response = await fetch('/config/basemap.json');
  if (!response.ok) throw new Error('Basemap configuration unavailable');
  const config = await response.json();
  state.offline = new URLSearchParams(location.search).get('mode') === 'offline';
  const tileUrl = state.offline ? '/tiles/{z}/{x}/{y}.png' : config.url;
  const { ol } = window;
  const view = new ol.View({ center: ol.proj.fromLonLat([7.5886, 47.5596]), zoom: 14, minZoom: 12, maxZoom: 17 });
  mapSource = new ol.source.Vector();
  const theme = getComputedStyle(document.documentElement);
  const routeColor = theme.getPropertyValue('--poc-route').trim();
  const originColor = theme.getPropertyValue('--poc-origin').trim();
  const destinationColor = theme.getPropertyValue('--poc-destination').trim();
  const white = theme.getPropertyValue('--poc-white').trim();
  const routeStyle = new ol.style.Style({ stroke: new ol.style.Stroke({ color: routeColor, width: 5, lineDash: [9, 7] }) });
  const pointStyle = (color) => new ol.style.Style({ image: new ol.style.Circle({
    radius: 10, fill: new ol.style.Fill({ color }), stroke: new ol.style.Stroke({ color: white, width: 3 }),
  }) });
  const tiles = new ol.source.XYZ({ url: tileUrl, maxZoom: config.max_zoom,
    attributions: '© Geodaten Kanton Basel-Stadt · CC BY 4.0', crossOrigin: 'anonymous' });
  tiles.on('tileloaderror', () => {
    state.basemapError = true;
    updateMapOverlay();
  });
  const map = new ol.Map({
    target: 'poc-map',
    layers: [
      new ol.layer.Tile({ opacity: Number(theme.getPropertyValue('--poc-basemap-opacity')), source: tiles }),
      new ol.layer.Vector({ source: mapSource, style: (feature) => {
        if (feature.get('kind') === 'route') return routeStyle;
        return pointStyle(feature.get('kind') === 'origin' ? originColor : destinationColor);
      } }),
    ],
    view,
  });
  window.routePreviewMap = map;
  map.on('singleclick', (event) => {
    if (!state.picking) return;
    const [lon, lat] = ol.proj.toLonLat(event.coordinate);
    const kind = state.picking;
    const place = { id: `pin-${kind}`, name: kind === 'origin' ? 'Pinned starting point' : 'Pinned destination', lon, lat };
    if (kind === 'origin') setOrigin(place, 'Map point selected');
    else selectDestination(place);
    $('#map-pick-banner').hidden = true;
    focusJourney();
  });
  renderMapRoute();
  map.updateSize();
}

$('#destination-input').addEventListener('input', (event) => renderSuggestions(event.target.value));
$('#destination-input').addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    const first = $('#suggestions button');
    if (first) { event.preventDefault(); first.click(); }
  }
});
$('#origin-input').addEventListener('change', (event) => {
  const match = PLACES.find((place) => place.name.toLocaleLowerCase() === event.target.value.trim().toLocaleLowerCase());
  if (match) setOrigin(match, 'Starting point selected');
  else {
    $('#origin-status').textContent = 'Choose a sample place or pin your start.';
    event.target.value = state.origin.name;
  }
});
$('#gps-button').addEventListener('click', useGps);
$('#pick-origin').addEventListener('click', () => pickOnMap('origin'));
$('#pick-destination').addEventListener('click', () => pickOnMap('destination'));
$('#fast-mode').addEventListener('click', () => setMode('fast'));
$('#shade-mode').addEventListener('click', () => setMode('shade'));
$('#show-route').addEventListener('click', showMap);
$('#back-to-plan').addEventListener('click', showPlan);

PLACES.forEach((place) => {
  const option = document.createElement('option');
  option.value = place.name;
  $('#origin-options').append(option);
});

setOrigin(FALLBACK_START, 'Sample start until GPS is available');
void createMap().catch(() => { $('#map-overlay').textContent = 'Basemap unavailable. Route controls still work.'; });
useGps();

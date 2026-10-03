import { CATEGORIES, PLACES } from './sample-places.js';
import { parseSnapshot } from '/src/api.js';
import { FOUNTAIN_BUFFER_M, SENSOR_BUFFER_M, routeGeometry, nearbyFeatures, exampleTemperature, temperatureColor } from './route-data.js';
import { WAYFINDING_PLACES, COOL_PLACES, routeStops } from './wayfinding-places.js';
import { exampleHeatFeatures, exampleShadowFeatures } from './preview-layers.js';

const FALLBACK_START = { id: 'sbb', name: 'Basel SBB · example start', lon: 7.590209, lat: 47.548055 };
const EXAMPLE_DESTINATION = PLACES.find((place) => place.id === 'marktplatz');
const state = {
  origin: FALLBACK_START, destination: null, mode: 'fast', picking: null,
  offline: false, basemapError: false, route: null, routeInfo: null,
  snapshot: null, sourceStatus: 'Loading Basel source data…',
  mapView: 'route', reverseHeat: false,
  layers: { fountains: true, sensors: true, landmarks: true, shadows: false, coolPlaces: false, heatmap: true },
};
const $ = (selector) => document.querySelector(selector);
const exampleSelected = () => state.origin.id === 'sbb' && state.destination?.id === 'marktplatz';
const sourceFeatures = (kind) => state.snapshot?.layers.find((layer) => layer.kind === kind)?.features ?? [];
const nearbyFountains = () => state.route ? nearbyFeatures(state.route, sourceFeatures('fountain'), FOUNTAIN_BUFFER_M) : [];
const nearbySensors = () => state.route ? nearbyFeatures(state.route, sourceFeatures('observation'), SENSOR_BUFFER_M) : [];

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

function journeySteps() {
  if (!state.destination) return [];
  if (!exampleSelected() || !state.route) return [
    ['Route pending', 'Street directions are available for the SBB → Marktplatz example.', 'Choose the example route to inspect the mapped path.'],
  ];
  const stops = routeStops(state.route, nearbyFountains());
  const water = stops.find((stop) => stop.type === 'water');
  const steps = [
    ['Start', 'Leave Centralbahnplatz by Basel SBB.', 'Saved pedestrian route start'],
    ['Walk', 'Follow Centralbahn-Passage and Steinenvorstadt.', 'Street names from the saved route'],
    ['Wayfinding', 'Reach Barfüsserplatz, a wayfinding node.', 'Stadtcasino and Barfüsserkirche are nearby landmarks; visibility unverified'],
    ['Rest', 'Consider resting near Barfüsserplatz.', 'Example rest point; seating unverified'],
    ['Walk', 'Continue toward Gerbergasse.', 'Follow the highlighted street path'],
  ];
  if (water) steps.push([
    'Water', `${water.sourceFeature.label} lies near this point.`,
    'Fountain location only; drinking water and operation unknown',
  ]);
  steps.push(
    ['Pause', 'Take a short pause before Marktplatz if needed.', 'Example pause; no verified seating'],
    ['Arrive', 'Reach Marktplatz.', 'Saved pedestrian route end'],
  );
  return steps;
}

function appendStep([type, instruction, note]) {
  const item = document.createElement('li');
  if (['Rest', 'Pause', 'Water'].includes(type)) item.className = 'care-step';
  const heading = document.createElement('strong');
  if (type === 'Rest') heading.append(icon('armchair'));
  if (type === 'Pause') heading.append(icon('pause'));
  if (type === 'Water') heading.append(icon('droplets'));
  if (type === 'Wayfinding') heading.append(icon('landmark'));
  heading.append(document.createTextNode(type));
  const text = document.createElement('p');
  text.textContent = instruction;
  const detail = document.createElement('small');
  detail.textContent = note;
  item.append(heading, text, detail);
  $('#step-list').append(item);
}

function renderNearbyDetails() {
  const details = $('#nearby-details');
  details.hidden = !exampleSelected() || !state.route;
  if (details.hidden) return;
  const fountains = nearbyFountains();
  const sensors = nearbySensors();
  $('#nearby-summary').textContent = `Nearby source points · ${fountains.length} fountains, ${sensors.length} sensors`;
  const list = $('#nearby-list');
  list.replaceChildren();
  fountains.forEach(({ feature, distance }) => {
    const item = document.createElement('li');
    item.textContent = `Fountain · ${feature.label} · ${Math.round(distance)} m from route · water status unknown`;
    list.append(item);
  });
  sensors.forEach(({ feature, distance }) => {
    const item = document.createElement('li');
    const reading = feature.value == null ? 'no reading' : `${feature.value.toFixed(1)}°C`;
    const observed = feature.provenance.observed_at ?
      new Date(feature.provenance.observed_at).toLocaleString('en-GB', { timeZone: 'Europe/Zurich' }) : 'time unknown';
    item.textContent = `Sensor · ${feature.label} · ${Math.round(distance)} m from route · ${reading} · ${feature.availability} · observed ${observed}`;
    list.append(item);
  });
  WAYFINDING_PLACES.forEach((place) => {
    const item = document.createElement('li');
    item.textContent = `Wayfinding ${place.type} · ${place.label} · ${place.note} `;
    const source = document.createElement('a');
    source.href = place.sourceUrl;
    source.textContent = 'OSM source';
    source.target = '_blank';
    source.rel = 'noopener noreferrer';
    item.append(source);
    list.append(item);
  });
  COOL_PLACES.forEach((place) => {
    const item = document.createElement('li');
    item.textContent = `Cool-place candidate · ${place.label} · ${place.note} `;
    const source = document.createElement('a');
    source.href = place.operatorUrl;
    source.textContent = 'Check opening hours';
    source.target = '_blank';
    source.rel = 'noopener noreferrer';
    item.append(source);
    list.append(item);
  });
}

function renderJourney() {
  const destination = state.destination;
  $('#selected-journey').hidden = !destination;
  $('#map-title').textContent = destination ? destination.name : 'Explore Basel';
  $('#step-list').replaceChildren();
  if (destination) {
    $('#journey-mode').textContent = state.mode === 'fast' ? 'Fastest preference' : 'More shade preference';
    $('#journey-title').textContent = destination.name;
    $('#journey-summary').textContent = exampleSelected() && state.route ?
      `From Basel SBB. ${Math.round(state.routeInfo.distance_m)} m along saved pedestrian streets.` :
      'Choose the SBB → Marktplatz example for a checked street path.';
    const preference = state.mode === 'fast' ? 'Fastest' : 'More shade';
    $('#steps-summary').textContent = exampleSelected() && state.route ?
      `${preference} preference · ${Math.round(state.routeInfo.distance_m)} m · saved street route` :
      `${preference} preference · street route unavailable for this selection`;
    journeySteps().forEach(appendStep);
  } else {
    $('#steps-summary').textContent = 'Choose a destination to preview directions.';
  }
  const fountains = exampleSelected() ? nearbyFountains().length : 0;
  const sensors = exampleSelected() ? nearbySensors().length : 0;
  $('#source-status').textContent = `${state.sourceStatus} · ${fountains} fountains within 50 m · ${sensors} sensors within 250 m`;
  $('#map-legend').hidden = !exampleSelected() || !state.route;
  updateDisplayControls();
  renderNearbyDetails();
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
  $('#map-overlay').textContent = exampleSelected() && state.route ?
    `${preference} · street route · ${state.mapView === 'route' ? 'example route temperatures' :
      state.layers.heatmap ? 'example area heat' : 'area heat hidden'}` :
    state.destination ? 'Street route unavailable for this selection. Try the SBB → Marktplatz example.' :
      'Choose a place to preview a route.';
}

let mapSource;
let heatSource;
let shadowSource;
let heatmapLayer;
let shadowLayer;
let routeStyles;
let heatColors;
const routeAnchors = [
  { celsius: 26, cssProperty: '--poc-temp-26' },
  { celsius: 29, cssProperty: '--poc-temp-29' },
  { celsius: 36, cssProperty: '--poc-temp-36' },
];

function routeSegments() {
  const { Feature } = window.ol;
  const { LineString } = window.ol.geom;
  const { coordinates, cumulative, length } = state.route;
  const project = window.ol.proj.fromLonLat;
  const features = [];
  for (let index = 1; index < coordinates.length; index += 1) {
    const start = coordinates[index - 1];
    const end = coordinates[index];
    const metres = cumulative[index] - cumulative[index - 1];
    const pieces = Math.max(1, Math.ceil(metres / 12));
    for (let piece = 0; piece < pieces; piece += 1) {
      const point = (part) => start.map((value, axis) => value + (end[axis] - value) * part);
      const fraction = (cumulative[index - 1] + metres * (piece + 0.5) / pieces) / length;
      const feature = new Feature(new LineString([project(point(piece / pieces)), project(point((piece + 1) / pieces))]));
      feature.set('kind', 'route');
      feature.set('temperature', exampleTemperature(fraction));
      features.push(feature);
    }
  }
  return features;
}

function sourceMarkers(kind, items) {
  const { Feature } = window.ol;
  const { Point } = window.ol.geom;
  return items.map(({ feature }) => {
    const marker = new Feature(new Point(window.ol.proj.fromLonLat(feature.geometry.coordinates)));
    marker.set('kind', kind);
    marker.set('sourceFeature', feature);
    marker.set('popup', kind === 'sensor' ?
      `${feature.label} · ${feature.value == null ? 'No reading' : `${feature.value.toFixed(1)}°C`} · ${feature.availability} · ${state.sourceStatus}` :
      `${feature.label} · Drinking water and operation unknown · ${state.sourceStatus}`);
    return marker;
  });
}

function placeMarkers(kind, places) {
  const { Feature } = window.ol;
  const { Point } = window.ol.geom;
  return places.map((place) => {
    const marker = new Feature(new Point(window.ol.proj.fromLonLat(place.coordinates)));
    marker.set('kind', kind);
    marker.set('label', place.label);
    marker.set('popup', `${place.label} · ${place.note}`);
    return marker;
  });
}

function stopMarkers(stops) {
  const { Feature } = window.ol;
  const { Point } = window.ol.geom;
  return stops.map((stop) => {
    const marker = new Feature(new Point(window.ol.proj.fromLonLat(stop.coordinates)));
    marker.set('kind', 'stop');
    marker.set('stopType', stop.type);
    marker.set('label', stop.label);
    marker.set('popup', `${stop.label} · ${stop.note}`);
    return marker;
  });
}

function updateDisplayControls() {
  $('#route-heat-view').setAttribute('aria-pressed', String(state.mapView === 'route'));
  $('#area-heat-view').setAttribute('aria-pressed', String(state.mapView === 'area'));
  $('#reverse-heat').setAttribute('aria-pressed', String(state.reverseHeat));
  $('#heat-ramp').classList.toggle('reversed', state.reverseHeat);
  $('#heat-ramp').alt = state.reverseHeat ?
    'Yellow through red to purple reversed temperature colour ramp' :
    'Purple through red to yellow temperature colour ramp';
  const areaHidden = state.mapView === 'area' && !state.layers.heatmap;
  $('#ramp-display').hidden = areaHidden;
  $('#legend-title').textContent = state.mapView === 'route' ? 'Example route temperature' :
    areaHidden ? 'Area heat hidden' : 'Example area heat';
  $('#legend-note').textContent = state.mapView === 'route' ?
    'Start 26°C · peak 36°C · end 31°C' :
    areaHidden ? 'Teal line shows the route.' : 'Example heat surface. Teal line shows the route.';
  $('#legend-fountains').hidden = !state.layers.fountains;
  $('#legend-sensors').hidden = !state.layers.sensors;
  $('#legend-wayfinding').hidden = !state.layers.landmarks;
  $('#legend-cool').hidden = !state.layers.coolPlaces;
  $('#legend-shadow').hidden = !state.layers.shadows;
  $('#layer-note').textContent = state.mapView === 'route' ?
    'Route colours use example temperatures. Shadows are illustrative; cooling-place AC is unknown.' :
    'Area heat uses example values near the route. It is not a measured temperature map.';
}

function renderMapRoute() {
  if (!mapSource || !window.ol) return;
  mapSource.clear();
  heatSource.clear();
  shadowSource.clear();
  const { Feature } = window.ol;
  const { Point, LineString } = window.ol.geom;
  const project = (place) => window.ol.proj.fromLonLat([place.lon, place.lat]);
  if (exampleSelected() && state.route) {
    const outline = new Feature(new LineString(state.route.coordinates.map((point) => window.ol.proj.fromLonLat(point))));
    outline.set('kind', 'route-outline');
    mapSource.addFeature(outline);
    if (state.mapView === 'route') mapSource.addFeatures(routeSegments());
    else {
      const route = new Feature(new LineString(state.route.coordinates.map((point) => window.ol.proj.fromLonLat(point))));
      route.set('kind', 'plain-route');
      mapSource.addFeature(route);
    }
    if (state.layers.fountains) mapSource.addFeatures(sourceMarkers('fountain', nearbyFountains()));
    if (state.layers.sensors) mapSource.addFeatures(sourceMarkers('sensor', nearbySensors()));
    if (state.layers.landmarks) mapSource.addFeatures(placeMarkers('wayfinding', WAYFINDING_PLACES));
    if (state.layers.coolPlaces) mapSource.addFeatures(placeMarkers('cool-place', COOL_PLACES));
    mapSource.addFeatures(stopMarkers(routeStops(state.route, nearbyFountains())));
    if (state.layers.shadows) shadowSource.addFeatures(exampleShadowFeatures(window.ol, state.route));
    if (state.mapView === 'area' && state.layers.heatmap) {
      heatSource.addFeatures(exampleHeatFeatures(window.ol, state.route));
    }
  }
  heatmapLayer.setVisible(state.mapView === 'area' && state.layers.heatmap);
  shadowLayer.setVisible(state.layers.shadows);
  const origin = new Feature(new Point(project(state.origin)));
  origin.set('kind', 'origin');
  mapSource.addFeature(origin);
  if (!state.destination) return;
  const destination = new Feature(new Point(project(state.destination)));
  destination.set('kind', 'destination');
  mapSource.addFeature(destination);
}

function focusJourney() {
  if (!state.destination || !window.routePreviewMap) return;
  if (exampleSelected() && state.route) {
    const extent = window.ol.extent.boundingExtent(state.route.coordinates.map((point) => window.ol.proj.fromLonLat(point)));
    window.routePreviewMap.getView().fit(extent, { padding: [75, 75, 75, 75], maxZoom: 16, duration: 300 });
    return;
  }
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
  heatSource = new ol.source.Vector();
  shadowSource = new ol.source.Vector();
  const theme = getComputedStyle(document.documentElement);
  const teal = theme.getPropertyValue('--poc-teal').trim();
  const originColor = theme.getPropertyValue('--poc-origin').trim();
  const destinationColor = theme.getPropertyValue('--poc-destination').trim();
  const sensorColor = theme.getPropertyValue('--poc-sensor').trim();
  const landmarkColor = theme.getPropertyValue('--poc-landmark').trim();
  const coolColor = theme.getPropertyValue('--poc-cool-place').trim();
  const outlineColor = theme.getPropertyValue('--poc-route-outline').trim();
  const white = theme.getPropertyValue('--poc-white').trim();
  const baseAnchors = routeAnchors.map(({ celsius, cssProperty }) => ({
    celsius, rgb: theme.getPropertyValue(cssProperty).trim().match(/[a-f\d]{2}/gi).map((part) => parseInt(part, 16)),
  }));
  routeStyles = new Map();
  const outlineStyle = new ol.style.Style({ stroke: new ol.style.Stroke({ color: outlineColor, width: 10 }) });
  const plainRouteStyle = new ol.style.Style({ stroke: new ol.style.Stroke({ color: teal, width: 7 }) });
  const segmentStyle = (feature) => {
    const anchors = baseAnchors.map((anchor, index) => ({
      celsius: anchor.celsius,
      rgb: state.reverseHeat ? baseAnchors[baseAnchors.length - 1 - index].rgb : anchor.rgb,
    }));
    const color = temperatureColor(feature.get('temperature'), anchors);
    if (!routeStyles.has(color)) routeStyles.set(color, new ol.style.Style({
      stroke: new ol.style.Stroke({ color, width: 7 }),
    }));
    return routeStyles.get(color);
  };
  const pointStyle = (color) => new ol.style.Style({ image: new ol.style.Circle({
    radius: 10, fill: new ol.style.Fill({ color }), stroke: new ol.style.Stroke({ color: white, width: 3 }),
  }) });
  const fountainStyle = new ol.style.Style({ image: new ol.style.Circle({
    radius: 5, fill: new ol.style.Fill({ color: destinationColor }),
    stroke: new ol.style.Stroke({ color: white, width: 2 }),
  }) });
  const sensorStyle = new ol.style.Style({
    image: new ol.style.Circle({ radius: 5, fill: new ol.style.Fill({ color: white }),
      stroke: new ol.style.Stroke({ color: sensorColor, width: 2 }) }),
  });
  const iconStyle = (name, label, color, offsetY = -29) => [
    new ol.style.Style({ image: new ol.style.Circle({ radius: 19,
      fill: new ol.style.Fill({ color: white }), stroke: new ol.style.Stroke({ color, width: 3 }),
    }) }),
    new ol.style.Style({
      image: new ol.style.Icon({ src: `/poc-assets/icons/${name}.svg`, scale: 0.85 }),
      text: new ol.style.Text({ text: label, offsetY, font: '700 13px sans-serif',
        fill: new ol.style.Fill({ color: outlineColor }),
        backgroundFill: new ol.style.Fill({ color: white }),
        padding: [3, 5, 3, 5],
      }),
    }),
  ];
  const stopStyles = new Map([
    ['rest', iconStyle('armchair', 'REST', teal)],
    ['water', iconStyle('droplets', 'WATER', teal)],
    ['pause', iconStyle('pause', 'PAUSE', teal)],
  ]);
  const cueStyle = (name, color) => [
    new ol.style.Style({ image: new ol.style.Circle({ radius: 13,
      fill: new ol.style.Fill({ color: white }), stroke: new ol.style.Stroke({ color, width: 3 }),
    }) }),
    new ol.style.Style({ image: new ol.style.Icon({ src: `/poc-assets/icons/${name}.svg`, scale: 0.55 }) }),
  ];
  const landmarkStyles = new Map([
    ['Barfüsserplatz', cueStyle('map-pin', landmarkColor)],
    ['Stadtcasino Basel', cueStyle('landmark', landmarkColor)],
    ['Barfüsserkirche', cueStyle('landmark', landmarkColor)],
  ]);
  const coolPlaceStyle = iconStyle('landmark', 'Foyer Public · AC?', coolColor, 29);
  const shadowStyle = new ol.style.Style({
    fill: new ol.style.Fill({ color: theme.getPropertyValue('--poc-shadow-example-fill').trim() }),
    stroke: new ol.style.Stroke({ color: theme.getPropertyValue('--poc-shadow-example-stroke').trim(), width: 2, lineDash: [7, 5] }),
  });
  shadowLayer = new ol.layer.Vector({ source: shadowSource, visible: false, style: shadowStyle });
  heatmapLayer = new ol.layer.Heatmap({ source: heatSource, visible: false,
    blur: 35, radius: 42, opacity: Number(theme.getPropertyValue('--poc-heat-opacity')),
    weight: (feature) => feature.get('weight'),
  });
  heatColors = baseAnchors.map(({ rgb }) => `rgb(${rgb.join(',')})`);
  heatmapLayer.setGradient(heatColors);
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
      heatmapLayer,
      shadowLayer,
      new ol.layer.Vector({ source: mapSource, style: (feature) => {
        if (feature.get('kind') === 'route-outline') return outlineStyle;
        if (feature.get('kind') === 'route') return segmentStyle(feature);
        if (feature.get('kind') === 'plain-route') return plainRouteStyle;
        if (feature.get('kind') === 'fountain') return fountainStyle;
        if (feature.get('kind') === 'sensor') return sensorStyle;
        if (feature.get('kind') === 'stop') return stopStyles.get(feature.get('stopType'));
        if (feature.get('kind') === 'wayfinding') return landmarkStyles.get(feature.get('label'));
        if (feature.get('kind') === 'cool-place') return coolPlaceStyle;
        return pointStyle(feature.get('kind') === 'origin' ? originColor : destinationColor);
      } }),
    ],
    view,
  });
  window.routePreviewMap = map;
  map.on('singleclick', (event) => {
    if (!state.picking) {
      const popup = map.forEachFeatureAtPixel(event.pixel, (feature) => feature.get('popup'));
      if (popup) $('#map-overlay').textContent = popup;
      return;
    }
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

async function loadExampleRoute() {
  const response = await fetch('/api/poc-route', { signal: AbortSignal.timeout(10_000) });
  if (!response.ok) throw new Error('Saved street route unavailable');
  const collection = await response.json();
  const feature = collection.features?.find((item) => item.properties?.route_id === 'demo-route-a');
  if (feature?.geometry?.type !== 'LineString' || !Array.isArray(feature.geometry.coordinates)) {
    throw new Error('Saved street route invalid');
  }
  state.route = routeGeometry(feature.geometry.coordinates);
  state.routeInfo = feature.properties;
  renderJourney();
  focusJourney();
}

function useSnapshot(snapshot, status, saved = false) {
  const parsed = parseSnapshot(snapshot);
  state.snapshot = saved ? {
    ...parsed,
    layers: parsed.layers.map((layer) => ({
      ...layer,
      availability: layer.availability === 'current' ? 'stale' : layer.availability,
      features: layer.features.map((feature) => ({
        ...feature,
        availability: feature.availability === 'current' ? 'stale' : feature.availability,
      })),
    })),
  } : parsed;
  state.sourceStatus = status;
  renderJourney();
}

async function loadSources() {
  try {
    const saved = await fetch('/poc-assets/provider-snapshot.json');
    if (!saved.ok) throw new Error('Saved source data unavailable');
    const snapshot = await saved.json();
    const savedDate = new Date(snapshot.generated_at).toLocaleString('en-GB', {
      day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Europe/Zurich',
    });
    useSnapshot(snapshot, `Saved source snapshot · ${savedDate}`, true);
  } catch {
    state.sourceStatus = 'Basel source data unavailable';
    renderJourney();
  }
  const mode = state.offline ? 'offline' : 'online';
  try {
    const response = await fetch(`/api/map?mode=${mode}`, { signal: AbortSignal.timeout(30_000) });
    if (!response.ok) throw new Error('Provider API unavailable');
    const snapshot = parseSnapshot(await response.json());
    if (snapshot.layers.some((layer) => layer.features.length > 0)) {
      useSnapshot(snapshot, state.offline ? 'Saved offline provider data' : 'Basel provider data');
    }
  } catch {
    // The dated saved snapshot remains visible when providers cannot be reached.
  }
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
$('#route-heat-view').addEventListener('click', () => {
  state.mapView = 'route';
  renderJourney();
});
$('#area-heat-view').addEventListener('click', () => {
  state.mapView = 'area';
  renderJourney();
});
$('#reverse-heat').addEventListener('click', () => {
  state.reverseHeat = !state.reverseHeat;
  routeStyles?.clear();
  if (heatmapLayer) heatmapLayer.setGradient(state.reverseHeat ? [...heatColors].reverse() : heatColors);
  renderJourney();
});
document.querySelectorAll('[data-layer]').forEach((checkbox) => checkbox.addEventListener('change', () => {
  state.layers[checkbox.dataset.layer] = checkbox.checked;
  renderJourney();
}));
$('#show-route').addEventListener('click', showMap);
$('#back-to-plan').addEventListener('click', showPlan);
$('#try-example').addEventListener('click', () => {
  setOrigin(FALLBACK_START, 'Example start selected');
  selectDestination(EXAMPLE_DESTINATION);
  showMap();
});

PLACES.forEach((place) => {
  const option = document.createElement('option');
  option.value = place.name;
  $('#origin-options').append(option);
});

state.offline = new URLSearchParams(location.search).get('mode') === 'offline';
setOrigin(FALLBACK_START, 'Sample start until GPS is available');
selectDestination(EXAMPLE_DESTINATION);
void createMap().catch(() => { $('#map-overlay').textContent = 'Basemap unavailable. Route controls still work.'; });
void loadExampleRoute().catch(() => { $('#map-overlay').textContent = 'Saved street route unavailable.'; });
void loadSources();
useGps();

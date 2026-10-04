import {
  routeGeometry,
  positionAlongRoute
} from './route-planner-data.js';
import {
  WAYFINDING_PLACES
} from './wayfinding-places.js';

const configuration = await fetch('/config/landmarks.json').then((response) =>
  response.ok ? response.json() : null).catch(() => null);
export {
  configuration as landmarkSettings
};
let cachedLandmarks = null;
export function setCachedLandmarks(layer) {
  cachedLandmarks = layer;
}

function validPlace(place) {
  if (!place || typeof place !== 'object') return false;
  const point = place.coordinates;
  return place.id && typeof place.label === 'string' && place.label.trim() &&
    !/^mapped\b/i.test(place.label) && typeof place.sourceUrl === 'string' &&
    /^https:\/\//.test(place.sourceUrl) && Array.isArray(point) && point.length === 2 &&
    point.every(Number.isFinite) && Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90;
}

/** Copy checked places and named non-fixture RouteAmenities stops with provenance. */
export function savedLandmarkEvidence(amenities = null) {
  if (!configuration) return {
    availability: 'missing',
    places: [],
    explanation: 'Landmark configuration unavailable.'
  };
  const places = WAYFINDING_PLACES.filter(place => !cachedLandmarks?.features?.some(feature => feature.label === place.label)).map((place) => ({
    ...place,
    checkedAt: configuration.known_places_checked_at,
    retrievedAt: null,
    note: 'Mapped place centre; visibility from this route is unverified.',
    visibility: 'unknown',
    familiar: 'unknown',
  }));
  const features = [...amenities?.rest_stops?.features ?? [], ...cachedLandmarks?.features ?? []];
  for (const feature of features) {
    if (feature.provenance?.fixture !== false || feature.geometry?.type !== 'Point') continue;
    const place = {
      id: feature.id,
      label: feature.label,
      coordinates: feature.geometry.coordinates,
      sourceUrl: feature.provenance.source_url,
      checkedAt: null,
      retrievedAt: feature.provenance.retrieved_at ?? null,
      observedAt: feature.provenance.observed_at ?? null,
      visibility: 'unknown',
      familiar: 'unknown',
      sourceFeature: feature,
      note: feature.explanation,
    };
    if (validPlace(place)) places.push(place);
  }
  return {
    availability: cachedLandmarks?.availability === 'current' ? 'current' : 'limited',
    places,
    explanation: configuration.coverage_note
  };
}

/** Search the saved named evidence without requiring a selected walking route. */
export function searchSavedLandmarks(query, evidence = savedLandmarkEvidence(), limit = 8) {
  const normalize = (text) => text.toLocaleLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/ß/g, 'ss');
  const words = normalize(query.trim()).split(/\s+/).filter(Boolean);
  if (!words.length || !evidence || ['missing', 'failed', 'unsupported'].includes(evidence.availability)) return [];
  const seen = new Set();
  const reference = WAYFINDING_PLACES.find(place => place.id === configuration?.search_reference_id);
  return (evidence.places ?? []).filter(validPlace).filter((place) => {
      const name = normalize(place.label);
      if (seen.has(place.id) || !words.every((word) => name.includes(word))) return false;
      seen.add(place.id);
      return true;
    }).map(place => ({
      place,
      distance: reference ? routeGeometry([reference.coordinates, place.coordinates]).length : null
    }))
    .sort((a, b) => (a.distance ?? 0) - (b.distance ?? 0)).slice(0, limit).map(({
      place,
      distance
    }) => ({
      id: `landmark-${place.id}`,
      name: place.label,
      lon: place.coordinates[0],
      lat: place.coordinates[1],
      landmark: place,
      locationHint: reference ? `~${Math.round(distance)} m from ${reference.label} (straight line)` : null,
    }));
}

/** Match a selected MapFeature's geometry, preserving original mapped positions. */
export function routeLandmarkCandidates(route, evidence = savedLandmarkEvidence(), settings = configuration) {
  if (!settings || !Number.isFinite(settings.route_buffer_metres) ||
    settings.route_buffer_metres <= 0 || !Number.isInteger(settings.max_markers) ||
    settings.max_markers <= 0) return {
    availability: 'missing',
    routeId: route?.id ?? null,
    candidates: [],
    explanation: 'Landmark configuration unavailable.',
  };
  if (!route || route.geometry?.type !== 'LineString') return {
    availability: 'missing',
    routeId: null,
    candidates: [],
    explanation: 'Select a walking route to see mapped landmark candidates.',
  };
  if (!evidence || ['missing', 'failed', 'unsupported'].includes(evidence.availability) || !Array.isArray(evidence.places)) return {
    availability: 'missing',
    routeId: route.id,
    candidates: [],
    explanation: 'Saved landmark data unavailable. No substitute markers were invented.',
  };
  const coordinates = route.geometry.coordinates;
  const validGeometry = Array.isArray(coordinates) && coordinates.length >= 2 &&
    coordinates.every((point) => Array.isArray(point) && point.length === 2 &&
      point.every(Number.isFinite) && Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90);
  const geometry = validGeometry ? routeGeometry(coordinates) : {
    length: 0
  };
  if (!Number.isFinite(geometry.length) || geometry.length <= 0) return {
    availability: 'missing',
    routeId: route.id,
    candidates: [],
    explanation: 'Route geometry unavailable for landmark matching.',
  };
  const seen = new Set();
  const nearby = evidence.places.filter(validPlace).flatMap((place) => {
    if (seen.has(place.id)) return [];
    seen.add(place.id);
    const position = positionAlongRoute(geometry, place.coordinates);
    return position.distance <= settings.route_buffer_metres ? [{
      ...place,
      coordinates: [...place.coordinates],
      routeId: route.id,
      fraction: position.fraction,
      distanceMetres: position.distance,
      visibility: 'unknown',
      familiar: 'unknown',
      kind: 'landmark',
    }] : [];
  }).sort((a, b) => a.fraction - b.fraction);
  const candidates = nearby.slice(0, settings.max_markers);
  return {
    availability: candidates.length ? 'limited' : 'empty',
    routeId: route.id,
    candidates,
    explanation: `${candidates.length} mapped candidates near this route. ${evidence.explanation ?? ''}${nearby.length > candidates.length ? ' Marker count limited; additional candidates omitted.' : ''}`,
  };
}

/** Mount a hidden OpenLayers layer; update replaces markers and emits evidence status. */
export function mountRouteLandmarks(map, {
  style,
  onStatus = () => {},
  settings = configuration,
  ol = window.ol
} = {}) {
  const source = new ol.source.Vector();
  const theme = getComputedStyle(document.documentElement);
  const layer = new ol.layer.Vector({
    source,
    visible: false,
    zIndex: settings?.layer_z_index,
    style: style ?? new ol.style.Style({
      image: new ol.style.Icon({
        src: '/src/icons/landmark.svg',
        color: theme.getPropertyValue('--poc-landmark').trim(),
        scale: settings?.icon_scale,
      })
    }),
  });
  map.addLayer(layer);
  let visible = false;
  let result = {
    availability: 'missing',
    candidates: [],
    routeId: null,
    explanation: 'Select a walking route to see mapped landmark candidates.'
  };
  let disposed = false;

  function redraw() {
    source.clear();
    layer.setVisible(visible && !disposed);
    if (!visible || disposed) return;
    source.addFeatures(result.candidates.map((candidate) => {
      const marker = new ol.Feature({
        geometry: new ol.geom.Point(ol.proj.fromLonLat(candidate.coordinates)),
        landmarkCandidate: candidate,
      });
      marker.setId(candidate.id);
      return marker;
    }));
  }
  return {
    layer,
    update(route, evidence = savedLandmarkEvidence()) {
      if (disposed) return result;
      result = routeLandmarkCandidates(route, evidence, settings);
      redraw();
      onStatus(result);
      return result;
    },
    setVisible(value) {
      if (disposed) return;
      visible = Boolean(value);
      redraw();
      onStatus(result);
    },
    dispose() {
      disposed = true;
      source.clear();
      layer.setVisible(false);
      map.removeLayer(layer);
    },
  };
}

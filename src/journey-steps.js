import {
  amenitiesAtRestStops
} from './route-amenities.js';
import {
  routeGeometry,
  positionAlongRoute,
  coordinateAtFraction
} from './route-planner-data.js';
import {
  WAYFINDING_PLACES
} from './wayfinding-places.js';

// A nearby mapped centre is a reference, never a verified visible turn marker.
const LANDMARK_REFERENCE_METRES = 50;
const COLLAPSE_CANDIDATES_ABOVE = 2;

function walkingTime(seconds) {
  return seconds < 60 ? `${Math.round(seconds)} sec` : `${Math.round(seconds / 60)} min`;
}

function landmarkReference(step, geometry, landmarks) {
  const stepPosition = positionAlongRoute(geometry, step.location);
  return landmarks.map((position) => {
      const alongDistance = Math.abs(position.fraction - stepPosition.fraction) * geometry.length;
      return {
        place: position.place,
        distance: Math.hypot(position.distance, alongDistance)
      };
    }).filter((item) => item.distance <= LANDMARK_REFERENCE_METRES)
    .sort((a, b) => a.distance - b.distance)[0];
}

// These are preparation prompts, not medical thresholds or verified stops.
export function journeyItems(route, amenities = [], landmarks = WAYFINDING_PLACES, settings = {}) {
  if (!route?.route || route.geometry?.type !== 'LineString') return [];
  const distance = route.route.distance_m;
  const directions = route.directions;
  const geometry = routeGeometry(route.geometry.coordinates);
  const namedStops = amenities.filter(({
      feature
    }) =>
    feature.geometry?.type === 'Point' && feature.rest_type === 'indoor' &&
    feature.provenance?.source_url && feature.provenance.fixture === false &&
    feature.label && !feature.label.startsWith('Mapped ')).map(({
    feature
  }) => ({
    label: feature.label,
    coordinates: feature.geometry.coordinates,
    sourceUrl: feature.provenance.source_url,
  }));
  const references = [...landmarks, ...namedStops];
  const referencePositions = references.filter(place => place.sourceUrl && place.coordinates).map(place => ({
    place,
    ...positionAlongRoute(geometry, place.coordinates)
  }));
  const supported = directions?.route_id === route.id;
  const items = [];
  if (!supported) items.push({
    fraction: 0,
    kind: 'start',
    text: 'Start walking along the displayed route'
  }, {
    fraction: 1,
    kind: 'arrive',
    text: 'Arrive at your destination'
  });
  let continued = false;
  if (supported) directions.steps.forEach(step => {
    if (step.kind === 'continue' && continued) return;
    if (step.kind === 'continue') continued = true;
    else continued = false;
    const reference = step.kind === 'turn' ? landmarkReference(step, geometry, referencePositions) : null;
    const text = reference ? `${step.text.split(' on ')[0]} by ${reference.place.label}` : step.text;
    items.push({
      fraction: distance ? step.at_metres / distance : 0,
      text,
      kind: step.kind,
      landmarkId: reference?.place.id
    });
  });
  // Route-side references keep their mapped locations; never infer a turn from them.
  const nearby = referencePositions
    .filter(item => item.distance <= (settings.guide_buffer_metres ?? 50) && item.fraction > 0.02 && item.fraction < 0.98)
    .sort((a, b) => a.fraction - b.fraction);
  let lastLandmark = -Infinity;
  const seen = new Set(items.map(item => item.landmarkId).filter(Boolean));
  nearby.forEach(item => {
    if (seen.has(item.place.id) || item.fraction * geometry.length - lastLandmark < (settings.guide_spacing_metres ?? 120)) return;
    // References close to retained turns belong to that turn rather than an extra row.
    if (items.some(step => step.kind === 'turn' && Math.abs(step.fraction - item.fraction) * geometry.length < LANDMARK_REFERENCE_METRES)) return;
    const before = coordinateAtFraction(geometry, Math.max(0, item.fraction - 0.001));
    const after = coordinateAtFraction(geometry, Math.min(1, item.fraction + 0.001));
    const cross = (after[0] - before[0]) * (item.place.coordinates[1] - before[1]) - (after[1] - before[1]) * (item.place.coordinates[0] - before[0]);
    const side = item.distance >= 5 ? ` on your ${cross>0?'left':'right'}` : '';
    items.push({
      fraction: item.fraction,
      kind: 'landmark',
      text: `Continue past ${item.place.label}${side}`
    });
    seen.add(item.place.id);
    lastLandmark = item.fraction * geometry.length;
  });
  items.push(...amenitiesAtRestStops(geometry, route.route.duration_s, amenities).map((stop) => ({
    fraction: stop.fraction,
    kind: 'prompt',
    text: `${stop.walk_minutes} minutes walking: consider water and a rest. No stop is verified here.`,
    amenities: stop.amenities,
  })));
  return items.sort((a, b) => a.fraction - b.fraction);
}

export function mountJourneySteps(container) {
  const update = (route, {
    amenities = [],
    landmarks = WAYFINDING_PLACES,
    landmarkSettings = {}
  } = {}) => {
    container.replaceChildren();
    if (!route) return;
    const heading = document.createElement('h3');
    heading.textContent = 'Your walking guide';
    container.append(heading);
    if (!route.directions || route.directions.route_id !== route.id) {
      const unavailable = document.createElement('p');
      unavailable.textContent = 'Directions unavailable for this route. Inspect the map; turns are not verified.';
      container.append(unavailable);
    }
    const list = document.createElement('ol');
    list.className = 'walking-guide-list';
    for (const item of journeyItems(route, amenities, landmarks, landmarkSettings)) {
      const row = document.createElement('li');
      row.dataset.kind = item.kind;
      row.textContent = item.text;
      if (item.amenities?.length) {
        const group = document.createElement(item.amenities.length > COLLAPSE_CANDIDATES_ABOVE ? 'details' : 'div');
        if (item.amenities.length > COLLAPSE_CANDIDATES_ABOVE) {
          const summary = document.createElement('summary');
          summary.textContent = `${item.amenities.length} nearby water and bench candidates`;
          group.append(summary);
        }
        const candidates = document.createElement('ul');
        for (const {
            feature
          }
          of item.amenities) {
          const candidate = document.createElement('li');
          candidate.textContent = `${feature.kind === 'fountain' ? 'Water' : 'Bench'}: ${feature.label}. Access and availability need checking; a diversion is not included.`;
          candidates.append(candidate);
        }
        group.append(candidates);
        row.append(group);
      }
      list.append(row);
    }
    container.append(list);
    if (route.directions?.route_id === route.id) {
      const detail = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = 'All turn-by-turn instructions';
      const full = document.createElement('ol');
      full.className = 'walking-turn-list';
      route.directions.steps.forEach(step => {
        const row = document.createElement('li');
        row.textContent = `${step.text}${step.distance_m>0?` · ${Math.round(step.distance_m)} m (${walkingTime(step.duration_s)})`:''}`;
        full.append(row);
      });
      detail.append(summary, full);
      container.append(detail);
    }
  };
  return {
    update,
    dispose: () => container.replaceChildren()
  };
}

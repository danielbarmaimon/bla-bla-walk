import {
  plannedRestStops
} from './route-amenities.js';
import {
  routeGeometry,
  positionAlongRoute
} from './route-planner-data.js';
import {
  WAYFINDING_PLACES
} from './wayfinding-places.js';

// A nearby mapped centre is a reference, never a verified visible turn marker.
const LANDMARK_REFERENCE_METRES = 25;

function walkingTime(seconds) {
  return seconds < 60 ? `${Math.round(seconds)} sec` : `${Math.round(seconds / 60)} min`;
}

function landmarkReference(step, geometry, landmarks) {
  const stepPosition = positionAlongRoute(geometry, step.location);
  return landmarks.filter((place) => place.sourceUrl && place.coordinates).map((place) => {
      const position = positionAlongRoute(geometry, place.coordinates);
      const alongDistance = Math.abs(position.fraction - stepPosition.fraction) * geometry.length;
      return {
        place,
        distance: Math.hypot(position.distance, alongDistance)
      };
    }).filter((item) => item.distance <= LANDMARK_REFERENCE_METRES)
    .sort((a, b) => a.distance - b.distance)[0];
}

// These are preparation prompts, not medical thresholds or verified stops.
export function journeyItems(route, amenities = [], landmarks = WAYFINDING_PLACES) {
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
  const items = directions?.route_id === route.id ? directions.steps.map((step) => {
    const reference = step.kind !== 'arrive' ? landmarkReference(step, geometry, references) : null;
    const landmark = reference ? ` Near ${reference.place.label} (mapped reference; visibility unverified).` : '';
    const effort = step.distance_m > 0 ? `. Walk ${Math.round(step.distance_m)} m (about ${walkingTime(step.duration_s)}).` : '';
    return {
      fraction: distance ? step.at_metres / distance : 0,
      text: `${step.text}${effort}${landmark}`,
      kind: step.kind,
    };
  }) : [];
  items.push(...plannedRestStops(geometry, route.route.duration_s).map((stop) => ({
    fraction: stop.fraction,
    kind: 'prompt',
    text: `${stop.walk_minutes} minutes walking: consider water and a rest. No stop is verified here.`,
  })));
  items.push(...amenities.filter((item) => Number.isFinite(item.fraction) &&
    item.fraction >= 0 && item.fraction < 1).map(({
    fraction,
    feature
  }) => ({
    fraction,
    kind: 'amenity',
    text: `Nearby ${feature.kind === 'fountain' ? 'water candidate' : 'rest candidate'}: ${feature.label}. Access${feature.kind === 'fountain' ? ', drinking water' : ''} and availability need checking; a diversion is not included.`,
  })));
  return items.sort((a, b) => a.fraction - b.fraction);
}

export function mountJourneySteps(container) {
  const update = (route, {
    amenities = [],
    landmarks = WAYFINDING_PLACES
  } = {}) => {
    container.replaceChildren();
    if (!route) return;
    const heading = document.createElement('h3');
    heading.textContent = 'Walking directions';
    container.append(heading);
    if (!route.directions || route.directions.route_id !== route.id) {
      const unavailable = document.createElement('p');
      unavailable.textContent = 'Directions unavailable for this route. Inspect the map; turns are not verified.';
      container.append(unavailable);
    }
    const list = document.createElement('ol');
    for (const item of journeyItems(route, amenities, landmarks)) {
      const row = document.createElement('li');
      row.dataset.kind = item.kind;
      row.textContent = item.text;
      list.append(row);
    }
    container.append(list);
  };
  return {
    update,
    dispose: () => container.replaceChildren()
  };
}

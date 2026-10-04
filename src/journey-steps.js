import {
  amenitiesAtRestStops
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
const COLLAPSE_CANDIDATES_ABOVE = 2;

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
  };
  return {
    update,
    dispose: () => container.replaceChildren()
  };
}

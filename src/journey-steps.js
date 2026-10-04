import {
  plannedRestStops
} from './route-amenities.js';
import {
  routeGeometry
} from './route-planner-data.js';

// These are preparation prompts, not medical thresholds or verified stops.
export function journeyItems(route, amenities = []) {
  if (!route?.route || route.geometry?.type !== 'LineString') return [];
  const distance = route.route.distance_m;
  const directions = route.directions;
  const items = directions?.route_id === route.id ? directions.steps.map((step) => ({
    fraction: distance ? step.at_metres / distance : 0,
    text: step.distance_m > 0 ? `${step.text}. Walk ${Math.round(step.distance_m)} m (about ${Math.max(1, Math.round(step.duration_s / 60))} min).` : step.text,
    kind: step.kind,
  })) : [];
  const geometry = routeGeometry(route.geometry.coordinates);
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
    amenities = []
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
    for (const item of journeyItems(route, amenities)) {
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

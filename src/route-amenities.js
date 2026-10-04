import {
  nearbyFeatures,
  coordinateAtFraction
} from './route-planner-data.js';

export function routeAmenities(route, data, settings, indoorPlaces = []) {
  if (!route || !data) return [];
  const fountains = nearbyFeatures(route, data.fountains.features, settings.fountain_buffer_metres);
  const rests = nearbyFeatures(route, data.rest_stops.features, settings.rest_buffer_metres);
  const indoor = nearbyFeatures(route, indoorPlaces, settings.rest_buffer_metres);
  return [...fountains, ...rests, ...indoor].sort((a, b) => a.fraction - b.fraction);
}

export function plannedRestStops(route, durationSeconds, intervalMinutes = 15) {
  if (!route || !Number.isFinite(durationSeconds) || durationSeconds <= 0) return [];
  const stops = [];
  for (let minutes = intervalMinutes; minutes * 60 < durationSeconds; minutes += intervalMinutes) {
    const fraction = minutes * 60 / durationSeconds;
    stops.push({
      fraction,
      walk_minutes: minutes,
      coordinates: coordinateAtFraction(route, fraction)
    });
  }
  return stops;
}

export function amenityLabel(feature) {
  return feature.kind === 'fountain' ? 'WATER' : feature.rest_type === 'bench' ? 'BENCH' : feature.rest_type === 'indoor' ? feature.label : 'REST';
}

const REST_CANDIDATE_RADIUS_METRES = 150;
const ROUTE_CANDIDATE_BUFFER_METRES = 50;

// Keep guide candidates near a planned pause, not at every point along the walk.
export function amenitiesAtRestStops(route, durationSeconds, amenities, radiusMetres = REST_CANDIDATE_RADIUS_METRES) {
  const stops = plannedRestStops(route, durationSeconds).map(stop => ({
    ...stop,
    amenities: []
  }));
  for (const item of amenities) {
    if (item.feature.kind !== 'fountain' && item.feature.rest_type !== 'bench') continue;
    if (!Number.isFinite(item.fraction) || !Number.isFinite(item.distance) || item.distance > ROUTE_CANDIDATE_BUFFER_METRES) continue;
    const nearest = [...stops].sort((a, b) => Math.abs(a.fraction - item.fraction) - Math.abs(b.fraction - item.fraction))[0];
    if (nearest && Math.abs(nearest.fraction - item.fraction) * route.length <= radiusMetres) nearest.amenities.push(item);
  }
  return stops;
}

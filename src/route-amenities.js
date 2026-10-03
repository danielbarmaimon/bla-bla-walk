import {
  nearbyFeatures
} from './route-planner-data.js';

export function routeAmenities(route, data, settings, indoorPlaces = []) {
  if (!route || !data) return [];
  const fountains = nearbyFeatures(route, data.fountains.features, settings.fountain_buffer_metres);
  const rests = nearbyFeatures(route, data.rest_stops.features, settings.rest_buffer_metres);
  const indoor = nearbyFeatures(route, indoorPlaces, settings.rest_buffer_metres);
  return [...fountains, ...rests, ...indoor].sort((a, b) => a.fraction - b.fraction);
}

export function amenityLabel(feature) {
  return feature.kind === 'fountain' ? 'WATER' : feature.rest_type === 'bench' ? 'BENCH' : 'REST';
}

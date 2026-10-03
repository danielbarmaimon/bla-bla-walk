import { coordinateAtFraction, positionAlongRoute } from './route-data.js';

// OSM feature centres checked 2026-10-03. Proximity does not prove visibility.
export const WAYFINDING_PLACES = [
  {
    id: 'barfuesserplatz', label: 'Barfüsserplatz', type: 'node',
    coordinates: [7.5890461, 47.5548988],
    sourceUrl: 'https://www.openstreetmap.org/way/132752251',
    note: 'Square on the route; a wayfinding node.',
  },
  {
    id: 'stadtcasino', label: 'Stadtcasino Basel', type: 'landmark',
    coordinates: [7.5901346, 47.5542438],
    sourceUrl: 'https://www.openstreetmap.org/way/147634462',
    note: 'Nearby building; visibility from the path is unverified.',
  },
  {
    id: 'barfuesserkirche', label: 'Barfüsserkirche', type: 'landmark',
    coordinates: [7.5905029, 47.5544915],
    sourceUrl: 'https://www.openstreetmap.org/way/137472263',
    note: 'Nearby church; visibility from the path is unverified.',
  },
];

export const COOL_PLACES = [
  {
    id: 'foyer-public', label: 'Theater Basel · Foyer Public',
    coordinates: [7.5902308, 47.5527602],
    sourceUrl: 'https://www.bs.ch/it/node/31069',
    operatorUrl: 'https://www.theater-basel.ch/de/foyerpublic',
    note: 'Public indoor rest candidate. Check today’s hours. Air conditioning unverified.',
  },
];

export function routeStops(route, fountains) {
  const restFraction = positionAlongRoute(route, WAYFINDING_PLACES[0].coordinates).fraction;
  const water = fountains.find((item) => item.fraction > restFraction && item.distance <= 25);
  const stops = [
    {
      type: 'rest', label: 'Rest', fraction: restFraction,
      coordinates: coordinateAtFraction(route, restFraction),
      note: 'Optional rest at Barfüsserplatz. Seating is unverified.',
    },
  ];
  if (water) stops.push({
    type: 'water', label: 'Fountain', fraction: water.fraction,
    coordinates: coordinateAtFraction(route, water.fraction),
    note: `${water.feature.label}, ${Math.round(water.distance)} m off route. Drinking and operation unknown.`,
    sourceFeature: water.feature,
  });
  stops.push({
    type: 'pause', label: 'Pause', fraction: 0.93,
    coordinates: coordinateAtFraction(route, 0.93),
    note: 'Optional pause before Marktplatz. Seating is unverified.',
  });
  return stops.sort((a, b) => a.fraction - b.fraction);
}

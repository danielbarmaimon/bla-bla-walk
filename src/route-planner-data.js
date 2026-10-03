// Route proximity calculations for the checked SBB → Marktplatz alternatives.
export const FOUNTAIN_BUFFER_M = 50;
export const SENSOR_BUFFER_M = 250;
const METRES_PER_DEGREE = 111_320;

function metrePoint(coordinates, latitude) {
  return [
    coordinates[0] * METRES_PER_DEGREE * Math.cos(latitude * Math.PI / 180),
    coordinates[1] * METRES_PER_DEGREE,
  ];
}

export function routeGeometry(coordinates) {
  const latitude = coordinates.reduce((sum, point) => sum + point[1], 0) / coordinates.length;
  const points = coordinates.map((point) => metrePoint(point, latitude));
  const cumulative = [0];
  for (let index = 1; index < points.length; index += 1) {
    cumulative.push(cumulative[index - 1] + Math.hypot(
      points[index][0] - points[index - 1][0],
      points[index][1] - points[index - 1][1],
    ));
  }
  return {
    coordinates,
    points,
    cumulative,
    length: cumulative.at(-1),
    latitude
  };
}

export function positionAlongRoute(route, coordinates) {
  const point = metrePoint(coordinates, route.latitude);
  let closest = {
    distance: Infinity,
    fraction: 0
  };
  for (let index = 1; index < route.points.length; index += 1) {
    const a = route.points[index - 1];
    const b = route.points[index];
    const dx = b[0] - a[0];
    const dy = b[1] - a[1];
    const squared = dx * dx + dy * dy;
    const along = squared ? Math.max(0, Math.min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / squared)) : 0;
    const distance = Math.hypot(point[0] - a[0] - along * dx, point[1] - a[1] - along * dy);
    if (distance < closest.distance) {
      closest = {
        distance,
        fraction: (route.cumulative[index - 1] + Math.sqrt(squared) * along) / route.length,
      };
    }
  }
  return closest;
}

export function nearbyFeatures(route, features, metres) {
  return features.flatMap((feature) => {
    if (feature.geometry?.type !== 'Point') return [];
    const position = positionAlongRoute(route, feature.geometry.coordinates);
    return position.distance <= metres ? [{
      feature,
      ...position
    }] : [];
  }).sort((a, b) => a.fraction - b.fraction);
}

export function coordinateAtFraction(route, fraction) {
  const target = Math.max(0, Math.min(1, fraction)) * route.length;
  for (let index = 1; index < route.cumulative.length; index += 1) {
    if (target <= route.cumulative[index]) {
      const distance = route.cumulative[index] - route.cumulative[index - 1];
      const share = distance ? (target - route.cumulative[index - 1]) / distance : 0;
      return route.coordinates[index - 1].map((value, axis) =>
        value + (route.coordinates[index][axis] - value) * share);
    }
  }
  return route.coordinates.at(-1);
}

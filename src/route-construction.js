import {
  routeGeometry,
  coordinateAtFraction
} from './route-planner-data.js';

export function constructionMarkers(routes, snapshot, day, settings) {
  if (!snapshot?.provenance || !snapshot.covers_from || day < snapshot.covers_from) return [];
  const {
    fromLonLat,
    toLonLat
  } = window.ol.proj;
  // Local metric projection; samples keep the check bounded on long routes.
  const points = routes.flatMap(feature => {
    const route = routeGeometry(feature.geometry.coordinates);
    const count = Math.max(1, Math.ceil(route.length / settings.route_sample_metres));
    return Array.from({
      length: count + 1
    }, (_, index) => {
      const coordinate = coordinateAtFraction(route, index / count);
      return {
        position: fromLonLat(coordinate),
        scale: Math.cos(coordinate[1] * Math.PI / 180)
      };
    });
  });
  if (!points.length) return [];
  const routeExtent = window.ol.extent.buffer(window.ol.extent.boundingExtent(points.map(point => point.position)), settings.near_route_metres / Math.min(...points.map(point => point.scale)));
  return snapshot.sites.filter(site => site.starts_on <= day && day <= site.ends_on).flatMap(site => {
    const polygon = new window.ol.geom.Polygon(site.geometry.coordinates.map(ring => ring.map(point => fromLonLat(point))));
    if (!window.ol.extent.intersects(routeExtent, polygon.getExtent())) return [];
    let closest = null;
    for (const {
        position,
        scale
      }
      of points) {
      const inside = polygon.intersectsCoordinate(position);
      const point = inside ? position : polygon.getClosestPoint(position);
      // Correct Web Mercator lengths for Basel latitude.
      const distance = Math.hypot(position[0] - point[0], position[1] - point[1]) * scale;
      if (!closest || distance < closest.distance) closest = {
        distance,
        point
      };
    }
    if (!closest || closest.distance > settings.near_route_metres) return [];
    return [{
      kind: 'construction',
      label: '',
      coordinates: toLonLat(closest.point),
      sourceFeature: {
        id: `construction-${site.id}`,
        kind: 'construction',
        label: 'Mapped construction site',
        geometry: site.geometry,
        availability: snapshot.availability,
        provenance: snapshot.provenance,
        explanation: `Project ${site.project_id} · mapped interval ${site.starts_on}–${site.ends_on}. ${snapshot.availability === 'current' ? 'Daily snapshot' : 'Saved / stale snapshot'} retrieved ${snapshot.provenance.retrieved_at}. Near a displayed route; pedestrian closure and access are unverified.`
      }
    }];
  });
}

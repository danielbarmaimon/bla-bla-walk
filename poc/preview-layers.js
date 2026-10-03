import { coordinateAtFraction, exampleTemperature } from './route-data.js';

export function exampleHeatFeatures(ol, route) {
  return Array.from({ length: 17 }, (_, index) => index / 16).map((fraction) => {
    const point = new ol.Feature(new ol.geom.Point(
      ol.proj.fromLonLat(coordinateAtFraction(route, fraction)),
    ));
    point.set('weight', Math.max(0.15, (exampleTemperature(fraction) - 22) / 30));
    return point;
  });
}

export function exampleShadowFeatures(ol, route) {
  return [0.27, 0.71].map((fraction) => {
    const circle = new ol.Feature(new ol.geom.Circle(
      ol.proj.fromLonLat(coordinateAtFraction(route, fraction)), 55,
    ));
    circle.set('kind', 'example-shadow');
    return circle;
  });
}

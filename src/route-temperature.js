import {
  routeGeometry,
  coordinateAtFraction
} from './route-planner-data.js';

// Exploratory inverse-distance weighting; never add shade/PET cooling offsets.
export function sensorCohort(features, settings, now = Date.now()) {
  const valid = features.filter(sensor => sensor.kind === 'observation' &&
    !sensor.provenance.fixture && Number.isFinite(sensor.value) && sensor.unit === '°C' &&
    sensor.geometry.type === 'Point' && sensor.availability !== 'missing' &&
    Number.isFinite(Date.parse(sensor.provenance.observed_at)) &&
    Date.parse(sensor.provenance.observed_at) <= now + settings.future_tolerance_minutes * 60000);
  const latest = Math.max(...valid.map(sensor => Date.parse(sensor.provenance.observed_at)));
  return valid.filter(sensor => latest - Date.parse(sensor.provenance.observed_at) <= settings.alignment_minutes * 60000);
}

export function estimateTemperature(coordinates, sensors, settings) {
  const near = sensors.map(sensor => ({
      sensor,
      distance: routeGeometry([coordinates, sensor.geometry.coordinates]).length
    })).filter(item => item.distance <= settings.radius_metres)
    .sort((a, b) => a.distance - b.distance).slice(0, settings.nearest_sensors);
  if (near.length < settings.minimum_sensors) return null;
  const weights = near.map(item => 1 / Math.max(1, item.distance) ** 2);
  return {
    value: near.reduce((sum, item, index) => sum + item.sensor.value * weights[index], 0) /
      weights.reduce((sum, value) => sum + value, 0),
    sensors: near.map(item => item.sensor)
  };
}

export function temperatureProfile(route, layer, settings, now = Date.now()) {
  const sensors = sensorCohort(layer?.features ?? [], settings, now);
  const count = route ? Math.min(settings.max_segments, Math.max(1, Math.ceil(route.length / settings.step_metres))) : 0;
  const segments = Array.from({
    length: count
  }, (_, index) => {
    const start = index / count,
      end = (index + 1) / count;
    const estimate = estimateTemperature(coordinateAtFraction(route, (start + end) / 2), sensors, settings);
    return {
      start,
      end,
      estimate
    };
  });
  const values = segments.filter(item => item.estimate).map(item => item.estimate.value);
  if (!values.length) return {
    segments,
    sensors,
    coverage: 0
  };
  const minimum = Math.min(...values),
    maximum = Math.max(...values);
  const span = Math.max(settings.minimum_span_c, maximum - minimum);
  const centre = (minimum + maximum) / 2;
  const used = [...new Map(segments.flatMap(item => item.estimate?.sensors ?? []).map(sensor => [sensor.id, sensor])).values()];
  return {
    segments,
    sensors: used,
    minimum,
    maximum,
    low: centre - span / 2,
    high: centre + span / 2,
    coverage: values.length / count,
    stale: used.some(sensor => sensor.availability !== 'current' ||
      now - Date.parse(sensor.provenance.observed_at) > settings.current_age_minutes * 60000),
    oldest: Math.min(...used.map(sensor => Date.parse(sensor.provenance.observed_at))),
    latest: Math.max(...used.map(sensor => Date.parse(sensor.provenance.observed_at)))
  };
}

export function temperatureColour(value, low, high, palette) {
  const fraction = Math.max(0, Math.min(1, (value - low) / (high - low)));
  const position = fraction * (palette.length - 1);
  const index = Math.min(palette.length - 2, Math.floor(position));
  const share = position - index;
  const rgb = hex => [1, 3, 5].map(start => parseInt(hex.slice(start, start + 2), 16));
  const a = rgb(palette[index]),
    b = rgb(palette[index + 1]);
  return '#' + a.map((value, axis) => Math.round(value + (b[axis] - value) * share).toString(16).padStart(2, '0')).join('');
}

export function validateSensorInterpolation(layer, settings, now = Date.now()) {
  const sensors = sensorCohort(layer.features, settings, now);
  const errors = sensors.flatMap(sensor => {
    const estimate = estimateTemperature(sensor.geometry.coordinates, sensors.filter(other => other.id !== sensor.id), settings);
    return estimate ? [Math.abs(estimate.value - sensor.value)] : [];
  });
  return {
    count: errors.length,
    total: sensors.length,
    meanAbsoluteError: errors.length ? errors.reduce((sum, value) => sum + value, 0) / errors.length : null
  };
}

import {
  temperatureProfile,
  combinedTemperatureProfile,
  temperatureColour,
  validateSensorInterpolation
} from './route-temperature.js';
import {
  badgeActive
} from './layer-badges.js';

const $ = selector => document.querySelector(selector);
const baselDate = date => new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Europe/Zurich',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit'
}).format(date);
const baselDay = () => baselDate(new Date());

export function chooseTemperaturePalette(profile, forecast, settings, day, choice = 'auto', today = baselDay()) {
  if (choice !== 'auto') return {
    name: choice,
    reason: 'Manual display palette'
  };
  let value, reason;
  if (profile.coverage && !profile.stale && day === today) {
    value = (profile.minimum + profile.maximum) / 2;
    reason = 'Current sensor estimates';
  } else if (Number.isFinite(forecast?.days?.[day])) {
    value = forecast.days[day];
    reason = `${forecast.availability==='current'?'Forecast':'Saved forecast'} daily mean for ${day}: ${value.toFixed(1)} °C · Open-Meteo`;
  } else if (profile.coverage) {
    value = (profile.minimum + profile.maximum) / 2;
    reason = 'Saved sensor estimates; day forecast unavailable';
  } else return {
    name: 'summer',
    reason: 'Sensor temperature and day forecast unavailable; no coloured estimates'
  };
  return {
    name: value < settings.winter_below_c ? 'winter' : 'summer',
    reason
  };
}

export function nearestForecastHour(forecast, arrivalTime) {
  if (forecast?.availability !== 'current' || !(arrivalTime instanceof Date) ||
    !Number.isFinite(arrivalTime.getTime())) return null;
  let nearest = null;
  let nearestDifference = 30 * 60 * 1000;
  for (const hour of forecast.hours ?? []) {
    const timestamp = Date.parse(hour.valid_time);
    if (!Number.isFinite(timestamp) || !Number.isFinite(hour.temperature_c)) continue;
    const difference = Math.abs(timestamp - arrivalTime.getTime());
    if (difference <= nearestDifference) {
      nearest = {
        value: hour.temperature_c,
        validTime: new Date(timestamp)
      };
      nearestDifference = difference;
    }
  }
  return nearest;
}

export async function routeTemperatureView(map, mode, onUpdate, onSensors = () => {}) {
  const settings = await fetch('/config/route-temperature.json').then(reply => reply.json());
  let layer = null,
    forecast = null,
    loading = true,
    forecastRequested = false;
  let validation = null;

  function requestForecast() {
    if (forecastRequested) return;
    forecastRequested = true;
    fetch(`/api/palette-forecast?mode=${encodeURIComponent(mode)}`).then(reply => {
      if (!reply.ok) throw new Error('Forecast unavailable');
      return reply.json();
    }).then(data => {
      forecast = data;
    }).catch(() => {
      forecast = null;
    }).finally(onUpdate);
  }
  const theme = getComputedStyle(document.documentElement);
  const colour = name => theme.getPropertyValue(`--temperature-${name}`).trim();
  const palettes = {
    summer: [colour('summer-cold'), colour('summer-middle'), colour('summer-warm')],
    winter: [colour('winter-cold'), colour('winter-warm')]
  };
  fetch(`/api/route-temperatures?mode=${encodeURIComponent(mode)}`).then(reply => {
    if (!reply.ok) throw Error('Sensor data unavailable');
    return reply.json();
  }).then(data => {
    layer = data;
    onSensors(data);
    validation = validateSensorInterpolation(data, settings);
  }).catch(() => {
    layer = null;
  }).finally(() => {
    loading = false;
    onUpdate();
  });
  $('#temperature-palette').addEventListener('change', onUpdate);

  return {
    render(routes, selectedRouteId) {
      const profiles = routes.map(({
        id,
        route
      }) => ({
        id,
        route,
        profile: temperatureProfile(route, layer, settings)
      }));
      const profile = combinedTemperatureProfile(profiles.map(item => item.profile), settings);
      const day = $('#departure-time').value.slice(0, 10) || baselDay();
      const choice = $('#temperature-palette').value;
      if (routes.length) requestForecast();
      const selected = chooseTemperaturePalette(profile, forecast, settings, day, choice);
      const palette = palettes[selected.name];
      const visible = badgeActive('#temperature-route-toggle');
      map.setTemperatureProfiles(profiles.map(item => ({
        ...item,
        colours: item.profile.segments.map(segment => segment.estimate ? temperatureColour(segment.estimate.value, profile.low, profile.high, palette) : theme.getPropertyValue('--unknown').trim())
      })), visible);
      const legend = $('#temperature-legend');
      legend.replaceChildren();
      const status = document.createElement('p');
      status.textContent = loading ? 'Loading real sensor readings…' : !routes.length ? 'Show a route to see sensor temperature estimates.' : profile.coverage ?
        `${profile.stale?'SAVED / STALE':'Current'} sensor-based estimate: ${profile.minimum.toFixed(1)}–${profile.maximum.toFixed(1)} °C · ${Math.round(profile.coverage*100)}% of visible paths covered · ${profile.sensors.length} contributing sensors · ${selected.name} palette. ${selected.reason}.` :
        `Route temperature unavailable: fewer than ${settings.minimum_sensors} time-aligned sensors within ${settings.radius_metres} m. ${selected.reason}.`;
      legend.append(status);
      if (profile.coverage) {
        const ramp = document.createElement('div');
        ramp.className = 'temperature-ramp';
        ramp.style.background = `linear-gradient(to right,${palette.join(',')})`;
        const range = document.createElement('p');
        range.textContent = `Colder ${profile.low.toFixed(1)} °C → warmer ${profile.high.toFixed(1)} °C · shared scale for all visible routes, minimum ${settings.minimum_span_c} °C span`;
        const detail = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = 'Temperature method, sensor times and sources';
        detail.append(summary);
        const method = document.createElement('p');
        method.textContent = `Exploratory inverse-distance-squared estimate from up to ${settings.nearest_sensors} sensors within ${settings.radius_metres} m, aligned within ${settings.alignment_minutes} minutes. No shade cooling or PET adjustment. Raw uncorrected readings; street temperature accuracy unverified. Withheld-station check: ${validation?.count ?? 0}/${validation?.total ?? 0} stations supported${validation?.meanAbsoluteError==null?'':`, mean absolute error ${validation.meanAbsoluteError.toFixed(2)} °C`}; this is not independent field validation.`;
        detail.append(method);
        const list = document.createElement('ul');
        profile.sensors.forEach(sensor => {
          const item = document.createElement('li');
          item.textContent = `${sensor.label}: ${sensor.value.toFixed(1)} °C · observed ${sensor.provenance.observed_at} · retrieved ${sensor.provenance.retrieved_at ?? 'unknown'} · ${sensor.provenance.attribution} · ${sensor.provenance.licence}`;
          list.append(item);
        });
        detail.append(list);
        const link = document.createElement('a');
        link.href = 'https://data.bs.ch/explore/dataset/100009/';
        link.textContent = 'meteoblue observations via Open Data Basel-Stadt · CC BY 4.0';
        detail.append(link);
        legend.append(ramp, range, detail);
      }
      if (forecast?.provenance) {
        const link = document.createElement('a');
        link.href = forecast.provenance.source_url;
        link.textContent = `${forecast.availability === 'stale' ? 'Saved ' : ''}Weather data by Open-Meteo · CC BY 4.0 · fixed Basel point · retrieved ${forecast.provenance.retrieved_at}`;
        legend.append(link);
      }
      return profiles.find(item => item.id === selectedRouteId)?.profile ?? null;
    },
    forecastForArrival(date) {
      if (!(date instanceof Date) || !Number.isFinite(date.getTime())) return null;
      const nearest = nearestForecastHour(forecast, date);
      return {
        value: nearest?.value ?? null,
        validTime: nearest?.validTime ?? null,
        availability: forecast?.availability ?? 'missing'
      };
    }
  };
}

export function showRouteTemperature(sample) {
  const element = $('#temperature-sample');
  element.replaceChildren();
  const heading = document.createElement('strong');
  heading.textContent = `Estimated air temperature here: ${sample.value.toFixed(1)} °C`;
  const details = document.createElement('p');
  details.textContent = 'Interpolated from ' + sample.sensors.map(sensor => `${sensor.label} (${sensor.value.toFixed(1)} °C at ${sensor.provenance.observed_at})`).join(', ') + '. Raw sensor readings; this point is not measured.';
  element.append(heading, details);
}

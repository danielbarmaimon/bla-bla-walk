import {
  temperatureProfile,
  temperatureColour,
  validateSensorInterpolation
} from './route-temperature.js';

const $ = selector => document.querySelector(selector);
const baselDay = () => new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Europe/Zurich',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit'
}).format(new Date());

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

export async function routeTemperatureView(map, mode, onUpdate) {
  const settings = await fetch('/config/route-temperature.json').then(reply => reply.json());
  let layer = null,
    forecast = null,
    loading = true,
    forecastRequested = false;
  let validation = null;
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
    validation = validateSensorInterpolation(data, settings);
  }).catch(() => {
    layer = null;
  }).finally(() => {
    loading = false;
    onUpdate();
  });
  ['temperature-route-toggle', 'temperature-palette'].forEach(id => $('#' + id).addEventListener('change', onUpdate));

  return {
    render(route) {
      const profile = temperatureProfile(route, layer, settings);
      const day = $('#departure-time').value.slice(0, 10) || baselDay();
      const choice = $('#temperature-palette').value;
      if (choice === 'auto' && (!profile.coverage || profile.stale || day !== baselDay()) && !loading && !forecastRequested) {
        forecastRequested = true;
        fetch(`/api/palette-forecast?mode=${encodeURIComponent(mode)}`).then(reply => reply.json()).then(data => {
          forecast = data;
        }).catch(() => {
          forecast = null;
        }).finally(onUpdate);
      }
      const selected = chooseTemperaturePalette(profile, forecast, settings, day, choice);
      const palette = palettes[selected.name];
      const visible = $('#temperature-route-toggle').checked;
      map.setTemperatureProfile(route, profile, profile.segments.map(item => item.estimate ? temperatureColour(item.estimate.value, profile.low, profile.high, palette) : theme.getPropertyValue('--unknown').trim()), visible);
      const legend = $('#temperature-legend');
      legend.replaceChildren();
      const status = document.createElement('p');
      status.textContent = loading ? 'Loading real sensor readings…' : !route ? 'Select a route to see sensor temperature estimates.' : profile.coverage ?
        `${profile.stale?'SAVED / STALE':'Current'} sensor-based estimate: ${profile.minimum.toFixed(1)}–${profile.maximum.toFixed(1)} °C · ${Math.round(profile.coverage*100)}% of selected route covered · ${profile.sensors.length} contributing sensors · ${selected.name} palette. ${selected.reason}.` :
        `Route temperature unavailable: fewer than ${settings.minimum_sensors} time-aligned sensors within ${settings.radius_metres} m. ${selected.reason}.`;
      legend.append(status);
      if (profile.coverage) {
        const ramp = document.createElement('div');
        ramp.className = 'temperature-ramp';
        ramp.style.background = `linear-gradient(to right,${palette.join(',')})`;
        const range = document.createElement('p');
        range.textContent = `Colder ${profile.low.toFixed(1)} °C → warmer ${profile.high.toFixed(1)} °C · relative scale, minimum ${settings.minimum_span_c} °C span`;
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
        link.textContent = `Weather data by Open-Meteo · CC BY 4.0 · palette only · retrieved ${forecast.provenance.retrieved_at}`;
        legend.append(link);
      }
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

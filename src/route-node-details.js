export const MAX_VISIBLE_ROUTE_POINTS = 48;
const ROUTE_POINT_HIT_RADIUS = 56;

function supportedShadePercentage(evidence, startMetres, endMetres) {
  if (!evidence || evidence.shade_state !== 'current' ||
      !evidence.shade_time_matches_request || !evidence.shade_geometry_matches_request ||
      !Number.isFinite(startMetres) || !Number.isFinite(endMetres) || endMetres <= startMetres) return null;

  const samples = evidence.samples
    .filter(sample => sample.end_metres > startMetres && sample.start_metres < endMetres)
    .map(sample => ({
      ...sample,
      overlap: Math.max(0, Math.min(endMetres, sample.end_metres) - Math.max(startMetres, sample.start_metres))
    }))
    .filter(sample => sample.overlap > 0)
    .sort((a, b) => a.start_metres - b.start_metres);
  let covered = 0;
  let shaded = 0;
  let cursor = startMetres;
  for (const sample of samples) {
    const overlapStart = Math.max(startMetres, sample.start_metres);
    if (overlapStart > cursor + 0.01 || ![1, 2].includes(sample.state)) return null;
    const overlapEnd = Math.min(endMetres, sample.end_metres);
    const length = overlapEnd - Math.max(cursor, overlapStart);
    if (length <= 0) continue;
    covered += length;
    if (sample.state === 2) shaded += length;
    cursor = overlapEnd;
  }
  if (cursor < endMetres - 0.01 || covered < endMetres - startMetres - 0.01) return null;
  return shaded / covered * 100;
}

export function routePointDetails(route, profile, evidence, fraction, departureTime) {
  const segments = profile?.segments ?? [];
  const index = Math.min(segments.length - 1, Math.floor(fraction * segments.length));
  const temperature = segments[index]?.estimate?.value;
  const distance = route?.route?.distance_m;
  const duration = route?.route?.duration_s;
  const departureMilliseconds = new Date(departureTime).getTime();
  const arrivalTime = Number.isFinite(duration) && duration >= 0 && Number.isFinite(departureMilliseconds) ?
    new Date(departureMilliseconds + duration * fraction * 1000) : null;
  const startMetres = Number.isFinite(distance) ? distance * (index / Math.max(1, segments.length)) : null;
  const endMetres = Number.isFinite(distance) ? distance * ((index + 1) / Math.max(1, segments.length)) : null;
  return {
    temperature: Number.isFinite(temperature) ? temperature : null,
    arrivalTime,
    remainingMetres: Number.isFinite(distance) && distance >= 0 ? distance * (1 - fraction) : null,
    remainingSeconds: Number.isFinite(duration) && duration >= 0 ? duration * (1 - fraction) : null,
    shadePercentage: supportedShadePercentage(evidence, startMetres, endMetres)
  };
}

export function mountRouteNodeDetails(mapWrap, sliderHost) {
  const card = document.createElement('section');
  card.className = 'route-node-card';
  card.hidden = true;
  card.setAttribute('aria-labelledby', 'route-node-title');
  card.setAttribute('aria-live', 'polite');
  mapWrap.append(card);
  const pointTargets = document.createElement('div');
  pointTargets.className = 'route-node-targets';
  pointTargets.setAttribute('aria-hidden', 'true');
  mapWrap.append(pointTargets);

  const label = document.createElement('label');
  label.className = 'route-node-slider-label';
  label.textContent = 'Inspect route point';
  const slider = document.createElement('input');
  slider.type = 'range';
  slider.min = '0';
  slider.max = '0';
  slider.value = '0';
  slider.disabled = true;
  slider.setAttribute('aria-describedby', 'route-node-help');
  label.append(slider);
  sliderHost.replaceChildren(label);
  const help = document.createElement('p');
  help.id = 'route-node-help';
  help.className = 'route-node-help';
  help.textContent = 'Focus the slider, then use the arrow keys to inspect route sections.';
  sliderHost.append(help);

  let selected = null;
  let activeRouteId = null;
  let latest = null;
  let cardHovered = false;
  let pointHovered = false;
  card.addEventListener('pointerenter', () => { cardHovered = true; });
  card.addEventListener('pointerleave', () => {
    setTimeout(() => {
      cardHovered = false;
      if (!pointHovered && selected?.source === 'hover') dismiss();
    }, 0);
  });

  function nearestPointTarget(clientX, clientY) {
    let nearest = null;
    let nearestDistance = ROUTE_POINT_HIT_RADIUS;
    pointTargets.querySelectorAll('.route-node-target:not([hidden])').forEach(target => {
      const bounds = target.getBoundingClientRect();
      const distance = Math.hypot(clientX - (bounds.left + bounds.width / 2),
        clientY - (bounds.top + bounds.height / 2));
      if (distance <= nearestDistance) {
        nearest = target;
        nearestDistance = distance;
      }
    });
    return nearest;
  }

  function handlePointerMove(event) {
    if (event.pointerType === 'touch' || event.target.closest('.route-node-card')) return;
    if (event.target.closest('.ol-control, .map-overlay, .map-pick-banner')) {
      pointHovered = false;
      if (selected?.source === 'hover') dismiss();
      return;
    }
    const target = nearestPointTarget(event.clientX, event.clientY);
    pointHovered = Boolean(target);
    if (!target) {
      if (!cardHovered && selected?.source === 'hover') dismiss();
      return;
    }
    const fraction = Number(target.dataset.fraction);
    if (selected?.source === 'hover' && selected.fraction === fraction) return;
    select(fraction, latest?.pixelForFraction?.(fraction), 'hover');
  }

  function formatDetails(fraction) {
    const detail = routePointDetails(latest.route, latest.profile, latest.evidence, fraction, latest.departureTime);
    card.replaceChildren();
    const heading = document.createElement('h3');
    heading.id = 'route-node-title';
    heading.textContent = `Route point · ${Math.round(fraction * 100)}%`;
    const list = document.createElement('dl');
    const arrivalLabel = detail.arrivalTime ?
      new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(detail.arrivalTime) : null;
    const rows = [
      ['Temperature', arrivalLabel ? `Unavailable · no hourly forecast for ~${arrivalLabel} arrival` : 'Unavailable · arrival-time forecast unavailable'],
      ['Distance left', detail.remainingMetres == null ? 'Unavailable' : `${Math.round(detail.remainingMetres)} m`],
      ['ETA', detail.remainingSeconds == null ? 'Unavailable' : `in ${Math.round(detail.remainingSeconds / 60)} min`]
    ];
    if (detail.shadePercentage != null) rows.push(['Local segment shadow', `${Math.round(detail.shadePercentage)}% (sampled estimate)`]);
    rows.forEach(([term, value]) => {
      const dt = document.createElement('dt');
      dt.textContent = term;
      const dd = document.createElement('dd');
      dd.textContent = value;
      list.append(dt, dd);
    });
    card.append(heading, list);
    card.hidden = false;
  }

  function dismiss() {
    selected = null;
    card.hidden = true;
  }

  function select(fraction, pixel, source = 'selection') {
    if (!latest || !Number.isFinite(fraction)) return;
    selected = { fraction, pixel, source };
    const closest = latest.pointFractions.reduce((best, item, index) =>
      Math.abs(item - fraction) < Math.abs(latest.pointFractions[best] - fraction) ? index : best, 0);
    slider.value = String(closest);
    formatDetails(fraction);
    positionCard(pixel);
  }

  function positionPoints() {
    if (!latest) return;
    const mapBounds = mapWrap.querySelector('#map').getBoundingClientRect();
    const wrapBounds = mapWrap.getBoundingClientRect();
    pointTargets.querySelectorAll('.route-node-target').forEach(target => {
      const pixel = latest.pixelForFraction?.(Number(target.dataset.fraction));
      if (!pixel) {
        target.hidden = true;
        return;
      }
      target.hidden = pixel[0] < -16 || pixel[1] < -16 ||
        pixel[0] > mapBounds.width + 16 || pixel[1] > mapBounds.height + 16;
      target.style.left = `${mapBounds.left - wrapBounds.left + pixel[0]}px`;
      target.style.top = `${mapBounds.top - wrapBounds.top + pixel[1]}px`;
    });
  }

  function positionCard(pixel) {
    if (!pixel) return;
    const bounds = mapWrap.getBoundingClientRect();
    const cardBounds = card.getBoundingClientRect();
    const mapBounds = mapWrap.querySelector('#map').getBoundingClientRect();
    const pointX = mapBounds.left - bounds.left + pixel[0];
    const pointY = mapBounds.top - bounds.top + pixel[1];
    const candidates = [
      [pointX + 24, pointY + 24],
      [pointX - cardBounds.width - 24, pointY + 24],
      [pointX + 24, pointY - cardBounds.height - 24],
      [pointX - cardBounds.width - 24, pointY - cardBounds.height - 24]
    ].map(([left, top]) => [
      Math.max(8, Math.min(bounds.width - cardBounds.width - 8, left)),
      Math.max(8, Math.min(bounds.height - cardBounds.height - 8, top))
    ]);
    const obstacles = [...mapWrap.querySelectorAll('.ol-control, .map-overlay:not([hidden]), .map-pick-banner:not([hidden])')]
      .map(element => {
        const rect = element.getBoundingClientRect();
        return {
          left: rect.left - bounds.left,
          top: rect.top - bounds.top,
          right: rect.right - bounds.left,
          bottom: rect.bottom - bounds.top
        };
      });
    const [left, top] = candidates.sort((a, b) => {
      const score = ([x, y]) => {
        const overlap = obstacles.filter(item => x < item.right && x + cardBounds.width > item.left &&
          y < item.bottom && y + cardBounds.height > item.top).length;
        const distance = Math.hypot(x + cardBounds.width / 2 - pointX, y + cardBounds.height / 2 - pointY);
        return overlap * 10000 - distance;
      };
      return score(a) - score(b);
    })[0];
    card.style.left = `${left}px`;
    card.style.top = `${top}px`;
  }

  slider.addEventListener('focus', () => {
    if (latest && !selected) {
      const fraction = latest.pointFractions[Math.floor(latest.pointFractions.length / 2)];
      select(fraction, latest.pixelForFraction?.(fraction), 'keyboard');
    }
  });
  slider.addEventListener('input', () => {
    if (!latest) return;
    const fraction = latest.pointFractions[Number(slider.value)];
    select(fraction, latest.pixelForFraction?.(fraction), 'keyboard');
  });
  slider.addEventListener('keydown', event => {
    if (event.key === 'Escape' && selected) {
      dismiss();
      slider.blur();
    }
  });

  function attachMap(map) {
    return map.onViewChange(positionPoints);
  }

  mapWrap.addEventListener('pointermove', handlePointerMove);
  mapWrap.addEventListener('pointerleave', () => {
    setTimeout(() => {
      pointHovered = false;
      if (!cardHovered && selected?.source === 'hover') dismiss();
    }, 0);
  });
  mapWrap.addEventListener('click', event => {
    if (event.target.closest('.route-node-card, .ol-control, .map-overlay, .map-pick-banner')) return;
    const target = nearestPointTarget(event.clientX, event.clientY);
    if (!target) {
      if (selected?.source === 'selection') dismiss();
      return;
    }
    event.stopPropagation();
    const fraction = Number(target.dataset.fraction);
    select(fraction, latest?.pixelForFraction?.(fraction), 'selection');
  }, true);

  return {
    update(data) {
      if (activeRouteId !== data.route?.id) dismiss();
      activeRouteId = data.route?.id ?? null;
      latest = data.route ? data : null;
      const count = data.pointFractions?.length ?? 0;
      slider.disabled = !latest || count < 1;
      slider.max = String(Math.max(0, count - 1));
      if (!latest) sliderHost.hidden = true;
      else sliderHost.hidden = false;
      pointTargets.replaceChildren();
      data.pointFractions?.forEach(fraction => {
        const target = document.createElement('button');
        target.type = 'button';
        target.tabIndex = -1;
        target.className = 'route-node-target';
        target.dataset.fraction = String(fraction);
        target.setAttribute('aria-label', `Inspect route point ${Math.round(fraction * 100)}%`);
        pointTargets.append(target);
      });
      positionPoints();
      if (selected && latest) {
        formatDetails(selected.fraction);
        positionCard(latest.pixelForFraction?.(selected.fraction));
      }
    },
    select,
    attachMap,
    dismiss
  };
}

const NUMBER = new Intl.NumberFormat('en-GB', {
  maximumFractionDigits: 0
});

function textElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  return element;
}

function metres(value) {
  return Number.isFinite(value) ? `${NUMBER.format(value)} m` : 'Unknown';
}

function percentage(value) {
  return Number.isFinite(value) ? `${NUMBER.format(value)}%` : 'Unknown';
}

function routeMetrics(route, metrics) {
  const summary = document.createElement('dl');
  summary.className = 'comparison-metrics';
  const entries = [
    ['Walking estimate', `${metres(route.route?.distance_m)} · ${Number.isFinite(route.route?.duration_s) ? `${NUMBER.format(route.route.duration_s / 60)} min` : 'time unknown'}`],
    ['Trip duration', metrics ? `${NUMBER.format(metrics.duration_minutes)} min · ${NUMBER.format(metrics.walking_minutes)} walking + ${NUMBER.format(metrics.stop_minutes)} stop` : 'Unknown · comparison pending'],
    ['Shade / exposed', metrics ? `${metres(metrics.shaded_metres)} shaded (${percentage(metrics.shade_percentage)}) · ${metres(metrics.unshaded_metres)} exposed (${percentage(metrics.unshaded_percentage)})` : 'Unknown · shade not calculated'],
    ['Unknown coverage', metrics ? `${metres(metrics.unknown_metres)} (${percentage(metrics.unknown_percentage)})` : 'Unknown · calculation unavailable'],
    ['Water evidence', metrics?.water_complete ? metrics.water_state?.replaceAll('_', ' ') : 'Unknown · operation, access or freshness unverified']
  ];
  entries.forEach(([label, value]) => {
    summary.append(textElement('dt', '', label), textElement('dd', '', value));
  });
  return summary;
}

/** Render T5 comparison evidence without promoting missing evidence to a claim. */
export function renderTripComparison(container, {
  routes,
  comparison = null,
  preference = 'fastest_overall',
  selectedRouteId,
  chosenRouteId,
  onChoose = () => {},
  onShow = () => {}
}) {
  container.replaceChildren();
  const view = comparison?.[preference];
  const status = textElement(
    'p',
    'comparison-status',
    view ? view.explanation : 'No calculated comparison yet. Inspect routes; eligibility and recommendations remain unknown.'
  );
  status.setAttribute('role', 'status');
  container.append(status);

  routes.forEach((route) => {
    const card = document.createElement('article');
    card.className = 'comparison-card';
    if (route.id === selectedRouteId) card.classList.add('is-selected');
    const heading = document.createElement('div');
    heading.className = 'comparison-card-heading';
    heading.append(textElement('h3', '', route.label));
    if (view?.winner === route.id) heading.append(textElement('strong', '', 'Recommended'));
    const routeStatus = view?.route_statuses?.[route.id] ?? 'comparison pending';
    heading.append(textElement('span', 'route-eligibility', routeStatus.replaceAll('_', ' ')));
    card.append(heading);
    card.append(routeMetrics(route, view?.metrics?.[route.id]));

    if (route.pet) {
      card.append(textElement(
        'p',
        'comparison-historical',
        `Historical PET · ${metres(route.pet.known_distance_m)} classified · ${metres(route.pet.unknown_distance_m)} unknown · ${route.pet.availability}`
      ));
    }
    const reasons = view?.reasons?.[route.id] ?? [];
    if (reasons.length) card.append(textElement('p', 'comparison-reasons', `Cannot recommend: ${reasons.join(', ').replaceAll('_', ' ')}.`));

    const metrics = view?.metrics?.[route.id];
    const samples = metrics?.samples ?? [];
    if (samples.length) {
      const details = document.createElement('details');
      details.append(textElement('summary', '', 'Calculation times, model and sources'));
      details.append(textElement('p', '', `Night: ${metres(metrics.night_metres)}. Route source: ${metrics.provenance?.provider ?? 'unknown'}; ${metrics.provenance?.attribution ?? ''}; ${metrics.provenance?.licence ?? ''}. Retrieved ${metrics.provenance?.retrieved_at ?? 'unknown'}.`));
      const list = document.createElement('ul');
      samples.forEach((sample) => list.append(textElement('li', '', `${metres(sample.start_metres)}–${metres(sample.end_metres)}: ${['unknown', 'sunlit', 'shaded', 'night'][sample.state]}. Requested ${sample.requested_time}; effective ${sample.metadata?.effective_time ?? 'unavailable'}; geometry ${sample.metadata?.geometry_version ?? 'unavailable'}; ${sample.model}. ${sample.explanation}`)));
      details.append(list);
      card.append(details);
    }
    if (view?.contributions?.[route.id]) card.append(textElement('p', '', `Weighted contributions: ${Object.entries(view.contributions[route.id]).map(([name, value]) => `${name} ${value.toFixed(3)}`).join(' · ')}`));
    const actions = document.createElement('div');
    actions.className = 'comparison-actions';
    const show = document.createElement('button');
    show.type = 'button';
    show.dataset.routeId = route.id;
    show.dataset.action = 'show';
    show.className = 'comparison-secondary';
    show.textContent = 'Show on map';
    show.addEventListener('click', () => onShow(route));
    const choose = document.createElement('button');
    choose.type = 'button';
    choose.dataset.routeId = route.id;
    choose.dataset.action = 'choose';
    choose.className = 'comparison-primary';
    choose.textContent = route.id === chosenRouteId ? 'Chosen route' : 'Choose route';
    choose.setAttribute('aria-pressed', String(route.id === chosenRouteId));
    const eligible = view?.manual_choices?.includes(route.id) ?? false;
    choose.disabled = !eligible;
    choose.addEventListener('click', () => onChoose(route));
    actions.append(show, choose);
    card.append(actions);
    container.append(card);
  });
}
